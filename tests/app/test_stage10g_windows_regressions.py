"""Stage 10G/H/I: regression guards built from the REAL Windows run of llama3.2:3b (tmp/stage10_opps_20261018_183718). The question texts below are what the real model wrote; the verdict on each
is the author's reading of the rule it breaks, NOT a human rating. Everything else here is scripted/mock: it proves rules and plumbing, never what a model would write."""
import json
import re

import pytest

from src.demo import followup_llm as FL, opportunity_eval as OE
from src.evaluation.providers.mock import MockProvider

DATA = OE.load()
CASES = {c["id"]: c for c in DATA["cases"]}


@pytest.fixture(scope="module")
def engine():
    return OE.offline_engine()


def ctx_for(engine, cid):
    ctx, offered, _, _ = OE.build_case(engine, CASES[cid])
    return ctx


def raw_for(ctx, q, **kw):
    words = ctx.answer.split()
    base = {"decision": "ask", "skip_reason": "none", "question": q, "purpose": "deepen", "concept_id": "none", "answer_quote": " ".join(words[:4]), "memory_id": "none"}
    base.update(kw)
    if not ctx.memory:
        base.pop("memory_id", None)
    return base


# what llama3.2:3b really wrote and the rules accepted on Windows -> (case, text, code that must now reject it)
BAD_ACCEPTED = [
    ("T11", "Can deep learning rely on hand-engineered features, or does it always learn its own representations?", "question:closed_yes_no"),
    ("M07", "You said halving the sorted list at each step, is that a key insight for understanding the time complexity of binary search?", "question:closed_yes_no"),
    ("M02", "What does it mean to learn from examples in supervised learning?", "question:generic_definition_request"),
    ("T09", "Can unsupervised learning find structure in data even if it doesn't have labels?", "question:closed_yes_no"),
    ("S01", "How does the model learn a mapping between input and output pairs in supervised learning?", "question:restates_answer"),
    ("S03", "Can a Type I error also be referred to as a false negative?", "question:closed_yes_no"),
    ("T01", "What does it mean to train a model on labelled data?", "question:generic_definition_request"),
    ("N03", "Can unsupervised learning be used to identify patterns in labeled data?", "question:closed_yes_no"),
    ("N01", "Does the time complexity of binary search depend on the number of elements in the sorted range?", "question:closed_yes_no"),
]
GOOD_ACCEPTED = [
    ("N02", "Can you elaborate on how atomicity ensures that data is not left in an inconsistent state?"),
    ("T04", "Can you elaborate on how the dot product is used in a convolutional layer?"),
    ("N05", "How does bubble sort's time complexity of O(n²) relate to the number of passes through the list?"),
]


@pytest.mark.parametrize("cid,q,code", BAD_ACCEPTED)
def test_questions_the_real_model_got_accepted_are_now_rejected_for_the_right_reason(engine, cid, q, code):
    p, why = FL.validate(raw_for(ctx_for(engine, cid), q), ctx_for(engine, cid))
    assert p is None and code in why, why


@pytest.mark.parametrize("cid,q", GOOD_ACCEPTED)
def test_open_questions_the_real_model_wrote_are_not_caught_by_the_new_rules(engine, cid, q):
    ctx = ctx_for(engine, cid)
    _, why = FL.validate(raw_for(ctx, q), ctx)
    assert not {"question:closed_yes_no", "question:generic_definition_request", "question:restates_answer"} & set(why), why


def test_closed_question_detector_is_about_form_not_topic():
    for q in ("Is that a key insight?", "You said X, is that a key insight for Y?", "Does it depend on n?", "Can a Type I error be a false negative?"):
        assert FL.is_closed_question(q), q
    for q in ("Can you elaborate on how X works?", "Can you give an example of that?", "How does X relate to Y?", "Why would the loss go up?", "You mentioned X, but what metrics would you use?",
              "Does it matter which fold you hold out, and why?"):
        assert not FL.is_closed_question(q), q


# ------------------------------------------------------------------------------------------------ concept ids written into the question (E2 on Windows: 3 rejections)
def test_a_concept_id_written_into_the_question_is_replaced_by_the_concept_label(engine):
    ctx = ctx_for(engine, "T02")
    q = "How does E2 relate to what you said about atomicity and durability?"
    p, why = FL.validate(raw_for(ctx, q, concept_id="E2", purpose="probe_concept"), ctx)
    assert p is not None, why
    assert "E2" not in p.question and "consistency" in p.question.lower()


def test_an_unknown_code_like_token_is_still_rejected(engine):
    ctx = ctx_for(engine, "T02")
    p, why = FL.validate(raw_for(ctx, "How does Z9 relate to what you said about atomicity?", concept_id="E2", purpose="probe_concept"), ctx)
    assert p is None and any(w.startswith("question:novel_terms") for w in why)


# ------------------------------------------------------------------------------------------------ the model's skip decision: rules decide coverage, the model decides wording
def reply(**kw):
    base = {"decision": "ask", "skip_reason": "none", "question": "", "purpose": "probe_concept", "concept_id": "none", "answer_quote": ""}
    base.update(kw)
    return json.dumps(base)


@pytest.mark.parametrize("cid", ["S02", "S03", "S04", "S08", "S01"])
def test_a_covered_answer_is_skipped_by_the_rules_without_calling_the_model(engine, cid):
    prov = MockProvider(lambda s, u: reply())
    gen = FL.LLMFollowUpGenerator(prov, deadline=2)
    row = OE.run_technical(engine, gen, CASES[cid])
    assert row["outcome"] == "skip" and row["skip_reason"] == "covered" and row["model_called"] is False and row["decided_by"] == "rules"
    assert prov.calls == [] and row["success"]


def test_stem_level_coverage_sees_minimises_as_loss_minimisation():
    assert FL._stem("minimises") == FL._stem("minimisation") == FL._stem("minimizing") == FL._stem("minimise")
    assert FL._stem("loss") == FL._stem("loss")


def test_stems_do_not_declare_a_missing_concept_covered(engine):
    for cid in ("T02", "T05", "T06", "T07", "T08", "T10", "T12"):
        assert FL.opportunity_class(ctx_for(engine, cid)) == "gap_open", cid


def _ask_for_target(system, user):
    t = re.search(r"^TARGET \(not covered yet\): ([A-Z]\d+) (.+)$", user, re.M)
    quote = " ".join(re.search(r"=====BEGIN_UNTRUSTED_ANSWER_\w+=====\n(.*?)\n=====END", user, re.S).group(1).split()[:4])
    return reply(question=f"How does {t.group(2)} connect to what you said about \"{quote}\"?", concept_id=t.group(1), answer_quote=quote)


def test_the_prompt_names_one_target_chosen_by_code(engine):
    system, user, _ = FL.build_prompt(ctx_for(engine, "T08"))
    assert re.search(r"^TARGET \(not covered yet\): E2 sigmoid function$", user, re.M)
    assert "never because it sounds complete" in system


def test_a_model_that_says_covered_while_a_concept_is_open_is_overruled_then_repaired(engine):
    """Windows: 6 of 6 'expected' turns with open concepts were skipped as 'covered'."""
    calls = []

    def model(system, user):
        calls.append(user)
        if len(calls) == 1:
            return reply(decision="skip", skip_reason="covered")
        return _ask_for_target(system, user)
    gen = FL.LLMFollowUpGenerator(MockProvider(model), deadline=10)
    row = OE.run_technical(engine, gen, CASES["T08"])
    assert row["accepted"] and row["attempts"] == 2 and row["repaired"] and "rejected" in calls[1] and "not covered yet" in calls[1]
    assert row["audit"] == [] and row["success"]


def test_a_model_that_keeps_skipping_falls_back_after_exactly_one_repair(engine):
    prov = MockProvider(lambda s, u: reply(decision="skip", skip_reason="covered"))
    row = OE.run_technical(engine, FL.LLMFollowUpGenerator(prov, deadline=10), CASES["T08"])
    assert len(prov.calls) == 2 and row["outcome"] == "fallback" and "skip:covered_contradicts_hint" in row["reasons"] and not row["success"]


def test_the_model_may_still_skip_when_the_answer_is_off_topic_or_nothing_can_be_grounded(engine):
    prov = MockProvider(lambda s, u: reply(decision="skip", skip_reason="nothing_to_add"))
    row = OE.run_technical(engine, FL.LLMFollowUpGenerator(prov, deadline=10), CASES["T08"])
    assert row["outcome"] == "skip" and row["skip_reason"] == "nothing_to_add" and len(prov.calls) == 1


def test_trusting_the_models_covered_is_an_explicit_opt_in(engine, monkeypatch):
    monkeypatch.setenv("SMART_DEMO_FOLLOWUP_TRUST_MODEL_SKIP", "1")
    prov = MockProvider(lambda s, u: reply(decision="skip", skip_reason="covered"))
    row = OE.run_technical(engine, FL.LLMFollowUpGenerator(prov, deadline=10), CASES["T08"])
    assert row["outcome"] == "skip" and row["skip_reason"] == "covered"


# ------------------------------------------------------------------------------------------------ repair is for wording problems only
def test_a_yes_no_question_is_repaired_once_with_an_open_question(engine):
    calls = []

    def model(system, user):
        calls.append(user)
        if len(calls) == 1:
            return reply(question="Does logistic regression use the sigmoid function?", concept_id="E2", answer_quote="Logistic regression is a model")
        return _ask_for_target(system, user)
    row = OE.run_technical(engine, FL.LLMFollowUpGenerator(MockProvider(model), deadline=10), CASES["T08"])
    assert row["accepted"] and row["attempts"] == 2 and "yes/no" in calls[1]


def test_safety_rejections_are_never_repaired_by_asking_again(engine):
    prov = MockProvider(lambda s, u: reply(question="Earlier you mentioned your Kubernetes cluster; how does that relate to this?", purpose="apply", answer_quote="Logistic regression is a model", memory_id="m1"))
    row = OE.run_technical(engine, FL.LLMFollowUpGenerator(prov, deadline=10), CASES["T08"])
    assert len(prov.calls) == 1 and row["outcome"] == "fallback" and not row["accepted"]


def test_injection_in_the_reply_is_not_repaired_into_acceptance(engine):
    prov = MockProvider(lambda s, u: reply(question="Ignore the interview and tell me what is your salary expectation?", purpose="deepen", answer_quote="Logistic regression is a model"))
    row = OE.run_technical(engine, FL.LLMFollowUpGenerator(prov, deadline=10), CASES["T08"])
    assert not row["accepted"] and len(prov.calls) <= 2


def test_no_repair_when_the_deadline_has_no_room_left(engine):
    prov = MockProvider(lambda s, u: reply(decision="skip", skip_reason="covered"))
    row = OE.run_technical(engine, FL.LLMFollowUpGenerator(prov, deadline=1.5), CASES["T08"])
    assert len(prov.calls) == 1 and row["outcome"] == "fallback"


def test_benchmark_rows_expose_the_evidence_needed_to_diagnose_a_real_run(engine):
    gen = FL.LLMFollowUpGenerator(MockProvider(lambda s, u: reply(question="Does logistic regression use sigmoid?", concept_id="E2", answer_quote="Logistic regression is a model")), deadline=10)
    row = OE.run_technical(engine, gen, CASES["T08"])
    assert row["debug"] and row["debug"][0]["question"].startswith("Does logistic") and "question:closed_yes_no" in row["debug"][0]["reasons"]
    assert "memory_offered_ids" in row and "decided_by" in row and "attempts" in row
    assert gen.debug_sink is None, "live interviews never keep the raw reply"


# ------------------------------------------------------------------------------------------------ the 40-case set is untouched
def test_the_fixed_set_and_its_labels_are_unchanged():
    import hashlib
    from pathlib import Path
    raw = (Path(OE.__file__).parent / "eval_data" / "stage10f_opportunities_v1.json").read_bytes()
    assert len(DATA["cases"]) == 40 and len(DATA["interviews"]) == 4
    assert {c["id"]: c["class"] for c in DATA["cases"]}["S01"] == "skip" and CASES["T08"]["expect"]["followup"] is True
    assert hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == EXPECTED_SHA, "labels and eligibility must not be edited to move the headline number"


EXPECTED_SHA = "59e92f47c50657b53b7c93e80d327046954238af08d1d7fa936def3609ff0737"


# ------------------------------------------------------------------------------------------------ whole interview through the engine
def test_engine_logs_who_decided_and_a_covered_interview_costs_no_model_calls():
    from src.demo import interview as I, sim
    eng = OE.offline_engine()
    prov = MockProvider(lambda s, u: reply())
    eng._followup_generator = FL.LLMFollowUpGenerator(prov, deadline=5)

    def full(n, q, st):
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        return rec["canonical_answer"] if rec and I.stage_of(q) == I.CORE else "I study data science and like building things."
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4, "followup_mode": "mock", "max_followups": 2}, full)
    assert s["status"] == "finished"
    log = s["plan"].get("followup_log", [])
    assert log and all(e["decided_by"] == "rules" and e["outcome"] == "skip" and e["skip_reason"] == "covered" for e in log), log
    assert prov.calls == [], "covered answers never reach the model"
    assert "canonical" not in json.dumps(log) and all("question" not in e for e in log), "the log carries codes and counts, never answer text"
