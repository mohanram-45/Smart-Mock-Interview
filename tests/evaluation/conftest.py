import copy

import pytest

from src.evaluation.evaluator import AnswerEvaluator
from src.evaluation.grounding import reference_from_record
from src.evaluation.providers.mock import MockProvider
from src.evaluation.schema import EvaluationRequest, ReferenceBundle
from src.retrieval.corpus import load_corpus

BUBBLE, ACID, OVERFIT, TIMESENS = "smi-0453", "smi-0427", "smi-0264", "smi-j0024"


@pytest.fixture(scope="session")
def by_id():
    return {r["question_id"]: r for r in load_corpus()["records"]}


@pytest.fixture()
def make_req(by_id):
    def _mk(qid, answer, support=None, reference=None):
        r = by_id[qid]
        return EvaluationRequest(question_id=qid, question=r["question"], domain=r["domain"], topic=r["topic"], difficulty=r["difficulty"],
                                 candidate_answer=answer, reference=reference or reference_from_record(r), support=support or [])
    return _mk


def level(n, j="ok"):
    return {"level": n, "justification": j}


def llm_json(levels=(4, 4, 4, 4), **over):
    """A scripted, VALID model reply (contract tests only). levels = (correctness, completeness, relevance, reasoning)."""
    d = {"gradable": True, "not_gradable_reason": "",
         "rubric": {"correctness": level(levels[0]), "completeness": level(levels[1]), "relevance": level(levels[2]), "reasoning": level(levels[3])},
         "score_rationale": "Scripted rationale tying levels to the answer.", "correct_concepts": [], "missing_concepts": [], "factual_errors": [],
         "strengths": ["clear"], "improvement_suggestions": ["add detail"], "improved_example_answer": "", "follow_up_question": "Why?",
         "supporting_evidence": [], "confidence": "high", "verification_limitations": []}
    d.update(over)
    return d


@pytest.fixture()
def evaluator_for():
    def _mk(script, **kw):
        p = MockProvider(script)
        sleeps = []
        ev = AnswerEvaluator(p, sleep=sleeps.append, nonce_factory=lambda: "testnonce0001", **kw)
        ev.mock, ev.sleeps = p, sleeps
        return ev
    return _mk
