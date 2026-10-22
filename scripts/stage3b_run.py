"""Stage 3B: run the benchmark through a REAL local model (Ollama) with the Stage 3A evaluator. Writes raw evidence only; analysis is separate.

    python scripts/stage3b_run.py --model <installed-model-name> --set smoke            # 12 items x 1 run: does it work at all?
    python scripts/stage3b_run.py --model <name> --set full --repeats 3                # 43 items x 3 runs (consistency)
    python scripts/stage3b_run.py --model <name> --set full --repeats 1 --stress-temperature 0.3 --stress-repeats 2

Safety: only talks to your local Ollama (OLLAMA_HOST or 127.0.0.1:11434); NEVER pulls a model (it exits if the model is not installed);
no hosted API is touched. Results are saved after every call, so you can stop with Ctrl+C and keep what has run. --selftest uses a
scripted MOCK instead of a model and is only for checking the plumbing.
"""
import argparse, hashlib, json, os, platform, statistics, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "data" / "evaluation" / "bench_v1"
OUT = ROOT / "data" / "evaluation" / "stage3b"
SMOKE = "B01,B03,B04,B07,B11,B13,B15,B20,B22,B40,B41,B43".split(",")


def http_json(host, path, body=None, timeout=15):
    req = urllib.request.Request(host + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def code_fingerprint():
    h = hashlib.sha256()
    for f in sorted((ROOT / "src" / "evaluation").rglob("*.py")):
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()[:16]


class Recording:
    """Wraps a provider and keeps every raw reply / error (the evaluator itself only keeps validated results)."""
    def __init__(self, inner):
        self.inner, self.name, self.model, self.is_mock, self.paid = inner, inner.name, inner.model, inner.is_mock, inner.paid
        self.log = []

    def generate(self, system, user):
        t = time.perf_counter()
        try:
            r = self.inner.generate(system, user)
            self.log.append({"ok": True, "ms": round((time.perf_counter() - t) * 1000, 1), "raw": r.text, "usage": r.usage})
            return r
        except Exception as e:
            self.log.append({"ok": False, "ms": round((time.perf_counter() - t) * 1000, 1), "error": f"{type(e).__name__}: {e}"[:300]})
            raise


def selftest_provider(exps):
    """PLUMBING ONLY. Replies with a canned JSON whose levels follow the expectation midpoint. Says nothing about any model."""
    from src.evaluation.providers.mock import MockProvider
    by_text = {}
    def reply(system, user):
        for iid, e in exps.items():
            if iid in by_text and by_text[iid] in user:
                lo, hi = e["score_min"] or 0, e["score_max"] or 100
                lv = max(0, min(4, round(((lo + hi) / 2) / 25)))
                return {"gradable": True, "rubric": {k: {"level": lv, "justification": "selftest"} for k in ("correctness", "completeness", "relevance", "reasoning")},
                        "score_rationale": "SELFTEST canned reply", "confidence": "medium"}
        return {"gradable": False, "not_gradable_reason": "selftest: unknown item"}
    return MockProvider(reply), by_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=False, default="")
    ap.add_argument("--set", choices=["smoke", "full"], default="smoke")
    ap.add_argument("--items", default="", help="comma list of item ids (overrides --set)")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--stress-temperature", type=float, default=None)
    ap.add_argument("--stress-repeats", type=int, default=2)
    ap.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--schema", action="store_true", help="Ollama schema-constrained output (all keys required) instead of plain JSON mode")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out-dir", default=str(OUT))
    a = ap.parse_args()
    host = a.host if a.host.startswith("http") else "http://" + a.host
    host = host.rstrip("/")

    from src.evaluation.evaluator import AnswerEvaluator
    from src.evaluation.grounding import build_request
    from src.evaluation.prompt import PROMPT_VERSION
    from src.evaluation.rubric import RUBRIC_VERSION
    from src.evaluation.providers.http import OllamaProvider
    from src.evaluation.schema import OUTPUT_JSON_SCHEMA
    from src.retrieval.service import RetrievalService

    items = [json.loads(l) for l in (BENCH / "items.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    exps = {e["item_id"]: e for e in map(json.loads, (BENCH / "expectations.jsonl").read_text(encoding="utf-8").splitlines() if (BENCH / "expectations.jsonl").exists() else [])} if a.selftest else {}
    want = [x.strip() for x in a.items.split(",") if x.strip()] or (SMOKE if a.set == "smoke" else [i["item_id"] for i in items])
    items = [i for i in items if i["item_id"] in want]

    meta = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "platform": platform.platform(), "python": sys.version.split()[0],
            "host": host, "model": a.model, "set": a.set if not a.items else "custom", "repeats": a.repeats, "num_ctx": a.num_ctx,
            "prompt_version": PROMPT_VERSION, "rubric_version": RUBRIC_VERSION, "evaluation_code_fingerprint": code_fingerprint(),
            "bench": "bench_v1", "is_mock": bool(a.selftest), "structured_schema": bool(a.schema)}
    if a.selftest:
        meta["model"] = meta["model"] or "SELFTEST-MOCK"
    else:
        if not a.model:
            sys.exit("--model is required (use the probe script to see installed models)")
        try:
            tags = http_json(host, "/api/tags")
        except Exception as e:
            sys.exit(f"Cannot reach Ollama at {host}: {e}\nStart Ollama, or pass --host. Nothing was downloaded.")
        names = [m["name"] for m in tags.get("models", [])]
        if a.model not in names:
            sys.exit(f"Model {a.model!r} is not installed. Installed: {names}\nThis script never downloads models.")
        try:
            sh = http_json(host, "/api/show", {"model": a.model})
            meta["model_details"] = {"details": sh.get("details"), "parameters": (sh.get("parameters") or "")[:400], "capabilities": sh.get("capabilities")}
        except Exception as e:
            meta["model_details"] = {"error": str(e)[:200]}
        meta["ollama_version"] = http_json(host, "/api/version").get("version")

    svc = RetrievalService()
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in meta["model"])
    out = Path(a.out_dir) / f"runs_{safe}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {"meta": meta, "runs": []}
    plan = [(i, r, 0.0) for r in range(a.repeats) for i in items]
    if a.stress_temperature is not None:
        plan += [(i, r, a.stress_temperature) for r in range(a.stress_repeats) for i in items]
    print(f"{len(plan)} calls planned against {meta['model']} ({'MOCK SELFTEST' if a.selftest else host}); results -> {out}")
    t_start = time.perf_counter()
    for n, (it, rep, temp) in enumerate(plan, 1):
        req = build_request(it["question_id"], it["candidate_answer"], service=svc)
        if a.selftest:
            inner, by_text = selftest_provider(exps)
            by_text[it["item_id"]] = it["candidate_answer"][:40] if it["candidate_answer"] else "\0never"
        else:
            inner = OllamaProvider(a.model, host, a.timeout, num_ctx=a.num_ctx, temperature=temp, seed=7 + rep,
                                  response_schema=OUTPUT_JSON_SCHEMA if a.schema else None)
        prov = Recording(inner)
        ev = AnswerEvaluator(prov, max_retries=1)
        t = time.perf_counter()
        res = ev.evaluate(req)
        wall = round((time.perf_counter() - t) * 1000, 1)
        rec = {"item_id": it["item_id"], "repeat": rep, "temperature": temp, "wall_ms": wall, "result": json.loads(res.model_dump_json()), "provider_log": prov.log}
        if not a.selftest and n == 1:
            try:
                rec["ollama_ps_after_first_call"] = http_json(host, "/api/ps")
            except Exception as e:
                rec["ollama_ps_after_first_call"] = {"error": str(e)[:100]}
        doc["runs"].append(rec)
        out.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        r = rec["result"]
        el = time.perf_counter() - t_start
        print(f"[{n}/{len(plan)}] {it['item_id']} r{rep} T={temp}: {r['evaluation_status']:<22} score={r['provisional_score']} conf={r['confidence']} attempts={r['provenance']['attempts']} {wall/1000:.1f}s  (eta {el/n*(len(plan)-n)/60:.0f} min)")
    print("\ndone ->", out, "\nnext: python audit/evaluation/stage3b_analyze.py", out)


if __name__ == "__main__":
    main()
