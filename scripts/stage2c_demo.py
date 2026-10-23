"""Stage 2C local demo: start the EXISTING Flask app, pick curated mode explicitly, get a question, retrieve related knowledge.

  python scripts/stage2c_demo.py                      # your machine: real app scorers + real MiniLM (needs the HF cache, faiss)
  python scripts/stage2c_demo.py --backend dev-lsa --stub-scorer   # sandbox/CI: stand-in embedder + stub answer scorer (LABELLED)

Nothing here validates candidate correctness: the similarity number is whatever the app's EXISTING scorer returns for the model chosen.
"""
import argparse, json, os, statistics, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STUB_LAUNCHER = r'''
import sys, importlib.util
sys.path.insert(0, %(root)r)
spec = importlib.util.spec_from_file_location("smart_app", %(app)r); m = importlib.util.module_from_spec(spec); sys.modules["smart_app"] = m; spec.loader.exec_module(m)
import interview_session
class StubScorer:                       # DEMO ONLY: token-overlap stand-in; not one of the project's scorers
    def score(self, ref, ans):
        r = set((ref or "").lower().split()); a = (ans or "").lower().split()
        return 0.0 if not a else min(1.0, sum(w in r for w in a) / len(a))
interview_session.get_scorer = lambda key, corpus=None: StubScorer()
m.app.run(host="127.0.0.1", port=%(port)d, debug=False, use_reloader=False)
'''


def call(base, method, path, body=None):
    req = urllib.request.Request(base + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read()), (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), (time.perf_counter() - t0) * 1000


def show(title, status, body, ms=None):
    print(f"\n=== {title}  [HTTP {status}{'' if ms is None else f', {ms:.1f} ms'}]")
    print(json.dumps(body, indent=2, ensure_ascii=False)[:1600])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5057)
    ap.add_argument("--backend", default="minilm", choices=["minilm", "dev-lsa"])
    ap.add_argument("--stub-scorer", action="store_true")
    ap.add_argument("--model", default="bert", help="app scoring model when not stubbed (bilstm|bert|tfidf)")
    ap.add_argument("--n-latency", type=int, default=50)
    a = ap.parse_args()
    env = dict(os.environ, SMART_RETRIEVAL_BACKEND=a.backend, SMART_RETRIEVAL_ENABLED="1", PYTHONPATH=str(ROOT))
    env.pop("SMART_QUESTION_SOURCE", None)                      # default flag state: legacy
    if a.stub_scorer:
        cmd = [sys.executable, "-c", STUB_LAUNCHER % {"root": str(ROOT), "app": str(ROOT / "main" / "app.py"), "port": a.port}]
    else:
        cmd = [sys.executable, "-c", f"import runpy,sys; sys.argv=['app']; sys.path.insert(0,{str(ROOT)!r}); import importlib.util as u; s=u.spec_from_file_location('smart_app',{str(ROOT/'main'/'app.py')!r}); m=u.module_from_spec(s); sys.modules['smart_app']=m; s.loader.exec_module(m); m.app.run(host='127.0.0.1',port={a.port},debug=False,use_reloader=False)"]
    print(f"Embedder: {'REAL all-MiniLM-L6-v2' if a.backend == 'minilm' else 'dev-lsa STAND-IN (TF-IDF+SVD, NOT MiniLM)'}; "
          f"answer scorer: {'STUB (demo only)' if a.stub_scorer else 'app model ' + a.model}")
    proc = subprocess.Popen(cmd, env=env, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{a.port}"
    try:
        for _ in range(120):
            try:
                if call(base, "GET", "/health")[0] == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            sys.exit("server did not start")
        show("1. existing app is up: GET /health", *call(base, "GET", "/health")[:2])
        s, d, ms = call(base, "POST", "/api/start-interview", {"role": "Python Developer", "model": a.model if not a.stub_scorer else "bilstm"})
        show("2a. DEFAULT (legacy) start - unchanged contract, integer id", s, d["current_question"] if s == 200 else d, ms)
        s, st, _ = call(base, "GET", "/api/retrieval/status")
        show("2b. retrieval status BEFORE first curated use (lazy: nothing loaded yet)", s, {k: st[k] for k in ("mode", "backend", "model", "n_records")})
        s, d, ms = call(base, "POST", "/api/start-interview", {"role": "Machine Learning Engineer", "question_source": "curated",
                                                               "model": a.model if not a.stub_scorer else "bilstm"})
        show("3. curated mode selected EXPLICITLY (question_source=curated)", s, d, ms)
        sid, cq = d["session_id"], d["current_question"]
        s, ctx, ms = call(base, "GET", f"/api/retrieval/session-context?session_id={sid}&k=3")
        show(f"4. related knowledge for {cq['question_id']} (first call = cold model + index load)", s,
             {k: ctx[k] for k in ("mode", "score_type", "for_question_id", "latency_ms")} | {"results": [{k: h[k] for k in ("rank", "score", "question_id", "domain", "difficulty", "question")} for h in ctx["results"]]}, ms)
        s, ans, ms = call(base, "POST", "/api/submit-answer", {"session_id": sid, "answer": "It learns from labelled data to minimise a loss."})
        show("5. existing evaluation path (the app's own scorer; similarity != validated correctness)", s, {k: ans[k] for k in ("similarity_score", "round_action")}, ms)
        s, nxt, _ = call(base, "POST", "/api/next-question", {"session_id": sid})
        show("6. next question through the existing interface", s, nxt)
        lat = []
        for q in ["what is overfitting", "explain gradient descent", "sql window functions", "how does attention work", "tokenization in nlp"] * (a.n_latency // 5):
            s, r, ms = call(base, "POST", "/api/retrieval/search", {"query": q, "k": 5})
            lat.append((ms, r["latency_ms"]))
        http = sorted(x[0] for x in lat); eng = sorted(x[1] for x in lat)
        pct = lambda v, p: v[min(len(v) - 1, int(p * len(v)))]
        _, st, _ = call(base, "GET", "/api/retrieval/status")
        summary = {"n": len(lat), "http_ms": {"mean": round(statistics.mean(http), 2), "p50": round(pct(http, .5), 2), "p95": round(pct(http, .95), 2)},
                   "engine_ms": {"mean": round(statistics.mean(eng), 2), "p50": round(pct(eng, .5), 2), "p95": round(pct(eng, .95), 2)},
                   "semantic_loads": st["semantic_loads"], "timings_s": st["timings_s"], "mode": st["mode"]}
        show("7. warm latency + model/index loaded exactly once", 200, summary)
        s, r, _ = call(base, "POST", "/api/retrieval/search", {"query": "x", "k": 0})
        show("8. invalid input", s, r)
    finally:
        proc.terminate()
        try: proc.wait(10)
        except Exception: proc.kill()


if __name__ == "__main__":
    main()
