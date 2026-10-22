"""Stage 10N Windows regression repair: diagnostics for the five failures of the first Windows run. Changes nothing, asserts nothing; it prints what THIS machine does so the cause can be read off.
Run from the project root:  .\\.bot\\Scripts\\python.exe scripts\\stage10n_windows_repair_diag.py [--out tmp\\stage10n_diag.json] [--skip-real]
--skip-real skips the steps that load Sentence-BERT/FAISS (they can take a minute the first time)."""
import argparse
import importlib.util
import json
import os
import platform
import random
import re
import socket
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INTRO = ("I developed an oral cancer classification model using PyTorch. I achieved 91% accuracy on the test set. The hardest challenge was class imbalance in the training data.")
OUT: dict = {}


def section(name, fn):
    t0 = time.perf_counter()
    try:
        OUT[name] = fn()
    except Exception as e:                                                          # a diagnostic reports its own failure and carries on
        OUT[name] = {"diag_error": f"{type(e).__name__}: {str(e)[:300]}"}
    OUT[name + "_s"] = round(time.perf_counter() - t0, 2) if isinstance(OUT[name], dict) else None
    print(f"[{name}] {json.dumps(OUT[name], default=str)[:1600]}")


def environment():
    pk = {m: importlib.util.find_spec(m) is not None for m in ("torch", "sentence_transformers", "faiss", "ollama")}
    env = {k: v for k, v in os.environ.items() if k.startswith(("SMART_", "OLLAMA"))}
    return {"python": sys.version.split()[0], "platform": platform.platform(), "installed": pk, "env": env}


def engine(search_fn, directory):
    from src.demo import sim
    from src.demo.engine import DemoEngine
    from src.demo.store import DemoStore
    return DemoEngine(DemoStore(Path(directory) / "sessions"), scorer_factory=lambda k, c: sim.Overlap(), feedback_fn=lambda s, q, a, m: "", rng=random.Random(11), search_fn=search_fn)


def rankings():
    """Which retrieval ranks candidate questions, and do the two rankings agree on the questions an interview will pick (cause of A and C)?"""
    from src.demo import engine as E, sim
    out = {}
    for name, fn in (("default_service", E._service_search), ("bm25_only", sim.bm25_search)):
        t0 = time.perf_counter()
        r = fn("how do you evaluate a classification model", "Machine Learning")
        out[name] = {"mode": r.get("mode"), "top5_question_ids": [h["question_id"] for h in r["results"][:5]], "seconds": round(time.perf_counter() - t0, 2)}
    out["same_top5"] = out["default_service"]["top5_question_ids"] == out["bm25_only"]["top5_question_ids"]
    return out


def memory_pick(search_fn, label):
    """Failure A: the first memory reference of a five-question interview with the oral-cancer introduction, for this ranking."""
    from src.demo import interview as I, sim
    d = tempfile.mkdtemp()
    eng = engine(search_fn, d)

    def ans(n, q, s):
        if I.stage_of(q) == I.INTRO:
            return INTRO
        rec = eng.record(q["question_id"]) if q.get("question_id") else None
        return rec["canonical_answer"] if rec else "I would explain it step by step with an example."
    s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5}, ans)
    refs = [r for r in t if r["memory_ref"]]
    return {"ranking": label, "core_questions": [r["question"][:60] for r in t if r["stage"] == "core"],
            "first_memory_ref": refs and {"turn": refs[0]["n"], "lead": refs[0]["lead"][:120], "question": refs[0]["question"][:160], "kind": refs[0]["memory_ref"].get("kind")}}


def time_budget(search_fn, label):
    from src.demo import interview as I
    eng = engine(search_fn, tempfile.mkdtemp())
    res = {}
    for kind, answer in (("short", "It is a thing used in machine learning."),
                         ("strong", "Cross validation splits the data into folds and averages the score across them for a steadier estimate of performance.")):
        s = eng.create({"role": "Data Scientist", "practical": True, "size": 6, "time_budget_min": 1})
        eng.submit(s["id"], 1, "I work on data problems.")
        eng.get(s["id"])["created_at"] = "2000-01-01T00:00:00+00:00"
        eng.submit(s["id"], 2, answer)
        d = eng.get(s["id"])
        res[kind] = {"status": d["status"], "ended_reason": d["plan"].get("ended_reason"), "follow_ups": sum(1 for q in d["questions"] if q.get("stage") == I.FOLLOW_UP), "expected": "finished / time_budget / 0"}
    return {"ranking": label, **res}


def citation(search_fn, label):
    """Failure C: what a scripted model that always writes about the oral cancer project gets, against what is OFFERED, for a cross-validation question."""
    from src.demo import followup_llm as FL, policy as POL
    from src.evaluation.providers.mock import MockProvider

    def reply(system, user):
        mem = re.search(r"^EARLIER \(turn \d+, .*?id (m\d+)\)", user, re.M)
        tgt = re.search(r"^TARGET \(not covered yet\): \S+ (.+)$", user, re.M)
        return {"decision": "ask", "question": f"How does {tgt.group(1) if tgt else 'validation'} apply to your oral cancer classification model?", "purpose": "apply", "concept_id": "none", "memory_id": mem.group(1) if mem else "none"}
    eng = engine(search_fn, tempfile.mkdtemp())
    eng._followup_generator = FL.LLMFollowUpGenerator(MockProvider(reply), deadline=5)
    s = eng.create({"role": "Data Scientist", "practical": False, "size": 5, "followup_mode": "mock"})
    eng.submit(s["id"], 1, INTRO)
    cur = eng.get(s["id"])
    q = cur["questions"][1]
    ans = "Cross validation splits the data into folds. I would measure accuracy on held out folds."
    rec = eng.record(q["question_id"])
    offered = POL.retrieve_for_followup(cur, q, ans, 2, rec, k=2)
    r = eng._llm_followup(cur, 1, rec, ans)
    return {"ranking": label, "core_question": q["question"], "offered": [(h["item"]["id"], h["item"]["kind"], h["item"]["text"][:50]) for h in offered],
            "memory_stage": r["log"].get("memory_stage"), "cited": bool(r["item"] and r["item"].get("memory_id")),
            "reading": "memory_stage not_connected with an offered statement that is not the project = the meaningful-connection rule working, not a persistence fault"}


def import_trace():
    """Failure D: who asks for torch / sentence_transformers / faiss while the DEFAULT engine opens a session (run in a clean child process so nothing is cached)."""
    import subprocess
    code = r'''
import importlib.abc, importlib.util, json, os, sys, tempfile, traceback
tmp = tempfile.mkdtemp(); os.environ["SMART_DEMO_DATA_DIR"] = tmp
WATCH = ("torch", "sentence_transformers", "faiss"); seen = []
class R(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in WATCH and name not in [s[0] for s in seen]:
            seen.append((name, [f"{f.filename.replace(chr(92), '/').split('/')[-1]}:{f.name}" for f in traceback.extract_stack()[:-1] if "src" in f.filename][-5:]))
        return None
sys.meta_path.insert(0, R())
spec = importlib.util.spec_from_file_location("smart_app", "main/app.py"); m = importlib.util.module_from_spec(spec); sys.modules["smart_app"] = m; spec.loader.exec_module(m)
from src.demo.engine import DemoEngine
from src.demo.routes import set_engine
from src.demo.store import DemoStore
class S:
    def score(self, r, a): return 0.5
set_engine(DemoEngine(DemoStore(tmp), scorer_factory=lambda k, c: S(), feedback_fn=lambda *a: "ok"))
c = m.app.test_client(); before = list(seen)
for u in ("/demo/about", "/demo/guide", "/demo/"): c.get(u)
before_session = len(seen)
c.post("/demo/api/sessions", json={"role": "Python Developer", "size": 3, "practical": False, "max_followups": 0})
print(json.dumps({"attempts_before_first_session": before_session, "attempts_after_first_session": [(n, st) for n, st in seen], "loaded_modules": [x for x in sys.modules if x.split(".")[0] in WATCH][:6]}))
'''
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    line = [x for x in r.stdout.splitlines() if x.startswith("{")]
    return json.loads(line[-1]) if line else {"diag_error": r.stderr[-400:]}


def unreachable_endpoint():
    """Failure E: how THIS OS treats a closed local port, and which typed error the client raises for it."""
    from src.demo import ollama_stream as OS
    t0 = time.perf_counter()
    try:
        socket.create_connection(("127.0.0.1", 9), 2).close()
        raw = "connected (something listens on port 9)"
    except Exception as e:
        raw = f"{type(e).__name__}: {e}"
    raw_s = round(time.perf_counter() - t0, 2)
    t0 = time.perf_counter()
    try:
        OS.StreamingOllama("llama3.2:3b", "http://127.0.0.1:9").generate_bounded("s", "u", 2)
        typed = "no error"
    except Exception as e:
        typed = f"{type(e).__module__}.{type(e).__name__}: {str(e)[:100]}"
    return {"raw_connect": raw, "raw_connect_seconds": raw_s, "client_raises": typed, "client_seconds": round(time.perf_counter() - t0, 2),
            "expected": "src.evaluation.errors.ProviderUnavailable (a connect timeout and a refusal are both 'unreachable')"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tmp/stage10n_windows_repair_diag.json")
    ap.add_argument("--skip-real", action="store_true", help="do not load Sentence-BERT / FAISS")
    a = ap.parse_args()
    from src.demo import engine as E, sim
    section("environment", environment)
    if not a.skip_real:
        section("rankings", rankings)
    runs = [("bm25_only", sim.bm25_search)] + ([] if a.skip_real else [("default_service", E._service_search)])
    for label, fn in runs:
        section(f"A_memory_pick[{label}]", lambda fn=fn, label=label: memory_pick(fn, label))
        section(f"B_time_budget[{label}]", lambda fn=fn, label=label: time_budget(fn, label))
        section(f"C_citation[{label}]", lambda fn=fn, label=label: citation(fn, label))
    section("D_import_trace", import_trace)
    section("E_unreachable_endpoint", unreachable_endpoint)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
