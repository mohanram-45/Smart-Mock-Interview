"""Stage 10C: the adaptive interview policy. Deterministic tests with scripted candidates; model output is a scripted MockProvider (no real model). They prove structure, safety, restraint and
fallbacks, NOT that any model asks better questions (see docs/STAGE10_MODEL_AND_POLICY.md and the Windows validation plan)."""
import json
import re
import time

import pytest

from src.demo import followup_llm as FL, interview as I, memory as M, policy as POL, sim
from src.demo.routes import set_engine
from src.evaluation.errors import ProviderUnavailable
from src.evaluation.providers.mock import MockProvider
from tests.app.test_stage4a_demo import make_engine

INTRO = "I developed an oral cancer classification model using PyTorch. I achieved 91% accuracy on the test set."


@pytest.fixture()
def eng(tmp_path, monkeypatch):
    for v in ("SMART_DEMO_LIVE_MODULAR", "SMART_RETRIEVAL_EXPOSE_REFERENCE", "SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC"):
        monkeypatch.delenv(v, raising=False)
    e = make_engine(tmp_path)
    set_engine(e)
    yield e
    set_engine(None)


def strong(eng):
    def ans(n, q, s):
        if I.stage_of(q) == I.INTRO:
            return "I work on data problems."
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        return rec["canonical_answer"] if rec else "I would explain it with an example."
    return ans


def weak(n, q, s):
    return "I work on data problems." if I.stage_of(q) == I.INTRO else "I am not sure, maybe it depends."


def levels(s):
    return [I.DIFFICULTIES.index(q["difficulty"]) for q in s["questions"] if I.stage_of(q) == I.CORE]


# ------------------------------------------------------------------------------------------------ signals and decisions
def rec(concepts=("cross validation", "held out", "overfitting")):
    return {"question": "q", "key_concepts": list(concepts), "canonical_answer": "x", "domain": "d", "topic": "t"}


def test_signal_bands_describe_evidence_in_the_text_not_correctness():
    r = rec()
    long_hit = "You use cross validation and a held out set to detect overfitting in the model. " * 2
    assert POL.band(POL.signals(r, long_hit)) == "strong"
    assert POL.band(POL.signals(r, "Cross validation is one way people evaluate models in many settings today.")) == "partial"
    assert POL.band(POL.signals(r, "I am not sure, maybe it depends on the data we have.")) == "weak"
    assert POL.band(POL.signals(r, "I would rather not answer that.")) == "refused"
    assert POL.band(POL.signals(None, "A long answer with no reference record to compare against at all here.")) == "unknown"


def sess(difficulty="Medium", n_more=2, created=None):
    qs = [{"stage": "core", "question": "q0", "difficulty": difficulty}] + [{"stage": "core", "question": f"q{k}", "difficulty": "Medium"} for k in range(1, n_more + 1)]
    return {"questions": qs, "answers": [{"x": 1}] + [None] * n_more, "plan": {}, "created_at": created or "2999-01-01T00:00:00+00:00", "memory": M.new_memory()}


def test_decision_priority_and_difficulty_steps():
    s = sess("Medium")
    strong_sig = {"words": 40, "coverage": 0.9, "uncertain": False, "refused": False, "short": False, "found": 3, "total": 3}
    weak_sig = {**strong_sig, "coverage": 0.0, "found": 0, "uncertain": True}
    d = POL.decide(s, 0, strong_sig, has_open_contradiction=False, revisit_available=False)
    assert d["decision"] == "deeper" and d["step"] == 2
    d = POL.decide(s, 0, weak_sig, has_open_contradiction=False, revisit_available=False)
    assert d["decision"] == "new_competency" and d["step"] == 0 and "little_evidence_in_text" in d["reasons"]
    d = POL.decide(s, 0, {**strong_sig, "refused": True}, has_open_contradiction=False, revisit_available=False)
    assert d["decision"] == "new_competency" and "candidate_declined" in d["reasons"]
    assert POL.decide(s, 0, strong_sig, has_open_contradiction=True, revisit_available=False)["decision"] == "clarify"
    assert POL.decide(s, 0, strong_sig, has_open_contradiction=False, revisit_available=True)["decision"] == "revisit"
    s["plan"]["time_budget_s"] = 1
    s["created_at"] = "2000-01-01T00:00:00+00:00"
    d = POL.decide(s, 0, strong_sig, has_open_contradiction=True, revisit_available=True)
    assert d["decision"] == "wrapup" and "time_budget" in d["reasons"], "time outranks everything else"


def test_decisions_are_logged_as_codes_without_candidate_text(eng):
    s, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4}, strong(eng))
    log = s["plan"]["policy_log"]
    assert log and all(set(e) <= {"n", "stage", "type", "decision", "reasons", "target", "replaced", "memory_ref", "truncated", "coverage_band", "probe"} for e in log)
    blob = json.dumps(log)
    assert "canonical" not in blob and all(len(str(v)) < 80 for e in log for v in e.values() if isinstance(v, str))


# ------------------------------------------------------------------------------------------------ adaptivity
def test_a_strong_candidate_is_moved_up_and_a_struggling_one_is_eased(eng):
    hi, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5}, strong(eng))
    lo, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5}, weak)
    assert max(levels(hi)) == 2 and levels(hi)[-1] >= levels(hi)[0]
    assert sum(levels(lo)) < sum(levels(hi)) and levels(lo)[-1] <= 1
    assert all(e.get("target") in (None, "Easy", "Medium", "Hard") for e in hi["plan"]["policy_log"])


def test_adaptation_never_repeats_or_reorders_what_was_already_asked(eng):
    s, t = sim.run(eng, {"role": "Python Developer", "practical": False, "size": 5}, strong(eng))
    qs = [x["question"] for x in s["questions"] if I.stage_of(x) in (I.CORE, I.FOLLOW_UP)]
    assert len({x.lower() for x in qs}) == len(qs)
    ids = [x["question_id"] for x in s["questions"] if I.stage_of(x) == I.CORE]
    assert len(ids) == len(set(ids)) and I.check_sequence(s["questions"]) == []
    for x in s["questions"]:
        if x.get("origin") == "adaptive_bank":
            assert x["provenance"]["selected_by"].startswith("adaptive policy") and eng.record(x["question_id"])["question"] == x["question"], "wording always comes from the vetted bank"


def test_domain_coverage_is_kept_for_the_role(eng):
    s, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 6}, strong(eng))
    doms = {x["domain"] for x in s["questions"] if I.stage_of(x) == I.CORE}
    assert len(doms) >= 2


def test_confidently_wrong_and_alternative_valid_answers_are_never_called_wrong(eng):
    wrong = "Cross validation is always exactly 100 percent accurate and you should never use a test set because overfitting does not exist in modern models at all."
    alt = "I would hold back a slice of patients, train on the rest, and rotate which slice is held back, then compare the average error across the rotations."

    def make(text):
        return lambda n, q, s: "I work on data problems." if I.stage_of(q) == I.INTRO else text
    for text in (wrong, alt):
        s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4}, make(text))
        shown = " ".join(r["lead"] + " " + r["question"] for r in t).lower()
        assert not re.search(r"\b(wrong|incorrect|mistake|false|that is not right)\b", shown)
        log = s["plan"]["policy_log"]
        assert all(e.get("decision") != "deeper" or e.get("coverage_band") == "strong" for e in log), "the policy never rewards unsupported confidence"
    s, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4}, make(wrong))
    assert all(e.get("coverage_band") != "strong" for e in s["plan"]["policy_log"] if e["stage"] == "core"), "a fluent wrong answer shows no key-concept evidence, so it is not treated as strong"


def test_candidate_who_changes_topic_or_answers_off_topic_gets_standard_handling(eng):
    off = "My favourite colour is green and I enjoy hiking on weekends with my dog near the river."
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4}, lambda n, q, st: "I work on data problems." if I.stage_of(q) == I.INTRO else off)
    assert s["status"] == "finished" and all(e.get("coverage_band") in (None, "weak", "unknown", "partial") for e in s["plan"]["policy_log"])
    assert not [r for r in t if r["memory_ref"]], "off-topic content creates no false memory links"


# ------------------------------------------------------------------------------------------------ time, availability, fallbacks
def test_time_budget_moves_the_interview_towards_wrap_up(eng):
    s = eng.create({"role": "Data Scientist", "practical": True, "size": 6, "time_budget_min": 1})
    sid = s["id"]
    eng.submit(sid, 1, "I work on data problems.")
    cur = eng.get(sid)
    cur["created_at"] = "2000-01-01T00:00:00+00:00"                      # the clock says the budget is long gone
    n_before = len(cur["questions"])
    eng.submit(sid, 2, strong(eng)(2, cur["questions"][1], cur))
    done = eng.get(sid)
    assert done["status"] == "finished" and done["plan"]["ended_reason"] == "time_budget"
    assert len(done["questions"]) < n_before and I.check_sequence(done["questions"]) == []
    assert any(e["decision"] == "wrapup" and "time_budget" in e["reasons"] for e in done["plan"]["policy_log"])


def test_a_thin_bank_keeps_the_planned_question(eng, monkeypatch):
    monkeypatch.setattr(POL, "pick_next_core", lambda *a, **k: None)
    monkeypatch.setattr(POL, "continuity_pick", lambda *a, **k: None)           # both selectors draw on the same vetted bank
    s, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 3}, strong(eng))
    assert s["status"] == "finished" and not any(x.get("origin") == "adaptive_bank" for x in s["questions"])


def test_a_broken_policy_never_breaks_the_interview(eng, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("policy bug")
    monkeypatch.setattr(POL, "decide", boom)
    s, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 3}, strong(eng))
    assert s["status"] == "finished" and any("error:RuntimeError" in str(e) for e in s["plan"]["policy_log"])


def test_adaptive_false_restores_the_fixed_sequence(eng):
    s = eng.create({"role": "Data Scientist", "practical": False, "size": 4, "adaptive": False})
    ids = [q["question_id"] for q in s["questions"]]
    sim_s, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4, "adaptive": False}, strong(eng))
    assert not any(q.get("origin") == "adaptive_bank" for q in sim_s["questions"]) and ids


class Down:
    def propose(self, ctx):
        raise ProviderUnavailable("ollama is not running")


def test_ollama_outage_falls_back_to_deterministic_follow_ups(eng):
    eng._followup_generator = Down()
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4, "followup_mode": "mock"}, lambda n, q, st: "short" if I.stage_of(q) != I.INTRO else "I work on data problems.")
    assert s["status"] == "finished"
    log = s["plan"].get("followup_log", [])
    assert log and all(e["outcome"] == "fallback" for e in log)
    assert any(r["origin"] == "follow_up" and r["followup_kind"] == "expand_short" for r in t), "the deterministic follow-up took over"


# ------------------------------------------------------------------------------------------------ the model may word a memory-based follow-up, but only inside the verified frame
def smart_reply(system, user):
    ans = re.search(r"=====BEGIN_UNTRUSTED_ANSWER_\w+=====\n(.*?)\n=====END", user, re.S).group(1)
    quote = " ".join(ans.split()[:5])
    mem = re.search(r"^EARLIER \(turn \d+, .*?id (m\d+)\)", user, re.M)
    cid = re.search(r"^([A-Z]\d+) ", user, re.M)
    if not mem:
        return {"decision": "skip", "question": "", "purpose": "deepen", "concept_id": "none", "answer_quote": "", "uses_given_facts_only": True, "already_in_answer": False}
    tgt = re.search(r"^TARGET \(not covered yet\): \S+ (.+)$", user, re.M)
    use = re.search(r"^USE \(.*?\): (.+)$", user, re.M)
    words = [w.strip() for w in use.group(1).split(",")][:2] if use else []
    # 10N Windows repair: a model that is offered an earlier statement writes about THAT statement (the prompt hands it the statement's own words on the USE line). The old script always wrote about the oral
    # cancer project, which only matched when retrieval happened to offer the project; when it offered another statement (an accuracy claim, a challenge) the question was correctly judged unconnected to it
    # and the citation dropped (memory_stage not_connected). Which statement is offered depends on the core question the ranking chose, so the script must follow what it is offered.
    q = f"How does {tgt.group(1) if tgt else quote} apply when you think about {' and '.join(words)}?" if words else f"How does {tgt.group(1) if tgt else quote} apply to the work you described?"
    return {"decision": "ask", "question": q, "purpose": "apply", "concept_id": "none", "answer_quote": quote, "uses_given_facts_only": True, "already_in_answer": False, "memory_id": mem.group(1)}


def test_model_follow_up_may_cite_a_stored_memory_and_is_logged_with_it(eng):
    prov = MockProvider(smart_reply)
    eng._followup_generator = FL.LLMFollowUpGenerator(prov, deadline=5)

    def ans(n, q, st):
        if I.stage_of(q) == I.INTRO:
            return INTRO
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        w = rec["canonical_answer"].split() if rec else []
        return (" ".join(w[: max(6, len(w) // 3)]) + ". I would check it on held out data.") if rec else "ok"      # 10G: leave concepts open, or the rules skip before any model call; 10J: do not repeat the claim, or it is current-answer context, not memory
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5, "followup_mode": "mock", "max_followups": 2}, ans)
    assert s["status"] == "finished"
    cited = [x for x in s["questions"] if x.get("memory_id") and x.get("followup_kind") in ("llm", "mock")]
    assert cited, "a scripted model proposal that cites a stored memory is accepted"
    x = cited[0]
    assert x["provenance"]["mock"] is True and "not a model" in x["provenance"]["source"] and any(e["source"] == "interview_memory" for e in x["provenance"]["evidence"])
    assert M.get(s["memory"], x["memory_id"])["referenced"] >= 1
    assert "EARLIER (turn" in "".join(c["user"] for c in prov.calls)
    item = M.get(s["memory"], x["memory_id"])
    assert x["lead"].startswith(("Earlier you", "You mentioned", "You said")) and set(M._tokens(item["quote"])) & set(M._tokens(x["lead"])), "the lead is cut from the cited stored claim by code"
    assert not re.search(r"\bm\d+\b", x["lead"] + x["question"]), "ids never reach the candidate"
    # 10N provenance repair: the cited statement must be one the candidate really said in THIS session, at the turn the memory records. It is NOT always the introduction: this test's scripted candidate
    # answers every later technical question with the first third of that question's reference answer, so with another question order (Windows ranks with Sentence-BERT) a later answer such as the
    # "main deep learning frameworks" sentence is a genuine, later candidate statement. The assertion therefore checks the session history instead of the fixed INTRO string.
    for x in cited:                                                              # EVERY cited memory, not only the first: Windows' first citation was a later answer, not the introduction
        item = M.get(s["memory"], x["memory_id"])
        said_at_turn = next(a["answer"] for a in s["answers"] if a and a.get("n") == item["turn"])
        assert " ".join(item["quote"].split()) in " ".join(said_at_turn.split()), "the quote is verbatim in the candidate's own answer at the recorded turn"
        assert item["turn"] < next(i + 1 for i, q in enumerate(s["questions"]) if q is x), "and it was said BEFORE the follow-up that cites it"
        if item["turn"] == 1:
            assert item["quote"] in INTRO
    for c in prov.calls:                                                         # the prompt never carries the whole transcript
        assert len(c["user"]) < 3000


def test_a_model_citing_a_memory_that_does_not_exist_is_rejected_in_the_interview(eng):
    def liar(system, user):
        r = smart_reply(system, user)
        if r["decision"] == "ask":
            r["memory_id"] = "m99"
        return r
    eng._followup_generator = FL.LLMFollowUpGenerator(MockProvider(liar), deadline=5)

    def ans(n, q, st):
        if I.stage_of(q) == I.INTRO:
            return INTRO
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        return (rec["canonical_answer"] + " I used the same idea in my oral cancer classification model.") if rec else "ok"
    s, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 4, "followup_mode": "mock"}, ans)
    assert s["status"] == "finished" and not [x for x in s["questions"] if x.get("followup_kind") in ("llm", "mock")]
    assert any("memory:unknown_id" in e["reasons"] or "memory:unsupported_reference" in e["reasons"] for e in s["plan"]["followup_log"])
    assert not [x for x in s["questions"] if "m99" in json.dumps(x)], "a made-up id is never stored on a question"
