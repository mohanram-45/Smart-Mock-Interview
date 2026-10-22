"""Stage 10N Windows regression repair. Each test pins one confirmed root cause of the five failures the first real Windows run reported (A memory, B time budget, C citation, D import isolation,
E unreachable endpoint). They run on any platform; where the Windows environment differs (Sentence-BERT/FAISS installed, TCP connect behaviour) the difference is reproduced with a stand-in."""
import json
import random
import re
import socket

import pytest

from src.demo import followup_llm as FL, interview as I, memory as M, ollama_stream as OS, policy as POL
from src.evaluation.errors import ProviderUnavailable
from src.evaluation.providers.mock import MockProvider
from tests.app.test_stage4a_demo import make_engine
from tests.app.test_stage9c_followup import ctx as make_ctx, good

INTRO3 = ("I developed an oral cancer classification model using PyTorch. I achieved 91% accuracy on the test set. "
          "The hardest challenge was class imbalance in the training data.")


@pytest.fixture()
def eng(tmp_path):
    return make_engine(tmp_path)


# ------------------------------------------------------------------------------------------------ B: no follow-up once the time budget is spent
def _expired(eng, answer, **cfg):
    s = eng.create({"role": "Data Scientist", "practical": True, "size": 6, "time_budget_min": 1, **cfg})
    sid = s["id"]
    eng.submit(sid, 1, "I work on data problems.")
    cur = eng.get(sid)
    cur["created_at"] = "2000-01-01T00:00:00+00:00"
    eng.submit(sid, 2, answer)
    return eng.get(sid)


def test_B_a_short_answer_after_the_budget_gets_no_follow_up_and_the_interview_ends(eng):
    done = _expired(eng, "It is a thing used in machine learning.")                       # a short answer: the rules WANT a follow-up
    assert done["status"] == "finished" and done["plan"]["ended_reason"] == "time_budget"
    assert not any(q.get("stage") == I.FOLLOW_UP for q in done["questions"]) and done["plan"].get("followups_used", 0) == 0


def test_B_a_memory_follow_up_cannot_extend_the_interview_either(eng, monkeypatch):
    """On Windows the semantic ranking found a memory follow-up even for a strong answer. Whatever source proposes the follow-up, the budget decides first."""
    item = {"question_id": None, "domain": None, "difficulty": None, "topic": None, "question_type": "", "stage": I.FOLLOW_UP, "origin": "memory_followup", "parent_n": 2, "scored": False, "scorable": None,
            "code_spec": None, "question": "Earlier you said you built a model. How did you decide?", "followup_kind": "memory", "memory_id": "m1", "provenance": {}}
    monkeypatch.setattr(eng, "_memory_followup", lambda *a, **k: dict(item))
    done = _expired(eng, "Cross validation splits the data into folds and averages the score across them for a steadier estimate of performance.")
    assert done["status"] == "finished" and done["plan"]["ended_reason"] == "time_budget"
    assert not any(q.get("origin") == "memory_followup" for q in done["questions"])


def test_B_the_model_is_not_even_called_when_the_budget_is_spent(eng):
    prov = MockProvider(lambda system, user: {"decision": "skip", "question": "", "purpose": "deepen", "concept_id": "none"})
    eng._followup_generator = FL.LLMFollowUpGenerator(prov, deadline=5)
    done = _expired(eng, "It is a thing used in machine learning.", followup_mode="mock")
    assert done["status"] == "finished" and prov.calls == [], "no model work is started for a follow-up that cannot be added"


def test_B_within_the_budget_the_same_short_answer_still_gets_its_follow_up(eng):
    s = eng.create({"role": "Data Scientist", "practical": True, "size": 6, "time_budget_min": 120})
    eng.submit(s["id"], 1, "I work on data problems.")
    eng.submit(s["id"], 2, "It is a thing used in machine learning.")
    cur = eng.get(s["id"])
    assert cur["status"] == "active" and any(q.get("stage") == I.FOLLOW_UP for q in cur["questions"]), "the time-budget contract did not remove follow-ups for interviews that have time"


# ------------------------------------------------------------------------------------------------ A: an alternative, grounded recall is legitimate
def test_A_a_cross_validation_question_recalls_the_stated_result_in_the_candidates_own_words(eng):
    """Exactly the follow-up the Windows run produced. The candidate said 'I achieved 91% accuracy on the test set' in the introduction; recalling it is grounded, attributed and hedged."""
    s = eng.create({"role": "Data Scientist", "practical": False, "size": 5})
    eng.submit(s["id"], 1, INTRO3)
    cur = eng.get(s["id"])
    q = cur["questions"][1]
    fu = eng._memory_followup(cur, 1, eng.record(q["question_id"]), "I would measure accuracy, precision and recall on a held out test set and compare them across models carefully.")
    assert fu is not None and fu["followup_kind"] == "memory"
    item = M.get(cur["memory"], fu["memory_id"])
    assert item["turn"] == 1 and item["quote"] in INTRO3 and item["kind"] == "achievement"
    assert fu["question"].startswith("You mentioned a result earlier") and "91% accuracy" in fu["question"]
    assert fu["provenance"]["memory_ref"]["claim_status"].startswith("candidate claim")
    assert "achieved" not in fu["question"], "the claim is repeated as something they REPORTED, never asserted as fact"


def test_A_the_recall_never_comes_from_another_session(tmp_path):
    a = make_engine(tmp_path / "a")
    b = make_engine(tmp_path / "b")
    sa = a.create({"role": "Data Scientist", "practical": False, "size": 5})
    a.submit(sa["id"], 1, INTRO3)
    sb = b.create({"role": "Data Scientist", "practical": False, "size": 5})
    b.submit(sb["id"], 1, "I built a warehouse inventory tracker in Excel.")
    cur = b.get(sb["id"])
    q = cur["questions"][1]
    fu = b._memory_followup(cur, 1, b.record(q["question_id"]), "I would measure accuracy, precision and recall on a held out test set and compare them across models carefully.")
    blob = json.dumps(cur["memory"]) + (fu["question"] if fu else "")
    assert "oral cancer" not in blob.lower() and "91%" not in blob


# ------------------------------------------------------------------------------------------------ C: a memory citation must connect to what was offered
def _mem_session(tmp_path, reply):
    prov = MockProvider(reply)
    e = make_engine(tmp_path)
    e._followup_generator = FL.LLMFollowUpGenerator(prov, deadline=5)
    s = e.create({"role": "Data Scientist", "practical": False, "size": 5, "followup_mode": "mock"})
    e.submit(s["id"], 1, INTRO3)
    cur = e.get(s["id"])
    return e, cur, prov


ANS = "Cross validation splits the data into folds. I would measure accuracy on held out folds."


def _adaptive(system, user):
    from tests.app.test_stage10c_policy import smart_reply
    return smart_reply(system, user)


def _unadaptive(system, user):
    """The OLD scripted model: it always writes about the oral cancer project, whichever statement it was offered."""
    mem = re.search(r"^EARLIER \(turn \d+, .*?id (m\d+)\)", user, re.M)
    tgt = re.search(r"^TARGET \(not covered yet\): \S+ (.+)$", user, re.M)
    return {"decision": "ask", "question": f"How does {tgt.group(1) if tgt else 'validation'} apply to your oral cancer classification model?", "purpose": "apply", "concept_id": "none",
            "memory_id": mem.group(1) if mem else "none"}


def test_C_a_model_that_builds_on_the_statement_it_was_offered_is_cited(tmp_path):
    e, cur, prov = _mem_session(tmp_path, _adaptive)
    q = cur["questions"][1]
    r = e._llm_followup(cur, 1, e.record(q["question_id"]), ANS)
    assert r["item"] is not None and r["item"].get("memory_id"), r["log"]
    item = M.get(cur["memory"], r["item"]["memory_id"])
    assert item["quote"] in INTRO3 and r["log"]["memory_stage"] == "used"
    assert set(M._tokens(item["quote"])) & set(M._tokens(r["item"]["lead"])), "the lead is the cited statement"


def test_C_a_question_that_ignores_the_offered_statement_keeps_no_citation(tmp_path):
    """The meaningful-connection requirement stays. When the model is offered the accuracy claim or the challenge but writes about the oral cancer project, the lead-in is NOT attached (the candidate would
    not see why it was said) and no memory use is claimed."""
    e, cur, prov = _mem_session(tmp_path, _unadaptive)
    q = cur["questions"][1]
    offered = POL.retrieve_for_followup(cur, q, ANS, 2, e.record(q["question_id"]), k=2)
    assert offered, "the scenario offers a statement"
    r = e._llm_followup(cur, 1, e.record(q["question_id"]), ANS)
    first = offered[0]["item"]
    if "oral" in first["text"].lower() or "cancer" in first["text"].lower():
        pytest.skip("this retrieval order offered the project itself, which the old script does connect to")
    assert r["item"] is None or not r["item"].get("memory_id")
    assert r["log"]["memory_stage"] in ("not_connected", "declined", "not_used", "rejected", "none_offered", "no_usable_lead") and not r["log"].get("memory_cited")


def test_C_an_id_that_was_never_offered_or_belongs_to_another_session_is_never_cited(tmp_path):
    def liar(system, user):
        return {"decision": "ask", "question": "How does cross validation apply to your oral cancer classification model?", "purpose": "apply", "concept_id": "none", "memory_id": "m1"}
    e = make_engine(tmp_path)
    e._followup_generator = FL.LLMFollowUpGenerator(MockProvider(liar), deadline=5)
    s = e.create({"role": "Data Scientist", "practical": False, "size": 5, "followup_mode": "mock"})
    e.submit(s["id"], 1, "I built a warehouse inventory tracker in Excel.")
    cur = e.get(s["id"])
    q = cur["questions"][1]
    r = e._llm_followup(cur, 1, e.record(q["question_id"]), ANS)
    assert r["item"] is None or (not r["item"].get("memory_id") and "Earlier you" not in (r["item"].get("lead") or ""))


# ------------------------------------------------------------------------------------------------ prompt size (a 10N regression found while reproducing C)
def test_the_memory_prompt_stays_under_the_limit_even_with_a_long_question_and_answer():
    c = make_ctx()
    c.question = "A dashboard shows that product pages with more images have a higher conversion rate and the team wants to double the number of images on every page; " * 14
    c.answer = "word " * 400
    c.memory = [{"id": "m3", "turn": 1, "quote": "I achieved 91% accuracy on the test set " * 6, "kind": "achievement", "subject": "accuracy", "text": "reported 91% accuracy", "confidence": "high",
                 "reason": "shared_words", "score": 0.6, "lead": "You mentioned a result earlier: reported 91% accuracy."}]
    c.previous = ["What is the first long question that was asked before this one " * 3] * 3
    for mode in ("standard", "memory"):
        _, user, _ = FL.build_prompt(c, nonce="n", mode=mode)
        assert len(user) < 3000, (mode, len(user))
        assert "TARGET" in user and "BEGIN_UNTRUSTED_ANSWER_n" in user


def test_trimming_never_drops_the_earlier_statement_or_the_answer():
    c = make_ctx()
    c.memory = [{"id": "m3", "turn": 1, "quote": "I achieved 91% accuracy on the test set", "kind": "achievement", "subject": "accuracy", "text": "reported 91% accuracy", "confidence": "high",
                 "reason": "shared_words", "score": 0.6, "lead": "You mentioned a result earlier: reported 91% accuracy."}]
    c.question = "Q " * 900
    _, user, _ = FL.build_prompt(c, nonce="n", mode="memory")
    assert "EARLIER (turn 1" in user and "BEGIN_UNTRUSTED_ANSWER_n" in user and "END_UNTRUSTED_ANSWER_n" in user


# ------------------------------------------------------------------------------------------------ D/A/C: tests rank with BM25 unless they ask otherwise
def test_the_suite_ranks_candidate_questions_with_bm25_only(eng):
    res = eng._search_fn("how do you evaluate a classification model", "Machine Learning")
    assert res["mode"] == "bm25_fallback", "a Windows environment with Sentence-BERT installed must not change what the unit tests rank with"

def test_a_default_service_left_in_the_singleton_does_not_change_the_suite_ranking(eng):
    """Windows failure 1: an earlier call to get_service() leaves the REAL default service cached; it ranks semantically wherever Sentence-BERT is installed. The fixture used to treat any non-None
    singleton as 'a test installed this' and so delegated to it, depending on test order. Simulated with a semantic-mode stand-in assigned directly (not through set_service)."""
    from src.retrieval import service as S

    class Semantic:
        def search(self, query, k=5, domain=None, **kw):
            return {"mode": "semantic", "results": []}
    before = S._service
    S._service = Semantic()
    try:
        assert eng._search_fn("how do you evaluate a classification model", "Machine Learning")["mode"] == "bm25_fallback"
    finally:
        S._service = before


def test_a_service_a_test_installs_on_purpose_is_still_honoured(tmp_path, eng):
    from src.retrieval.service import RetrievalService, set_service
    svc = RetrievalService(backend="dev-lsa", index_root=tmp_path / "idx", cache_dir=tmp_path / "cache")
    set_service(svc)
    try:
        assert eng._search_fn("how do you evaluate a classification model", "Machine Learning")["mode"] == "semantic", "explicit dependency injection keeps working"
    finally:
        set_service(None)
    assert eng._search_fn("how do you evaluate a classification model", "Machine Learning")["mode"] == "bm25_fallback"


def test_the_bm25_ranker_never_creates_or_touches_the_process_wide_service():
    from src.demo import sim
    from src.retrieval import service as S
    before = S._service
    S._service = None
    try:
        res = sim.bm25_search("how do you evaluate a classification model", "Machine Learning")
        assert res["mode"] == "bm25_fallback" and res["results"] and S._service is None, "it used its own lexical-only service"
    finally:
        S._service = before


def test_production_retrieval_still_goes_through_the_semantic_capable_service_when_nothing_is_patched():
    """In a clean process (no test fixture) the engine's ranking hook is the process-wide service, so Sentence-BERT + FAISS stay available in production."""
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    code = ("from src.demo import engine as E\nfrom src.retrieval import service as S\n"
            "class Stub:\n    def search(self, q, k=5, domain=None, **kw):\n        return {'mode': 'semantic', 'marker': 'service'}\n"
            "S.set_service(Stub())\nassert E._service_search('q', 'Python')['marker'] == 'service'\n"
            "e = E.DemoEngine.__new__(E.DemoEngine)\nprint('PRODUCTION_HOOK_OK')\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0 and "PRODUCTION_HOOK_OK" in r.stdout, r.stderr[-600:]


def test_the_suite_does_not_inherit_the_sentence_bert_memory_switch_from_the_shell(eng):
    import os
    assert os.environ.get("SMART_DEMO_MEMORY_SBERT") is None and M.default_embedder().name != "sentence-bert"


# ------------------------------------------------------------------------------------------------ E: refusal, connect timeout, response deadline, missing model are four different failures
def _prov():
    return OS.StreamingOllama("llama3.2:3b", "http://127.0.0.1:9")


def test_E_a_connect_timeout_is_unavailable_not_a_response_deadline(monkeypatch):
    """Windows retries the SYN to a closed local port for about two seconds before it refuses, so the endpoint that Linux refuses at once timed out inside the connect window there and was reported as
    `DeadlineExceeded: no response within the deadline`. The stand-in raises that same timeout from connect(): no network is touched."""
    import http.client

    def slow_connect(self):
        raise socket.timeout("timed out")
    monkeypatch.setattr(http.client.HTTPConnection, "connect", slow_connect)
    with pytest.raises(ProviderUnavailable) as ei:
        _prov().generate_bounded("s", "u", 2)
    assert "connect timed out" in str(ei.value) and not isinstance(ei.value, OS.DeadlineExceeded)


def test_E_a_refused_connection_is_unavailable(monkeypatch):
    import http.client

    def refused(self):
        raise ConnectionRefusedError(10061, "refused")
    monkeypatch.setattr(http.client.HTTPConnection, "connect", refused)
    with pytest.raises(ProviderUnavailable) as ei:
        _prov().generate_bounded("s", "u", 2)
    assert "ConnectionRefusedError" in str(ei.value)


def test_E_a_timeout_AFTER_connecting_is_still_a_response_deadline(monkeypatch):
    """A slow model is not an unreachable server: once connected, running out of time stays DeadlineExceeded (with its partial metrics)."""
    import http.client

    class Sock:
        def settimeout(self, t): pass
        def shutdown(self, *a): pass
        def close(self): pass

    def ok_connect(self):
        self.sock = Sock()

    def request(self, *a, **k):
        raise socket.timeout("timed out")
    monkeypatch.setattr(http.client.HTTPConnection, "connect", ok_connect)
    monkeypatch.setattr(http.client.HTTPConnection, "request", request)
    with pytest.raises(OS.DeadlineExceeded) as ei:
        _prov().generate_bounded("s", "u", 2)
    assert "no response within the deadline" in str(ei.value) and "client_elapsed_ms" in ei.value.metrics


def test_E_the_generator_turns_an_unreachable_endpoint_into_a_clean_fallback(monkeypatch):
    import http.client
    monkeypatch.setattr(http.client.HTTPConnection, "connect", lambda self: (_ for _ in ()).throw(socket.timeout("timed out")))
    g = FL.LLMFollowUpGenerator(_prov(), deadline=2)
    out = g.propose(make_ctx())
    assert out.kind == "fallback" and out.proposal is None, "the interview carries on with the deterministic follow-up; no exception reaches the API"


# ------------------------------------------------------------------------------------------------ the Windows diagnostic itself
def test_the_windows_diagnostic_runs_and_reports_every_section_without_an_error(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    out = tmp_path / "diag.json"
    r = subprocess.run([sys.executable, str(root / "scripts" / "stage10n_windows_repair_diag.py"), "--skip-real", "--out", str(out)], cwd=root, capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stderr[-800:]
    d = json.loads(out.read_text(encoding="utf-8"))
    for k in ("environment", "A_memory_pick[bm25_only]", "B_time_budget[bm25_only]", "C_citation[bm25_only]", "D_import_trace", "E_unreachable_endpoint"):
        assert k in d and "diag_error" not in d[k], (k, d.get(k))
    assert d["B_time_budget[bm25_only]"]["short"]["status"] == "finished" and d["E_unreachable_endpoint"]["client_raises"].startswith("src.evaluation.errors.ProviderUnavailable")
