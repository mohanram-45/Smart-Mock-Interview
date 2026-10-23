"""Stage 10L: case-by-case comparison of the REAL Windows runs with the CURRENT code. No language model is called here.

  python scripts/stage10l_compare.py [--out reports/stage10_jkl_eval]

Inputs (frozen, never edited): reports/stage10_windows_evidence/results.json (run 1, prompt 10.fu4) and reports/stage10_windows_evidence_2/results.json (run 2, prompt 10.fu5, llama3.2:3b).

What is produced, and what each part IS:
  1. run 2 RE-SCORED with the corrected formula (`opportunity_eval.score_row`). Behavioural rows are recomputed from the deterministic probes; technical rows keep what the model really did, and
     the accepted question is re-audited against the current retrieval. This is a re-scoring of recorded behaviour, not a new model run.
  2. a QUESTION-LEVEL REPLAY of every reply the model wrote in run 2 through the current rules. Windows did not keep purpose / concept_id / answer_quote, so a stand-in value is used for them and the
     replay is run for both purposes that matter ('deepen' and 'probe_concept'). It shows which rules now fire; it does not show what a model would write under prompt 10.fu6.
  3. the scripted (stand-in model) result for the current code, labelled as such.
The 80% target is NOT claimed: the real-model number for the current code needs a Windows run (see the report)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import followup_llm as FL, opportunity_eval as OE  # noqa: E402

RUN1 = ROOT / "reports" / "stage10_windows_evidence" / "results.json"
RUN2 = ROOT / "reports" / "stage10_windows_evidence_2" / "results.json"

# author's reading, from the recorded replies in results.json and from the fixture context (see the report for the evidence quoted in full)
ROOT_CAUSE = {
    "T02": ("rejected: concept_already_in_answer", "The question names consistency (open) AND atomicity (already stated). The validator trusted the model's declared concept id, which was the stated one, so a good question was vetoed.", "validator", "concept ids are read from the question text; a question that names an open concept is not vetoed for also naming a covered one"),
    "T03": ("rejected: concept_already_in_answer + not_tied_to_answer", "'It is O(log n).' states one concept; the question compares binary and linear search. Declared-id veto again, and the 4-word answer gives few tie words.", "validator", "ids derived from the question; linear search is the open TARGET and is named, which counts as a tie"),
    "T07": ("skip chosen AND a question written", "decision=skip with the question 'How do non-linearities help ...?'. The old code accepted the skip and dropped the question silently.", "model payload + silent handling", "payload:skip_with_question is a rejection with a targeted repair; if it repeats, the deterministic follow-up is used and the class is payload_inconsistent"),
    "T09": ("rejected twice: restates_answer (+ evidence:none_verified)", "Both questions paraphrase 'finds structure in data without labels'. The repair said only 'ask about the TARGET', which did not change a 3B model's output.", "model quality + weak repair", "repair now quotes the rejected question and asks for an example, reason, limit or trade-off about the named TARGET; the standard prompt asks for a progressive question"),
    "T10": ("rejected: repeats_earlier + ignores the open concept + restates", "'How would you evaluate a logistic regression model?' repeats an earlier question; the open concepts were ROC/AUC, confusion matrix, precision/recall.", "model quality (ignored TARGET)", "question:ignores_target (probe_concept must name an open concept); repeat veto unchanged"),
    "M01": ("accepted, memory_id none", "Two statements were offered; the question uses 'class imbalance' (which is in the stored challenge) but cites nothing. The old prompt let the model decide to cite, and it declined.", "generation + citation metadata (retrieval OK)", "memory mode: one statement, code-built lead-in, memory_id in {id, none}; uncited use of statement-only words is rejected (memory:uncited_reference)"),
    "M02": ("no memory offered; repeated question", "The spam-classifier statement shares no word with 'Supervised learning is learning from examples'. The retrieval query held only the question and answer, not the vetted concepts of the question (labelled training data, classification).", "RETRIEVAL", "query expanded with the question's vetted concepts and reference; quote-aware specific_overlap"),
    "M03": ("accepted, memory_id none", "Two statements offered; generic pytest-mocking question; nothing cited.", "generation", "memory mode as M01"),
    "M04": ("no memory offered; 'E1 consistency' leaked", "'concurrent transactions' vs 'Atomicity means all or nothing': no shared word, and the matching part of the claim (billing database ... concurrent transactions) was in the quote, which the overlap test ignored. Also an id leak.", "RETRIEVAL + id leak", "quote-aware overlap + vetted-concept query; ids replaced by labels and rejected in the audit (id_leak)"),
    "M05": ("accepted, memory_id none", "One statement offered; a generic logistic-regression question; nothing cited.", "generation", "memory mode as M01"),
    "M06": ("accepted, memory_id none; question says 'your convolutional neural network'", "'convolutional neural network' is in the turn-1 statement and NOT in the current answer ('It uses neural networks with many layers'). So it is a real but undisclosed reference to a stored statement: an implicit grounded reference with missing citation metadata, not ordinary current-answer context and not invented.", "citation metadata (an implicit use)", "uncited use of statement-only words is rejected; in memory mode the lead-in is added by code and the id is validated"),
    "M07": ("rejected: repeats_earlier", "The question repeats the binary-search explanation the candidate just gave; the stored statement (a library-catalogue search feature) was offered but not used.", "generation", "memory mode connects the claim to the open TARGET (O(log n))"),
    "B07": ("class skip, outcome probe, success true", "The fixture labels B07 'skip' but expects followup=null (unspecified) and safety=true; the deterministic probe asks about the missing action/result, safely. The old scorer returned ok=True for any null expectation, so a probe counted as a skip success.", "FIXTURE inconsistency + scorer shortcut", "scored on safety only, excluded from the strict skip rate, listed under fixture_defects; label NOT changed (approval needed)"),
}


def load_run(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))["results"][0]


def replay(engine, case, row):
    """Question-level replay of the replies recorded in `row['debug']` through the current rules."""
    ctx, offered, s, core = OE.build_case(engine, case)
    quote = " ".join(case["answer"].split()[:5])
    out = []
    for d in row.get("debug") or []:
        verdicts = {}
        for purpose in ("deepen", "probe_concept"):
            raw = {"decision": d.get("decision") or "ask", "skip_reason": d.get("skip_reason") or "none", "question": d.get("question") or "", "purpose": purpose, "concept_id": "none", "answer_quote": quote}
            ctx.memory_lead  # noqa: B018  (property; standard mode never shows memory)
            prop, reasons = FL.validate(raw, ctx, "standard")
            verdicts[purpose] = "accepted" if prop is not None else list(reasons)
        out.append({"attempt": d["attempt"], "question": d.get("question"), "decision": d.get("decision"), "recorded_reasons": d.get("reasons"), "now_if_deepen": verdicts["deepen"], "now_if_probe_concept": verdicts["probe_concept"]})
    return out


def rescore(engine, data, run):
    cases = {c["id"]: c for c in data["cases"]}
    rows = []
    for r in run["rows"]:
        case = cases[r["id"]]
        if case["mode"] == "behavioural":
            nr = OE.run_behavioural(case)                                                         # deterministic probes: recomputing is exact
            nr["evidence"] = "deterministic_scripted_probe"
            rows.append(nr)
            continue
        ctx, offered, s, core = OE.build_case(engine, case)
        nr = dict(r)
        nr["mode"] = "technical"
        nr["audit"] = OE.audit(r["question"], ctx, None, [m["id"] for m in offered], None, s) if r.get("accepted") and r.get("question") else []
        nr["useful_valid"] = bool(r.get("accepted") and not nr["audit"])
        nr["payload_issues"] = OE.payload_issues_from_debug(r.get("debug"))
        nr["memory_stage"] = None
        nr["memory_grounded"] = False
        nr["success"], nr["success_basis"], nr["strict"] = OE.score_row(nr)
        nr["failure_type"] = OE._failure_type(case["class"], {**nr, "offered_memory": r.get("offered_memory", 0)})          # as it happened on Windows: what was offered THEN
        nr["offered_now"] = len(offered)
        rows.append(nr)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "stage10_jkl_eval"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = OE.load()
    cases = {c["id"]: c for c in data["cases"]}
    r1, r2 = load_run(RUN1), load_run(RUN2)
    eng = OE.offline_engine()
    re2 = rescore(eng, data, r2)
    S2 = OE.aggregate(re2)
    scripted = OE.run_all(eng, OE.scripted_generator(), data, evidence="scripted_stand_in")
    miss1 = {m["id"] for m in r1["misses"]}
    old2 = {x["id"]: x for x in r2["rows"]}
    new = {x["id"]: x for x in scripted["rows"]}
    rec = {x["id"]: x for x in re2}
    table, replays = [], {}
    for c in data["cases"]:
        i = c["id"]
        rp = replay(eng, c, old2[i]) if c["mode"] == "technical" and old2[i].get("debug") else []
        if rp:
            replays[i] = rp
        table.append({"id": i, "class": c["class"], "mode": c["mode"], "run1_success": i not in miss1, "run2_success_as_reported": old2[i]["success"], "run2_outcome": old2[i]["outcome"], "run2_reasons": old2[i].get("reasons"),
                      "run2_rescored_success": rec[i]["success"], "run2_rescored_basis": rec[i].get("success_basis"), "run2_rescored_strict": rec[i].get("strict", True),
                      "scripted_current_success": new[i]["success"], "scripted_current_stage": new[i].get("memory_stage"), "root_cause": ROOT_CAUSE.get(i)})
    summary = {
        "windows_run1": {"prompt": r1["prompt_version"], "useful_valid": f"{r1['useful_valid']}/{r1['eligible_opportunities']}"},
        "windows_run2_as_reported": {"prompt": r2["prompt_version"], "useful_valid": f"{r2['useful_valid']}/{r2['eligible_opportunities']}", "by_class": {k: f"{v['success']}/{v['n']}" for k, v in r2["by_class"].items()},
                                     "fallbacks": r2["latency_and_fallbacks"]["fallbacks"] if "latency_and_fallbacks" in r2 else r2.get("dimensions", {}).get("latency_and_fallbacks", {}).get("fallbacks")},
        "windows_run2_rescored": {"eligible": S2["eligible"], "by_class": {k: {"success": v["success"], "n_strict": v["n_strict"], "safety_only": v["safety_only"]} for k, v in S2["by_class"].items()},
                                  "fixture_defects": [d["id"] for d in S2["fixture_defects"]], "quality_gates": S2["quality_gates"]},
        "scripted_current_code": {"evidence": "scripted_stand_in: mechanics only, NOT language-model evidence", "eligible": scripted["summary"]["eligible"]},
        "target_80_percent": {"real_model_for_current_code": "NOT MEASURED. No Ollama in this environment. Windows verification is outstanding.", "windows_run2_rescored_rate": S2["eligible"]["rate"]},
    }
    (out / "windows_comparison.json").write_text(json.dumps({"summary": summary, "cases": table, "question_level_replay": replays}, indent=1, default=str), encoding="utf-8")
    L = ["# Windows evidence vs current code, case by case (10L)", "",
         "**Evidence labels.** `Windows run 1/2` = real llama3.2:3b on the user's machine (frozen files). `re-scored` = the same recorded behaviour under the corrected formula (no new model call). "
         "`scripted` = a rule-based stand-in model on the current code (mechanics only). `replay` = recorded questions through the current rules (not a model run).", "",
         f"- Windows run 1 (prompt {r1['prompt_version']}): **{summary['windows_run1']['useful_valid']}** useful+valid",
         f"- Windows run 2 (prompt {r2['prompt_version']}), as reported: **{summary['windows_run2_as_reported']['useful_valid']}**; by class {summary['windows_run2_as_reported']['by_class']}",
         f"- Windows run 2 re-scored with the corrected formula: **{S2['eligible']['success']}/{S2['eligible']['n']} = {S2['eligible']['rate']:.1%}**; technical expected {S2['eligible']['technical_expected']}, behavioural scripted probes "
         f"{S2['eligible']['behavioural_scripted_probes']}, grounded memory use {S2['eligible']['memory_use_grounded']}; strict skip {S2['by_class']['skip']['success']}/{S2['by_class']['skip']['n_strict']} plus safety-only {S2['by_class']['skip']['safety_only']}",
         f"- Current code with the scripted stand-in: {scripted['summary']['eligible']['success']}/{scripted['summary']['eligible']['n']} (**mechanics only**)",
         f"- **80% target on a real model for the current code: NOT MEASURED.** Windows verification is outstanding.", "",
         "| case | class | run 1 | run 2 reported | run 2 re-scored | scripted now | run 2 outcome / reasons |", "|---|---|---|---|---|---|---|"]
    for t in table:
        L.append(f"| {t['id']} | {t['class']} | {'ok' if t['run1_success'] else 'MISS'} | {'ok' if t['run2_success_as_reported'] else 'MISS'} | {'ok' if t['run2_rescored_success'] else 'MISS'}{'' if t['run2_rescored_strict'] else ' (safety only)'} | "
                 f"{'ok' if t['scripted_current_success'] else 'MISS'} | {t['run2_outcome']} {t['run2_reasons'] or ''} |")
    L += ["", "## Root causes by case (from the recorded replies and the fixture context)", "", "| case | what Windows showed | root cause | layer | change |", "|---|---|---|---|---|"]
    for i, v in ROOT_CAUSE.items():
        L.append(f"| {i} | {v[0]} | {v[1]} | {v[2]} | {v[3]} |")
    L += ["", "## Question-level replay of run 2's replies through the current rules", "",
          "Windows kept only the question text, decision, skip_reason and memory_id. The replay uses a stand-in purpose, so each reply is shown under `deepen` and `probe_concept`. `accepted` means no current rule fires on the wording; "
          "it is NOT a quality verdict and not what the model would write under the new prompt.", "", "| case | attempt | recorded question | recorded reasons | now if deepen | now if probe_concept |", "|---|---|---|---|---|---|"]
    for i, lst in replays.items():
        for d in lst:
            if d["recorded_reasons"] or d["decision"] == "skip" or i in ROOT_CAUSE:
                L.append(f"| {i} | {d['attempt']} | {(d['question'] or '')[:110]} | {d['recorded_reasons']} | {d['now_if_deepen']} | {d['now_if_probe_concept']} |")
    L += ["", "## Memory-use cases, re-audited", ""]
    for t in table:
        if t["class"] == "memory_use":
            x = rec[t["id"]]
            L.append(f"- `{t['id']}`: Windows offered {old2[t['id']]['offered_memory']} statement(s); the current retrieval offers {x['offered_now']}; run 2 re-audit: {x['audit'] or 'no finding'}; failure type: {x['failure_type']}; scripted now: stage `{t['scripted_current_stage']}`")
    L += ["", "No human has rated anything in these runs. `human_validated` is false in both result files."]
    (out / "windows_comparison.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:14]))
    print(f"wrote {out / 'windows_comparison.md'}")


if __name__ == "__main__":
    main()
