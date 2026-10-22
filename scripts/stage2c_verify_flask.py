"""Stage 2C-final: verify the selected retrieval format through the REAL Flask app with REAL all-MiniLM-L6-v2 (run on your machine).

    python scripts/stage2c_verify_flask.py            ->  writes reports/stage2c_flask_verification.json and prints PASS/FAIL per check

Uses Flask's test client against main/app.py (real routes, real session class, real MiniLM + FAISS, answer scorer NOT invoked for the
retrieval checks). The legacy cold-start probe times the app's own `get_scorer('bert')` separately from retrieval. Nothing here
changes behaviour or data; it only reads and times.
"""
import importlib.util, json, os, random, statistics, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for p in ("src", "src/components", "src/model"):
    sys.path.insert(0, str(ROOT / p))
os.environ["SMART_RETRIEVAL_ENABLED"] = "1"

results, evidence = [], {}


def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f"  - {detail}" if detail else ""))


def main():
    spec = importlib.util.spec_from_file_location("smart_app", ROOT / "main" / "app.py")
    m = importlib.util.module_from_spec(spec); sys.modules["smart_app"] = m; spec.loader.exec_module(m)
    from src.retrieval.corpus import corpus_fingerprint, load_corpus
    from src.retrieval.service import RetrievalService, set_service
    corpus = load_corpus(); fp0 = corpus_fingerprint(corpus["records"])
    tmp = tempfile.mkdtemp()
    svc = RetrievalService(backend="minilm", local_files_only=True, index_root=Path(tmp) / "i", cache_dir=Path(tmp) / "c")
    set_service(svc)
    m.app.config["TESTING"] = True
    c = m.app.test_client()
    post = lambda path, body: c.post(path, json=body)

    t = time.perf_counter(); r = post("/api/retrieval/search", {"query": "Explain how bubble sort works and why it is slow.", "k": 5}); first_ms = (time.perf_counter() - t) * 1000
    d = r.get_json(); ids = [h["question_id"] for h in d["results"]]
    check("semantic mode with real MiniLM", d["mode"] == "semantic", f"first request {first_ms:.0f} ms (includes model load + index build/load)")
    check("bubble sort paraphrase: smi-0453 first, quicksort smi-0452 in top 3", ids[0] == "smi-0453" and "smi-0452" in ids[:3], str(ids))
    evidence["bubble_paraphrase"] = d["results"]
    lat = []
    for q in ["what is overfitting", "explain SQL joins", "how does a transformer work", "docker vs virtual machine", "what is a p-value"] * 10:
        t = time.perf_counter(); post("/api/retrieval/search", {"query": q, "k": 5}); lat.append((time.perf_counter() - t) * 1000)
    evidence["warm_latency_ms"] = {"n": len(lat), "p50": round(statistics.median(lat), 2), "p95": round(sorted(lat)[int(.95 * len(lat)) - 1], 2)}
    st = c.get("/api/retrieval/status").get_json(); evidence["status"] = st
    check("selected format active, model/index loaded once across 51 requests", st["doc_mode"] == "qk_concise" and st["semantic_loads"] == 1, json.dumps({k: st.get(k) for k in ("doc_mode", "mode", "semantic_loads")}))
    ids_all = [x["question_id"] for x in corpus["records"]]
    check("stable id <-> FAISS row mapping (666 ids in corpus order)", svc._semantic.vindex.ids == ids_all and svc._semantic.vindex.index.ntotal == 666)
    d = post("/api/retrieval/search", {"query": "explain joins", "k": 5, "domain": "SQL", "difficulty": "Medium"}).get_json()
    check("domain + difficulty filters", d["results"] and all(h["domain"] == "SQL" and h["difficulty"] == "Medium" for h in d["results"]))
    check("metadata present and canonical answer redacted", all(h.get("topic") and h["question_id"].startswith("smi-") and "canonical_answer" not in h for h in d["results"]))
    r = post("/api/start-interview", {"role": "Machine Learning Engineer", "question_source": "curated", "model": "bilstm"})
    sj0 = r.get_json(); sid = sj0["session_id"]; cur = sj0["current_question"]["question_id"]
    sj = c.get("/api/retrieval/session-context", query_string={"session_id": sid, "k": 5}).get_json()
    sids = [h["question_id"] for h in sj["results"]]
    check("session-context excludes the current question and returns 5 related", cur not in sids and len(sids) == 5 and sj["for_question_id"] == cur, f"{cur} -> {sids}")
    q = svc.get("smi-0453")["question"]
    d = post("/api/retrieval/search", {"query": q, "k": 6}).get_json(); oth = [h["question_id"] for h in d["results"] if h["question_id"] != "smi-0453"]
    check("bubble sort exact question: self best, quicksort smi-0452 in top 5 after excluding self", d["results"][0]["question_id"] == "smi-0453" and "smi-0452" in oth[:5], str(oth))
    off = post("/api/retrieval/search", {"query": "How do I prepare a sourdough starter?", "k": 3, "min_score": 0.6}).get_json()
    check("explicit threshold flags off-topic as no_answer (no default threshold is validated)", off.get("no_answer") is True)
    check("no dataset change", corpus_fingerprint(load_corpus()["records"]) == fp0)
    bad = RetrievalService(backend="minilm", model_name="/nonexistent/model", local_files_only=True, index_root=Path(tmp) / "j", cache_dir=Path(tmp) / "k")
    set_service(bad); fb = post("/api/retrieval/search", {"query": "bubble sort", "k": 3}).get_json()
    check("explicit BM25 fallback when the model cannot load", fb["mode"] == "bm25_fallback" and fb["results"], fb.get("mode", ""))
    set_service(svc)

    # legacy cold start: time the app's own scorer load separately from retrieval
    import interview_session  # noqa: F401
    from model_registry import get_scorer
    t = time.perf_counter(); get_scorer("bert"); s1 = time.perf_counter() - t
    t = time.perf_counter(); get_scorer("bert"); s2 = time.perf_counter() - t
    evidence["legacy_scorer_load_s"] = {"first_get_scorer_bert": round(s1, 2), "second": round(s2, 2)}
    t = time.perf_counter(); r = post("/api/start-interview", {"role": "Python Developer", "model": "bert"}); evidence["legacy_start_after_warm_s"] = round(time.perf_counter() - t, 2)
    evidence["legacy_start_status"] = r.status_code
    print("legacy scorer load (first/second): %.2fs / %.2fs ; start after warm: %.2fs" % (s1, s2, evidence["legacy_start_after_warm_s"]))

    out = ROOT / "reports" / "stage2c_flask_verification.json"
    out.write_text(json.dumps({"results": results, "evidence": evidence, "all_pass": all(x["pass"] for x in results)}, indent=2), encoding="utf-8")
    print("\nALL PASS" if all(x["pass"] for x in results) else "\nSOME CHECKS FAILED", "->", out)


if __name__ == "__main__":
    main()
