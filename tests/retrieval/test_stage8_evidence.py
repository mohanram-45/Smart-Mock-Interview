"""Stage 8B: retrieval evidence band, embedding coverage, provenance and the diagnostics endpoint. Offline: dev-lsa stand-in and fake tokenizers only."""
import json
from pathlib import Path

import pytest

from src.retrieval import evidence

ROOT = Path(__file__).resolve().parents[2]


def test_band_thresholds_and_no_calibration_claim():
    assert evidence.assess_evidence([0.39], "cosine")["band"] == "insufficient"
    assert evidence.assess_evidence([0.40], "cosine")["band"] == "weak"
    assert evidence.assess_evidence([0.449], "cosine")["band"] == "weak"
    assert evidence.assess_evidence([0.45, 0.30], "cosine")["band"] == "adequate"
    e = evidence.assess_evidence([0.6, 0.5], "cosine")
    assert e["calibrated"] is False and e["margin"] == pytest.approx(0.1) and "uncalibrated" in e["basis"]


def test_empty_and_bm25_results_get_no_numeric_band():
    assert evidence.assess_evidence([], "cosine")["band"] == "insufficient"
    b = evidence.assess_evidence([7.2, 3.0], "bm25")
    assert b["band"] == "not_available" and b["margin"] is None and "fallback" in b["reason"]


def _rec(answer="First sentence here. Second sentence here. Third one."):
    return {"question_id": "smi-x", "topic": "T", "question": "Q?", "key_concepts": ["a", "b"], "canonical_answer": answer, "provenance": {"origin": "v5"}}


def _words(text):
    return len(text.split())


def test_coverage_reports_unknown_without_a_tokenizer():
    c = evidence.embedding_coverage(_rec(), "qk_concise", None)
    assert c["status"] == "unknown" and c["answer_sentences_embedded"] is None and c["answer_sentences_total"] == 3


def test_coverage_distinguishes_complete_partial_and_head_truncated():
    assert evidence.embedding_coverage(_rec(), "qk_concise", _words, 256)["status"] == "answer_complete"
    long_answer = " ".join(f"Sentence number {i} says something useful." for i in range(60))
    partial = evidence.embedding_coverage(_rec(long_answer), "qk_concise", _words, 80)
    assert partial["status"] == "answer_partial" and 0 < partial["answer_sentences_embedded"] < partial["answer_sentences_total"] == 60
    assert evidence.embedding_coverage(_rec(), "qk_concise", _words, 6)["status"] == "head_truncated"
    assert evidence.embedding_coverage(_rec(), "qk", _words)["status"] == "answer_not_embedded"


def test_provenance_never_contains_reference_text():
    p = evidence.hit_provenance(_rec(), corpus_sha256="ab" * 32, doc_mode="qk_concise", rank_in_other=2)
    flat = json.dumps(p)
    assert p["origin"] == "v5" and p["bm25_rank"] == 2 and len(p["corpus_sha256"]) == 16
    assert "sentence" not in flat.lower() and "Key concepts" not in flat


def test_agreement_is_informational():
    a = evidence.agreement(["a", "b", "c"], ["a", "c", "z"])
    assert a == {"k": 3, "top1_same": True, "overlap_at_k": 2, "bm25_returned": 3}
    assert evidence.agreement([], [])["top1_same"] is False


# ---- service + Flask ----
@pytest.fixture()
def dsvc(tmp_path):
    from src.retrieval.service import RetrievalService, set_service
    s = RetrievalService(backend="dev-lsa", index_root=tmp_path / "idx", cache_dir=tmp_path / "cache")
    set_service(s)
    yield s
    set_service(None)


def test_diagnose_has_versions_and_no_reference_material(dsvc):
    d = dsvc.diagnose("How does a clustered index differ from a non-clustered index in SQL?", 3)
    assert d["mode"] == "semantic" and d["score_type"] == "cosine" and len(d["results"]) == 3
    assert d["versions"]["index_matches_corpus"] is True and d["versions"]["corpus_sha256"] == dsvc.corpus()["manifest"]["corpus_sha256"]
    assert d["evidence"]["calibrated"] is False and "agreement" in d
    rec = dsvc.get(d["results"][0]["question_id"])
    flat = json.dumps(d)
    assert rec["canonical_answer"][:60] not in flat and rec["question"] not in flat
    for r in d["results"]:
        assert set(r) == {"rank", "score", "question_id", "domain", "topic", "difficulty", "provenance", "embedding_coverage"}
        assert r["embedding_coverage"]["token_counter"].startswith("approximate")        # the dev stand-in only approximates tokens: labelled, not presented as MiniLM truth


def test_diagnose_falls_back_to_bm25_without_claiming_a_band(dsvc, monkeypatch):
    monkeypatch.setattr(dsvc, "_load_semantic", lambda: None)
    dsvc._sem_error = "forced for test"
    d = dsvc.diagnose("clustered index", 2)
    assert d["mode"] == "bm25_fallback" and d["evidence"]["band"] == "not_available" and d["versions"]["index_faiss_sha256"] is None
    assert all(r["embedding_coverage"]["status"] == "not_applicable" for r in d["results"])


def test_diagnose_rejects_bad_input(dsvc):
    from src.retrieval.service import RetrievalInputError
    with pytest.raises(RetrievalInputError):
        dsvc.diagnose("", 3)
    with pytest.raises(RetrievalInputError):
        dsvc.diagnose("ok", 0)


def test_diagnostics_route_is_opt_in_and_never_exposes_reference(dsvc, monkeypatch):
    from flask import Flask
    from src.retrieval.flask_api import init_retrieval
    monkeypatch.delenv("SMART_RETRIEVAL_ENABLED", raising=False)
    monkeypatch.delenv("SMART_QUESTION_SOURCE", raising=False)
    monkeypatch.setenv("SMART_RETRIEVAL_EXPOSE_REFERENCE", "1")         # even the reference-exposure opt-in must not leak through diagnostics
    app = Flask(__name__)
    init_retrieval(app, {})
    c = app.test_client()
    assert c.post("/api/retrieval/diagnostics", json={"query": "sql index"}).status_code == 404
    monkeypatch.setenv("SMART_RETRIEVAL_ENABLED", "1")
    r = c.post("/api/retrieval/diagnostics", json={"query": "How does a clustered index work in SQL?", "k": 2})
    assert r.status_code == 200
    body = r.get_json()
    assert "reference_answer" not in json.dumps(body) and "canonical_answer" not in json.dumps(body)
    assert c.post("/api/retrieval/diagnostics", json={"query": ""}).status_code == 400
    assert c.post("/api/retrieval/diagnostics", data="x").status_code == 400


def test_stored_minilm_numbers_behind_the_band_still_hold():
    """The band's documented evidence is recomputed from the committed Stage 2C rankings, so the docstring cannot drift from the data."""
    from src.retrieval.evaluate import load_eval_set
    R = json.loads((ROOT / "data/retrieval/stage2c/rankings_minilm.json").read_text(encoding="utf-8"))["sets"]
    for name, path, na_caught, ans_flagged in (("dev", "data/retrieval/eval/stage2c_dev_v2plus.jsonl", 19, 4), ("challenge", "data/retrieval/eval/challenge_v1/eval_set.jsonl", 10, 1)):
        rk = R[name]["rankings"]["dense_qk_concise"]
        ev = load_eval_set(ROOT / path)
        low = lambda e: rk[e["query_id"]][0][1] < evidence.BAND_INSUFFICIENT_BELOW  # noqa: E731
        assert sum(low(e) for e in ev if not e["relevant"]) == na_caught
        assert sum(low(e) for e in ev if e["relevant"]) == ans_flagged


def test_committed_probe_report_matches_recomputation_and_rerank_is_not_adopted():
    import importlib.util
    spec = importlib.util.spec_from_file_location("stage8_retrieval_probe", ROOT / "scripts" / "stage8_retrieval_probe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--check"]) == 0
    dev = mod.compute()["rerank"]["dev"]["by_weight"]
    assert max(v["success@1"] for v in dev.values()) == dev["0.0"]["success@1"]      # no concept-coverage weight beats plain cosine on dev
    import src.retrieval as pkg
    assert not hasattr(pkg, "rerank")                                              # nothing was shipped for an idea that did not help
