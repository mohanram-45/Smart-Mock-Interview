"""Stage 12 live-evaluation correction (22-23 Oct 2026). The REAL qwen2.5:7b run matched 0/3 expected verdicts. These tests pin the causes found in its recorded outputs:

  1. a "contradiction" whose explanation only says the reference does not MENTION something, backed by a quote that is the whole reference (absence is not contradiction);
  2. the same finding re-judged by nobody: now a second, independent model call must say "contradicts";
  3. a requirement that merely restates the question's subject blocking or rescuing a verdict;
  4. a group credit ("any of clustering / dimensionality reduction / ...") given although no member is named in the answer;
  5. one false claim next to one right idea being called "incorrect", and one wrong sentence being counted twice.

Everything here is SCRIPTED (stand-in model replies). It proves the rules, not model quality; the live re-run is verify_ollama_stage12.bat.
The recorded replies below are copied from tmp/stage12_live/results.json.
"""
from __future__ import annotations

import json

import pytest

from src.demo import assessment as A
from src.evaluation.modular import contradictions as CX
from src.evaluation.providers.base import ProviderResponse

REF = ("Autoencoder is an artificial neural network. It can learn representation for a set of data without any supervision. The network automatically learns by copying "
       "its input to the output; typically, the internal representation consists of smaller dimensions than the input vector. As a result, they can learn efficient ways of representing the data.")
Q = "What do you understand by Autoencoder?"
CORE = {"stage": "core", "question": Q}


class P:
    model, is_mock, paid = "scripted", True, False

    def __init__(self, found, confirm="contradicts", boom=False):
        self.found, self.confirm, self.boom, self.response_schema, self.n_confirm = found, confirm, boom, None, 0

    def generate(self, system, user):
        if system == CX.CONFIRM_SYSTEM:
            self.n_confirm += 1
            if self.boom:
                raise TimeoutError("slow")
            return ProviderResponse(json.dumps({"verdict": self.confirm}), self.model, 1.0, {})
        return ProviderResponse(json.dumps({"contradictions": self.found}), self.model, 1.0, {})


# ---------------------------------------------------------------- 1. the recorded false allegations (correct paraphrase) are rejected by the code, not by luck
RECORDED_FALSE = [
    {"claim_id": "c1", "reference_quote": REF[:REF.index("As a result")].strip(), "why": "The reference does not mention a narrow bottleneck layer."},
    {"claim_id": "c2", "reference_quote": "It can learn representation for a set of data without any supervision", "why": "The reference does not state that the autoencoder needs no labels."},
]
PARAPHRASE = [{"id": "c1", "text": "It is a network trained to reproduce its own input through a narrow bottleneck layer."},
              {"id": "c2", "text": "Because the target is the input itself it needs no labels, and the bottleneck forces it to learn a compact code of the data."}]


def test_recorded_false_allegations_are_rejected_for_the_right_reasons():
    r = CX.verify({"contradictions": RECORDED_FALSE}, REF, PARAPHRASE)
    assert r["items"] == []
    assert [x["reason"] for x in r["rejected"]] == ["quote_too_broad", "absence_is_not_contradiction"]


@pytest.mark.parametrize("why", ["The reference does not mention it.", "Not mentioned in the reference.", "The reference doesn't specify this.", "No mention of this anywhere.",
                                 "The reference is silent on this.", "The reference fails to include that."])
def test_absence_wording_is_never_a_contradiction(why):
    r = CX.verify({"contradictions": [{"claim_id": "c2", "reference_quote": "It can learn representation for a set of data without any supervision", "why": why}]}, REF, PARAPHRASE)
    assert r["items"] == [] and r["rejected"][0]["reason"] == "absence_is_not_contradiction"


def test_a_genuine_statement_of_the_opposite_is_still_accepted():
    claims = [{"id": "c1", "text": "An autoencoder always needs labelled training data to learn."}]
    ok = {"claim_id": "c1", "reference_quote": "It can learn representation for a set of data without any supervision", "why": "The reference says no supervision is needed."}
    r = CX.verify({"contradictions": [ok]}, REF, claims)
    assert [i["claim_id"] for i in r["items"]] == ["c1"]
    assert not CX._ABSENCE.search("Autoencoders do not always need labelled data.")            # a negation inside a real contradiction is not "absence"


# ---------------------------------------------------------------- 2. the second, independent call
def test_second_check_drops_a_finding_the_model_calls_consistent():
    p = P([{"claim_id": "c2", "reference_quote": "It can learn representation for a set of data without any supervision", "why": "Both describe training without labels."}], confirm="consistent")
    r = CX.check(p, Q, REF, PARAPHRASE)
    assert r["status"] == "checked" and r["items"] == [] and r["rejected"][-1]["reason"] == "second_check_consistent" and p.n_confirm == 1


def test_second_check_keeps_a_confirmed_contradiction_and_marks_it():
    claims = [{"id": "c1", "text": "An autoencoder always needs labelled training data to learn."}]
    p = P([{"claim_id": "c1", "reference_quote": "It can learn representation for a set of data without any supervision", "why": "The reference says no supervision is needed."}])
    r = CX.check(p, Q, REF, claims)
    assert r["status"] == "checked" and r["items"][0]["confirmed"] is True and r["version"] == "12.c2"


def test_a_failed_second_check_is_an_error_never_a_clean_result():
    claims = [{"id": "c1", "text": "An autoencoder always needs labelled training data to learn."}]
    p = P([{"claim_id": "c1", "reference_quote": "It can learn representation for a set of data without any supervision", "why": "The reference says no supervision is needed."}], boom=True)
    r = CX.check(p, Q, REF, claims)
    assert r["status"] == "error" and r["items"] == [] and "confirmation_failed" in r["error"]
    a = {"answer": "x " * 20, "skipped": False, "legacy": {}, "terms": {}, "modular": {"mode": "live", "status": "done", "view": _view([_o("alpha", "essential", "satisfied")], cx=r)}}
    assert A.assess(a, CORE)["verdict"] == "uncertain"                                         # satisfied requirements + an unchecked contradiction pass = not "correct"


def test_confirmation_sees_only_the_claim_and_the_quoted_sentence():
    seen = []

    class Spy(P):
        def generate(self, system, user):
            if system == CX.CONFIRM_SYSTEM:
                seen.append(user)
            return super().generate(system, user)

    claims = [{"id": "c1", "text": "An autoencoder always needs labelled training data to learn."}]
    CX.check(Spy([{"claim_id": "c1", "reference_quote": "It can learn representation for a set of data without any supervision", "why": "No supervision is needed."}]), Q, REF, claims)
    assert "labelled training data" in seen[0] and "without any supervision" in seen[0] and "copying its input" not in seen[0]


# unseen genuine false claims keep being found (other topics, other wording)
@pytest.mark.parametrize("ref,claim,quote", [
    ("Unsupervised learning finds structure in data that has inputs X but no target labels.", "Unsupervised learning requires every sample to have a target label.", "finds structure in data that has inputs X but no target labels"),
    ("Reject H0 if p < alpha, otherwise fail to reject H0 (which is not proof that H0 is true).", "A large p-value proves the null hypothesis is true.", "which is not proof that H0 is true"),
    ("A mutable default argument is created once, when the function is defined.", "A mutable default argument is created fresh on every call.", "is created once, when the function is defined"),
])
def test_unseen_genuine_false_claims_are_still_detected(ref, claim, quote):
    p = P([{"claim_id": "c1", "reference_quote": quote, "why": "The reference says the opposite."}])
    r = CX.check(p, "Q", ref, [{"id": "c1", "text": claim}])
    assert r["status"] == "checked" and len(r["items"]) == 1


# unseen correct paraphrases: even if the first model pass is wrong in the recorded way, nothing survives
@pytest.mark.parametrize("claim,quote,why", [
    ("Training needs no human-provided targets because the network learns from its own input.", "It can learn representation for a set of data without any supervision", "The reference does not describe the training targets."),
    ("It squeezes the data through a small hidden layer and rebuilds it.", "typically, the internal representation consists of smaller dimensions than the input vector", "Reference never mentions a hidden layer."),
])
def test_unseen_correct_paraphrases_are_not_flagged(claim, quote, why):
    p = P([{"claim_id": "c1", "reference_quote": quote, "why": why}], confirm="consistent")
    r = CX.check(p, Q, REF, [{"id": "c1", "text": claim}])
    assert r["items"] == []


def test_paraphrase_survives_even_if_the_wording_check_is_passed_but_the_second_call_disagrees():
    p = P([{"claim_id": "c1", "reference_quote": "typically, the internal representation consists of smaller dimensions than the input vector", "why": "The reference gives a different size."}], confirm="unrelated")
    assert CX.check(p, Q, REF, [{"id": "c1", "text": "It squeezes the data through a small hidden layer and rebuilds it."}])["items"] == []


# ---------------------------------------------------------------- 3. assessment rules
def _o(label, tier, status, kind="concept", **detail):
    o = {"requirement_id": label[:2], "label": label, "tier": tier, "kind": kind, "status": status}
    if detail:
        o["detail"] = detail
    return o


def _view(outcomes, cx=None, errors=()):
    return {"status": "advisory_only", "outcomes": outcomes, "feedback": {"factual_errors": list(errors)}, "source": {"tags": []}, "safeguards": {"applied": []},
            "contradictions": cx or {"status": "checked", "items": []}, "taxonomy": {}}


def _stored(outcomes, answer, cx=None, errors=()):
    return {"answer": answer, "skipped": False, "legacy": {"status": "scored", "score": 50.0}, "terms": {"found": ["x"], "missing": []},
            "modular": {"mode": "live", "status": "done", "view": _view(outcomes, cx, errors)}}


PARA_ANSWER = "It is a network trained to reproduce its own input through a narrow bottleneck layer. Because the target is the input itself it needs no labels."


def test_recorded_paraphrase_outcomes_are_correct_not_incorrect():
    """The recorded outcomes of the live paraphrase run, with the (now rejected) false allegations removed: the topic-word requirement 'autoencoder' was unverified."""
    outs = [_o("autoencoder", "essential", "undetermined"), _o("artificial neural network", "essential", "satisfied"), _o("representation learning", "supporting", "satisfied")]
    r = A.assess(_stored(outs, PARA_ANSWER), CORE)
    assert (r["verdict"], r["reason"]) == ("correct", "all_essential_demonstrated") and r["unverified_concepts"] == []


def test_topic_word_requirement_never_rescues_a_wrong_or_empty_answer():
    outs = [_o("autoencoder", "essential", "undetermined"), _o("artificial neural network", "essential", "missing")]
    assert A.assess(_stored(outs, "Something about neural things."), CORE)["verdict"] == "incorrect"
    outs = [_o("autoencoder", "essential", "undetermined"), _o("artificial neural network", "essential", "undetermined")]
    assert A.assess(_stored(outs, "Something."), CORE)["verdict"] == "uncertain"


def test_topic_word_requirement_does_not_apply_to_other_questions():
    outs = [_o("clustering", "essential", "undetermined"), _o("unlabelled data", "essential", "satisfied")]
    assert A.assess(_stored(outs, "No labels are used."), {"stage": "core", "question": "What is unsupervised learning?"})["verdict"] == "uncertain"


def test_one_false_claim_next_to_a_right_idea_is_partially_correct():
    cx = {"status": "checked", "items": [{"claim": "It always needs labelled training data.", "why": "no", "reference_quote": "without any supervision", "confirmed": True}]}
    outs = [_o("autoencoder", "essential", "satisfied"), _o("artificial neural network", "essential", "undetermined")]
    r = A.assess(_stored(outs, "An autoencoder is a neural network. It always needs labelled training data.", cx), CORE)
    assert (r["verdict"], r["reason"]) == ("partially_correct", "misconception")
    assert A.assess(_stored([_o("autoencoder", "essential", "satisfied")], "x", {"status": "checked", "items": cx["items"] + [{**cx["items"][0], "claim": "Another wrong one."}]}), CORE)["verdict"] == "incorrect"


def test_one_wrong_sentence_found_twice_counts_once():
    err = {"concept": "a", "your_words": ["It always needs labelled training data."], "why_wrong": "x", "reference_says": "y", "severity": "major"}
    cx = {"status": "checked", "items": [{"claim": "It always needs labelled training data.", "why": "no", "reference_quote": "q", "confirmed": True}]}
    r = A.assess(_stored([_o("alpha", "essential", "satisfied")], "Alpha is x. It always needs labelled training data.", cx, [err, {**err, "concept": "b"}]), CORE)
    assert len(r["misconceptions"]) == 1 and r["verdict"] == "partially_correct"


# group credit
def _group(status, members):
    return _o("an unsupervised task", "essential", status, kind="group", min_required=1, correct_members=members, unverified_members=[], incorrect_members=[], other_valid_absent_confirmed=True)


SHORT = "Unsupervised learning is a type of machine learning where the model finds patterns and structures in data without labelled outputs."
Q2 = {"stage": "core", "question": "What is unsupervised Learning?"}


def test_group_credit_without_a_named_member_is_not_credit():
    """The live run credited 'an unsupervised task' to an answer that names no task."""
    for members in (["dimensionality reduction"], ["pattern discovery"], ["clustering"], []):
        r = A.assess(_stored([_o("unlabelled data", "essential", "satisfied"), _group("satisfied", members)], SHORT), Q2)
        assert r["verdict"] == "uncertain" and "an unsupervised task" in r["unverified_concepts"], members


def test_group_credit_with_a_named_member_stands():
    ans = "It looks for structure in unlabelled data, for example grouping customers with clustering."
    r = A.assess(_stored([_o("unlabelled data", "essential", "satisfied"), _group("satisfied", ["clustering"])], ans), Q2)
    assert r["verdict"] == "correct"
    ans2 = "It works without labels and does dimensionality reduction such as PCA."
    assert A.assess(_stored([_o("unlabelled data", "essential", "satisfied"), _group("satisfied", ["dimensionality reduction"])], ans2), Q2)["verdict"] == "correct"


def test_group_downgrade_does_not_touch_stored_data_and_old_sessions_without_members_still_assess():
    outs = [_o("unlabelled data", "essential", "satisfied"), {**_group("satisfied", ["clustering"]), "detail": {"min_required": 1}}]
    snap = json.dumps(outs, sort_keys=True)
    assert A.assess(_stored(outs, SHORT), Q2)["verdict"] == "correct"
    assert json.dumps(outs, sort_keys=True) == snap


def test_abstract_single_concepts_keep_credit_for_different_wording():
    """No lexical test on single concepts: 'unlabelled data' credited to 'without labelled outputs' (or any paraphrase) stays credited."""
    r = A.assess(_stored([_o("unlabelled data", "essential", "satisfied"), _o("artificial neural network", "essential", "satisfied")], "It learns from inputs with no targets given."), Q2)
    assert r["verdict"] == "correct"


def test_similarity_still_never_decides():
    outs = [_o("alpha", "essential", "satisfied")]
    assert {A.assess({**_stored(outs, "alpha"), "legacy": {"status": "scored", "score": s}}, CORE)["verdict"] for s in (0, 50, 99)} == {"correct"}


def test_independent_set_is_live_only_and_the_failed_run_is_not_rewritten():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("s12c", Path(__file__).resolve().parents[2] / "scripts" / "stage12_assess_answers.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ind = [c for c in m.CASES if c["id"].startswith("ind_")]
    assert len(ind) == 6 and all(c["live_only"] for c in ind)
    assert {r["id"] for r in m.run(live=False)["rows"]}.isdisjoint({c["id"] for c in ind})          # a scripted stand-in is never reported for them
    exp = {c["id"]: c["expected"] for c in m.CASES if c["id"] in ("autoencoder_misconception", "autoencoder_paraphrase", "unsupervised_short")}
    assert exp == {"autoencoder_misconception": "partially_correct", "autoencoder_paraphrase": "correct", "unsupervised_short": "partially_correct"}   # labels unchanged
