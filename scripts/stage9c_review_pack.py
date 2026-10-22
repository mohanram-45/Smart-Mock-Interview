"""Stage 9C: build a BLIND human-review pack for the experimental follow-ups and grounded feedback, and score the returned labels.

  python scripts/stage9c_review_pack.py build  --cases docs/stage9c_eval/cases_seed.json --out OUTDIR [--mode mock|live]
  python scripts/stage9c_review_pack.py score  --key OUTDIR/key.json --labels OUTDIR/reviewer_A.csv [--labels OUTDIR/reviewer_B.csv]

build writes   reviewer_sheet.csv   what reviewers get: shuffled case ids, question, the curated concepts, the answer, the proposed follow-up (or '(none)'), the written feedback, and EMPTY label columns.
                                    It contains no category, no origin, no mode, no model name and no system label.
               key.json             the private side: case id -> category, origin, mode, raw outcome. Keep it away from reviewers.
score  reports reviewer agreement (Cohen's kappa) and per-label rates ONLY when two reviewers labelled the same rows, and says 'no human labels' otherwise.
       Synthetic and human rows are always reported separately. It never prints an 'accuracy'.
Cases with answer = null are slots for human-written answers and are skipped until filled."""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LABELS = ["followup_relevant", "followup_repeats_shown_concept", "followup_invents_fact", "feedback_false_concept_credit", "feedback_false_error_accusation", "feedback_useful", "notes"]
YES_NO = {"y", "n", "unclear"}


def _fill(tpl: str, rec: dict) -> str:
    canon = rec["canonical_answer"]
    sents = re.split(r"(?<=[.!?])\s+", canon.strip())
    return tpl.replace("{first_sentence}", sents[0]).replace("{first_half}", " ".join(sents[: max(1, len(sents) // 2)])).replace("{canonical}", canon)


def build(cases_path: Path, out: Path, mode: str, seed: int = 9) -> dict:
    from src.demo import experimental as MA, followup_llm as FL, grounded as G
    from src.retrieval.service import get_service
    recs = get_service().records()
    pool = [r for r in recs if MA.is_scorable(r["question_id"])]
    doc = json.loads(cases_path.read_text(encoding="utf-8"))
    rows, key = [], {}
    gen = FL.make_generator("live" if mode == "live" else "mock")
    for c in doc["cases"]:
        if not c.get("answer"):
            continue
        rec = pool[int(c["select"].split("#")[1]) % len(pool)]
        answer = _fill(c["answer"], rec)
        ctx = FL.Context(role="", stage="core", question_id=rec["question_id"], question=rec["question"], topic=rec.get("topic") or "", answer=answer, concepts=FL.concepts_for(rec),
                         reference=rec.get("canonical_answer") or "", previous=[])
        out_fu = gen.propose(ctx)
        view = MA.evaluate("live" if mode == "live" else "mock", rec, answer)
        g = G.build(view, answer=answer)
        fb = "(no feedback returned)" if not g else " | ".join([g["headline"]] + [f"COVERED: {x['concept']}" for x in g["supported"]] + [f"NOT FOUND: {x['concept']}" for x in g["maybe_missing"]]
                                                                + [f"POSSIBLE ERROR: {x['concept']} (reference: {x['reference_says']})" for x in g["errors"]] + [f"UNDECIDED: {x['concept']}" for x in g["uncertain"]])
        rows.append({"question": rec["question"], "curated_concepts": "; ".join(x["label"] for x in ctx.concepts), "answer": answer,
                     "proposed_followup": out_fu.proposal.question if out_fu.proposal and out_fu.proposal.question else "(none)", "written_feedback": fb, "_cid": c["case_id"]})
        key[c["case_id"]] = {"category": c["category"], "origin": c["origin"], "question_id": rec["question_id"], "mode": mode, "followup_outcome": out_fu.kind, "followup_reasons": out_fu.reasons,
                             "feedback_status": g["status"] if g else None}
    random.Random(seed).shuffle(rows)
    out.mkdir(parents=True, exist_ok=True)
    blind = {}
    with open(out / "reviewer_sheet.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["review_id", "question", "curated_concepts", "answer", "proposed_followup", "written_feedback"] + LABELS)
        w.writeheader()
        for i, r in enumerate(rows, 1):
            rid = f"R{i:03d}"
            blind[rid] = r.pop("_cid")
            w.writerow({"review_id": rid, **r, **{k: "" for k in LABELS}})
    (out / "key.json").write_text(json.dumps({"review_to_case": blind, "cases": key}, indent=1), encoding="utf-8")
    return {"rows": len(rows), "skipped_slots": sum(1 for c in doc["cases"] if not c.get("answer"))}


def _kappa(a, b):
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def score(key_path: Path, label_paths: list) -> dict:
    key = json.loads(key_path.read_text(encoding="utf-8"))
    sheets = []
    for p in label_paths:
        with open(p, newline="", encoding="utf-8") as f:
            sheets.append({r["review_id"]: r for r in csv.DictReader(f)})
    filled = [s for s in sheets if any((r.get(LABELS[0]) or "").strip() for r in s.values())]
    if not filled:
        return {"status": "no human labels", "claim": "none: no accuracy or quality figure can be reported"}
    res = {"status": "labelled", "reviewers": len(filled), "agreement": {}, "rates": {}}
    if len(filled) >= 2:
        for lab in LABELS[:-1]:
            ids = [i for i in filled[0] if (filled[0][i].get(lab) or "").strip() in YES_NO and (filled[1].get(i, {}).get(lab) or "").strip() in YES_NO]
            res["agreement"][lab] = {"n": len(ids), "kappa": _kappa([filled[0][i][lab].strip() for i in ids], [filled[1][i][lab].strip() for i in ids])}
    for origin in ("human", "synthetic"):
        res["rates"][origin] = {}
        for lab in LABELS[:-1]:
            vals = [(s[i].get(lab) or "").strip() for s in filled for i in s if key["cases"][key["review_to_case"][i]]["origin"] == origin]
            vals = [v for v in vals if v in YES_NO]
            res["rates"][origin][lab] = {"n": len(vals), "yes": sum(v == "y" for v in vals), "unclear": sum(v == "unclear" for v in vals)} if vals else {"n": 0}
    res["claim"] = "descriptive counts from the labelled rows only; with fewer than two reviewers or a small n these are NOT accuracy estimates"
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--cases", required=True); b.add_argument("--out", required=True); b.add_argument("--mode", default="mock", choices=["mock", "live"])
    s = sub.add_parser("score"); s.add_argument("--key", required=True); s.add_argument("--labels", action="append", required=True)
    a = ap.parse_args()
    print(json.dumps(build(Path(a.cases), Path(a.out), a.mode) if a.cmd == "build" else score(Path(a.key), [Path(x) for x in a.labels]), indent=1))
