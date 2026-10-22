"""Stage 11: replay the model questions RECORDED in a real Stage 10 results.json through the objective engine's code (no model is called).

  .bot\\Scripts\\python.exe scripts\\stage11_replay_recorded.py --results tmp\\stage10_opps_20261021_205846\\results.json --out tmp\\stage11_replay

What it tells you: for every question the real llama3.2:3b wrote on the frozen benchmark (accepted or rejected by Stage 10N), what the objective engine's CODE would have done with it: ask/skip is no
longer the model's, the memory id and lead-in are attached (or refused) by code, and the weak-question rules are applied.
What it does NOT tell you: what a model would write under the new prompt (11.obj1). A replay of recorded text is an offline test of the decision, attribution and validation code, never a measurement of a model.
Every row is labelled `evidence: replay_of_recorded_real_replies`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import followup_llm as FL, intel, opportunity_eval as OE  # noqa: E402

WEAK_CASES = ("T02", "T04", "T10", "M07", "N02")          # accepted by the Stage 10N rules but flagged for scrutiny in the Stage 11 brief (listed for the report, never used by the code)


def replay(results_path: Path) -> dict:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    run = data["results"][0]
    eng = OE.offline_engine()
    cases = {c["id"]: c for c in OE.load()["cases"]}
    FL.set_vocabulary_source(lambda: [])
    rows = []
    try:
        for r in run["rows"]:
            if r.get("mode") != "technical":
                continue
            ctx, offered, _s, _core = OE.build_case(eng, cases[r["id"]])
            obj = intel.plan_objective(ctx)
            offered_ids = [m["id"] for m in offered]
            rec = {"id": r["id"], "class": r["class"], "baseline_outcome": r["outcome"], "baseline_success": r["success"], "baseline_basis": r.get("success_basis"),
                   "baseline_question": r.get("question") or "", "payload_issues_recorded": OE.payload_issues_from_debug(r.get("debug") or []), "memory_offered_recorded": r.get("memory_offered_ids"), "memory_offered_here": offered_ids,
                   "objective": obj.summary() if obj else None, "attempts": [], "evidence": "replay_of_recorded_real_replies"}
            for d in r.get("debug") or []:
                q = d.get("question") or ""
                if not q.strip() or obj is None:
                    continue
                v = intel.evaluate_question(q, ctx, obj)
                rec["attempts"].append({"attempt": d["attempt"], "recorded_decision": d.get("decision"), "recorded_memory_id": d.get("memory_id"), "recorded_reasons_10n": d.get("reasons"), "question": q,
                                        "accepted": v.prop is not None, "memory_attributed": bool(v.prop is not None and v.prop.memory_id), "reasons": v.reasons, "memory_words_used": v.attr.used})
            rec["first_attempt_accepted"] = bool(rec["attempts"] and rec["attempts"][0]["accepted"])
            rec["any_attempt_accepted"] = any(a["accepted"] for a in rec["attempts"])
            rows.append(rec)
    finally:
        FL.set_vocabulary_source(None)
    return {"source": str(results_path), "prompt_version_recorded": run.get("prompt_version"), "model": run.get("model"), "rows": rows}


def summarise(res: dict) -> dict:
    rows = res["rows"]
    mem = [r for r in rows if r["class"] == "memory_use"]
    exp = [r for r in rows if r["class"] == "expected"]
    inc = [r for r in rows if r["class"] == "memory_inappropriate"]
    called = [r for r in rows if r["attempts"]]
    return {
        "technical_rows": len(rows), "rows_with_a_recorded_question": len(called),
        "memory_use": {"n": len(mem), "baseline_grounded_use": sum(1 for r in mem if r["baseline_success"]),
                       "first_question_attributed_by_code": sum(1 for r in mem if r["attempts"] and r["attempts"][0]["memory_attributed"]),
                       "any_recorded_question_attributed_by_code": sum(1 for r in mem if any(a["memory_attributed"] for a in r["attempts"])),
                       "any_recorded_question_valid_without_memory": sum(1 for r in mem if any(a["accepted"] and not a["memory_attributed"] for a in r["attempts"]))},
        "expected": {"n": len(exp), "baseline_success": sum(1 for r in exp if r["baseline_success"]), "first_question_accepted": sum(1 for r in exp if r["first_attempt_accepted"]),
                     "any_recorded_question_accepted": sum(1 for r in exp if r["any_attempt_accepted"])},
        "memory_inappropriate": {"n": len(inc), "baseline_success": sum(1 for r in inc if r["baseline_success"]), "any_recorded_question_attributed_by_code": sum(1 for r in inc if any(a["memory_attributed"] for a in r["attempts"]))},
        "weak_cases_flagged_in_brief": {r["id"]: {"baseline_accepted_question": r["baseline_question"], "objective_engine_accepts_it": bool(r["attempts"] and r["attempts"][-1]["accepted"]),
                                                  "reasons": r["attempts"][-1]["reasons"] if r["attempts"] else None} for r in rows if r["id"] in WEAK_CASES and r["baseline_success"]},
        "rows_with_a_payload_issue_in_any_recorded_attempt": sum(1 for r in rows if r["payload_issues_recorded"]),
        "memory_offered_mismatch_with_recorded_run": [r["id"] for r in rows if (r["memory_offered_recorded"] or []) != r["memory_offered_here"]],
    }


def to_markdown(res: dict, s: dict) -> str:
    L = ["# Stage 11 replay of recorded real replies", "", f"Source: `{res['source']}` (model {res['model']}, prompt {res['prompt_version_recorded']}). **This is a replay of recorded text through the objective engine's code. No model was called; it does not show what a model would write under the new prompt.**", "",
         "| case | class | 10N result | recorded question (1st attempt) | objective engine verdict | memory by code | reasons |", "|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        if not r["attempts"]:
            continue
        a = r["attempts"][0]
        L.append(f"| {r['id']} | {r['class']} | {'ok' if r['baseline_success'] else 'miss'} ({r['baseline_outcome']}) | {a['question'][:110]} | {'accept' if a['accepted'] else 'reject'} | {'yes' if a['memory_attributed'] else 'no'} | {', '.join(a['reasons'])[:90]} |")
    L += ["", "```json", json.dumps(s, indent=1), "```"]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out) if a.out else ROOT / "tmp" / f"stage11_replay_{time.strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(a.results):
        res = replay(Path(p))
        s = summarise(res)
        (out / f"replay_{i}.json").write_text(json.dumps({"summary": s, **res}, indent=1), encoding="utf-8")
        (out / f"replay_{i}.md").write_text(to_markdown(res, s), encoding="utf-8")
        print(to_markdown(res, s))
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
