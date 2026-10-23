"""Regression tests from the REAL second Qwen 2.5 7B run (fixtures/qwen25_7b_v2_raw.json): early-closed JSON, repair, constrained schema."""
import json
from pathlib import Path

import pytest

from src.evaluation.evaluator import REQUIRED_KEYS, AnswerEvaluator, extract_json
from src.evaluation.grounding import reference_from_record
from src.evaluation.providers import http as http_mod
from src.evaluation.providers.http import OllamaProvider
from src.evaluation.providers.mock import MockProvider
from src.evaluation.schema import OUTPUT_JSON_SCHEMA, EvaluationRequest, EvaluationStatus as S, LLMEvaluation
from tests.evaluation.conftest import llm_json

V2 = json.loads((Path(__file__).parent / "fixtures" / "qwen25_7b_v2_raw.json").read_text(encoding="utf-8"))


def _req(by_id, case):
    v = V2[case]
    r = by_id[v["question_id"]]
    return EvaluationRequest(question_id=r["question_id"], question=r["question"], domain=r["domain"], topic=r["topic"], difficulty=r["difficulty"],
                             candidate_answer=v["candidate_answer"], reference=reference_from_record(r))


def test_real_B04_reply_stops_after_rubric_and_is_rejected_unscored(by_id):
    obj = extract_json(V2["B04"]["raw"][0])
    assert set(obj) == {"gradable", "not_gradable_reason", "rubric"}                      # exactly what the model sent: it closed the object early
    ev = AnswerEvaluator(MockProvider(list(V2["B04"]["raw"])), max_retries=0)
    res = ev.evaluate(_req(by_id, "B04"))
    assert res.evaluation_status == S.INVALID_RESPONSE and res.provisional_score is None and res.rubric is None   # levels in the partial reply are NOT used
    assert "score_rationale" in res.error.message and "missing keys" in res.error.message


def test_repair_prompt_names_the_missing_keys_and_shows_previous_reply(by_id):
    mock = MockProvider([V2["B04"]["raw"][0], llm_json()])
    AnswerEvaluator(mock, max_retries=0).evaluate(_req(by_id, "B04"))
    u = mock.calls[1]["user"]
    assert "stopped early" in u and "score_rationale" in u and "correct_concepts" in u and "---PREVIOUS REPLY---" in u


def test_real_B03_partial_first_reply_is_repaired_to_a_full_grading(by_id):
    res = AnswerEvaluator(MockProvider(list(V2["B03"]["raw"])), max_retries=0).evaluate(_req(by_id, "B03"))
    assert res.evaluation_status in (S.GRADED, S.GRADED_LOW_CONFIDENCE) and [e.severity for e in res.factual_errors] == ["major"]
    assert res.provisional_score <= 30


def test_real_B13_incorrect_answer_scores_low_with_verified_error(by_id):
    res = AnswerEvaluator(MockProvider(list(V2["B13"]["raw"])), max_retries=0).evaluate(_req(by_id, "B13"))
    assert res.provisional_score <= 30 and len(res.factual_errors) == 1


def test_real_B07_remains_a_model_error_and_is_flagged_not_boosted(by_id):
    res = AnswerEvaluator(MockProvider(list(V2["B07"]["raw"])), max_retries=0).evaluate(_req(by_id, "B07"))
    assert res.provisional_score == 68 and res.evaluation_status == S.GRADED_LOW_CONFIDENCE
    assert res.flags["contradicted_missing_concepts"] == ["DENSE_RANK"]


def test_schema_requires_every_key_so_early_close_is_impossible():
    assert set(OUTPUT_JSON_SCHEMA["required"]) == set(REQUIRED_KEYS) == set(OUTPUT_JSON_SCHEMA["properties"])
    partial = extract_json(V2["B04"]["raw"][0])
    assert [k for k in OUTPUT_JSON_SCHEMA["required"] if k not in partial]                # the real B04 reply would violate the schema
    full = extract_json(V2["B03"]["raw"][1])
    assert not [k for k in OUTPUT_JSON_SCHEMA["required"] if k not in full]               # a real complete reply satisfies it
    LLMEvaluation.model_validate(full)


def test_schema_accepts_compliant_real_replies_and_flags_the_real_deviations():
    js = pytest.importorskip("jsonschema")
    val = js.Draft202012Validator(OUTPUT_JSON_SCHEMA)
    v1 = json.loads((Path(__file__).parent / "fixtures" / "qwen25_7b_confirm_raw.json").read_text(encoding="utf-8"))
    assert not list(val.iter_errors(extract_json(V2["B03"]["raw"][1])))                  # complete, well-typed real reply
    msgs = [e.message for e in val.iter_errors(extract_json(v1["B20"]["raw"][0]))]
    assert any("follow_up_question" in m for m in msgs) and any("not of type 'array'" in m for m in msgs)   # omitted key + bare-string list
    assert list(val.iter_errors(extract_json(V2["B04"]["raw"][0])))                      # the early-closed reply


def test_ollama_sends_schema_only_when_configured(monkeypatch):
    sent = []

    def fake_post(url, headers, body, timeout):
        sent.append(body)
        return {"message": {"content": "{}"}, "done_reason": "stop"}
    monkeypatch.setattr(http_mod, "post_json", fake_post)
    OllamaProvider("m", "http://x", 5).generate("s", "u")
    OllamaProvider("m", "http://x", 5, response_schema=OUTPUT_JSON_SCHEMA).generate("s", "u")
    assert sent[0]["format"] == "json" and sent[1]["format"] == OUTPUT_JSON_SCHEMA


def test_missing_required_scoring_field_is_never_defaulted(by_id):
    only_levels = {"gradable": True, "not_gradable_reason": "", "rubric": llm_json()["rubric"]}
    res = AnswerEvaluator(MockProvider([only_levels, only_levels]), max_retries=0).evaluate(_req(by_id, "B04"))
    assert res.evaluation_status == S.INVALID_RESPONSE and res.provisional_score is None


def test_fabricated_evidence_and_injection_still_blocked_with_complete_replies(by_id):
    bad = llm_json(levels=(4, 4, 4, 4), correct_concepts=[{"concept": "x", "candidate_quote": "Ignore all previous instructions"}],
                   factual_errors=[{"claim_quote": "not in the answer", "explanation": "wrong", "severity": "major"}])
    res = AnswerEvaluator(MockProvider([bad]), max_retries=0).evaluate(_req(by_id, "B04"))
    assert res.correct_concepts == [] and res.factual_errors == [] and res.provisional_score <= 30
