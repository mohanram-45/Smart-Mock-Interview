"""Stage F: optional, separate, asynchronous-compatible feedback."""
import json

from src.evaluation.modular.feedback import FeedbackProvider, build_feedback, feedback_payload
from tests.evaluation.mod_helpers import run

A = "Type I error is a false positive. Type II error is a false negative."
Q = "Type I error is a false positive"


def _res(by_id, spec, ans=A, **kw):
    return run(by_id, "smi-0198", ans, spec=spec, reasoning=["c1"], **kw)[0]


def test_feedback_contains_only_verified_findings_and_candidate_quotes(by_id):
    spec = {"Type I error": ("states_correctly", "c1"), "Type II error": ("states_incorrectly", "c2", "wrong direction", "Type II error is a false negative", "major"),
            "false positive": ("states_correctly", "c1")}
    fb = build_feedback(feedback_payload(_res(by_id, spec)))
    assert [c["concept"] for c in fb.correct_concepts] == ["Type I error", "false positive"] and fb.correct_concepts[0]["your_words"] == [Q + "."]
    assert fb.factual_errors[0]["reference_says"] == "Type II error is a false negative" and fb.factual_errors[0]["your_words"] == ["Type II error is a false negative."]
    assert not fb.missing_essential_concepts


def test_unverified_is_reported_as_could_not_check_never_as_a_mistake(by_id):
    fb = build_feedback(feedback_payload(_res(by_id, {"Type I error": ("states_correctly", "c1")})))
    assert fb.could_not_verify and not fb.factual_errors
    assert any("not a judgement that they are wrong" in s for s in fb.suggestions)


def test_missing_essentials_listed_and_marked_advisory_for_non_eligible_records(by_id):
    res, _ = run(by_id, "smi-0431", "ROW_NUMBER is unique.", spec={"ROW_NUMBER": ("states_correctly", "c1"), "RANK": ("not_stated", []), "ties": ("not_stated", [])}, reasoning=["c1"])
    fb = build_feedback(feedback_payload(res))
    assert fb.advisory and {m["requirement"] for m in fb.missing_essential_concepts} == {"RANK", "ties"}
    assert any("AI-drafted" in s for s in fb.suggestions) and any("Advisory" in n for n in fb.notes)


def test_feedback_cannot_change_the_scoring_decision(by_id):
    res = _res(by_id, {"Type I error": ("states_correctly", "c1"), "Type II error": ("states_correctly", "c2"), "false positive": ("states_correctly", "c1"), "false negative": ("states_correctly", "c2")})
    before = json.dumps(res.to_dict(), sort_keys=True)
    build_feedback(feedback_payload(res))
    assert json.dumps(res.to_dict(), sort_keys=True) == before


def test_payload_is_json_serialisable_for_deferred_async_runs(by_id):
    res = _res(by_id, {"Type I error": ("states_correctly", "c1")})
    payload = json.loads(json.dumps(feedback_payload(res)))                 # e.g. put on a queue, rebuild later
    fb = build_feedback(payload)
    assert fb.question_id == "smi-0198" and fb.source == "deterministic"
    assert "provenance" not in payload and "score" not in payload           # scoring data is not an input to feedback


def test_optional_provider_and_failure_fallback(by_id):
    class Ok(FeedbackProvider):
        is_mock = True
        def phrase(self, payload): return "Nicely phrased feedback."
    class Boom(FeedbackProvider):
        def phrase(self, payload): raise TimeoutError("slow")
    payload = feedback_payload(_res(by_id, {"Type I error": ("states_correctly", "c1")}))
    assert build_feedback(payload, Ok()).source == "llm"
    fb = build_feedback(payload, Boom())
    assert fb.source == "deterministic" and any("feedback_provider_failed" in n for n in fb.notes) and fb.text


def test_no_feedback_input_for_non_gradable_results(by_id):
    res, _ = run(by_id, "smi-0198", "idk", spec={})
    fb = build_feedback(feedback_payload(res))
    assert not fb.correct_concepts and not fb.factual_errors
