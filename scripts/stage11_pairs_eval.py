"""Stage 11: the SAME hand-written good/bad question pairs judged by the Stage 10N validator and by the objective engine's validator (offline, no model).

  .bot\\Scripts\\python.exe scripts\\stage11_pairs_eval.py --out tmp\\stage11_pairs.json

False rejection = a reasonable question refused; false acceptance = a repeat / invented premise / unanswerable / given-away question let through. The pairs are AUTHOR JUDGEMENTS (not human ratings);
the `holdout*` sets were written by the same author as the rules, so they are sanity checks, not independent evidence. Offline code behaviour only: this says nothing about what a model writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import followup_llm as FL, intel, opportunity_eval as OE, question_pairs_eval as Q  # noqa: E402


def evaluate() -> dict:
    eng = OE.offline_engine()
    cases = {c["id"]: c for c in OE.load()["cases"]}
    FL.set_vocabulary_source(lambda: [])
    rows = []
    try:
        for it in Q.load()["items"]:
            ctx = Q._context(it, eng, cases)
            obj = intel.plan_objective(ctx)
            for kind, qs in (("good", [(g, None) for g in it["good"]]), ("bad", [(b["q"], b) for b in it["bad"]])):
                for q, meta in qs:
                    base_ok, _ = Q.judge(q, ctx)
                    if obj is None:
                        new_ok, why = False, ["no_open_concept"]
                    else:
                        v = intel.evaluate_question(q, ctx, obj)
                        new_ok, why = v.prop is not None, v.reasons
                    rows.append({"id": it["id"], "src": it["src"], "kind": kind, "question": q, "known_gap": bool(meta and meta.get("known_gap")), "stage10n_accepts": base_ok, "objective_accepts": new_ok, "objective_reasons": why})
    finally:
        FL.set_vocabulary_source(None)

    def part(src):
        r = [x for x in rows if src is None or x["src"] == src]
        g, b = [x for x in r if x["kind"] == "good"], [x for x in r if x["kind"] == "bad"]
        return {"n_good": len(g), "false_rejections_stage10n": sum(1 for x in g if not x["stage10n_accepts"]), "false_rejections_objective": sum(1 for x in g if not x["objective_accepts"]),
                "n_bad": len(b), "false_acceptances_stage10n": sum(1 for x in b if x["stage10n_accepts"]), "false_acceptances_objective": sum(1 for x in b if x["objective_accepts"])}
    return {"evidence": "offline_author_judged_pairs", "by_set": {s or "all": part(s) for s in ("fixture", "holdout", "holdout2", None)}, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = evaluate()
    print(json.dumps(res["by_set"], indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
