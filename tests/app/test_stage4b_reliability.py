"""Stage 4B: application reliability of the demo (/demo): scorer start-up safety, session persistence/expiry, refresh/back/duplicate handling, id/answer/score association,
stale data, failure paths. Same boundary as 4A: real Flask app + real corpus, stand-in scorer, no model called."""
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from src.demo import engine as ENG
from src.demo.engine import DemoEngine, DemoError
from src.demo.routes import set_engine
from src.demo.store import DemoStore
from tests.app.test_stage4a_demo import GOOD, Overlap, answer, create_bare, make_engine, start

ROOT = Path(__file__).resolve().parents[2]
BASE = {"role": "Python Developer", "size": 3, "practical": False, "max_followups": 0}


@pytest.fixture()
def eng(tmp_path, monkeypatch):
    monkeypatch.delenv("SMART_DEMO_LIVE_MODULAR", raising=False)
    monkeypatch.delenv("SMART_RETRIEVAL_EXPOSE_REFERENCE", raising=False)
    monkeypatch.delenv("SMART_DEMO_ALLOW_SCORER_SETUP", raising=False)
    e = make_engine(tmp_path)
    set_engine(e)
    yield e
    set_engine(None)


@pytest.fixture()
def c(app_module, eng):
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as cl:
        yield cl


def not_ready(key):
    return {"ready": False, "not_ready_reason": f"{key} is not set up", "setup_hint": "run the one-time setup"}


# ------------------------------------------------------------------------------------------------ start-up: never train / download inside a request
def test_registry_readiness_is_side_effect_free_and_does_not_import_heavy_libraries():
    code = ("import sys; sys.path.insert(0, 'src/model'); import model_registry as r\n"
            "out = {k: r.readiness(k) for k in r.MODEL_CHOICES}; out['x'] = r.readiness('nope')\n"
            "assert all(set(v) == {'ready', 'reason', 'hint'} for v in out.values()), out\n"
            "assert out['x']['ready'] is False\n"
            "assert 'torch' not in sys.modules and 'sentence_transformers' not in sys.modules and 'sklearn' not in sys.modules\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_unready_scorer_is_never_trained_by_a_web_request(tmp_path):
    calls = []
    e = make_engine(tmp_path, scorer_factory=lambda k, corpus: calls.append(k) or Overlap(), readiness_fn=not_ready)
    models = {m["key"]: m for m in e.legacy_models()}
    assert list(models) == ["bert"] and models["bert"]["ready"] is False
    s = e.create(BASE)
    assert calls == [], "the factory (which loads a model) must not run for an unready scorer"
    assert s["legacy"]["available"] is False and "not set up" in s["legacy"]["reason"] and "one-time setup" in s["legacy"]["reason"]
    e.submit(s["id"], 1, "Hello")
    a = e.submit(s["id"], 2, GOOD)                       # the interview still works, with an honest 'unavailable' - and no other scorer steps in
    assert a["legacy"]["status"] == "unavailable" and a["legacy"]["score"] is None and calls == []


def test_opt_in_setup_flag_allows_the_factory(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setenv("SMART_DEMO_ALLOW_SCORER_SETUP", "1")
    e = make_engine(tmp_path, scorer_factory=lambda k, corpus: calls.append(k) or Overlap(), readiness_fn=not_ready)
    s = e.create(BASE)
    assert calls == ["bert"] and s["legacy"]["available"] is True


def test_sentence_bert_is_the_only_and_default_scorer(tmp_path):
    e = make_engine(tmp_path)
    m = e.legacy_models()
    assert [x["key"] for x in m] == ["bert"] and m[0]["default"] is True
    for other in ("bilstm", "tfidf", "siamese", "gpt"):
        with pytest.raises(DemoError) as ex:
            e.create({**BASE, "legacy_model": other})
        assert ex.value.status == 400 and "only similarity scorer" in str(ex.value)
    assert e.create({**BASE, "legacy_model": "bert"})["config"]["legacy_model"] == "bert"


def test_scorer_is_loaded_once_even_under_concurrent_session_starts(tmp_path):
    loads, gate = [], threading.Event()
    def slow_factory(k, corpus):
        loads.append(k); gate.wait(0.3); return Overlap()
    e = make_engine(tmp_path, scorer_factory=slow_factory)
    ts = [threading.Thread(target=lambda: create_bare(e)) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert loads == ["bert"]


def test_setup_and_settings_pages_warn_when_sentence_bert_needs_setup(app_module, tmp_path):
    e = make_engine(tmp_path, readiness_fn=lambda k: not_ready(k))
    set_engine(e)
    try:
        app_module.app.config["TESTING"] = True
        cl = app_module.app.test_client()
        html = cl.get("/demo/settings").get_data(as_text=True)
        assert "needs one-time setup" in html and "bert is not set up" in html
        assert "Siamese" not in html and "TF-IDF" not in html                       # no other scorer is offered
        assert 'id="legacy-model"' not in cl.get("/demo/new").get_data(as_text=True)
    finally:
        set_engine(None)


def test_main_app_binds_locally_and_keeps_the_debugger_off_by_default():
    src = (ROOT / "main" / "app.py").read_text(encoding="utf-8")
    assert 'os.environ.get("SMART_HOST", "127.0.0.1")' in src and 'os.environ.get("SMART_DEBUG", "")' in src and "debug=debug" in src
    assert "host='0.0.0.0'" not in src and "debug=True" not in src


# ------------------------------------------------------------------------------------------------ association of ids, answers, scores and feedback
def test_question_answer_score_feedback_stay_associated(c, eng):
    class Echo:                                         # score is a pure function of the ANSWER, so any cross-wiring shows
        def score(self, ref, ans): return (len(ans) % 100) / 100
    eng._scorers["bert"] = Echo()
    eng._scorer_factory = lambda k, corpus: Echo()
    eng._feedback_fn = lambda s, q, a, m: f"Q={q}|A={a}|S={s}"
    r, sid = start(c, size=5)
    texts = [("alpha " * (i + 3)).strip() for i in range(5)]
    for i, t in enumerate(texts, 1):
        assert answer(c, sid, i, t).status_code == 200
    s = eng.get(sid)
    assert s["status"] == "finished"
    for i, (q, a) in enumerate(zip(s["questions"][1:], s["answers"][1:])):            # item 1 is the introduction
        assert a["n"] == i + 2 and a["question_id"] == q["question_id"] and a["answer"] == texts[i]
        assert a["legacy"]["score"] == round((len(texts[i]) % 100), 2)
        assert a["legacy"]["feedback"] == f"Q={q['question']}|A={texts[i]}|S={a['legacy']['score']}"
    assert len({q["question_id"] for q in s["questions"][1:]}) == 5                   # no question repeated within a session
    exp = c.get(f"/demo/s/{sid}/export.json").json
    assert [x["question_id"] for x in exp["answers"][1:]] == [q["question_id"] for q in s["questions"][1:]]
    assert [x["answer"] for x in exp["answers"][1:]] == texts
    page = c.get(f"/demo/s/{sid}/summary").get_data(as_text=True)
    pos = [page.index(f'id="q{i}"') for i in range(2, 7)]
    assert pos == sorted(pos) and all(texts[i] in page for i in range(5))


def test_two_interviews_never_mix(c, eng):
    _, a = start(c, size=2); _, b = start(c, size=2)
    assert a != b
    answer(c, a, 1, "answer-for-A"); answer(c, b, 1, "answer-for-B")
    assert eng.get(a)["answers"][1]["answer"] == "answer-for-A" and eng.get(b)["answers"][1]["answer"] == "answer-for-B"
    assert "answer-for-B" not in c.get(f"/demo/s/{a}/summary").get_data(as_text=True) or eng.get(a)["status"] == "active"
    answer(c, a, 2, "a2"); html = c.get(f"/demo/s/{a}/summary").get_data(as_text=True)
    assert "answer-for-A" in html and "answer-for-B" not in html


def test_stale_question_bank_blocks_scoring_without_changing_state(tmp_path):
    recs = {"v": None}
    from src.retrieval.service import get_service
    real = get_service().records()
    e = make_engine(tmp_path, records_fn=lambda: recs["v"] or real)
    s = create_bare(e)
    qid = s["questions"][1]["question_id"]
    recs["v"] = [dict(r, question=r["question"] + " (edited)") if r["question_id"] == qid else r for r in real]
    e._by_id = None
    with pytest.raises(DemoError) as ex:
        e.submit(s["id"], 2, GOOD)
    assert ex.value.status == 409 and ex.value.extra.get("stale") is True
    assert e.get(s["id"])["current"] == 1 and e.get(s["id"])["answers"][1] is None


# ------------------------------------------------------------------------------------------------ duplicates, refresh, back button
def test_identical_resubmission_is_an_idempotent_replay(c, eng):
    calls = []
    class Counting:
        def score(self, ref, ans): calls.append(ans); return 0.5
    eng._scorers["bert"] = Counting()
    _, sid = start(c, size=3)
    r1, r2 = answer(c, sid, 1), answer(c, sid, 1)
    assert r1.status_code == r2.status_code == 200 and len(calls) == 1
    assert eng.get(sid)["current"] == 2
    assert answer(c, sid, 1, "something else").status_code == 409                 # different text for a closed question is a conflict
    assert eng.get(sid)["answers"][1]["answer"] == GOOD


def test_concurrent_double_click_scores_once(c, eng):
    calls = []
    class Slow:
        def score(self, ref, ans): calls.append(1); time.sleep(0.15); return 0.5
    eng._scorers["bert"] = Slow()
    _, sid = start(c, size=3)
    out = []
    def go(): out.append(eng.submit(sid, 2, GOOD)["legacy"]["score"])
    ts = [threading.Thread(target=go) for _ in range(5)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(calls) == 1 and len(out) == 5 and len(set(out)) == 1 and eng.get(sid)["current"] == 2


def test_a_slow_scorer_in_one_interview_does_not_block_another(c, eng):
    release = threading.Event()
    class Gate:
        def score(self, ref, ans):
            if ans == "slow": release.wait(5)
            return 0.5
    eng._scorers["bert"] = Gate()
    _, a = start(c, size=2); _, b = start(c, size=2)
    t = threading.Thread(target=lambda: eng.submit(a, 2, "slow")); t.start()
    time.sleep(0.1)
    t0 = time.time(); eng.submit(b, 2, "fast"); fast = time.time() - t0
    release.set(); t.join()
    assert fast < 1.0, "interview B waited for interview A's scorer"


def test_refresh_and_back_button_pages(c, eng):
    _, sid = start(c, size=3)
    p1 = c.get(f"/demo/s/{sid}").get_data(as_text=True)
    assert c.get(f"/demo/s/{sid}").get_data(as_text=True) == p1                    # refresh = same question
    answer(c, sid, 1)
    p2 = c.get(f"/demo/s/{sid}").get_data(as_text=True)
    assert "Technical question" in p2 and p2 != p1
    stale = answer(c, sid, 1, "late tab")                                          # a back-button / stale tab submits question 1 again
    assert stale.status_code == 409 and stale.json["current"] == 3
    assert c.get(f"/demo/api/sessions/{sid}").json["current"] == 3
    c.post(f"/demo/api/sessions/{sid}/finish")
    assert c.get(f"/demo/s/{sid}").status_code == 302                              # interview page of a finished session goes to the summary
    assert c.get(f"/demo/s/{sid}/summary").status_code == 200
    late = answer(c, sid, 2, "after the end")
    assert late.status_code == 409 and late.json.get("finished") is True


def test_new_interview_after_completion_is_independent(c, eng):
    _, a = start(c, size=1); answer(c, a, 1)
    assert eng.get(a)["status"] == "finished"
    r, b = start(c, size=2)
    assert r.status_code == 201 and b != a and eng.get(b)["status"] == "active" and eng.get(a)["status"] == "finished"


def test_interview_page_shows_status_dots_and_summary_overview(c, eng):
    _, sid = start(c, size=3)
    answer(c, sid, 1); c.post(f"/demo/api/sessions/{sid}/skip", json={"n": 3})
    page = c.get(f"/demo/s/{sid}").get_data(as_text=True)
    assert page.count('class="stage-step ') >= 3 and 'stage-step done' in page and 'stage-step current' in page and "Introduction" in page
    answer(c, sid, 3)
    s = c.get(f"/demo/s/{sid}/summary").get_data(as_text=True)
    assert "Topics covered" in s and "What I noticed" in s and "Download my results" in s and "Delete this interview" in s


# ------------------------------------------------------------------------------------------------ persistence, expiry, deletion, privacy
def test_unfinished_interview_survives_a_server_restart(tmp_path):
    e1 = make_engine(tmp_path)
    s = create_bare(e1); e1.submit(s["id"], 2, GOOD)
    e2 = make_engine(tmp_path)                                                     # new process, same data folder
    again = e2.get(s["id"])
    assert again["status"] == "active" and again["current"] == 2 and again["answers"][1]["answer"] == GOOD and again["restored_from_disk"]
    e2.submit(s["id"], 3, "next"); assert e2.get(s["id"])["current"] == 3


def test_idle_eviction_does_not_lose_the_interview(tmp_path):
    e = make_engine(tmp_path); e.store.ttl = 0
    s = create_bare(e)
    e.store.put({"id": "demo_" + "1" * 20, "x": 1})                                 # triggers eviction of the idle session from memory
    assert e.get(s["id"])["id"] == s["id"]


def test_running_model_job_is_reported_as_interrupted_after_a_restart(app_module, tmp_path):
    e1 = make_engine(tmp_path, modular_evaluate=lambda mode, rec, ans: (_ for _ in ()).throw(AssertionError("never")), executor=_Never())
    s = create_bare(e1, modular_mode="mock")
    e1.submit(s["id"], 2, GOOD)
    assert e1.get(s["id"])["answers"][1]["modular"]["status"] == "pending"
    e2 = make_engine(tmp_path)
    set_engine(e2)
    try:
        app_module.app.config["TESTING"] = True
        cl = app_module.app.test_client()
        assert e2.get(s["id"])["answers"][1]["modular"]["status"] == "interrupted"
        j = cl.get(f"/demo/api/sessions/{s['id']}/answers/2").json
        assert j["modular_status"] == "interrupted" and "restarted" in j["html"] and "No score and no penalty" in j["html"] and "data-poll" not in j["html"]
    finally:
        set_engine(None)


class _Never:
    def submit(self, fn):                                                          # a job that never completes (server died)
        class F:
            def result(self_inner): return None
        return F()


def test_old_session_files_are_pruned_and_unknown_ids_never_touch_the_disk(tmp_path):
    st = DemoStore(tmp_path / "s", retention_days=1)
    old, new = "demo_" + "a" * 20, "demo_" + "b" * 20
    for sid in (old, new):
        st.save({"id": sid, "status": "finished", "answers": []})
    past = time.time() - 3 * 86400
    os.utime(tmp_path / "s" / f"{old}.json", (past, past))
    outside = tmp_path / "s" / "keep.txt"; outside.write_text("x")
    assert st.prune_files() == 1
    assert not (tmp_path / "s" / f"{old}.json").exists() and (tmp_path / "s" / f"{new}.json").exists() and outside.exists()
    assert st.get(old) is None and st.get("../keep") is None and st.delete("../keep") is False


def test_delete_erases_memory_and_disk(c, eng, tmp_path):
    _, sid = start(c, size=1); answer(c, sid, 1)
    f = tmp_path / "sessions" / f"{sid}.json"
    assert f.exists()
    r = c.post(f"/demo/api/sessions/{sid}/delete")
    assert r.status_code == 200 and not f.exists()
    assert c.get(f"/demo/api/sessions/{sid}").status_code == 404 and c.get(f"/demo/s/{sid}/summary").status_code == 404
    assert c.post(f"/demo/api/sessions/{sid}/delete").status_code == 200           # idempotent


def test_saved_files_and_export_hold_no_reference_answers(c, eng, tmp_path):
    _, sid = start(c, size=2); answer(c, sid, 1); answer(c, sid, 2)
    blob = (tmp_path / "sessions" / f"{sid}.json").read_text(encoding="utf-8")
    exp = c.get(f"/demo/s/{sid}/export.json")
    assert exp.status_code == 200 and "attachment" in exp.headers["Content-Disposition"]
    refs = [r["canonical_answer"] for r in eng.records() if r["question_id"] in {q["question_id"] for q in eng.get(sid)["questions"]}]
    assert refs and all(ref not in blob and ref not in exp.get_data(as_text=True) for ref in refs)
    assert exp.json["answers"][1]["experimental"]["human_validated"] is False


def test_concurrent_saves_never_leave_temp_files_or_corrupt_json(tmp_path):
    st = DemoStore(tmp_path / "s")
    s = {"id": "demo_" + "c" * 20, "status": "active", "answers": [], "n": 0}
    def w(i):
        for k in range(30):
            s["n"] = i * 100 + k; st.save(s)
    ts = [threading.Thread(target=w, args=(i,)) for i in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert json.loads((tmp_path / "s" / f"{s['id']}.json").read_text(encoding="utf-8"))["id"] == s["id"]
    assert list((tmp_path / "s").glob("*.tmp")) == []


# ------------------------------------------------------------------------------------------------ failure paths
def test_crashing_experimental_evaluator_never_leaves_an_answer_running(c, eng):
    def boom(mode, rec, ans): raise RuntimeError("secret internal detail")
    eng._modular_evaluate = boom
    _, sid = start(c, size=1, modular_mode="mock")
    r = answer(c, sid, 1)
    assert r.status_code == 200
    a = eng.get(sid)["answers"][1]
    assert a["modular"]["status"] == "failed" and a["modular"]["view"] is None
    assert a["legacy"]["status"] == "scored"                                      # the legacy result is untouched
    html = c.get(f"/demo/s/{sid}/summary").get_data(as_text=True)
    assert "Evaluation unavailable" in html and "secret internal detail" not in html and "data-poll" not in html


def test_corpus_unavailable_during_setup_and_session_start(app_module, tmp_path):
    def broken(): raise DemoError("The curated question bank could not be loaded.", 503)
    e = make_engine(tmp_path, records_fn=broken)
    set_engine(e)
    try:
        app_module.app.config["TESTING"] = True
        cl = app_module.app.test_client()
        page = cl.get("/demo/new")
        assert page.status_code == 200 and b"Question bank unavailable" in page.data
        r = cl.post("/demo/api/sessions", json=BASE)
        assert r.status_code == 503 and "question bank" in r.json["error"]
    finally:
        set_engine(None)


def test_garbage_input_is_rejected_cleanly(c, eng):
    _, sid = start(c, size=2)
    for body in ([], "x", 7, None):
        assert c.post(f"/demo/api/sessions/{sid}/answer", json=body).status_code == 400
    for bad in ({"n": True, "answer": "x"}, {"n": 1.5, "answer": "x"}, {"n": None, "answer": "x"}, {"n": 1, "answer": ["x"]}, {"n": 1, "answer": "\x00" * 3}):
        assert c.post(f"/demo/api/sessions/{sid}/answer", json=bad).status_code in (400, 409)
    assert c.get(f"/demo/api/sessions/{sid}").json["current"] == 2
    assert c.post("/demo/api/sessions", json={**BASE, "size": 99}).status_code == 400
    assert c.post("/demo/api/sessions", json={**BASE, "role": "Astronaut"}).status_code == 400
    assert c.get("/demo/api/sessions/demo_" + "f" * 20 + "/answers/1").status_code == 404


def test_candidate_text_is_escaped_everywhere_including_the_export_page(c, eng):
    evil = '<img src=x onerror=alert(1)> <script>alert(2)</script> {{7*7}} ${7*7}'
    _, sid = start(c, size=1); answer(c, sid, 1, evil)
    for url in (f"/demo/s/{sid}/summary", f"/demo/api/sessions/{sid}/answers/2"):
        body = c.get(url).get_data(as_text=True)
        body = json.loads(body)["html"] if url.endswith("/2") else body
        assert "<script>alert(2)" not in body and "<img src=x" not in body
        if url.endswith("summary"):
            assert "&lt;script&gt;alert(2)&lt;/script&gt;" in body and "{{7*7}}" in body and "${7*7}" in body       # shown literally, never evaluated
    exp = c.get(f"/demo/s/{sid}/export.json")
    assert exp.mimetype == "application/json" and exp.json["answers"][1]["answer"] == evil


def test_reference_answers_are_not_exposed_before_or_after_submission(c, eng):
    _, sid = start(c, size=2)
    refs = [r["canonical_answer"] for r in eng.records()][:300]
    q = c.get(f"/demo/s/{sid}").get_data(as_text=True)
    api = c.get(f"/demo/api/sessions/{sid}").get_data(as_text=True)
    after = answer(c, sid, 1).get_data(as_text=True)
    summ = c.get(f"/demo/s/{sid}/summary").get_data(as_text=True)
    assert not any(ref[:80] in blob for ref in refs for blob in (q, api, after, summ))
    assert "canonical_answer" not in api and "canonical_answer" not in after


def test_stage_4a_isolation_still_holds_default_flow_never_imports_modular(tmp_path):
    code = ("import sys, random\n"
            "from src.demo.engine import DemoEngine\nfrom src.demo.store import DemoStore\n"
            "class S:\n    def score(self, r, a): return .5\n"
            f"e = DemoEngine(DemoStore(r'{tmp_path}/x'), scorer_factory=lambda k, c: S(), feedback_fn=lambda *a: 'f', rng=random.Random(1))\n"
            "s = e.create({'role': 'Python Developer', 'difficulty': 'Medium', 'size': 2}); e.submit(s['id'], 1, 'a b c'); e.submit(s['id'], 2, 'd e'); e.summary(e.get(s['id']))\n"
            "assert not [m for m in sys.modules if m.startswith('src.evaluation.modular')], 'modular package loaded by the default flow'\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
