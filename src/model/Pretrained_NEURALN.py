"""Pretrained transformer answer scorer using Sentence-BERT embeddings."""
from __future__ import annotations

from math import sqrt


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


class SentenceBertAnswerScorer:
    """Score answers with a pretrained Sentence Transformers model.

    Model:
        sentence-transformers/all-MiniLM-L6-v2

    Install when needed:
        pip install sentence-transformers
    """

    model_name = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, model_name: str | None = None):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for the pretrained model. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        self.model_name = model_name or self.model_name
        self.model = SentenceTransformer(self.model_name)

    def score(self, reference_answer: str, user_answer: str) -> dict[str, float | str]:
        reference_embedding, user_embedding = self.model.encode(
            [reference_answer, user_answer],
            normalize_embeddings=True,
        )
        similarity = _cosine_similarity(
            reference_embedding.tolist(),
            user_embedding.tolist(),
        )

        return {
            "model": self.model_name,
            "similarity": round(float(similarity), 4),
            "score_percent": round(float(similarity) * 100, 2),
        }


if __name__ == "__main__":
    scorer = SentenceBertAnswerScorer()
    result = scorer.score(
        "Overfitting happens when a model learns noise in the training data.",
        "A model overfits when it memorises training data and performs badly on new data.",
    )
    print(result)

