import json

import pytest

from src.evaluation import errors as E
from src.evaluation.evaluator import AnswerEvaluator, extract_json
from src.evaluation.providers.mock import MockProvider
from src.evaluation.schema import EvaluationStatus as S
from tests.evaluation.conftest import BUBBLE, llm_json

ANS = "Bubble sort compares adjacent elements and swaps them; O(n²)."
OK = llm_json((4, 4, 4, 4), correct_concepts=[{"concept": "bubble sort", "candidate_quote": "compares adjacent elements"}])


def test_timeouts_retry_with_bounded_backoff_then_fail_without_fabrication(make_req, evaluator_for):
    ev = evaluator_for([E.ProviderTimeout("t")] * 10, max_retries=2)
    r = ev.evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.PROVIDER_ERROR and r.provisional_score is None and r.error.code == "provider_timeout" and r.error.retryable
    assert len(ev.mock.calls) == 3 and ev.sleeps == [0.5, 1.0]            # 1 call + 2 retries, exponential backoff
    assert r.correct_concepts == [] and r.score_rationale == "" and r.improved_example_answer == ""   # nothing invented


def test_transient_then_success(make_req, evaluator_for):
    ev = evaluator_for([E.ProviderTimeout("t"), E.ProviderUnavailable("down"), OK], max_retries=2)
    r = ev.evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.GRADED and r.provenance.attempts == 3


def test_zero_retries_means_one_call(make_req, evaluator_for):
    ev = evaluator_for([E.ProviderTimeout("t")] * 3, max_retries=0)
    assert ev.evaluate(make_req(BUBBLE, ANS)).evaluation_status == S.PROVIDER_ERROR and len(ev.mock.calls) == 1


@pytest.mark.parametrize("exc,code", [(E.ProviderAuthError("401"), "provider_auth_error"), (E.ProviderRequestError("400"), "provider_request_error"),
                                      (E.ProviderResponseError("bad"), "provider_bad_envelope")])
def test_non_retryable_errors_are_not_retried(make_req, evaluator_for, exc, code):
    ev = evaluator_for([exc, OK])
    r = ev.evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.PROVIDER_ERROR and r.error.code == code and not r.error.retryable and len(ev.mock.calls) == 1 and ev.sleeps == []


def test_rate_limit_honours_retry_after_but_caps_it(make_req, evaluator_for):
    ev = evaluator_for([E.ProviderRateLimited("429", retry_after=2.0), E.ProviderRateLimited("429", retry_after=999), OK], max_retries=2)
    assert ev.evaluate(make_req(BUBBLE, ANS)).evaluation_status == S.GRADED
    assert ev.sleeps == [2.0, 8.0]


def test_invalid_json_gets_one_repair_then_succeeds(make_req, evaluator_for):
    ev = evaluator_for(["Sure! The answer looks great.", OK])
    r = ev.evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.GRADED and len(ev.mock.calls) == 2
    assert "WAS REJECTED" in ev.mock.calls[1]["user"] and "Sure! The answer looks great." in ev.mock.calls[1]["user"]


def test_persistently_invalid_json_is_an_error_not_a_guess(make_req, evaluator_for):
    ev = evaluator_for(["not json", "{broken"])
    r = ev.evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.INVALID_RESPONSE and r.provisional_score is None and r.error.code == "invalid_response" and len(ev.mock.calls) == 2


@pytest.mark.parametrize("bad", [
    llm_json((4, 4, 4, 4), rubric={"correctness": {"level": 7}, "completeness": {"level": 1}, "relevance": {"level": 1}, "reasoning": {"level": 1}}),
    {**llm_json(), "rubric": None},
    {**llm_json(), "score_rationale": ""},
    {**llm_json(), "confidence": "certain"},
    [1, 2, 3],
])
def test_schema_violations_are_rejected(make_req, evaluator_for, bad):
    r = evaluator_for([bad, bad]).evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.INVALID_RESPONSE and r.provisional_score is None


def test_fenced_and_chatty_json_is_tolerated():
    assert extract_json("```json\n{\"a\": 1}\n```") == {"a": 1}
    assert extract_json("Here you go: {\"a\": {\"b\": 2}} hope it helps") == {"a": {"b": 2}}
    for bad in ("", "no braces", "[1]", "{'a': 1}"):
        with pytest.raises(ValueError):
            extract_json(bad)


def test_unknown_extra_keys_from_the_model_are_ignored(make_req, evaluator_for):
    r = evaluator_for({**OK, "provisional_score": 100, "chain_of_thought": "..."}).evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.GRADED and r.provisional_score == 100        # (from levels, not from the model's own number)
    r2 = evaluator_for({**llm_json((0, 0, 4, 0)), "provisional_score": 100}).evaluate(make_req(BUBBLE, ANS))
    assert r2.provisional_score == 15 and "chain_of_thought" not in r2.model_dump_json()   # a self-declared 100 is ignored


def test_no_provider_is_a_clear_status(make_req):
    r = AnswerEvaluator(None).evaluate(make_req(BUBBLE, ANS))
    assert r.evaluation_status == S.PROVIDER_NOT_CONFIGURED and r.provisional_score is None and r.error.code == "provider_not_configured"


def test_unexpected_exceptions_in_a_provider_are_not_swallowed_silently(make_req, evaluator_for):
    with pytest.raises(RuntimeError):
        evaluator_for([RuntimeError("bug")]).evaluate(make_req(BUBBLE, ANS))     # programming errors surface; only ProviderError is mapped


def test_result_is_json_serialisable_for_every_status(make_req, evaluator_for):
    outs = [evaluator_for(OK).evaluate(make_req(BUBBLE, ANS)), evaluator_for(E.ProviderTimeout("t")).evaluate(make_req(BUBBLE, ANS)),
            evaluator_for("x").evaluate(make_req(BUBBLE, ANS)), AnswerEvaluator(None).evaluate(make_req(BUBBLE, ""))]
    for r in outs:
        json.loads(r.model_dump_json())
