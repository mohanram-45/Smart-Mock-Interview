"""Stage 10G: replay the REAL Windows run (prompt 10.fu4, llama3.2:3b) through the CURRENT rules. No model is called.

  python scripts/stage10g_replay_windows.py [--evidence reports/stage10_windows_evidence] [--out reports/stage10_ghi_eval]

Two things are produced: (1) a case-level failure table for the 14 missed opportunities, with the evidence in results.json and the code that now handles each; (2) a replay of the 22 questions the model
wrote on Windows through the new validator. Verdicts are the RULES' verdicts (fixed regexes and set tests), not human ratings. Questions that cited a stored memory are not replayed (they need the exact
memory the Windows session offered, which results.json does not record)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import followup_llm as FL, opportunity_eval as OE  # noqa: E402

# author's reading of each miss, from results.json evidence (reason codes, outcome) and the prompt the model was sent
DIAG = {
    "T02": ("rejected: question:novel_terms:E2", "model wrote the concept id 'E2' into the question text (prompt listed 'E2 consistency')", "prompt/schema design + validator-adjacent", "sanitise_ids replaces ids with labels; prompt says never write ids"),
    "T03": ("rejected: question:not_tied_to_answer", "wording did not build on a 4-word answer ('It is O(log n).'); text of the rejected reply was not recorded", "model quality or over-strict tie rule: UNDETERMINED", "TARGET concept chosen by code and concept_id inferred from the question; rejected replies are now recorded in results.json rows[].debug so the next run settles it"),
    "T05": ("model skip (covered)", "3 of 3 shown concepts 'not found'; the answer swaps 'is' and '=='", "LLM skipped an eligible follow-up", "skip 'covered' is overruled when concepts are open; ask-only prompt with TARGET; one repair"),
    "T06": ("model skip (covered)", "answer says O(n); concept O(n^2) 'not found'", "LLM skipped an eligible follow-up", "same"),
    "T07": ("model skip (covered)", "2 of 3 concepts 'not found'", "LLM skipped an eligible follow-up", "same"),
    "T08": ("model skip (covered)", "3 of 4 concepts 'not found' (sigmoid, parametric, discriminative)", "LLM skipped an eligible follow-up", "same"),
    "T10": ("model skip (covered)", "3 of 4 concepts 'not found' (ROC/AUC, confusion matrix, precision/recall)", "LLM skipped an eligible follow-up", "same"),
    "T12": ("model skip (covered)", "Type II error, false positive, false negative 'not found'", "LLM skipped an eligible follow-up", "same"),
    "S01": ("accepted a question (should skip)", "only 'loss minimisation' was 'not found'; the answer says 'minimises a loss'", "exact-word hint too literal", "stem-level coverage: now covered, skipped by the rules, model not called"),
    "S02": ("accepted a question (should skip)", "4 of 4 concepts 'found' and the model still asked", "LLM ignored the hint", "all concepts covered -> skipped by the rules, model not called"),
    "S03": ("accepted 'Can a Type I error also be referred to as a false negative?'", "4 of 4 concepts 'found'; the question is also a yes/no that plants a wrong claim", "LLM ignored the hint + low-quality wording", "rules skip; closed_yes_no rule"),
    "M02": ("accepted without citation: 'What does it mean to learn from examples in supervised learning?'", "a definition re-ask of the candidate's own phrase; no stored memory cited (whether one was offered is not recorded)", "model quality (generic) + memory use UNDETERMINED", "'what does it mean' rejected + one repair; offered memory ids now recorded per case"),
    "M04": ("rejected: question:novel_terms:E2", "same id leak as T02", "prompt/schema design", "sanitise_ids"),
    "M07": ("accepted without citation: 'You said halving the sorted list ..., is that a key insight ...?'", "yes/no question that only repeats the candidate's words; no memory used", "model quality", "closed_yes_no rejected + one repair"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=str(ROOT / "reports" / "stage10_windows_evidence"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "stage10_ghi_eval"))
    a = ap.parse_args()
    ev = Path(a.evidence)
    res = json.loads((ev / "results.json").read_text(encoding="utf-8"))["results"][0]
    key = json.loads((ev / "key.json").read_text(encoding="utf-8"))
    sheet = {r["item_id"]: r["interviewer_text"] for r in csv.DictReader((ev / "review_sheet.csv").open(encoding="utf-8"))}
    data = OE.load()
    cases = {c["id"]: c for c in data["cases"]}
    eng = OE.offline_engine()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for iid, k in key.items():
        cid, q = k["case"], sheet[iid]
        row = {"item": iid, "case": cid, "class": k["class"], "cited_memory": k["cites_memory"], "question": q, "verdict": "", "codes": []}
        if cid.startswith("B"):
            row["verdict"] = "n/a (behavioural probe: deterministic bank, not model-written)"
        elif k["cites_memory"]:
            row["verdict"] = "not replayed (needs the memory the Windows session offered)"
        else:
            ctx, _, _, _ = OE.build_case(eng, cases[cid])
            words = ctx.answer.split()
            raw = {"decision": "ask", "skip_reason": "none", "question": q, "purpose": "deepen", "concept_id": "none", "answer_quote": " ".join(words[:4])}
            if ctx.memory:
                raw["memory_id"] = "none"
            p, why = FL.validate(raw, ctx)
            cov = FL.opportunity_class(ctx)
            if cov == "covered":
                row["verdict"] = "no question asked now: answer covered, skipped by the rules"
            elif p is None:
                row["verdict"] = "rejected now (then one repair attempt)"
                row["codes"] = why
            else:
                row["verdict"] = "still accepted"
        rows.append(row)
    missed = [m for m in res["misses"]]
    L = ["# Stage 10G: failure analysis of the real Windows run", "",
         f"Evidence: `reports/stage10_windows_evidence/` (llama3.2:3b, Ollama {res['ollama_version']}, prompt {res['prompt_version']}). Measured on Windows by you; nothing here was re-run on a model.", "",
         f"23 eligible opportunities, {res['useful_valid']} useful+valid ({res['useful_valid_rate']:.1%}); {res['by_class']['skip']['success']}/11 skips correct; {res['quality_gates']['fabricated_memory_references']} fabricated memory references; "
         f"{res['reply_truncated']} truncated; cold {res['cold_load_ms']} ms, first call {res['first_call_ms']} ms, warm median {res['warm_latency_ms']['median']} ms.", "",
         "## Per-class view (not just the aggregate)", "", "| class | n | success | accepted | model skipped | fell back |", "|---|---|---|---|---|---|"]
    for c, d in res["by_class"].items():
        L.append(f"| {c} | {d['n']} | {d['success']} | {d['accepted']} | {d['model_skipped']} | {d['fell_back']} |")
    L += ["", f"Rejection codes on Windows: {res['rejection_reason_codes']}. Skip reasons: {res['skip_reasons']}.", "",
          "## Case-level failure table (14 misses)", "", "| case | class | what happened | evidence | cause | legitimate safety rejection? | fix |", "|---|---|---|---|---|---|---|"]
    for m in missed:
        d = DIAG[m["id"]]
        legit = "no" if m["id"] not in ("T03",) else "unclear"
        L.append(f"| {m['id']} | {m['class']} | {d[0]} | {d[1]} | {d[2]} | {legit} | {d[3]} |")
    L += ["", "No miss was a legitimate safety rejection: the two `novel_terms` rejections were the model echoing a prompt id, and `not_tied_to_answer` on T03 is unresolved (see its row).", "",
          "## What the 12 'useful' results hide", "",
          "The automatic score counted a question as useful when the rules accepted it and the audit found nothing. Replaying the 22 questions the model wrote through the current rules:", "",
          "| item | case | class | question (model-written) | now |", "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['item']} | {r['case']} | {r['class']} | {r['question']} | {r['verdict']}{' (' + ', '.join(r['codes']) + ')' if r['codes'] else ''} |")
    missed_ids = {m["id"] for m in missed}
    rejected_success = [r for r in rows if r["verdict"].startswith(("rejected", "no question")) and r["class"] in ("expected", "memory_use") and r["case"] not in missed_ids]
    L += ["", f"Of the 12 counted as useful, {len(rejected_success)} would now be rejected or skipped ({', '.join(r['case'] for r in rejected_success)}). "
          "So the 52.2% overstated the quality of what was accepted: the strict reading of the same Windows run is lower, and the repairs must be judged on a new real run, not on this replay.", ""]
    (out / "windows_failure_analysis.md").write_text("\n".join(L), encoding="utf-8")
    (out / "windows_replay.json").write_text(json.dumps({"rows": rows, "diagnosis": DIAG}, indent=1), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
