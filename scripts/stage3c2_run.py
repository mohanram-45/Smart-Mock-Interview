"""Stage 3C-2: controlled run of the modular evaluator with a REAL local model (Ollama, qwen2.5:7b), plus the legacy single-call evaluator on the
SAME frozen answers under the same model settings.

  python scripts/stage3c2_run.py --dry-run          # offline: verify the freeze, build every prompt + schema, check sizes. No model, no network.
  python scripts/stage3c2_run.py                    # the experiment (needs local Ollama with qwen2.5:7b INSTALLED; it never downloads anything)
  (normally launched through scripts\\stage3c2_run.ps1, which also samples RAM / GPU)

Hard rules: refuses to run if anything frozen has changed; talks only to local Ollama; never pulls a model; no hosted API; results are written after every
call; the model never assigns a score (the rubric engine does, from verified findings). Raw model replies are kept for audit.
Mock-free: this script contains no mock path. (Plumbing is tested separately against a fake local server in tests/evaluation.)
"""
import argparse, json, os, platform, shutil, statistics, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
D = ROOT / "data" / "evaluation" / "stage3c2"
MODEL = "qwen2.5:7b"


def http_json(host, path, body=None, timeout=20):
    req = urllib.request.Request(host + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def gpu_snapshot():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"], capture_output=True, text=True, timeout=10).stdout
        return out.strip()[:200]
    except Exception as e:
        return f"error: {e}"[:100]


def ram_snapshot():
    try:
        import psutil
        v = psutil.virtual_memory()
        return {"total_gb": round(v.total / 2**30, 2), "available_gb": round(v.available / 2**30, 2)}
    except Exception:
        return None


def ollama_ps(host):
    try:
        return http_json(host, "/api/ps", timeout=5)
    except Exception as e:
        return {"error": str(e)[:100]}


def load_sample(ids=None):
    rows = [json.loads(l) for l in (D / "sample.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if not ids or r["sample_id"] in ids]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ids", default="", help="comma list of sample ids (SUBSET RUN: marked partial, not the frozen experiment)")
    ap.add_argument("--skip-legacy", action="store_true")
    ap.add_argument("--out-dir", default="")
    a = ap.parse_args(argv)
    host = a.host if a.host.startswith("http") else "http://" + a.host
    host = host.rstrip("/")

    import stage3c2_freeze as fz
    drift = fz.verify(quiet=True)
    if drift:
        sys.exit("REFUSING TO RUN: the frozen experiment has changed: " + ", ".join(drift) + "\nRestore the frozen files (or start a new, separately approved experiment).")
    cfg = fz.MODEL_CONFIG
    if a.model != cfg["model"]:
        sys.exit(f"REFUSING TO RUN: the frozen model is {cfg['model']!r}, not {a.model!r}.")

    from src.evaluation.evaluator import AnswerEvaluator
    from src.evaluation.grounding import reference_from_record
    from src.evaluation.providers.http import OllamaProvider
    from src.evaluation.schema import OUTPUT_JSON_SCHEMA, EvaluationRequest
    from src.evaluation.modular import ModularEvaluator, ReferenceMaterial, ScopeStore
    from src.evaluation.modular.feedback import build_feedback, feedback_payload
    from src.evaluation.modular.qwen_verifier import QwenConceptVerifier, build_prompt, build_schema
    from src.evaluation.modular.verification import ConceptVerifier, RawVerification
    from src.retrieval.corpus import load_corpus

    ids = {x.strip() for x in a.ids.split(",") if x.strip()}
    sample = load_sample(ids)
    recs = {r["question_id"]: r for r in load_corpus()["records"]}
    store = ScopeStore.load()
    partial = bool(ids) and len(sample) != len(load_sample())
    meta = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "platform": platform.platform(), "python": sys.version.split()[0], "host": host,
            "frozen_config": cfg, "freeze_manifest_sha256": fz.sha_file(fz.MANIFEST), "answers": len(sample), "partial_run": partial, "dry_run": a.dry_run,
            "labels": "none used by the run; AI expectations are in a separate file and are provisional", "ram_before": ram_snapshot(), "gpu_before": gpu_snapshot()}

    # ----------------------------------------------------------------------------------------------------------- dry run (offline)
    if a.dry_run:
        class Audit(ConceptVerifier):
            name, is_mock, model = "prompt-audit", True, "none"
            def __init__(self): self.rows = []
            def verify(self, request):
                try:
                    import jsonschema
                except ImportError:
                    jsonschema = None
                system, user, _ = build_prompt(request)
                schema = build_schema(request)
                if jsonschema:
                    jsonschema.Draft202012Validator.check_schema(schema)
                self.rows.append({"question_id": request.question_id, "prompt_chars": len(system) + len(user), "approx_prompt_tokens": round((len(system) + len(user)) / 3.5),
                                  "expected_verdicts": len(request.expected_keys()), "claims": len(request.claims), "schema_chars": len(json.dumps(schema))})
                return RawVerification(())
        v = Audit(); ev = ModularEvaluator(store, v)
        per = {}
        for s in sample:
            r = ev.evaluate(s["question_id"], s["question"], s["answer_text"], ReferenceMaterial.from_corpus_record(recs[s["question_id"]]))
            per[s["sample_id"]] = r.status.value
        worst = max((x["approx_prompt_tokens"] for x in v.rows), default=0)
        doc = {"meta": meta, "per_answer_status_in_dry_run": per, "prompts": v.rows, "max_approx_prompt_tokens": worst, "num_ctx": cfg["num_ctx"],
               "fits_context": worst + cfg["max_output_tokens"] < cfg["num_ctx"]}
        out = Path(a.out_dir) if a.out_dir else D / "dry_run.json"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print(f"dry run OK: {len(v.rows)} prompts built for {len(sample)} answers; largest ~{worst} tokens (context {cfg['num_ctx']}); nothing was sent to any model.")
        return 0 if doc["fits_context"] else 2

    # ----------------------------------------------------------------------------------------------------------- preflight
    try:
        tags = http_json(host, "/api/tags")
    except Exception as e:
        sys.exit(f"Cannot reach Ollama at {host}: {e}\nStart Ollama and re-run. Nothing was downloaded.")
    names = [m["name"] for m in tags.get("models", [])]
    if a.model not in names:
        sys.exit(f"Model {a.model!r} is not installed. Installed: {names}\nThis script never downloads models.")
    meta["ollama_version"] = http_json(host, "/api/version").get("version")
    try:
        sh = http_json(host, "/api/show", {"model": a.model})
        meta["model_details"] = {"details": sh.get("details"), "parameters": (sh.get("parameters") or "")[:400]}
    except Exception as e:
        meta["model_details"] = {"error": str(e)[:200]}
    t = time.perf_counter()
    http_json(host, "/api/generate", {"model": a.model, "keep_alive": "30m"}, timeout=cfg["timeout_s"])        # loads the model, generates nothing
    meta["model_load_s"] = round(time.perf_counter() - t, 1)
    meta["ollama_ps_after_load"] = ollama_ps(host)

    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = Path(a.out_dir) if a.out_dir else ROOT / "data" / "evaluation" / "stage3c2_results" / run_id
    if out_dir.exists() and any(out_dir.iterdir()):
        sys.exit(f"{out_dir} already has results; refusing to overwrite.")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "results.json"
    doc = {"meta": meta, "modular": [], "legacy": []}
    save = lambda: out.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    save()
    mk = lambda seed, schema=None: OllamaProvider(a.model, host, cfg["timeout_s"], max_output_tokens=cfg["max_output_tokens"], num_ctx=cfg["num_ctx"],
                                                  temperature=cfg["temperature"], seed=seed, response_schema=schema)
    total = len(sample) * (cfg["modular_repeats"] + (0 if a.skip_legacy else cfg["legacy_repeats"]))
    n = 0; t0 = time.perf_counter()
    print(f"{total} answer evaluations planned ({len(sample)} answers); results -> {out}")

    # ----------------------------------------------------------------------------------------------------------- modular pass
    for rep in range(cfg["modular_repeats"]):
        for s in sample:
            verifier = QwenConceptVerifier(mk(cfg["seed_base"] + rep))
            ev = ModularEvaluator(store, verifier, max_retries=cfg["modular_max_retries"])
            tt = time.perf_counter()
            res = ev.evaluate(s["question_id"], s["question"], s["answer_text"], ReferenceMaterial.from_corpus_record(recs[s["question_id"]]))
            wall = round((time.perf_counter() - tt) * 1000, 1)
            fb = build_feedback(feedback_payload(res))
            doc["modular"].append({"sample_id": s["sample_id"], "repeat": rep, "seed": cfg["seed_base"] + rep, "wall_ms": wall, "result": res.to_dict(),
                                   "verifier_trace": verifier.trace, "feedback": fb.__dict__, "ollama_ps": ollama_ps(host), "gpu": gpu_snapshot(), "ram": ram_snapshot()})
            save(); n += 1
            print(f"[{n}/{total}] modular r{rep} {s['sample_id']}: {res.status.value:<14} score={res.score} conf={res.confidence} {wall/1000:.1f}s")

    # ----------------------------------------------------------------------------------------------------------- legacy pass
    if not a.skip_legacy:
        for rep in range(cfg["legacy_repeats"]):
            for s in sample:
                r = recs[s["question_id"]]
                req = EvaluationRequest(question_id=s["question_id"], question=s["question"], domain=r["domain"], topic=r["topic"], difficulty=r["difficulty"],
                                        candidate_answer=s["answer_text"], reference=reference_from_record(r), support=[])
                inner = mk(cfg["seed_base"] + rep, OUTPUT_JSON_SCHEMA)
                log = []
                class Rec:
                    name, model, is_mock, paid = inner.name, inner.model, inner.is_mock, inner.paid
                    def generate(self_, system, user):
                        tq = time.perf_counter()
                        try:
                            x = inner.generate(system, user); log.append({"ok": True, "ms": round((time.perf_counter() - tq) * 1000, 1), "raw": x.text, "usage": x.usage}); return x
                        except Exception as e:
                            log.append({"ok": False, "ms": round((time.perf_counter() - tq) * 1000, 1), "error": f"{type(e).__name__}: {e}"[:300]}); raise
                tt = time.perf_counter()
                res = AnswerEvaluator(Rec(), max_retries=cfg["legacy_max_retries"]).evaluate(req)
                wall = round((time.perf_counter() - tt) * 1000, 1)
                doc["legacy"].append({"sample_id": s["sample_id"], "repeat": rep, "seed": cfg["seed_base"] + rep, "wall_ms": wall, "result": json.loads(res.model_dump_json()),
                                      "provider_log": log, "ollama_ps": ollama_ps(host), "gpu": gpu_snapshot()})
                save(); n += 1
                print(f"[{n}/{total}] legacy  r{rep} {s['sample_id']}: {res.evaluation_status.value:<22} score={res.provisional_score} {wall/1000:.1f}s")

    doc["meta"]["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc["meta"]["total_wall_s"] = round(time.perf_counter() - t0, 1)
    doc["meta"]["gpu_after"] = gpu_snapshot(); doc["meta"]["ram_after"] = ram_snapshot(); doc["meta"]["ollama_ps_after"] = ollama_ps(host)
    save()
    print("\ndone ->", out, "\nnext: python audit\\evaluation\\stage3c2_analyze.py", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
