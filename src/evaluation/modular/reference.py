"""Reference material for ONE question (read-only view). Original question ids and reference answers are preserved verbatim."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Tuple


@dataclass(frozen=True)
class ReferenceMaterial:
    question_id: str
    canonical_answer: str = ""
    alternative_answers: Mapping[str, str] = field(default_factory=dict)
    common_mistakes: Tuple[str, ...] = ()

    def quote_corpus(self) -> str:
        """Text a verifier may quote when alleging an error: the reference answer, accepted alternatives and documented mistakes."""
        parts = [self.canonical_answer, *self.alternative_answers.values(), *self.common_mistakes]
        return "\n".join(p for p in parts if p)

    @classmethod
    def from_corpus_record(cls, rec: Mapping) -> "ReferenceMaterial":
        return cls(question_id=rec["question_id"], canonical_answer=rec.get("canonical_answer") or "",
                   alternative_answers=dict(rec.get("alternative_answers") or {}), common_mistakes=tuple(rec.get("common_mistakes") or ()))
