"""Stage 10E: cross-turn interview intelligence, scenarios A-E, end to end through the real engine, retrieval, memory and policy. Candidates are SCRIPTED and the optional language model is a
rule-based stand-in: this proves the behaviour of the system around a model, not what a real model writes (that is measured on the user's machine)."""
import json
import re

import pytest

from src.demo import followup_llm as FL, interview as I, memory as M, opportunity_eval as OE, sim

ONC = "I developed an oral cancer classification model using PyTorch. I achieved 91% accuracy on the test set. The hardest challenge was class imbalance in the training data. I want a data science role."
EARLIER = re.compile(r"\b(earlier|previously|you mentioned|you said|you described|you explained)\b", re.I)


@pytest.fixture
def eng(tmp_path):
    return sim.offline_engine(tmp_path)


def canonical(eng, intro):
    def ans(n, q, s):
        if I.stage_of(q) == I.INTRO:
            return intro
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        return rec["canonical_answer"] if rec else "I would check it on held out data."
    return ans


# ------------------------------------------------------------------------------------------------ A. project recall
def test_A_project_recall_asks_a_grounded_question_about_the_stored_project(eng):
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 7}, canonical(eng, ONC))
    grounded = [r for r in t if r["followup_kind"] == "memory" and (r["memory_ref"] or {}).get("kind") in ("project", "challenge", "achievement")]
    assert grounded, "a later, relevant moment produced a question about the project"
    r = grounded[0]
    assert r["n"] >= 3 and any(x["n"] == 2 and x["stage"] == I.CORE for x in t), "after at least one unrelated technical question"
    item = M.get(s["memory"], r["memory_ref"]["id"])
    assert item["turn"] == 1 and item["quote"] in ONC and item["verified"] is False and r["memory_ref"]["claim_status"].startswith("candidate claim")
    text = r["question"].lower()
    assert ("oral cancer" in text or "class imbalance" in text) and any(w in text for w in ("earlier you", "you mentioned")), "the question names what the candidate said, as their statement"
    themed = ("evaluate" in text or "train" in text or "leak" in text or "deal with" in text or "decision" in text)
    assert themed, "the question is about training, evaluation, leakage or the challenge"
    assert s["status"] == "finished" and I.check_sequence(s["questions"]) == []
    assert item["referenced"] >= 1


def test_A_unrelated_questions_in_between_do_not_mention_the_project(eng):
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 7}, canonical(eng, ONC))
    refs = {r["n"] for r in t if r["memory_ref"]}
    assert len(refs) <= 4
    for r in t:
        if not r["memory_ref"] and r["stage"] != I.INTRO and r["followup_kind"] != "contradiction_clarification":
            assert not re.search(r"oral cancer|pytorch", (r["lead"] + " " + r["question"]).lower()), "no purposeless mention"


def test_A_the_model_path_may_build_on_the_same_stored_project(eng):
    """With a (scripted) language model the follow-up may cite the stored project; the citation is verified against the stored item."""
    gen = OE.scripted_generator()
    eng._followup_generator = gen
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 7, "followup_mode": "mock", "max_followups": 2}, canonical(eng, ONC))
    cited = [(i, x) for i, x in enumerate(s["questions"], 1) if x.get("memory_id") and x.get("followup_kind") in ("llm", "mock")]
    for i, x in cited:
        it = M.get(s["memory"], x["memory_id"])
        src = (s["answers"][it["turn"] - 1] or {}).get("answer", "")
        assert it is not None and it["quote"] in src and it["turn"] < i, "traceable to a real earlier candidate statement, at its own source turn (10J: later turns may be recalled too)"
        assert any(e["source"] == "interview_memory" and e["ref"] == x["memory_id"] for e in x["provenance"]["evidence"])
    assert s["status"] == "finished"


# ------------------------------------------------------------------------------------------------ B. technical continuity
LOGIT_INTRO = "Logistic regression is a model for classification. It predicts the probability of a class from input features."


def force_first_core(eng, sid, qid):
    s = eng.store.get(sid)
    rec = eng.record(qid)
    old = s["questions"][1]
    new = I._item(rec, I.CORE, selected_by="scripted scenario", matched=[], retrieval_mode="scripted", rank=1, slot="scenario")
    new["lead"] = old.get("lead") or "Now the technical part."
    s["questions"][1] = new
    eng.store.put(s)


def test_B_a_later_harder_question_builds_on_an_earlier_introductory_explanation(eng):
    s0 = eng.create({"role": "Data Scientist", "practical": False, "size": 7})
    sid = s0["id"]
    force_first_core(eng, sid, "smi-0137")
    for _ in range(14):
        s = eng.get(sid)
        if s["status"] == "finished":
            break
        i = s["current"]
        q = s["questions"][i]
        if I.stage_of(q) == I.INTRO:
            a = "I am a statistics graduate."
        elif q.get("question_id") == "smi-0137":
            a = LOGIT_INTRO
        else:
            rec = eng.record(q["question_id"]) if q.get("question_id") else None
            a = rec["canonical_answer"] if rec else "ok"
        eng.submit(sid, i + 1, a)
    s = eng.get(sid)
    qs = s["questions"]
    first = next(k for k, q in enumerate(qs) if q.get("question_id") == "smi-0137" and I.stage_of(q) == I.CORE)
    later = [(k, q) for k, q in enumerate(qs) if k > first + 1 and (q.get("provenance") or {}).get("memory_ref", {}).get("kind") == "explanation"
             and q.get("topic") == qs[first]["topic"]]
    assert later, "a later question on the same topic acknowledges the earlier explanation"
    k, q = later[0]
    assert k - first >= 2, "not the very next question: several turns later"
    assert q["difficulty"] in ("Medium", "Hard") and q["question_id"] != "smi-0137", "more advanced, not a repeat"
    assert "earlier you explained" in q["lead"].lower() and "step further" in q["lead"].lower()
    ref = q["provenance"]["memory_ref"]
    item = M.get(s["memory"], ref["id"])
    assert item["kind"] == "explanation" and item["turn"] == first + 1 and item["quote"] in LOGIT_INTRO
    asked = [x["question"] for x in qs[:k] if x.get("question")]
    assert q["question"] not in asked and I.check_sequence(qs) == []


# ------------------------------------------------------------------------------------------------ C. behavioural memory
def test_C_a_team_project_from_the_introduction_shapes_a_later_behavioural_question(eng):
    intro = "I am a statistics graduate. In my final-year team project I built a churn model with three classmates."
    star = ("In my final-year team project we had three weeks to build a model. I owned the evaluation: I wrote the comparison script and presented the results. As a result the demo ran 30% faster, and I learned to share evidence early.")

    def ans(n, q, s):
        return intro if I.stage_of(q) == I.INTRO else star
    s, t = sim.run(eng, {"role": "Data Scientist", "interview_type": "behavioural"}, ans)
    mem_q = [r for r in t if r["origin"] == "behavioural_memory"]
    assert mem_q, "a behavioural question was built on the stored project"
    r = mem_q[0]
    assert r["n"] >= 3 and "churn model" in r["question"].lower()
    assert re.search(r"disagree|contribution|responsib|outcome|result|went well|decision|learn|change", r["question"].lower()), "asks about contribution, a disagreement or an outcome"
    item = M.get(s["memory"], r["memory_ref"]["id"])
    assert item["turn"] == 1 and item["quote"] in intro
    assert sum(1 for x in t if x["origin"] == "behavioural_memory") <= 2
    assert s["status"] == "finished"


# ------------------------------------------------------------------------------------------------ D. contradiction
def test_D_two_conflicting_statements_get_a_calm_clarification_quoting_both(eng):
    def ans(n, q, s):
        if I.stage_of(q) == I.INTRO:
            return "I have two years of experience in data science. I built dashboards with Tableau."
        if n == 2:
            return "To be honest I have five years of experience in data science, and I use cross validation to check models on held out data."
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        return rec["canonical_answer"] if rec else "I would check it on held out data."
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5}, ans)
    cl = [r for r in t if r["followup_kind"] == "contradiction_clarification"]
    assert len(cl) == 1, "asked once"
    q = cl[0]["question"].lower()
    assert "two years" in q and "five years" in q, "both statements, in the candidate's own words"
    assert not re.search(r"\b(wrong|incorrect|lie|lied|false|liar|inconsistent|dishonest)\b", q)
    assert "which" in q or "clarify" in q or "help me" in q or "reconcile" in q or "?" in q


# ------------------------------------------------------------------------------------------------ E. restraint
def test_E_no_relevant_earlier_information_means_no_memory_reference(eng):
    def ans(n, q, s):
        return "I enjoy hiking and photography. I am looking for my first job." if I.stage_of(q) == I.INTRO else "I am not sure about that one."
    s, t = sim.run(eng, {"role": "Python Developer", "practical": False, "size": 5}, ans)
    assert not any(r["memory_ref"] for r in t)
    assert not any(EARLIER.search(r["lead"] + " " + r["question"]) for r in t if r["stage"] != I.INTRO), "nothing is invented to look attentive"
    assert [m["kind"] for m in s["memory"]["items"]] == [], "no role such as 'looking' is made up from 'I am looking for my first job'"


def test_E_the_only_references_are_to_real_stored_statements_and_never_to_the_irrelevant_introduction(eng):
    s, t = sim.run(eng, {"role": "Python Developer", "practical": False, "size": 5}, canonical(eng, "I enjoy hiking and photography. I am looking for my first job."))
    for r in t:
        if r["memory_ref"]:
            it = M.get(s["memory"], r["memory_ref"]["id"])
            assert it is not None and it["turn"] < r["n"] and it["quote"], "traceable"
        assert not re.search(r"hiking|photography", (r["lead"] + " " + r["question"]).lower())


def test_E_a_model_that_tries_to_invent_a_memory_is_rejected_and_the_interview_continues(eng):
    from src.evaluation.providers.mock import MockProvider

    def eager(system, user):
        quote = " ".join(re.search(r"=====BEGIN_UNTRUSTED_ANSWER_\w+=====\n(.*?)\n=====END", user, re.S).group(1).split()[:4])
        return {"decision": "ask", "skip_reason": "none", "question": "Earlier you mentioned your Kubernetes cluster; how does that relate to this?", "purpose": "apply", "concept_id": "none", "answer_quote": quote, "memory_id": "m1"}
    eng._followup_generator = FL.LLMFollowUpGenerator(MockProvider(eager), deadline=5)
    base = canonical(eng, "I enjoy hiking and photography.")

    def half(n, q, st):                                      # 10G: a fully covered answer is skipped by the rules before any model call, so give the model something left to ask about
        a = base(n, q, st)
        return a if I.stage_of(q) == I.INTRO else " ".join(a.split()[: max(6, len(a.split()) // 3)]) + "."
    s, t = sim.run(eng, {"role": "Python Developer", "practical": False, "size": 4, "followup_mode": "mock", "max_followups": 2}, half)
    assert s["status"] == "finished"
    assert not any("kubernetes" in (r["lead"] + " " + r["question"]).lower() for r in t)
    log = s["plan"].get("followup_log", [])
    assert log and all(e["outcome"] == "fallback" for e in log)
    assert any(any(x.startswith("memory:") for x in e["reasons"]) for e in log), "rejected for the invented reference, by code"


def test_E_an_unrelated_earlier_statement_is_not_offered_to_the_model(eng):
    data = OE.load()
    case = next(c for c in data["cases"] if c["id"] == "N01")
    ctx, offered, _, _ = OE.build_case(eng, case)
    assert offered == [] and ctx.memory == []
    row = OE.run_technical(eng, OE.scripted_generator(), case)
    assert not row["memory_cited"] and row["success"]
