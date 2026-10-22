"""Stage 9C: verify the interview against the REAL stack on your own machine (real Sentence-BERT, optionally real Ollama/Qwen). Nothing here is mocked except where stated.

  .bot\\Scripts\\python.exe scripts\\stage9c_verify_real_stack.py                 SBERT + interview-flow checks (a few minutes the first time: the model loads)
  .bot\\Scripts\\python.exe scripts\\stage9c_verify_real_stack.py --ollama         also a SMALL smoke test of the local-model follow-ups (N=--samples, default 3)
Writes tmp\\stage9c_real_stack_report.json and prints PASS / FAIL / SKIP per check. Exit code 1 if any check FAILs. Uses a temporary data folder: your saved interviews are untouched.
No paid API is used and nothing is downloaded by this script (if the Sentence-BERT files are not cached it SKIPs and says so)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
R = []


def rec(name, status, detail=""):
    R.append({"check": name, "status": status, "detail": detail})
    print(f"[{status}] {name}" + (f"  - {detail}" if detail else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama", action="store_true")
    ap.add_argument("--samples", type=int, default=3)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="smart9c_")
    os.environ["SMART_DEMO_DATA_DIR"] = tmp
    os.environ["HF_HUB_OFFLINE"] = "1"                          # never download: use the cache or skip
    from src.demo import interview as I
    from src.demo.engine import DemoEngine, SCORER_KEY
    from src.demo.store import DemoStore
    eng = DemoEngine(DemoStore(Path(tmp)))
    try:
        eng.records()
        rec("question bank loads", "PASS", f"{len(eng.records())} questions")
    except Exception as e:
        rec("question bank loads", "FAIL", str(e)); return finish()
    info = eng.legacy_models()
    ready = bool(info and info[0].get("ready"))
    rec("Sentence-BERT is the only scorer offered", "PASS" if [m["key"] for m in info] == [SCORER_KEY] else "FAIL", json.dumps([m["key"] for m in info]))
    if not ready:
        rec("Sentence-BERT model cached and loadable", "SKIP", (info[0].get("not_ready_reason") if info else "") or "not ready"); return finish()
    s = eng.create({"role": "Data Scientist"})
    sid = s["id"]
    rec("new session uses bert, no TF-IDF / Siamese", "PASS" if s["config"]["legacy_model"] == "bert" and not any(k in json.dumps(s["legacy"]).lower() for k in ("tfidf", "siamese", "lstm")) else "FAIL", s["legacy"].get("label", ""))
    good_ref, other = None, None
    graded, seen = [], []
    for _ in range(40):
        cur = eng.get(sid)
        if cur["status"] == "finished":
            break
        n = cur["current"] + 1
        q = cur["questions"][cur["current"]]
        rec_ = eng.record(q["question_id"]) if q.get("question_id") else None
        text = "Hi, I am a data scientist." if I.stage_of(q) == I.INTRO else (rec_["canonical_answer"] if rec_ else "Because it matters.")
        t0 = time.perf_counter()
        r = eng.submit(sid, n, text)
        again = eng.submit(sid, n, text)
        seen.append((I.stage_of(q), r["legacy"]["status"], r["legacy"].get("score"), round(time.perf_counter() - t0, 2)))
        if again.get("duplicate") is not True:
            rec(f"idempotent resubmit n={n}", "FAIL", "second identical submit was not treated as a duplicate")
    cur = eng.get(sid)
    rec("interview finishes by itself", "PASS" if cur["status"] == "finished" else "FAIL")
    intro_ok = all(st == "not_scored" for stage, st, _, _ in seen if stage in (I.INTRO, I.FOLLOW_UP))
    rec("introduction and follow-ups are not graded", "PASS" if intro_ok else "FAIL")
    sc = [x for x in seen if x[0] in (I.CORE, I.PRACTICAL)]
    rec("technical answers get a Sentence-BERT similarity", "PASS" if sc and all(x[1] == "scored" and x[2] is not None and 0 <= x[2] <= 100 for x in sc) else "FAIL", json.dumps([x[2] for x in sc]))
    rec("answering with the reference scores high (identical text)", "PASS" if sc and all(x[2] is not None for x in sc) and min(x[2] for x in sc) >= 85 else "FAIL", f"scores={[x[2] for x in sc]}")
    eng2 = DemoEngine(DemoStore(Path(tmp)))
    again = eng2.get(sid)
    rec("session resumes from disk in a fresh engine", "PASS" if again["status"] == "finished" and len(again["answers"]) == len(cur["answers"]) else "FAIL")
    rec("provenance preserved on every technical item", "PASS" if all((q.get("provenance") or {}).get("record_id") for q in again["questions"] if I.is_question(q)) else "FAIL")
    # similarity ordering with the real scorer: reference > paraphrase-ish > unrelated
    r0 = eng.records()[0]
    scorer = eng._scorers.get(SCORER_KEY)
    if scorer is not None:
        hi = scorer.score(r0["canonical_answer"], r0["canonical_answer"]); lo = scorer.score(r0["canonical_answer"], "I like pasta and long walks on the beach.")
        rec("similarity ordering (identical > unrelated)", "PASS" if hi > lo + 0.3 else "FAIL", f"identical={hi:.3f} unrelated={lo:.3f}")
    if a.ollama:
        smoke(a.samples)
    finish()


def smoke(n):
    """Smoke test of the 9D pipeline: warm the model in the background (as the app does), then ask for `n` follow-ups. Prints Ollama's real timings per call."""
    os.environ["SMART_DEMO_LIVE_MODULAR"] = "1"
    from src.demo import experimental as MA, followup_llm as FL
    from src.retrieval.service import get_service
    try:
        g = FL.make_generator("live")
    except Exception as e:
        rec("local model follow-ups", "SKIP", str(e)); return
    print(f"    model={g.model} deadline={g.deadline()}s (SMART_DEMO_FOLLOWUP_MODEL / SMART_DEMO_FOLLOWUP_DEADLINES to change)")
    t0 = time.time()
    g.start_warm()
    while g.warm_state in ("unknown", "warming") and time.time() - t0 < FL.WARM_DEADLINE_S + 5:
        time.sleep(0.5)
    rec("model warm-up (background load)", "PASS" if g.warm_state == "ready" else "FAIL", f"state={g.warm_state} {g.warm_info} after {time.time() - t0:.1f}s")
    if g.warm_state != "ready":
        return
    pool = [r for r in get_service().records() if MA.is_scorable(r["question_id"])][:n]
    lat, kinds, reasons = [], [], []
    for r in pool:
        ans = " ".join(r["canonical_answer"].split()[:30])
        ctx = FL.Context(role="Data Scientist", stage="core", question_id=r["question_id"], question=r["question"], topic=r.get("topic") or "", answer=ans, concepts=FL.concepts_for(r),
                         reference=r["canonical_answer"], previous=[])
        o = g.propose(ctx)
        lat.append(round(o.latency_ms / 1000, 1)); kinds.append(o.kind); reasons.append(o.reasons)
        print("   ", o.kind, f"{o.latency_ms/1000:.1f}s", {k: o.metrics.get(k) for k in ("prompt_tokens", "generated_tokens", "generate_tok_per_s", "load_ms")}, (o.proposal.question if o.proposal else o.reasons))
    ok = [k for k in kinds if k in ("llm", "skip")]
    rec("local model follow-up smoke test", "PASS" if ok else "FAIL", f"{len(ok)}/{len(kinds)} produced a rule-valid result; latencies (s)={lat}; fallbacks={[x for x in reasons if x]}. PASS means the plumbing works, NOT that the questions are good.")


def finish():
    out = ROOT / "tmp" / "stage9c_real_stack_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(R, indent=1), encoding="utf-8")
    bad = [r for r in R if r["status"] == "FAIL"]
    print(f"\n{len(R)} checks: {sum(r['status']=='PASS' for r in R)} PASS, {len(bad)} FAIL, {sum(r['status']=='SKIP' for r in R)} SKIP  ->  {out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
