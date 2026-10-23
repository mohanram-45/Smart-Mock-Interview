"""Stage 10N provenance repair: a stored candidate memory must be something the candidate said in THIS session, at the recorded turn, whichever order the candidate questions come in.

Why: the Windows run cited the sentence "The main general-purpose deep learning frameworks today are PyTorch, TensorFlow ... and JAX." and a test that assumed every memory came from the introduction failed.
Tracing it: that sentence is the first part of the REFERENCE answer of bank question smi-0034, and the test's scripted candidate answers every technical question with the first third of the reference answer.
So it was stored as a candidate statement (kind explanation) at the turn where smi-0034 was answered. It is a genuine, later candidate statement, not contamination. These tests pin that and the opposite
direction: reference text the candidate did NOT say is never stored."""
import json
import random

import pytest

from src.demo import followup_llm as FL, interview as I, memory as M, sim
from src.evaluation.providers.mock import MockProvider
from tests.app.test_stage4a_demo import make_engine
from tests.app.test_stage10c_policy import INTRO, smart_reply

FRAMEWORKS = "The main general-purpose deep learning frameworks today are PyTorch, TensorFlow (usually used through its Keras API) and JAX."


def first_third(eng):
    def ans(n, q, st):
        if I.stage_of(q) == I.INTRO:
            return INTRO
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        w = rec["canonical_answer"].split() if rec else []
        return (" ".join(w[: max(6, len(w) // 3)]) + ". I would check it on held out data.") if rec else "ok"
    return ans


def ranked(first_ids=(), reverse=False):
    """BM25 ranking with chosen questions moved to the front (or the whole order reversed): the order a different retrieval would give."""
    def fn(query, domain):
        r = sim.bm25_search(query, domain)
        res = list(r["results"])
        if reverse:
            res.reverse()
        res.sort(key=lambda h: 0 if h["question_id"] in first_ids else 1)
        return dict(r, results=res)
    return fn


def run(tmp_path, search_fn, seed=11, size=6, followup_mode="mock", role="Data Scientist"):
    eng = make_engine(tmp_path, search_fn=search_fn, rng=random.Random(seed))
    eng._followup_generator = FL.LLMFollowUpGenerator(MockProvider(smart_reply), deadline=5)
    s, t = sim.run(eng, {"role": role, "practical": False, "size": size, "followup_mode": followup_mode, "max_followups": 2}, first_third(eng))
    return eng, s, t


ORDERS = {"bm25": ranked(), "reversed": ranked(reverse=True), "frameworks_first": ranked(("smi-0034",)), "other_seed": ranked(reverse=True)}


def answer_at(s, turn):
    return next((a["answer"] for a in s["answers"] if a and a.get("n") == turn), None)


def assert_provenance(s):
    """Every stored item and every cited memory traces to the candidate's own words in this session."""
    for it in s["memory"]["items"]:
        said = answer_at(s, it["turn"])
        assert said is not None, f"memory {it['id']} names turn {it['turn']}, which the candidate never answered"
        assert " ".join(it["quote"].split()) in " ".join(said.split()), f"memory {it['id']} (turn {it['turn']}) is not verbatim in the candidate's answer at that turn"
        assert it["claim_status"].startswith("candidate claim") if "claim_status" in it else True
    for i, q in enumerate(s["questions"]):
        if q.get("memory_id"):
            item = M.get(s["memory"], q["memory_id"])
            assert item is not None and item["turn"] < i + 1, "a cited memory exists in this session and was said earlier than the question that cites it"


@pytest.mark.parametrize("name", list(ORDERS))
def test_every_stored_and_cited_memory_traces_to_the_candidates_own_answer_whatever_the_question_order(tmp_path, name):
    _, s, t = run(tmp_path, ORDERS[name], seed=11 if name != "other_seed" else 5)
    assert s["status"] == "finished" and s["memory"]["items"]
    assert_provenance(s)


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_provenance_holds_across_seeds_and_a_second_role(tmp_path, seed):
    for role in ("Data Scientist", "Python Developer"):
        _, s, _ = run(tmp_path / role.replace(" ", "_"), ranked(("smi-0034",), reverse=bool(seed % 2)), seed=seed, role=role)
        assert_provenance(s)


def test_the_windows_citation_is_a_genuine_later_candidate_statement_not_contamination(tmp_path):
    """Reproduces what the Windows run saw: the framework sentence of the REFERENCE answer is stored because the scripted candidate said it; it carries its real (later) turn."""
    eng = make_engine(tmp_path, search_fn=ranked(("smi-0034",)))
    s = eng.create({"role": "Data Scientist", "practical": False, "size": 5})
    eng.submit(s["id"], 1, INTRO)
    cur = eng.get(s["id"])
    rec = eng.record("smi-0034")
    assert rec["canonical_answer"].startswith(FRAMEWORKS), "the sentence is bank reference text"
    cur["questions"][1].update({"question_id": "smi-0034", "question": rec["question"], "domain": rec["domain"], "topic": rec["topic"]})
    answer = " ".join(rec["canonical_answer"].split()[:40])
    M.update(cur, n=2, answer=answer, q=cur["questions"][1], record=rec)
    items = [it for it in cur["memory"]["items"] if FRAMEWORKS[:40] in it["quote"]]
    assert items and all(it["turn"] == 2 and it["turn"] != 1 for it in items), "stored at the turn where the candidate said it, not turn 1"
    assert all(it["kind"] == "explanation" for it in items), "an explanation of a topic, never a claim about the candidate's own work"


def test_reference_text_the_candidate_did_not_say_is_never_stored(tmp_path):
    """The reverse direction (requirement: question-bank explanations and expected answers are never candidate claims)."""
    eng = make_engine(tmp_path, search_fn=ranked(("smi-0034",)))
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 6}, lambda n, q, st: INTRO if I.stage_of(q) == I.INTRO else "I am not sure about this one.")
    blob = json.dumps(s["memory"])
    for rec_id in ("smi-0034",):
        ref = eng.record(rec_id)["canonical_answer"]
        assert FRAMEWORKS[:50] not in blob and ref[:60] not in blob
    assert_provenance(s)
    assert all(it["turn"] == 1 for it in s["memory"]["items"]), "only the introduction was substantive, so only it was remembered"


def test_nothing_crosses_sessions_even_with_the_same_engine(tmp_path):
    eng = make_engine(tmp_path, search_fn=ranked(("smi-0034",)))
    a, _ = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5}, first_third(eng))
    b, tb = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5}, lambda n, q, st: "I built a warehouse inventory tracker in Excel." if I.stage_of(q) == I.INTRO else "I am not sure.")
    blob = json.dumps(b["memory"]) + " ".join(r["lead"] for r in tb) + " ".join(r["question"] for r in tb if r["memory_ref"])      # bank question texts are not memory
    assert "oral cancer" not in blob.lower() and "frameworks" not in blob.lower()
    assert_provenance(a)
    assert_provenance(b)
