"""Siamese Bi-LSTM model for answer semantic similarity scoring.

This module is intentionally separate from the Sentence-BERT transfer-learning
model and from the TF-IDF + grammar hybrid scorer. It trains directly from the
normal cleaned question JSON by creating in-memory contrastive pairs from the
reference answers. It uses only a learned text vocabulary, an embedding layer,
shared Bi-LSTM encoder weights, and a small regression head to predict a
similarity score in the range [0, 1].
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from torch.utils.data import DataLoader, Dataset, random_split


logger = logging.getLogger(__name__)


@dataclass
class SiameseBiLSTMConfig:
    max_vocab_size: int = 20000
    max_length: int = 96
    min_token_frequency: int = 1
    embedding_dim: int = 128
    hidden_dim: int = 128
    lstm_layers: int = 1
    dropout: float = 0.25
    batch_size: int = 32
    learning_rate: float = 0.001
    validation_split: float = 0.15
    random_seed: int = 42
    epochs: int = 12
    patience: int = 3
    negatives_per_answer: int = 3
    accuracy_tolerance: float = 0.10


class Vocabulary:
    pad_token = "<pad>"
    unknown_token = "<unk>"

    def __init__(self, token_to_id: dict[str, int] | None = None) -> None:
        self.token_to_id = token_to_id or {
            self.pad_token: 0,
            self.unknown_token: 1,
        }

    @property
    def size(self) -> int:
        return len(self.token_to_id)

    def fit(self, texts: Iterable[str], max_size: int, min_frequency: int) -> None:
        counts: dict[str, int] = {}
        for text in texts:
            for token in tokenize(text):
                counts[token] = counts.get(token, 0) + 1

        sorted_tokens = sorted(
            (
                (token, count)
                for token, count in counts.items()
                if count >= min_frequency
            ),
            key=lambda item: (-item[1], item[0]),
        )
        for token, _ in sorted_tokens[: max(0, max_size - self.size)]:
            if token not in self.token_to_id:
                self.token_to_id[token] = len(self.token_to_id)

    def encode(self, text: str, max_length: int) -> tuple[list[int], int]:
        tokens = tokenize(text)[:max_length]
        length = max(1, len(tokens))
        ids = [self.token_to_id.get(token, 1) for token in tokens]
        if not ids:
            ids = [1]
        ids = ids[:max_length]
        ids.extend([0] * (max_length - len(ids)))
        return ids, min(length, max_length)

    def to_dict(self) -> dict[str, int]:
        return dict(self.token_to_id)

    @classmethod
    def from_dict(cls, token_to_id: dict[str, int]) -> "Vocabulary":
        return cls(token_to_id=token_to_id)


def tokenize(text: Any) -> list[str]:
    text = "" if text is None else str(text).lower()
    return re.findall(r"[a-z0-9]+(?:[+#._-][a-z0-9]+)?", text)


class SimilarityPairDataset(Dataset):
    def __init__(
        self,
        records: list[dict[str, Any]],
        vocabulary: Vocabulary,
        max_length: int,
    ) -> None:
        self.records = records
        self.vocabulary = vocabulary
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        record = self.records[index]
        reference_ids, reference_length = self.vocabulary.encode(
            record["reference_answer"],
            self.max_length,
        )
        user_ids, user_length = self.vocabulary.encode(
            record["user_answer"],
            self.max_length,
        )
        return {
            "reference_ids": torch.tensor(reference_ids, dtype=torch.long),
            "reference_length": torch.tensor(reference_length, dtype=torch.long),
            "user_ids": torch.tensor(user_ids, dtype=torch.long),
            "user_length": torch.tensor(user_length, dtype=torch.long),
            "target": torch.tensor(float(record["similarity"]), dtype=torch.float32),
        }


class SiameseBiLSTMNetwork(nn.Module):
    def __init__(self, vocab_size: int, config: SiameseBiLSTMConfig) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, config.embedding_dim, padding_idx=0)
        lstm_dropout = config.dropout if config.lstm_layers > 1 else 0.0
        self.encoder = nn.LSTM(
            input_size=config.embedding_dim,
            hidden_size=config.hidden_dim,
            num_layers=config.lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=lstm_dropout,
        )
        encoded_dim = config.hidden_dim * 2
        comparison_dim = encoded_dim * 4
        self.regressor = nn.Sequential(
            nn.Linear(comparison_dim, encoded_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(encoded_dim, 64),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def encode(self, token_ids: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        lengths = lengths.detach().cpu().clamp(min=1)
        embedded = self.embedding(token_ids)
        packed = pack_padded_sequence(
            embedded,
            lengths,
            batch_first=True,
            enforce_sorted=False,
        )
        packed_output, _ = self.encoder(packed)
        output, _ = pad_packed_sequence(
            packed_output,
            batch_first=True,
            total_length=token_ids.size(1),
        )
        mask = (token_ids != 0).unsqueeze(-1)
        masked = output.masked_fill(~mask, float("-inf"))
        pooled = masked.max(dim=1).values
        return torch.where(torch.isfinite(pooled), pooled, torch.zeros_like(pooled))

    def forward(
        self,
        reference_ids: torch.Tensor,
        reference_length: torch.Tensor,
        user_ids: torch.Tensor,
        user_length: torch.Tensor,
    ) -> torch.Tensor:
        reference_vector = self.encode(reference_ids, reference_length)
        user_vector = self.encode(user_ids, user_length)
        features = torch.cat(
            [
                reference_vector,
                user_vector,
                torch.abs(reference_vector - user_vector),
                reference_vector * user_vector,
            ],
            dim=1,
        )
        return self.regressor(features).squeeze(1)


class SiameseBiLSTM:
    """Trainable semantic similarity scorer based on a Siamese Bi-LSTM."""

    def __init__(
        self,
        config: SiameseBiLSTMConfig | None = None,
        model_path: str | Path | None = None,
        dataset_path: str | Path | None = None,
        device: str | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.config = config or SiameseBiLSTMConfig()
        self.model_path = Path(model_path) if model_path else project_root / "results" / "siamese_bilstm.pt"
        self.dataset_path = (
            Path(dataset_path)
            if dataset_path
            else project_root / "data" / "processed" / "questions_cleaned.json"
        )
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.vocabulary = Vocabulary()
        self.model: SiameseBiLSTMNetwork | None = None
        self.is_trained = False
        if self.model_path.exists():
            self.load(self.model_path)

    def train(
        self,
        reference_answers: list[str] | None = None,
        user_answers: list[str] | None = None,
        similarity_labels: list[float] | None = None,
        epochs: int | None = None,
    ) -> dict[str, float]:
        if reference_answers is not None or user_answers is not None or similarity_labels is not None:
            if not (reference_answers and user_answers and similarity_labels):
                raise ValueError("reference_answers, user_answers, and similarity_labels must be supplied together.")
            records = [
                {
                    "reference_answer": reference,
                    "user_answer": answer,
                    "similarity": score,
                }
                for reference, answer, score in zip(reference_answers, user_answers, similarity_labels)
            ]
        else:
            records = self.load_training_records(self.dataset_path)
        return self.fit(records, epochs=epochs)

    def train_from_dataset(
        self,
        dataset_path: str | Path | None = None,
        epochs: int | None = None,
    ) -> dict[str, float]:
        records = self.load_training_records(Path(dataset_path) if dataset_path else self.dataset_path)
        return self.fit(records, epochs=epochs)

    def fit(self, records: list[dict[str, Any]], epochs: int | None = None) -> dict[str, float]:
        clean_records = [self.validate_training_record(record) for record in records]
        if len(clean_records) < 2:
            raise ValueError("At least two semantic similarity records are required for training.")

        torch.manual_seed(self.config.random_seed)
        self.vocabulary = Vocabulary()
        self.vocabulary.fit(
            (field for record in clean_records for field in (record["reference_answer"], record["user_answer"])),
            self.config.max_vocab_size,
            self.config.min_token_frequency,
        )
        self.model = SiameseBiLSTMNetwork(self.vocabulary.size, self.config).to(self.device)
        dataset = SimilarityPairDataset(clean_records, self.vocabulary, self.config.max_length)
        train_loader, valid_loader = self.make_loaders(dataset)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        loss_fn = nn.MSELoss()

        best_valid_loss = math.inf
        best_state: dict[str, torch.Tensor] | None = None
        stale_epochs = 0
        total_epochs = epochs or self.config.epochs
        history: dict[str, float] = {}

        for epoch in range(1, total_epochs + 1):
            train_metrics = self.run_epoch(train_loader, loss_fn, optimizer)
            train_loss = train_metrics["loss"]
            valid_metrics = (
                self.evaluate_metrics(valid_loader, loss_fn)
                if valid_loader
                else train_metrics
            )
            valid_loss = valid_metrics["loss"]
            history = {
                "epoch": float(epoch),
                "train_loss": train_loss,
                "train_mae": train_metrics["mae"],
                "train_accuracy": train_metrics["accuracy"],
                "validation_loss": valid_loss,
                "validation_mae": valid_metrics["mae"],
                "validation_accuracy": valid_metrics["accuracy"],
            }
            logger.info(
                (
                    "Siamese Bi-LSTM epoch %s/%s - train_loss=%.4f "
                    "train_mae=%.4f train_accuracy=%.2f%% "
                    "validation_loss=%.4f validation_mae=%.4f validation_accuracy=%.2f%%"
                ),
                epoch,
                total_epochs,
                train_loss,
                train_metrics["mae"],
                train_metrics["accuracy"] * 100,
                valid_loss,
                valid_metrics["mae"],
                valid_metrics["accuracy"] * 100,
            )
            if valid_loss < best_valid_loss:
                best_valid_loss = valid_loss
                best_state = {
                    key: value.detach().cpu().clone()
                    for key, value in self.model.state_dict().items()
                }
                stale_epochs = 0
            else:
                stale_epochs += 1
                if stale_epochs >= self.config.patience:
                    break

        if best_state is not None:
            self.model.load_state_dict(best_state)
        self.is_trained = True
        self.save(self.model_path)
        history["best_validation_loss"] = best_valid_loss
        return history

    def make_loaders(
        self,
        dataset: SimilarityPairDataset,
    ) -> tuple[DataLoader, DataLoader | None]:
        validation_count = int(len(dataset) * self.config.validation_split)
        if validation_count <= 0:
            return DataLoader(dataset, batch_size=self.config.batch_size, shuffle=True), None
        train_count = len(dataset) - validation_count
        generator = torch.Generator().manual_seed(self.config.random_seed)
        train_dataset, valid_dataset = random_split(dataset, [train_count, validation_count], generator=generator)
        return (
            DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True),
            DataLoader(valid_dataset, batch_size=self.config.batch_size, shuffle=False),
        )

    def run_epoch(
        self,
        loader: DataLoader,
        loss_fn: nn.Module,
        optimizer: torch.optim.Optimizer,
    ) -> dict[str, float]:
        assert self.model is not None
        self.model.train()
        total_loss = 0.0
        total_absolute_error = 0.0
        total_correct = 0
        total_items = 0
        for batch in loader:
            batch = self.move_batch(batch)
            optimizer.zero_grad()
            prediction = self.model(
                batch["reference_ids"],
                batch["reference_length"],
                batch["user_ids"],
                batch["user_length"],
            )
            loss = loss_fn(prediction, batch["target"])
            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
            optimizer.step()
            count = batch["target"].size(0)
            total_loss += loss.item() * count
            errors = torch.abs(prediction.detach() - batch["target"])
            total_absolute_error += errors.sum().item()
            total_correct += (errors <= self.config.accuracy_tolerance).sum().item()
            total_items += count
        total_items = max(1, total_items)
        return {
            "loss": total_loss / total_items,
            "mae": total_absolute_error / total_items,
            "accuracy": total_correct / total_items,
        }

    def evaluate(self, loader: DataLoader, loss_fn: nn.Module) -> float:
        return self.evaluate_metrics(loader, loss_fn)["loss"]

    def evaluate_metrics(self, loader: DataLoader, loss_fn: nn.Module) -> dict[str, float]:
        assert self.model is not None
        self.model.eval()
        total_loss = 0.0
        total_absolute_error = 0.0
        total_correct = 0
        total_items = 0
        with torch.no_grad():
            for batch in loader:
                batch = self.move_batch(batch)
                prediction = self.model(
                    batch["reference_ids"],
                    batch["reference_length"],
                    batch["user_ids"],
                    batch["user_length"],
                )
                loss = loss_fn(prediction, batch["target"])
                count = batch["target"].size(0)
                total_loss += loss.item() * count
                errors = torch.abs(prediction - batch["target"])
                total_absolute_error += errors.sum().item()
                total_correct += (errors <= self.config.accuracy_tolerance).sum().item()
                total_items += count
        total_items = max(1, total_items)
        return {
            "loss": total_loss / total_items,
            "mae": total_absolute_error / total_items,
            "accuracy": total_correct / total_items,
        }

    def score(self, reference_answer: str, user_answer: str) -> float:
        if not self.is_trained or self.model is None:
            if self.model_path.exists():
                self.load(self.model_path)
            else:
                self.train_from_dataset(self.dataset_path)
        assert self.model is not None
        self.model.eval()
        reference_ids, reference_length = self.vocabulary.encode(reference_answer, self.config.max_length)
        user_ids, user_length = self.vocabulary.encode(user_answer, self.config.max_length)
        with torch.no_grad():
            prediction = self.model(
                torch.tensor([reference_ids], dtype=torch.long, device=self.device),
                torch.tensor([reference_length], dtype=torch.long, device=self.device),
                torch.tensor([user_ids], dtype=torch.long, device=self.device),
                torch.tensor([user_length], dtype=torch.long, device=self.device),
            )
        return float(prediction.clamp(0.0, 1.0).item())

    def move_batch(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        return {key: value.to(self.device) for key, value in batch.items()}

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Cannot save before the model has been trained.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "config": asdict(self.config),
                "vocabulary": self.vocabulary.to_dict(),
                "model_state": self.model.state_dict(),
            },
            path,
        )

    def load(self, path: str | Path) -> None:
        checkpoint = torch.load(Path(path), map_location=self.device)
        self.config = SiameseBiLSTMConfig(**checkpoint["config"])
        self.vocabulary = Vocabulary.from_dict(checkpoint["vocabulary"])
        self.model = SiameseBiLSTMNetwork(self.vocabulary.size, self.config).to(self.device)
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()
        self.is_trained = True

    @staticmethod
    def load_json_records(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Training data not found: {path}")
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError(f"{path.name} must contain a JSON list.")
        return data

    def load_training_records(self, path: Path) -> list[dict[str, Any]]:
        source_records = self.load_json_records(path)
        if not source_records:
            raise ValueError(f"No records found in {path}")
        if {"reference_answer", "user_answer", "similarity"}.issubset(source_records[0]):
            return source_records
        return self.build_pairs_from_questions(source_records)

    def build_pairs_from_questions(self, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        references = [
            {
                "id": question.get("id", index),
                "domain": str(question.get("domain", "")),
                "reference_answer": str(question.get("reference_answer", "")).strip(),
            }
            for index, question in enumerate(questions)
            if str(question.get("reference_answer", "")).strip()
        ]
        if len(references) < 2:
            raise ValueError("At least two reference answers are required to train contrastive pairs.")

        records: list[dict[str, Any]] = []
        total = len(references)
        for index, item in enumerate(references):
            reference = item["reference_answer"]
            records.append(
                {
                    "reference_answer": reference,
                    "user_answer": reference,
                    "similarity": 1.0,
                }
            )
            for offset in range(1, self.config.negatives_per_answer + 1):
                negative = references[(index + offset * 17) % total]
                if negative["id"] == item["id"]:
                    negative = references[(index + offset * 17 + 1) % total]
                score = 0.15 if negative["domain"] == item["domain"] else 0.0
                records.append(
                    {
                        "reference_answer": reference,
                        "user_answer": negative["reference_answer"],
                        "similarity": score,
                    }
                )
        return records

    @staticmethod
    def validate_training_record(record: dict[str, Any]) -> dict[str, Any]:
        required = ("reference_answer", "user_answer", "similarity")
        missing = [field for field in required if field not in record]
        if missing:
            raise ValueError(f"Training record is missing required fields: {missing}")
        similarity = float(record["similarity"])
        if not 0.0 <= similarity <= 1.0:
            raise ValueError(f"Similarity must be between 0 and 1, got {similarity}")
        return {
            "reference_answer": str(record["reference_answer"]).strip(),
            "user_answer": str(record["user_answer"]).strip(),
            "similarity": similarity,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    scorer = SiameseBiLSTM()
    metrics = scorer.train_from_dataset()
    print(json.dumps(metrics, indent=2))
