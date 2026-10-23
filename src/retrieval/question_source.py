"""Curated question source for AdaptiveInterviewSession (opt-in via SMART_QUESTION_SOURCE=curated).

Returns legacy-shaped dicts so the session, scorers, feedback and report code run unchanged:
  {id: 'smi-0001' (stable string), domain, difficulty, question, reference_answer, topic}
Quarantined / boilerplate records are already excluded by the corpus loader (quarantined ids are removed and a leak fails strict loading).
"""
from __future__ import annotations

from typing import Any, Dict, List

from question_provider import QuestionSourceUnavailable   # src/components is on sys.path in the app

from .service import CorpusUnavailable, RetrievalService

# Role/UI domain codes in config.ROLE_MAPPING -> canonical curated domain labels. Applied to the curated source ONLY;
# the legacy path keeps its (mismatching) behaviour untouched.
DOMAIN_ALIASES = {"ML": "Machine Learning", "DL": "Deep Learning", "DATA_ANALYSIS": "Data Analysis"}


def normalise_domains(domains: List[str]) -> List[str]:
    return list(dict.fromkeys(DOMAIN_ALIASES.get(d, d) for d in domains))


class CuratedQuestionProvider:
    name = "curated"

    def __init__(self, service: RetrievalService):
        self.service = service

    def __call__(self, domains: List[str]) -> List[Dict[str, Any]]:
        try:
            records = self.service.records()
        except CorpusUnavailable as exc:
            raise QuestionSourceUnavailable(str(exc)) from exc
        want = set(normalise_domains(domains))
        return [{"id": r["question_id"], "domain": r["domain"], "difficulty": r["difficulty"], "question": r["question"],
                 "reference_answer": r["canonical_answer"], "topic": r["topic"]}
                for r in records if r["domain"] in want]
