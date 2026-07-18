"""Unified registry for the 3 answer-scoring models.

The project has three independent scorers (Siamese Bi-LSTM, Sentence-BERT,
TF-IDF + Grammar) with three different native return types. This module
wraps all three behind one interface:

    scorer.score(reference_answer, user_answer) -> float in [0.0, 1.0]

so callers (interview_session.py) never need to know which model is
active. A session picks ONE model at start time and uses it for every
question for the rest of that session.

Each model is loaded/trained at most once per process and then shared
across every session that picks it (loading a transformer or training a
network per-request would be far too slow).
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Keys used everywhere else (API requests, session state, cache keys).
MODEL_CHOICES: Dict[str, Dict[str, str]] = {
    "bilstm": {
        "label": "Siamese Bi-LSTM",
        "description": (
            "Custom neural network trained from scratch on this project's own "
            "question/answer pairs. Fast once trained, but only ever saw "
            "exact-match positives, so it is stricter with reworded answers."
        ),
    },
    "bert": {
        "label": "Sentence-BERT",
        "description": (
            "Pretrained transformer (all-MiniLM-L6-v2) fine-tuned on 1B+ general "
            "sentence pairs. Best at recognizing correct answers phrased in your "
            "own words."
        ),
    },
    "tfidf": {
        "label": "TF-IDF + Grammar",
        "description": (
            "Classic keyword-overlap similarity plus a grammar check. Fastest "
            "and simplest, but purely statistical - it rewards matching "
            "vocabulary rather than matching meaning."
        ),
    },
}

DEFAULT_MODEL = "bilstm"

_lock = threading.Lock()
_cache: Dict[str, "_BaseAdapter"] = {}


def is_valid_model(model_key: Optional[str]) -> bool:
    return model_key in MODEL_CHOICES


def list_models() -> List[Dict[str, str]]:
    return [{"key": key, **meta} for key, meta in MODEL_CHOICES.items()]


class _BaseAdapter:
    def ensure_ready(self) -> None:
        """Hook for models that need a one-time warmup (e.g. training)."""

    def score(self, reference_answer: str, user_answer: str) -> float:
        raise NotImplementedError


class _BiLSTMAdapter(_BaseAdapter):
    """Wraps SiameseBiLSTM. Needs an explicit training pass if no checkpoint exists."""

    def __init__(self) -> None:
        from SiameseBiLSTM import SiameseBiLSTM
        self._model = SiameseBiLSTM()

    def ensure_ready(self) -> None:
        if not self._model.is_trained:
            logger.info("Training Siamese Bi-LSTM from questions_cleaned.json (first use)")
            self._model.train_from_dataset(epochs=10)

    def score(self, reference_answer: str, user_answer: str) -> float:
        return float(self._model.score(reference_answer, user_answer))


class _BertAdapter(_BaseAdapter):
    """Wraps SentenceBertAnswerScorer, which returns a dict, not a bare float."""

    def __init__(self) -> None:
        from Pretrained_NEURALN import SentenceBertAnswerScorer
        self._model = SentenceBertAnswerScorer()

    def score(self, reference_answer: str, user_answer: str) -> float:
        result = self._model.score(reference_answer, user_answer)
        similarity = float(result["similarity"])
        return max(0.0, min(1.0, similarity))


class _TfidfAdapter(_BaseAdapter):
    """Wraps TraditionalMLScorer. Vectorizer benefits from seeing the full
    question corpus up front, so it's optionally passed in at load time."""

    def __init__(self, corpus: Optional[List[str]] = None) -> None:
        from TraditionalMLScorer import TraditionalMLScorer
        self._model = TraditionalMLScorer(all_questions=corpus)

    def score(self, reference_answer: str, user_answer: str) -> float:
        result = self._model.score(reference_answer, user_answer)
        # Use pure semantic similarity (score_percent), not the grammar-blended
        # final_score, so this stays directly comparable to the other 2 models.
        percent = float(result["score_percent"])
        return max(0.0, min(1.0, percent / 100.0))


_ADAPTER_CLASSES = {
    "bilstm": _BiLSTMAdapter,
    "bert": _BertAdapter,
    "tfidf": _TfidfAdapter,
}


def get_scorer(model_key: str, corpus: Optional[List[str]] = None) -> _BaseAdapter:
    """Return the shared, cached scorer instance for the given model key.

    Loading/training happens once per process per model. `corpus` (reference
    answers) is only used the first time the tfidf model is requested, to
    train its vectorizer.
    """
    if not is_valid_model(model_key):
        raise ValueError(f"Unknown model '{model_key}'. Choose from: {list(MODEL_CHOICES)}")

    with _lock:
        if model_key not in _cache:
            logger.info(f"Loading scoring model '{model_key}' for the first time")
            if model_key == "tfidf":
                _cache[model_key] = _TfidfAdapter(corpus=corpus)
            else:
                _cache[model_key] = _ADAPTER_CLASSES[model_key]()
        scorer = _cache[model_key]

    scorer.ensure_ready()
    return scorer
