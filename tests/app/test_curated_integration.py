"""Curated-mode integration through the REAL Flask routes. Retrieval embedder = dev-lsa stand-in (labelled); scorer = FakeScorer."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CUR = {"question_source": "curated"}


def start(client, **body):
    r = client.post("/api/start-interview", json={**CUR, **body})
    return r, r.get_json()


def sess(app_module, d):
    return app_module.sessions[d["session_id"]]


# ---------- selection, ids, metadata ----------
def test_curated_start_contract_and_stable_string_ids(client, svc, app_module):
    r, d = start(client, role="Python Developer")
    assert r.status_code == 200 and d["question_source"] == "curated"
    legacy_keys = {"session_id", "role", "selected_domains", "model", "started_at", "current_round", "current_question"}
    assert set(d) == legacy_keys | {"question_source"}                               # legacy keys all preserved
    cq = d["current_question"]
    assert {"question_id", "question", "question_number", "total_in_round"} <= set(cq)
    assert isinstance(cq["question_id"], str) and cq["question_id"].startswith("smi-")
    assert cq["domain"] == "Python" and cq["difficulty"] == "Easy" and cq["topic"]
    assert svc.get(cq["question_id"])["question"] == cq["question"]                  # id -> full record round-trips


def test_ids_stable_across_sessions_and_unique_within(client, svc, app_module):
    seen = set()
    for _ in range(3):
        _, d = start(client, role="Python Developer")
        s = sess(app_module, d)
        ids = [q["id"] for rnd in s.round_questions.values() for q in rnd]
        assert len(ids) == len(set(ids))
        seen |= set(ids)
    assert all(svc.get(i) is not None for i in seen)                                 # every id resolves in the corpus


@pytest.mark.parametrize("role,expected", [
    ("Machine Learning Engineer", {"Machine Learning", "Deep Learning", "Python"}),
    ("Data Scientist", {"Machine Learning", "Deep Learning", "NLP", "Data Analysis", "Python"}),
    ("Data Analyst", {"Data Analysis", "Python"}),
    ("NLP Engineer", {"NLP"}),
    ("Python Developer", {"Python"}),
])
def test_role_alias_mapping_gives_real_domains_in_curated_mode(client, svc, app_module, role, expected):
    r, d = start(client, role=role)
    assert r.status_code == 200, d
    s = sess(app_module, d)
    assert d["selected_domains"] == __import__("config").ROLE_MAPPING[role]          # response still shows the role's own codes
    assert {q["domain"] for q in s.all_questions} == expected


def test_difficulty_buckets_and_metadata_preserved(client, svc, app_module):
    _, d = start(client, role="Custom Interview", custom_domains=["Machine Learning", "SQL"])
    s = sess(app_module, d)
    for diff in ("Easy", "Medium", "Hard"):
        assert s.questions_by_difficulty[diff] and all(q["difficulty"] == diff for q in s.questions_by_difficulty[diff])
    q = s.all_questions[0]
    assert set(q) == {"id", "domain", "difficulty", "question", "reference_answer", "topic"} and q["reference_answer"]


def test_custom_domains_accept_canonical_and_alias_and_extra_curated_domains(client, svc, app_module):
    for doms in (["Machine Learning"], ["ML"], ["Generative AI & RAG"], ["MLOps & Model Deployment"]):
        r, d = start(client, role="Custom Interview", custom_domains=doms)
        assert r.status_code == 200, (doms, d)
    r, d = start(client, role="Custom Interview", custom_domains=["Underwater Basket Weaving"])
    assert r.status_code == 400 and d == {"error": "Failed to load questions for selected domains"}


def test_quarantined_and_boilerplate_excluded(svc):
    reg = json.loads((ROOT / "data/expansion/registry.json").read_text(encoding="utf-8")) if (ROOT / "data/expansion/registry.json").exists() else None
    ids = {r["question_id"] for r in svc.records()}
    quarantined = {q["id"] for q in (reg or {}).get("quarantined", [])}
    assert len(svc.records()) == 666
    assert not (ids & quarantined)
    for r in svc.records():                                                            # no empty/placeholder text
        assert len(r["question"].strip()) > 10 and len(r["canonical_answer"].strip()) > 20


def test_hard_pool_capacity_per_role(client, svc, app_module):
    """Measured, not assumed: each role must be able to seat at least 1 question per round; shortfalls are reported."""
    for role in ("Machine Learning Engineer", "Data Scientist", "Data Analyst", "NLP Engineer", "Python Developer"):
        _, d = start(client, role=role)
        s = sess(app_module, d)
        for diff in ("Easy", "Medium", "Hard"):
            assert len(s.questions_by_difficulty[diff]) >= 1, (role, diff)


# ---------- full flow with string ids ----------
def _drive(client, sid, max_steps=60):
    last = None
    for _ in range(max_steps):
        a = client.post("/api/submit-answer", json={"session_id": sid, "answer": "gradient descent minimises loss"})
        assert a.status_code == 200, a.get_json()
        a = a.get_json()
        if a["round_action"] == "end_interview":
            return a
        if a["round_action"] in ("next_round", "continue_round"):
            c = client.post("/api/check-round-completion", json={"session_id": sid}).get_json()
            last = c
        else:
            client.post("/api/next-question", json={"session_id": sid})
    raise AssertionError("interview did not terminate")


def test_full_curated_interview_and_report(client, svc, app_module):
    _, d = start(client, role="Python Developer", model="bilstm")
    sid = d["session_id"]
    _drive(client, sid)
    e = client.post("/api/end-interview", json={"session_id": sid})
    assert e.status_code == 202
    for _ in range(100):
        s = client.get(f"/api/reports/{sid}/status")
        if s.status_code != 202:
            break
        time.sleep(0.1)
    assert s.status_code == 200, s.get_json()
    rep = s.get_json()
    assert "status" not in rep or rep["status"] != "failed"                 # on success the route returns the report body itself
    assert "smi-" in json.dumps(rep)                                       # curated string ids survived into the report


def test_adaptive_engine_with_curated(client, svc, app_module):
    r, d = start(client, role="Data Scientist", model="tfidf")
    assert r.status_code == 200
    a = client.post("/api/submit-answer", json={"session_id": d["session_id"], "answer": "x"}).get_json()
    assert "similarity_score" in a


def test_followup_endpoints_carry_metadata_in_curated_only(client, svc, app_module):
    _, d = start(client, role="Python Developer")
    sid = d["session_id"]
    cur = client.get(f"/api/current-question?session_id={sid}").get_json()
    rep = client.get(f"/api/repeat-question?session_id={sid}").get_json()
    for body in (cur, rep):
        assert body["question_source"] == "curated" and body["domain"] == "Python" and body["difficulty"] == "Easy"
    nxt = client.post("/api/next-question", json={"session_id": sid}).get_json()
    assert nxt["question_source"] == "curated" and isinstance(nxt["question_id"], str)


# ---------- feature flag ----------
def test_default_is_legacy_and_ints(client, svc, app_module):
    r = client.post("/api/start-interview", json={"role": "Python Developer"})
    d = r.get_json()
    assert "question_source" not in d and isinstance(d["current_question"]["question_id"], int)
    assert sess(app_module, d).question_source == "legacy"


def test_env_flag_switches_default_and_request_overrides(client, svc, app_module, monkeypatch):
    monkeypatch.setenv("SMART_QUESTION_SOURCE", "curated")
    d = client.post("/api/start-interview", json={"role": "Python Developer"}).get_json()
    assert d["question_source"] == "curated" and isinstance(d["current_question"]["question_id"], str)
    d = client.post("/api/start-interview", json={"role": "Python Developer", "question_source": "legacy"}).get_json()
    assert "question_source" not in d and isinstance(d["current_question"]["question_id"], int)


def test_flag_switching_never_mixes_sources(client, svc, app_module):
    s1 = sess(app_module, client.post("/api/start-interview", json={"role": "Python Developer"}).get_json())
    s2 = sess(app_module, client.post("/api/start-interview", json={"role": "Python Developer", **CUR}).get_json())
    s3 = sess(app_module, client.post("/api/start-interview", json={"role": "Python Developer"}).get_json())
    assert all(isinstance(q["id"], int) for q in s1.all_questions) and all(isinstance(q["id"], int) for q in s3.all_questions)
    assert all(isinstance(q["id"], str) and q["id"].startswith("smi-") for q in s2.all_questions)
    assert {s1.question_source, s2.question_source, s3.question_source} == {"legacy", "curated"}


def test_source_locked_per_session_ignores_later_env_change(client, svc, app_module, monkeypatch):
    _, d = start(client, role="Python Developer")
    monkeypatch.setenv("SMART_QUESTION_SOURCE", "legacy")
    cur = client.get(f"/api/current-question?session_id={d['session_id']}").get_json()
    assert cur["question_source"] == "curated" and isinstance(cur["question_id"], str)


@pytest.mark.parametrize("val", ["bogus", "", 5, ["curated"], None.__class__.__name__])
def test_invalid_question_source_rejected(client, svc, val):
    r = client.post("/api/start-interview", json={"role": "Python Developer", "question_source": val})
    assert r.status_code == 400 and "Invalid question_source" in r.get_json()["error"]


def test_invalid_env_flag_is_loud_not_silent(client, svc, monkeypatch):
    monkeypatch.setenv("SMART_QUESTION_SOURCE", "nonsense")
    r = client.post("/api/start-interview", json={"role": "Python Developer"})
    assert r.status_code == 400 and "SMART_QUESTION_SOURCE" in r.get_json()["error"]


def test_legacy_mode_does_not_import_retrieval_stack():
    code = r'''
import sys, random
sys.path.insert(0, %r)
import importlib.util
spec = importlib.util.spec_from_file_location("smart_app", %r); m = importlib.util.module_from_spec(spec); sys.modules["smart_app"] = m; spec.loader.exec_module(m)
import interview_session
class S:
    def score(self, a, b): return 0.5
interview_session.get_scorer = lambda k, corpus=None: S()
c = m.app.test_client()
r = c.post("/api/start-interview", json={"role": "Python Developer"}); assert r.status_code == 200, r.get_json()
bad = [x for x in ("faiss", "torch", "sentence_transformers", "src.retrieval.service", "src.retrieval.index", "src.retrieval.embeddings") if x in sys.modules]
print("LOADED:" + ",".join(bad))
''' % (str(ROOT), str(ROOT / "main" / "app.py"))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    assert out.returncode == 0, out.stderr[-800:]
    assert out.stdout.strip().splitlines()[-1] == "LOADED:", out.stdout


# ---------- retrieval endpoints ----------
def test_retrieval_endpoints_hidden_in_default_legacy(client, svc):
    assert client.get("/api/retrieval/status").status_code == 404
    assert client.post("/api/retrieval/search", json={"query": "x"}).status_code == 404


@pytest.fixture()
def enabled(monkeypatch):
    monkeypatch.setenv("SMART_RETRIEVAL_ENABLED", "1")


def test_search_contract_and_redaction(client, svc, enabled, monkeypatch):
    r = client.post("/api/retrieval/search", json={"query": "what is overfitting in machine learning", "k": 3})
    d = r.get_json()
    assert r.status_code == 200 and d["mode"] == "semantic" and d["score_type"] == "cosine" and len(d["results"]) == 3
    assert d["threshold"]["applied"] is False and d["no_answer"] is False
    hit = d["results"][0]
    assert {"rank", "score", "question_id", "domain", "topic", "difficulty", "question", "key_concepts"} <= set(hit)
    assert "reference_answer" not in hit                                             # redacted by default
    monkeypatch.setenv("SMART_RETRIEVAL_EXPOSE_REFERENCE", "1")
    d2 = client.post("/api/retrieval/search", json={"query": "what is overfitting in machine learning", "k": 3}).get_json()
    assert d2["results"][0]["reference_answer"]
    assert [h["question_id"] for h in d["results"]] == [h["question_id"] for h in d2["results"]]


def test_search_filters(client, svc, enabled):
    d = client.post("/api/retrieval/search", json={"query": "explain joins", "k": 5, "domain": "SQL", "difficulty": "Medium"}).get_json()
    assert d["results"] and all(h["domain"] == "SQL" and h["difficulty"] == "Medium" for h in d["results"])


@pytest.mark.parametrize("body", [
    {}, {"query": ""}, {"query": "   "}, {"query": 5}, {"query": "x", "k": 0}, {"query": "x", "k": True}, {"query": "x", "k": "3"},
    {"query": "x", "domain": "Nope"}, {"query": "x", "difficulty": "Impossible"}, {"query": "x", "min_score": "high"}, {"query": "x" * 5000},
])
def test_search_invalid_inputs_400(client, svc, enabled, body):
    r = client.post("/api/retrieval/search", json=body)
    assert r.status_code == 400 and "error" in r.get_json()


def test_search_non_json_400(client, svc, enabled):
    assert client.post("/api/retrieval/search", data="x", content_type="text/plain").status_code == 400
    assert client.post("/api/retrieval/search", json=[1, 2]).status_code == 400


def test_no_answer_flag_only_with_explicit_threshold(client, svc, enabled):
    q = {"query": "overfitting in machine learning models", "k": 5}
    base = client.post("/api/retrieval/search", json=q).get_json()
    assert base["no_answer"] is False and base["results"]                            # no default threshold: candidates are always returned
    hi = client.post("/api/retrieval/search", json={**q, "min_score": 1.01}).get_json()   # cosine can never exceed 1
    assert hi["threshold"]["applied"] is True and hi["no_answer"] is True and hi["results"] == []
    assert "not validated" in hi["threshold"]["note"]
    kept = client.post("/api/retrieval/search", json={**q, "min_score": -1}).get_json()
    assert kept["no_answer"] is False and len(kept["results"]) == 5


def test_empty_retrieval_is_flagged_no_answer(client, svc, enabled):
    """Out-of-vocabulary gibberish gives the dev stand-in a zero vector -> nothing retrieved; must be flagged, not silent."""
    d = client.post("/api/retrieval/search", json={"query": "zxqv blorf wug flim", "k": 5}).get_json()
    assert d["results"] == [] and d["no_answer"] is True


def test_repeated_requests_load_model_once_and_are_deterministic(client, svc, enabled):
    outs = [client.post("/api/retrieval/search", json={"query": "bias variance tradeoff", "k": 5}).get_json() for _ in range(15)]
    assert svc.sem_loads == 1 and svc.status()["semantic_loads"] == 1
    assert len({json.dumps([h["question_id"] for h in o["results"]]) for o in outs}) == 1
    assert svc.requests == 15


def test_status_lazy_then_loaded(client, svc, enabled):
    assert client.get("/api/retrieval/status").get_json()["mode"] == "not_loaded"
    client.post("/api/retrieval/search", json={"query": "x y"})
    st = client.get("/api/retrieval/status").get_json()
    assert st["mode"] == "semantic" and st["n_records"] == 666 and st["corpus_ok"] and "model_load_s" in st["timings_s"]


def test_session_context(client, svc, app_module):
    _, d = start(client, role="Python Developer")
    cur = d["current_question"]
    r = client.get(f"/api/retrieval/session-context?session_id={d['session_id']}&k=4")
    b = r.get_json()
    assert r.status_code == 200 and b["for_question_id"] == cur["question_id"] and len(b["results"]) == 4
    assert all(h["question_id"] != cur["question_id"] for h in b["results"]) and [h["rank"] for h in b["results"]] == [1, 2, 3, 4]
    assert all("reference_answer" not in h for h in b["results"])
    assert client.get(f"/api/retrieval/session-context?session_id={d['session_id']}&k=abc").status_code == 400
    assert client.get("/api/retrieval/session-context?session_id=nope").status_code == 400


def test_session_context_rejects_legacy_session(client, svc, app_module):
    d = client.post("/api/start-interview", json={"role": "Python Developer"}).get_json()
    r = client.get(f"/api/retrieval/session-context?session_id={d['session_id']}")
    assert r.status_code == 409 and r.get_json()["question_source"] == "legacy"


# ---------- failure handling ----------
def test_corrupt_index_is_rebuilt_once(client, svc, enabled, tmp_path):
    client.post("/api/retrieval/search", json={"query": "warm up"})
    f = next((tmp_path / "idx").glob("*/index.faiss"))
    f.write_bytes(b"corrupt" * 100)
    from src.retrieval.service import RetrievalService, set_service
    s2 = RetrievalService(backend="dev-lsa", index_root=tmp_path / "idx", cache_dir=tmp_path / "cache")
    set_service(s2)
    d = client.post("/api/retrieval/search", json={"query": "warm up"}).get_json()
    assert d["mode"] == "semantic" and s2.index_rebuilt is True and s2.sem_loads == 1


def test_missing_index_is_built(client, svc, enabled, tmp_path):
    assert not (tmp_path / "idx").exists()
    assert client.post("/api/retrieval/search", json={"query": "x y"}).get_json()["mode"] == "semantic"
    assert svc.index_rebuilt is True


def test_index_unusable_falls_back_to_bm25_and_says_so(client, svc, enabled, monkeypatch):
    import src.retrieval.index as ix
    monkeypatch.setattr(ix, "ensure_index", lambda *a, **k: (_ for _ in ()).throw(ix.IndexMismatchError("boom")))
    d = client.post("/api/retrieval/search", json={"query": "overfitting", "k": 3, "min_score": 0.5}).get_json()
    assert d["mode"] == "bm25_fallback" and d["score_type"] == "bm25" and "boom" in d["degraded_reason"]
    assert d["threshold"]["applied"] is False and "ignored" in d["threshold"]["note"]          # cosine threshold never applied to BM25
    assert all(h["question_id"].startswith("smi-") for h in d["results"])                      # still curated records only
    assert svc.sem_loads == 0 and client.get("/api/retrieval/status").get_json()["mode"] == "bm25_fallback"
    # failure is not retried per request (sticky) - no repeated slow failing loads
    client.post("/api/retrieval/search", json={"query": "overfitting"})
    assert svc.sem_loads == 0


def test_model_unavailable_falls_back_to_bm25(client, tmp_path, enabled):
    from src.retrieval.service import RetrievalService, set_service
    s = RetrievalService(backend="minilm", model_name=str(tmp_path / "no_such_model"), local_files_only=True,
                         index_root=tmp_path / "i", cache_dir=tmp_path / "c")
    set_service(s)
    try:
        d = client.post("/api/retrieval/search", json={"query": "what is a decision tree", "k": 3}).get_json()
        assert d["mode"] == "bm25_fallback" and d["degraded_reason"] and d["results"]
        # an interview can still be started - question selection does not need the model
        r = client.post("/api/start-interview", json={"role": "Python Developer", **CUR})
        assert r.status_code == 200
    finally:
        set_service(None)


def test_corpus_failure_returns_503_and_never_falls_back_to_legacy(client, tmp_path, enabled, app_module):
    from src.retrieval.service import RetrievalService, set_service
    set_service(RetrievalService(root=tmp_path, backend="dev-lsa"))                   # empty root -> corpus cannot load
    try:
        r = client.post("/api/start-interview", json={"role": "Python Developer", **CUR})
        assert r.status_code == 503 and r.get_json()["question_source"] == "curated" and "corpus unavailable" in r.get_json()["error"]
        assert app_module.sessions == {}                                              # no half-built session
        assert client.post("/api/retrieval/search", json={"query": "x y"}).status_code == 503
        st = client.get("/api/retrieval/status").get_json()
        assert st["corpus_ok"] is False and st["mode"] == "unavailable"
        r = client.post("/api/start-interview", json={"role": "Python Developer"})   # legacy is unaffected
        assert r.status_code == 200 and isinstance(r.get_json()["current_question"]["question_id"], int)
    finally:
        set_service(None)


def test_search_failure_inside_retriever_is_not_a_silent_success(client, svc, enabled, monkeypatch):
    client.post("/api/retrieval/search", json={"query": "warm"})
    monkeypatch.setattr(svc._semantic, "search", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("faiss exploded")))
    with pytest.raises(RuntimeError):
        client.post("/api/retrieval/search", json={"query": "x y"})       # propagates (TESTING mode); in production -> 500, never fake results


def test_warmup_flag_loads_in_background_without_blocking_startup(svc, monkeypatch):
    import flask, threading
    from src.retrieval import flask_api
    monkeypatch.setenv("SMART_RETRIEVAL_ENABLED", "1")
    monkeypatch.setenv("SMART_RETRIEVAL_WARMUP", "1")
    app = flask.Flask("warm_test")
    flask_api.retrieval_blueprint.name  # blueprint reused; register on a throwaway app
    flask_api.init_retrieval(app, {})
    for t in threading.enumerate():
        if t.name == "retrieval-warmup":
            t.join(60)
    assert svc.status()["mode"] == "semantic" and svc.sem_loads == 1
