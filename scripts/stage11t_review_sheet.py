"""Stage 11T: build the BLIND human-review sheet for the objective engine.

  .bot\\Scripts\\python.exe scripts\\stage11t_review_sheet.py --results tmp\\stage10_opps_20261022_162322\\results.json --out reports\\stage11_eval\\stage11t_review

Writes two files:
  sheet.csv  what a rater opens: the question asked, the candidate's answer, what they said earlier, what is still open in the rubric, and ONE follow-up exactly as the candidate would see it.
             Rating columns are empty. Nothing in this repository fills them.
  key.json   what the rater must NOT open until every row is rated: where each follow-up came from, and what the rules say about it now.

Two sources are mixed and shuffled, with random item ids, so neither the source nor the case can be read off the sheet:
  - every follow-up a real model run SHOWED (taken verbatim from results.json: the code-built lead-in is already part of that text, so it is never added a second time);
  - follow-ups written by the author of the repair, rendered as the engine would show them (lead-in only when the code keeps it).
The rules' verdict is in the key only; it is an automatic check, never a rating.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import followup_llm as FL, intel, opportunity_eval as OE  # noqa: E402

# Written by the author of the repair as plausible good follow-ups; the rater judges them blind alongside the model's. Case ids only select the interview context they belong to.
AUTHOR = [
    ("M01", "How would the ROC curve and AUC show how well your oral cancer classifier separates the two classes?"),
    ("M02", "How would the labelled training data shape what your spam classifier can learn?"),
    ("M03", "If one of your Flask API tests had to fake a database call, how would return_value and side_effect let you control what it returns or raises?"),
    ("M04", "If two of your money transfers ran at the same time, what could go wrong without isolation between the transactions?"),
    ("M05", "How would maximum likelihood estimation pick the weights behind that sigmoid output?"),
    ("M06", "Which features would the early and later layers of your tumour detection network learn, and why would that hierarchy help?"),
    ("M07", "If your search feature scanned every record with a linear search, how would its cost grow with the catalogue size?"),
    ("T10", "Why would a ROC curve tell you more than accuracy when one class is much rarer than the other?"),
    ("T11", "How could the early and later layers of a deep network learn increasingly abstract features of an image?"),
    ("T12", "In what situation would a test produce a false negative, and what would that cost?"),
    ("T03", "How many comparisons would a linear search need on the same sorted list if the target is missing?"),
    ("T04", "How would stacking a second convolutional layer change what the filters can detect?"),
]
RATING_COLUMNS = ["technically_correct_yes_no", "natural_for_an_interview_yes_no", "probes_something_still_open_yes_no", "claims_anything_the_candidate_did_not_say_yes_no",
                  "repeats_what_the_candidate_already_said_yes_no", "would_you_ask_it_yes_no", "reviewer_notes"]


def _context_columns(ctx: "FL.Context") -> dict:
    earlier = "; ".join(m.get("quote") or "" for m in ctx.memory) or "(nothing was offered)"
    still_open = ", ".join(c["label"] for c in FL.open_concepts(ctx)) or "(nothing)"
    return {"question_asked": ctx.question, "candidate_answer": ctx.answer, "what_the_candidate_said_earlier": earlier, "still_open_in_the_rubric": still_open}


def _rules_now(question: str, ctx: "FL.Context") -> dict:
    obj = intel.plan_objective(ctx)
    if obj is None:
        return {"rules_accept_it_now": False, "reasons_if_refused": ["no_open_concept"], "memory_attached_by_code": None, "lead_shown": False}
    v = intel.evaluate_question(question, ctx, obj)
    return {"rules_accept_it_now": v.prop is not None, "reasons_if_refused": v.reasons, "memory_attached_by_code": v.prop.memory_id if v.prop else None,
            "lead_shown": bool(v.prop and v.prop.lead), "shown_text": ((v.prop.lead + " ") if v.prop and v.prop.lead else "") + (v.prop.question if v.prop else question)}


def build(results: Path, out: Path, seed: int = 11) -> dict:
    doc = json.loads(results.read_text(encoding="utf-8"))
    run = doc["results"][0]
    eng = OE.offline_engine()
    cases = {c["id"]: c for c in OE.load()["cases"]}
    FL.set_vocabulary_source(lambda: [])
    rng = random.Random(seed)
    rows, key = [], []
    try:
        for r in run["rows"]:
            if r.get("mode") != "technical" or r.get("outcome") != "llm" or not (r.get("question") or "").strip():
                continue
            ctx = OE.build_case(eng, copy.deepcopy(cases[r["id"]]))[0]
            # What the model wrote is the shown text minus the code-built lead. results.json cuts each attempt's text at 200 characters, so the debug copy is used only when it is complete.
            shown = r["question"].strip()
            for m in ctx.memory:
                if m.get("lead") and shown.startswith(m["lead"]):
                    shown = shown[len(m["lead"]):].strip()
            accepted = [d for d in (r.get("debug") or []) if not d.get("reasons") and (d.get("question") or "").strip()]
            written = FL.sanitise_ids(accepted[-1]["question"], ctx) if accepted and accepted[-1]["question"].strip().endswith("?") else shown
            verdict = _rules_now(written, ctx)
            verdict.pop("shown_text", None)
            rows.append({**_context_columns(ctx), "follow_up_to_judge": r["question"].strip()})
            key.append({"case": r["id"], "source": f"shown_in_the_real_run_{run.get('prompt_version', '?')}", "model_wrote": written, **verdict})
        for cid, q in AUTHOR:
            ctx = OE.build_case(eng, copy.deepcopy(cases[cid]))[0]
            verdict = _rules_now(q, ctx)
            shown = verdict.pop("shown_text")
            rows.append({**_context_columns(ctx), "follow_up_to_judge": shown})
            key.append({"case": cid, "source": "written_by_the_repair_author", "model_wrote": None, **verdict})
    finally:
        FL.set_vocabulary_source(None)
    order = list(range(len(rows)))
    rng.shuffle(order)
    out.mkdir(parents=True, exist_ok=True)
    items = []
    with (out / "sheet.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["item", "question_asked", "candidate_answer", "what_the_candidate_said_earlier", "still_open_in_the_rubric", "follow_up_to_judge"] + RATING_COLUMNS)
        w.writeheader()
        for i in order:
            item = "R" + "%06x" % rng.getrandbits(24)
            w.writerow({"item": item, **rows[i], **{c: "" for c in RATING_COLUMNS}})
            items.append({"item": item, **key[i]})
    meta = {"status": "UNRATED", "meaning": "No person has rated this sheet. No number in any Stage 11 report is derived from it.",
            "how_to_use": "Open sheet.csv only. Judge each follow-up against the question asked, the candidate's answer and what they said earlier. Keep this key closed until every row is rated.",
            "mix": f"{sum(1 for k in key if k['source'].startswith('shown'))} follow-ups a real model run showed (verbatim) and {len(AUTHOR)} written by the repair author, shuffled and unlabelled.",
            "rules_verdict": "automatic rule check of the written question under the current code; NOT a rating", "source_results": str(results), "seed": seed, "items": items}
    (out / "key.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    meta = build(Path(a.results), Path(a.out), a.seed)
    print(f"{len(meta['items'])} items written to {a.out} (UNRATED)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
