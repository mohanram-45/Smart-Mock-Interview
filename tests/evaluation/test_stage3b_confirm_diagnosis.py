"""Regression tests from the REAL llama3.2:3b confirmation run (fixtures/llama32_3b_confirm_raw.json)."""
import json
from pathlib import Path

import pytest

from src.evaluation.evaluator import AnswerEvaluator
from src.evaluation.grounding import reference_from_record
from src.evaluation.providers.mock import MockProvider
from src.evaluation.schema import EvaluationRequest, EvaluationStatus as S
from tests.evaluation.conftest import llm_json

FX = json.loads((Path(__file__).parent / "fixtures" / "llama32_3b_confirm_raw.json").read_text(encoding="utf-8"))


def run(by_id, case, replies=None):
    r = by_id[FX[case]["question_id"]]
    req = EvaluationRequest(question_id=r["question_id"], question=r["question"], domain=r["domain"], topic=r["topic"], difficulty=r["difficulty"],
                            candidate_answer=FX[case]["candidate_answer"], reference=reference_from_record(r))
    return AnswerEvaluator(MockProvider(list(replies or FX[case]["raw"][:1])), max_retries=0).evaluate(req)


def test_B01_missing_score_rationale_stays_invalid_never_autoscored(by_id):
    res = run(by_id, "B01", FX["B01"]["raw"])             # both real replies omit score_rationale
    assert res.evaluation_status == S.INVALID_RESPONSE and res.provisional_score is None
    assert "score_rationale" in res.error.message


def test_B03_same_words_cannot_be_both_credit_and_error(by_id):
    res = run(by_id, "B03")
    assert len(res.factual_errors) == 1 and res.correct_concepts == []
    assert res.flags["conflicting_concepts_withheld"] == 1
    assert res.provisional_score <= 30                     # no verified knowledge -> unsupported-credit cap (reversed answer previously scored 68)


def test_conflict_rule_does_not_punish_unrelated_concepts(by_id):
    ans = FX["B01"]["candidate_answer"]
    r = by_id["smi-0441"]
    req = EvaluationRequest(question_id=r["question_id"], question=r["question"], domain=r["domain"], topic=r["topic"], difficulty=r["difficulty"],
                            candidate_answer=ans, reference=reference_from_record(r))
    ok = llm_json(correct_concepts=[{"concept": "value equality", "candidate_quote": "== compares values"}],
                  factual_errors=[{"claim_quote": "Two separate lists with the same elements are == but not is", "explanation": "invented problem", "severity": "minor"}])
    res = AnswerEvaluator(MockProvider([ok]), max_retries=0).evaluate(req)
    assert len(res.correct_concepts) == 1 and "conflicting_concepts_withheld" not in res.flags


def test_B04_empty_quotes_and_empty_claim_are_correctly_rejected(by_id):
    res = run(by_id, "B04")
    assert res.correct_concepts == [] and res.factual_errors == []
    assert res.flags["dropped_unverifiable"]["concepts"] == 4 and res.flags["dropped_unverifiable"]["errors"] == 1
    assert res.provisional_score == 30 and res.evaluation_status == S.GRADED_LOW_CONFIDENCE


def test_B07_quote_copied_from_reference_is_not_candidate_evidence(by_id):
    res = run(by_id, "B07")
    assert res.correct_concepts == [] and res.provisional_score == 30
    assert "improved_example_removed_reference_copy" in res.flags


def test_B20_injection_not_obeyed_and_flagged_low_confidence(by_id):
    res = run(by_id, "B20")
    assert res.flags["injection_suspected"] and res.confidence == "low"
    assert res.provisional_score != 100 and all("score of 100" not in c.candidate_quote for c in res.correct_concepts)
    assert "improved_example_removed_reference_copy" in res.flags
