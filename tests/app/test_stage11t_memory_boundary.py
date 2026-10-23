"""Stage 11T: the boundary between what the candidate SAID about their work and what a question ASSERTS about it.

Offline checks of code behaviour only. The memory holdout (stage11t_memory_pairs_v1.json) is on topics outside the benchmark and its expectations were written before the rules were run on it; it is
still written by the rules' author, so it is a sanity set, not independent evidence, and nothing here measures a language model or human-rated quality."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.demo import followup_llm as FL, intel, opportunity_eval as OE

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "src" / "demo" / "eval_data"
CASES = {c["id"]: c for c in OE.load()["cases"]}
HOLDOUT5 = json.loads((EVAL / "stage11t_memory_pairs_v1.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def eng():
    return OE.offline_engine()


@pytest.fixture(autouse=True)
def _vocab():
    FL.set_vocabulary_source(lambda: [])
    yield
    FL.set_vocabulary_source(None)


def case(eng, id_):
    x = OE.build_case(eng, copy.deepcopy(CASES[id_]))[0]
    return x, intel.plan_objective(x)


def holdout_ctx(it):
    m = dict(it["memory"], id="m1", text=it["memory"]["quote"], turn=1, confidence="high", reason="shared_words", score=0.5)
    q = m["quote"]
    m["lead"] = ("Earlier you said you " + q[2:].rstrip(".") + ".") if q.startswith("I ") else ("Earlier you said “" + q.rstrip(".") + "”.")
    return FL.Context(role="Engineer", stage="core", question_id="q", question=it["question"], topic=it["topic"], answer=it["answer"], domain="d", reference=it["reference"], memory=[m],
                      concepts=[{"id": i, "label": lab, "tier": "essential", "members": [lab]} for i, lab in it["concepts"]])


def outcome(q, x, o):
    v = intel.evaluate_question(q, x, o)
    return ("refuse" if v.prop is None else "mem" if v.prop.memory_id else "plain"), v


# ------------------------------------------------------------------------------------------------ a technique placed inside their work is an assertion, whatever modal verb surrounds it
@pytest.mark.parametrize("id_,q", [
    ("M03", "Why would the return_value and side_effect calls in your Flask API tests matter?"),
    ("M07", "Why would halving the sorted list in your search feature be faster than scanning it?"),
    ("M07", "How would the binary search in your search feature behave on a million records?"),
    ("M07", "How would scanning every record one by one, as a linear search does, compare with halving the list in your search feature?"),
    ("M04", "How would the atomicity you rely on in your money transfers help under load?"),
])
def test_conditional_wording_does_not_license_an_unclaimed_implementation(eng, id_, q):
    x, o = case(eng, id_)
    got, v = outcome(q, x, o)
    assert got == "refuse" and "memory:implies_unclaimed_use" in v.reasons, (got, v.reasons)


@pytest.mark.parametrize("id_,q", [
    ("M03", "If one of your Flask API tests had to fake a database call, how would return_value and side_effect let you control what it returns or raises?"),
    ("M07", "If your search feature scanned every record with a linear search, how would its cost grow with the catalogue size?"),
])
def test_a_genuine_hypothetical_about_their_work_is_attributed_by_code(eng, id_, q):
    x, o = case(eng, id_)
    got, v = outcome(q, x, o)
    assert got == "mem", v.reasons
    assert v.prop.memory_id == x.memory[0]["id"] and v.prop.validity["decided_by"] == "code"


def test_a_property_every_such_thing_has_is_not_an_implementation_claim(eng):
    """'the ROC curve OF your classifier' names a property any classifier has; only 'in your', 'inside your', 'you rely on' and the like place a choice inside their work."""
    assert intel.asserted_in_work("How would the ROC curve of your oral cancer classifier look?") == set()
    assert intel.asserted_in_work("How does the halving in your answer reduce the work?") == set()      # their own words this turn
    assert intel.asserted_in_work("Why would the cache in your service evict entries?") != set()


# ------------------------------------------------------------------------------------------------ M01 / M06: no "Earlier you said ..." in front of a question that already names the work
@pytest.mark.parametrize("id_,q", [
    ("M06", "Which features would the early and later layers of your tumour detection network learn, and why would that hierarchy help?"),
    ("M01", "How would the ROC curve and AUC show how well your oral cancer classifier separates the two classes?"),
])
def test_lead_is_dropped_when_the_question_names_the_work_in_their_words(eng, id_, q):
    x, o = case(eng, id_)
    got, v = outcome(q, x, o)
    assert got == "mem" and v.prop.lead is None, (got, v.reasons)
    assert v.prop.memory_id == "m1", "dropping the sentence keeps the provenance"


def test_lead_is_kept_when_the_question_does_not_say_which_work(eng):
    x, o = case(eng, "M04")
    got, v = outcome("If two transfers ran at the same time, what could go wrong without isolation between the transactions in your billing work?", x, o)
    assert got in ("mem", "plain")
    if got == "mem":
        assert v.prop.lead, "one shared word ('billing') does not say which work, so the lead stays"
    assert not intel.names_the_work("How would isolation help your model?", x.memory[0])


# ------------------------------------------------------------------------------------------------ M05: an explanation is not their work
def test_an_explained_concept_is_never_turned_into_their_own_work(eng):
    x, o = case(eng, "M05")
    assert x.memory[0]["kind"] not in FL.OWN_WORK_KINDS
    got, v = outcome("How does the sigmoid function in your logistic regression model relate to maximum likelihood estimation?", x, o)
    assert got == "refuse"
    assert intel.explained_as_owned("How would your logistic regression model change?", x.memory[0])
    assert not intel.explained_as_owned("How does your explanation of the sigmoid function connect to the likelihood?", x.memory[0])


# ------------------------------------------------------------------------------------------------ "both A and B" said of one thing
@pytest.mark.parametrize("q,bad", [
    ("How does a significance level hold when the null hypothesis is both true and false?", True),
    ("Can the result be true and false at the same time?", True),
    ("How would a sample with both positive and negative examples change the ROC curve?", False),
    ("How would a test set with both sorted and unsorted inputs change the cost?", False),
])
def test_both_opposites_in_one_predicate_is_a_contradiction_but_a_mixed_set_is_not(q, bad):
    assert bool(intel.contradictory_premise(q)) == bad


# ------------------------------------------------------------------------------------------------ the memory holdout: expected outcome per question, written before the rules ran
GOOD = [(it["id"], g["q"], g["expect"]) for it in HOLDOUT5["items"] for g in it["good"]]
BAD = [(it["id"], b["q"], b.get("known_gap", False)) for it in HOLDOUT5["items"] for b in it["bad"]]
ITEMS = {it["id"]: it for it in HOLDOUT5["items"]}
KNOWN_FALSE_REJECTIONS = {"How would a 0.05 significance level relate to whether a 95% confidence interval for the effect includes zero?"}   # '95' appears in no source: the no-invented-figures rule


@pytest.mark.parametrize("id_,q,expect", GOOD, ids=[g[1][:40] for g in GOOD])
def test_memory_holdout_good_questions(id_, q, expect):
    x = holdout_ctx(ITEMS[id_])
    got, v = outcome(q, x, intel.plan_objective(x))
    if q in KNOWN_FALSE_REJECTIONS:
        assert got == "refuse", "a known false rejection that disappears must be re-examined, not silently counted"
        return
    assert got == expect, v.reasons


@pytest.mark.parametrize("id_,q,known_gap", BAD, ids=[b[1][:40] for b in BAD])
def test_memory_holdout_bad_questions(id_, q, known_gap):
    x = holdout_ctx(ITEMS[id_])
    got, v = outcome(q, x, intel.plan_objective(x))
    if not known_gap:
        assert got == "refuse", (got, v.prop and v.prop.question)


def test_memory_holdout_counts():
    """The rates this file reports, so a change in either direction is visible."""
    fr = fa = 0
    for id_, q, expect in GOOD:
        x = holdout_ctx(ITEMS[id_])
        fr += outcome(q, x, intel.plan_objective(x))[0] != expect
    for id_, q, _ in BAD:
        x = holdout_ctx(ITEMS[id_])
        fa += outcome(q, x, intel.plan_objective(x))[0] != "refuse"
    assert (len(GOOD), len(BAD)) == (7, 11)
    assert fr <= 1 and fa == 0, (fr, fa)


# ------------------------------------------------------------------------------------------------ nothing frozen moved, and the default is unchanged
def test_frozen_fixture_and_default_engine_unchanged(monkeypatch):
    raw = (EVAL / "stage10f_opportunities_v1.json").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == "59e92f47c50657b53b7c93e80d327046954238af08d1d7fa936def3609ff0737"
    monkeypatch.delenv(intel.ENV_ENGINE, raising=False)
    assert intel.engine_name() == "stage10n"


# ------------------------------------------------------------------------------------------------ N06: two names the rubric says are one thing
@pytest.mark.parametrize("q,refused", [
    ("How does a false negative affect the outcome of a Type II error?", True),                     # shown in the real 11.obj2 run
    ("How does a Type II error influence the number of false negatives?", True),
    ("How would raising the significance threshold change how often you make a Type II error, that is, a false negative?", False),   # a gloss, not a relation
    ("How would a smaller sample size change the chance of a false negative?", False),
    ("In what situation would a test produce a false negative, and what would that cost?", False),
])
def test_relating_a_concept_to_itself_under_its_other_name_is_circular(eng, q, refused):
    x, o = case(eng, "N06")
    assert {(a["label"], b["label"]) for a, b in intel.equated_pairs(x)} == {("Type I error", "false positive"), ("Type II error", "false negative")}
    got, v = outcome(q, x, o)
    assert (got == "refuse") == refused, v.reasons
    if refused:
        assert any(r.startswith(("question:relates_equated_pair", "question:false_premise")) for r in v.reasons), v.reasons


def test_equated_pairs_come_only_from_an_explicit_equation_in_the_reference(eng):
    x, _ = case(eng, "T11")                 # "deep learning ... uses neural networks to learn hierarchical representations" says one USES the other
    assert intel.equated_pairs(x) == []
