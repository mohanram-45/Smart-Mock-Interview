"""Regression tests from REAL Qwen 2.5 7B and llama3.2:3b replies (fixtures/*_raw.json). Offline; replays only."""
import json
from pathlib import Path

import pytest

from src.evaluation.evaluator import AnswerEvaluator, _contains
from src.evaluation.grounding import reference_from_record
from src.evaluation.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from src.evaluation.providers.mock import MockProvider
from src.evaluation.schema import EvaluationRequest, EvaluationStatus as S
from tests.evaluation.conftest import llm_json

FD = Path(__file__).parent / "fixtures"
QW = json.loads((FD / "qwen25_7b_confirm_raw.json").read_text(encoding="utf-8"))
ALL = {n: json.loads((FD / f"{n}.json").read_text(encoding="utf-8"))
       for n in ("qwen25_7b_confirm_raw", "llama32_3b_confirm_raw", "llama32_3b_smoke_raw")}


def _req(by_id, v, answer=None):
    r = by_id[v["question_id"]]
    return EvaluationRequest(question_id=r["question_id"], question=r["question"], domain=r["domain"], topic=r["topic"], difficulty=r["difficulty"],
                             candidate_answer=answer or v["candidate_answer"], reference=reference_from_record(r))


def run(by_id, case, replies=None, fx=QW):
    return AnswerEvaluator(MockProvider(list(replies or fx[case]["raw"])), max_retries=0).evaluate(_req(by_id, fx[case]))


def test_quote_mark_style_is_formatting_but_words_must_match():
    assert _contains("`is` compares the values of two objects", "'is' compares the values of two objects")
    assert _contains('He said "use ==" here', "use ==")
    assert not _contains("`is` compares the values of two objects", "'is' compares the addresses of two objects")


def test_qwen_B03_real_factual_error_is_now_kept_and_concept_credit_withheld(by_id):
    res = run(by_id, "B03")
    assert [e.severity for e in res.factual_errors] == ["major"]          # was dropped by the apostrophe/backtick mismatch
    assert res.correct_concepts == [] and res.flags["conflicting_concepts_withheld"] == 1
    assert res.provisional_score <= 30 and res.evaluation_status == S.GRADED_LOW_CONFIDENCE


def test_qwen_B01_correct_answer_still_accepted(by_id):
    res = run(by_id, "B01")
    assert res.evaluation_status == S.GRADED and res.provisional_score == 96 and res.factual_errors == []
    assert res.correct_concepts and all(_contains(QW["B01"]["candidate_answer"], c.candidate_quote) for c in res.correct_concepts)


def test_qwen_B04_placeholder_quotes_get_no_credit_and_no_invented_score(by_id):
    res = run(by_id, "B04")
    assert res.correct_concepts == [] and res.flags["dropped_unverifiable"]["concepts"] == 2
    assert res.provisional_score == 30 and res.evaluation_status == S.GRADED_LOW_CONFIDENCE      # known limitation: model failed to quote


def test_qwen_B07_false_missing_claim_removed_and_flagged_but_score_not_raised(by_id):
    res = run(by_id, "B07")
    assert "DENSE_RANK" not in res.missing_concepts and res.flags["contradicted_missing_concepts"] == ["DENSE_RANK"]
    assert res.evaluation_status == S.GRADED_LOW_CONFIDENCE and res.provisional_score == 68    # no automatic boost
    assert len(res.correct_concepts) == 2


def test_missing_claim_matching_is_word_bounded(by_id):
    ans = "Properties of ROW_NUMBER: it numbers rows."
    v = QW["B07"]
    ok = llm_json(missing_concepts=["tie", "PARTITION BY"], correct_concepts=[{"concept": "ROW_NUMBER", "candidate_quote": "it numbers rows"}])
    res = AnswerEvaluator(MockProvider([ok]), max_retries=0).evaluate(_req(by_id, v, ans))
    assert res.missing_concepts == ["tie", "PARTITION BY"] and "contradicted_missing_concepts" not in res.flags


def test_qwen_B20_injection_not_obeyed(by_id):
    res = run(by_id, "B20")
    assert res.flags["injection_suspected"] and res.provisional_score <= 40 and res.confidence == "low"
    assert "improved_example_removed_reference_copy" in res.flags


def test_string_instead_of_list_is_tolerated_not_scored_blindly(by_id):
    assert run(by_id, "B20").improvement_suggestions            # Qwen B20 returned a bare string for improvement_suggestions


def test_fabricated_error_quote_still_rejected_with_looser_quote_marks(by_id):
    bad = llm_json(factual_errors=[{"claim_quote": "'is' stores values in a hash table", "explanation": "wrong", "severity": "major"}])
    res = AnswerEvaluator(MockProvider([bad]), max_retries=0).evaluate(_req(by_id, QW["B03"]))
    assert res.factual_errors == [] and res.flags["dropped_unverifiable"]["errors"] == 1


def test_prompt_v3b2_guides_meaning_scope_and_quotes():
    assert PROMPT_VERSION == "3b.2"
    for needle in ("MEANINGS, not required wording", "judge completeness against what the QUESTION asks", "never a placeholder", "if it is stated there, it is not missing"):
        assert needle in SYSTEM_PROMPT


@pytest.mark.parametrize("name", list(ALL))
def test_replay_invariants_across_all_saved_real_outputs(by_id, name):
    """For every saved real reply: kept evidence is really in the candidate text; only graded statuses carry a score; injection never yields credit."""
    fx = ALL[name]
    for case, v in fx.items():
        res = run(by_id, case, fx=fx)
        assert (res.provisional_score is not None) == (res.evaluation_status in (S.GRADED, S.GRADED_LOW_CONFIDENCE)), case
        for c in res.correct_concepts:
            assert _contains(v["candidate_answer"], c.candidate_quote), (case, c)
        for e in res.factual_errors:
            assert _contains(v["candidate_answer"], e.claim_quote) and e.explanation.strip(), (case, e)
        if res.flags.get("injection_suspected"):
            assert res.confidence == "low" and res.provisional_score != 100
