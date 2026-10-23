"""Stage 11U: the final Stage 11 quality correction.

Offline checks of code behaviour. The 'recorded' questions are the real llama3.2:3b output of the Windows run tmp/stage10_opps_20261022_194032 (prompt 11.obj4), quoted in full (results.json cuts
each attempt at 200 characters). The valid paraphrases were written by the rules' author: they guard against false rejection, they are not independent evidence of quality."""
import copy
import json
import re
from pathlib import Path

import pytest

from src.demo import followup_llm as FL, intel, opportunity_eval as OE
from src.evaluation.providers.mock import MockProvider

ROOT = Path(__file__).resolve().parents[2]
CASES = {c["id"]: c for c in OE.load()["cases"]}


@pytest.fixture(scope="module")
def eng():
    return OE.offline_engine()


@pytest.fixture(autouse=True)
def _vocab():
    FL.set_vocabulary_source(lambda: [])
    yield
    FL.set_vocabulary_source(None)


def judge(eng, id_, q):
    x = OE.build_case(eng, copy.deepcopy(CASES[id_]))[0]
    v = intel.evaluate_question(q, x, intel.plan_objective(x))
    return ("refuse" if v.prop is None else "mem" if v.prop.memory_id else "plain"), v


# ------------------------------------------------------------------------------------------------ A. memory: a known project is not an unclaimed technique
@pytest.mark.parametrize("id_,q,lead", [
    ("M02", "How would the use of labelled training data in your spam classifier affect its ability to learn from examples?", False),            # recorded; they said 'trained ... on labelled emails'
    ("M01", "How does the evaluation of a logistic regression model's performance, specifically its ROC curve and AUC, relate to the performance of your oral cancer classification model?", False),   # recorded; compares, claims nothing
    ("M07", "How would linear search affect the efficiency of your search feature?", False),                                                    # recorded; a possibility about a known feature
])
def test_recorded_memory_false_rejections_are_now_grounded_by_code(eng, id_, q, lead):
    got, v = judge(eng, id_, q)
    assert got == "mem", v.reasons
    assert v.prop.validity["decided_by"] == "code" and bool(v.prop.lead) == lead


@pytest.mark.parametrize("id_,q", [
    ("M07", "How does your search feature handle a list of thousands of books, making it efficient for large datasets?"),            # recorded attempt: an outcome stated as fact
    ("M07", "How would your binary search behave on a million records?"),                                                               # owns a technique they never named
    ("M07", "How does the process of halving the sorted list at each step relate to the time complexity of your search feature in the library catalogue?"),
    ("M04", "How do atomicity and isolation in your money transfers ensure that concurrent transactions do not see each other's uncommitted changes?"),   # recorded attempt
    ("M04", "How does atomicity in your money transfer handling in PostgreSQL relate to ensuring data consistency in the database?"),     # recorded (Stage 10N run)
    ("M03", "How does the use of return_value and side_effect in your Flask API tests with pytest affect the behavior of your API when these values are not provided?"),
    ("M01", "How would you use cross-validation to evaluate the performance of your logistic regression model in predicting oral cancer?"),   # they built a PyTorch model, not a logistic regression
    ("M02", "How does supervised learning apply in your spam classifier?"),
])
def test_invented_implementations_and_outcomes_stay_refused(eng, id_, q):
    got, v = judge(eng, id_, q)
    assert got == "refuse", (got, v.prop and v.prop.question)


def test_claims_come_from_grammar_not_from_a_shared_topic(eng):
    x = OE.build_case(eng, copy.deepcopy(CASES["M07"]))[0]
    m = x.memory[0]
    assert not intel.implies_unclaimed_use("How would linear search affect the efficiency of your search feature?", x, m)
    assert intel.implies_unclaimed_use("How does linear search work in your search feature?", x, m)                 # stated as fact
    assert not intel.implies_unclaimed_use("How would linear search work in your search feature?", x, m)            # asked as a possibility
    assert intel.implies_unclaimed_use("Why would the linear search in your search feature be slow?", x, m)         # 'the ... in your' presupposes it, whatever the modal
    assert intel.implies_unclaimed_use("If your search feature uses binary search, how would it scale?", x, m) is False
    assert intel.implies_unclaimed_use("Your search feature uses binary search, so how does it scale?", x, m)


def test_attribution_by_handle_only_in_the_objective_engine(eng):
    """The handle is the objective engine's own construct; Stage 10N keeps its exact behaviour."""
    x = OE.build_case(eng, copy.deepcopy(CASES["M07"]))[0]
    payload = {"decision": "ask", "question": "How would linear search affect the efficiency of your search feature?", "purpose": "probe_concept", "concept_id": "S1", "memory_id": "m1", "skip_reason": "none"}
    p_obj, _ = FL.validate(dict(payload), x, "memory", profile="objective")
    p_10n, _ = FL.validate(dict(payload), x, "memory", profile="stage10n")
    assert p_obj is not None and p_obj.memory_id == "m1"
    assert p_10n is None or p_10n.memory_id is None


def test_a_handle_without_the_objective_is_still_not_memory_use(eng):
    got, v = judge(eng, "M07", "How old is your search feature?")
    assert got == "refuse", v.reasons


# ------------------------------------------------------------------------------------------------ B. accepted technical inaccuracies (recorded, full text) and the reason each is refused
@pytest.mark.parametrize("id_,q,code", [
    ("T08", "How does the logistic regression model use the sigmoid function to calculate the probability of a class for a specific input feature?", "question:narrows_collection"),
    ("T10", "What metrics would you use to evaluate the model's performance on the cases where the predicted probability is closest to the actual positive class probability?", "question:invented_qualifier"),
    ("T11", "How do hierarchical representations in a decision tree compare to the representations learned by a deep neural network when classifying images?", "question:misattributed_target"),
    ("T12", "What is the outcome when a false negative is detected in a hypothesis test?", "question:unsupported_target_event"),
    ("M03", "How would using return_value and side_effect in your Flask API tests with pytest affect the behavior of your API when the side_effect is a temporary error, and the return_value is a successful response?", "question:unsupported_effect"),
    ("N06", "In a medical test, a doctor orders a biopsy to confirm whether a patient has cancer. The test comes back positive, indicating cancer. What happens if the biopsy is actually negative, meaning the patient doesn't have cancer?", "question:asserts_interpretation"),
])
def test_recorded_inaccuracies_are_refused_for_the_right_reason(eng, id_, q, code):
    got, v = judge(eng, id_, q)
    assert got == "refuse" and any(r.startswith(code) for r in v.reasons), v.reasons


# ------------------------------------------------------------------------------------------------ valid paraphrases that must keep passing
@pytest.mark.parametrize("id_,q", [
    ("T08", "How does logistic regression turn the weighted sum of the features into a probability with the sigmoid function?"),
    ("T08", "How would doubling a single feature's value change the probability the sigmoid function gives?"),
    ("T08", "Why does logistic regression pass its linear prediction through a sigmoid function?"),
    ("T10", "Why would a ROC curve tell you more than accuracy when one class is much rarer than the other?"),
    ("T10", "How would the ROC curve and AUC show whether the model ranks positives above negatives?"),
    ("T11", "How could the early and later layers of a deep network learn increasingly abstract features of an image?"),
    ("T11", "What hierarchical representations might a deep neural network learn from raw images?"),
    ("T12", "In what situation would a test produce a false negative, and what would that cost?"),
    ("T12", "What would happen if a false negative were made in a cancer screening study?"),
    ("T12", "How would a smaller sample size change the chance of a false negative?"),
    ("M03", "How would side_effect let a test check the error handling when a dependency raises an exception?"),
    ("M03", "How would return_value and side_effect change what the mocked dependency returns in a test?"),
    ("N06", "What would a false negative look like in a medical screening test?"),
    ("T07", "How do non-linear activation functions impact the decision boundaries of a neural network?"),
    ("T03", "How does the fact that binary search has a faster time complexity than linear search affect the number of comparisons needed to determine that the target is not found in a sorted list?"),
    ("M04", "How would uncontrolled isolation in your money transfers affect the accuracy of transaction balances?"),
])
def test_valid_paraphrases_are_not_refused(eng, id_, q):
    got, v = judge(eng, id_, q)
    assert got != "refuse", v.reasons


# ------------------------------------------------------------------------------------------------ the rules in isolation
def test_rule_edges():
    assert intel.asserts_interpretation("What happens if the scan is clear, meaning the patient is healthy?")
    assert not intel.asserts_interpretation("How would raising the threshold change how often you make a Type II error, that is, a false negative?")
    assert intel._prose("see https://api.example.com/users and ```x = api()``` here").strip().startswith("see")
    assert "api" not in intel._prose("fetch https://api.example.com/users/1")


def test_m03_effect_rule_ignores_the_api_in_the_code_sample(eng):
    """The M03 reference's test snippet calls 'https://api.example.com'; that is not the rubric saying a mock changes an API."""
    x = OE.build_case(eng, copy.deepcopy(CASES["M03"]))[0]
    assert "api.example.com" in x.reference
    assert "api" not in intel.premise_support(x)


def test_t09_fallback_rejection_is_kept(eng):
    """Checked, not relaxed: the recorded fallback question builds on nothing the candidate said, and 'interpretability' is the model's own topic."""
    got, v = judge(eng, "T09", "What is the trade-off in terms of interpretability for clustering as an unsupervised task?")
    assert got == "refuse" and "question:generic_definition_request" in v.reasons


def test_live_generator_falls_back_rather_than_showing_a_recorded_inaccuracy(eng):
    x = OE.build_case(eng, copy.deepcopy(CASES["T12"]))[0]
    q = "What is the outcome when a false negative is detected in a hypothesis test?"
    calls = []

    def reply(s, u):
        calls.append(u)
        return json.dumps({"question": q})
    out = FL.LLMFollowUpGenerator(MockProvider(reply), deadline=30, engine="objective").propose(x)
    assert out.proposal is None and out.kind == "fallback" and len(calls) == 2
    assert "is not how it works" in calls[-1]                                       # the retry says why


def test_prompt_version_and_default(monkeypatch):
    monkeypatch.delenv(intel.ENV_ENGINE, raising=False)
    assert intel.engine_name() == "stage10n" and intel.OBJ_PROMPT_VERSION == "11.obj5"
    assert re.search(r"11\.obj5", (ROOT / "src" / "demo" / "intel.py").read_text(encoding="utf-8"))
