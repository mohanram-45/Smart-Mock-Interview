"""Stage 10D-L evaluation, SCRIPTED / MOCK edition (runs anywhere, no model, no network):

  python scripts/stage10f_eval.py                      writes reports/stage10_jkl_eval/, reports/stage10_jkl_transcripts/, docs/stage10_review_jkl/
  python scripts/stage10f_eval.py --out tmp/x --transcripts tmp/x/t --review tmp/x/r --quick

What it does: runs the fixed per-opportunity set (src/demo/eval_data/stage10f_opportunities_v1.json, unchanged) against (1) a rule-based stand-in for a well-behaved model, (2) ten deliberately faulty
scripted models that the safety rules must stop, (3) two degenerate models and 21 synthetic rows that the SCORER must not reward, then four scripted interviews (technical x2, behavioural, mixed), scenarios
A-E through the real engine, and scenarios A, B and E again with the model path switched on (a scripted stand-in model; every question and lead-in still goes through the real validators).

WHAT THIS IS NOT: a measurement of any language model, of question quality, or of candidates. The stand-in follows the exact-words hint in the prompt, so its high acceptance on 'expected' turns is a
plumbing check, not a result. Real-model numbers come only from scripts/stage10_verify_real_stack.py on a machine with Ollama. No human has rated anything."""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import behavioural as B, followup_llm as FL, memory as M, opportunity_eval as OE  # noqa: E402

LABEL = "SCRIPTED / MOCK: rule-based stand-in for a model, synthetic candidates, lexical retrieval, no real model, no human labels"
EVIDENCE = "scripted_stand_in"


def _suite_module():
    spec = importlib.util.spec_from_file_location("stage10_eval_suite", ROOT / "scripts" / "stage10_eval_suite.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(quick: bool = False, a_review=None):
    R = {"label": LABEL, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "prompt_version": FL.PROMPT_VERSION, "set_version": OE.load()["version"], "rubric_version": B.versions()}
    data = OE.load()
    eng = OE.offline_engine()
    base = OE.run_all(eng, OE.scripted_generator(), data, evidence=EVIDENCE)
    R["opportunities"] = {"summary": base["summary"], "misses": [{"id": r["id"], "class": r["class"], "category": r["category"], "outcome": r["outcome"], "reasons": r.get("reasons", []), "basis": r.get("success_basis")}
                                                           for r in base["rows"] if r.get("strict", True) and not r["success"]],
                          "rows": [{k: v for k, v in r.items() if k != "metrics"} for r in base["rows"]]}
    tech_ids = [c["id"] for c in data["cases"] if c["mode"] == "technical"]
    R["faulty_models"] = {}
    for kind in OE.FAULTY:
        res = OE.run_all(eng, OE.scripted_generator(kind), data, only=tech_ids)
        g = res["summary"]["quality_gates"]
        R["faulty_models"][kind] = {"accepted": g["accepted_questions"], "fabricated_memory": g["fabricated_memory_references"], "rejection_codes": res["summary"]["reason_codes"]}
    R["degenerate_models"] = {}
    for kind in OE.DEGENERATE:
        bc = OE.run_all(eng, OE.scripted_generator(kind), data, only=tech_ids)["summary"]["by_class"]
        R["degenerate_models"][kind] = {"expected_success": bc["expected"]["success"], "memory_use_success": bc["memory_use"]["success"]}
    R["scorer_selftest"] = OE.scorer_selftest()
    pa = OE.review_pack_v2(base["rows"], Path(a_review) / "opportunities", evidence=EVIDENCE) if a_review else {}
    R["review_pack"] = pa
    transcripts, interviews = {}, {}
    for sc in data["interviews"]:
        e = OE.offline_engine()
        s, t, res = OE.run_interview(e, sc, followup_generator=OE.scripted_generator())
        interviews[sc["id"]] = {"mode": sc["mode"], "passed": res["passed"], "checks": res["checks"], "turns": res["turns"], "memory_refs": res["memory_refs"]}
        transcripts[{"I01": "technical_data_scientist", "I02": "behavioural", "I03": "mixed", "I04": "technical_python_developer"}[sc["id"]]] = (s, t)
    R["interviews"] = interviews
    scen = {}
    for name, fn, desc in OE.SCENARIOS:
        s, t, checks = fn(OE.offline_engine())
        scen[name] = {"description": desc, "passed": all(checks.values()), "checks": checks}
        transcripts["scenario_" + name] = (s, t)
    R["scenarios"] = scen
    scen_llm = {}
    for name, fn, desc in OE.SCENARIOS_LLM:
        s_, t_, checks = fn(OE.offline_engine())
        scen_llm[name] = {"description": desc, "passed": all(checks.values()), "checks": checks, "evidence": "scripted stand-in model (NOT a language model); real engine, real retrieval, real validators"}
        transcripts["scenario_" + name] = (s_, t_)
    R["scenarios_with_model_path"] = scen_llm
    # cost: engine turn time without any model, and the size of the prompt the model is given
    lat = []
    e = OE.offline_engine()
    sid = e.create({"role": "Data Scientist", "practical": False, "size": 4 if quick else 6})["id"]
    for n in range(1, 5 if quick else 7):
        t0 = time.perf_counter()
        e.submit(sid, n, OE.ONC if n == 1 else "Cross validation splits the data into folds and averages the held out score to estimate generalisation.")
        lat.append((time.perf_counter() - t0) * 1000)
    prov = OE.MockProvider(OE.scripted_reply)
    OE.run_all(e, FL.LLMFollowUpGenerator(prov, deadline=5), data, only=[c["id"] for c in data["cases"] if c["id"] in ("T01", "M01", "M05")])
    sizes = [len(c["system"]) + len(c["user"]) for c in prov.calls]
    std = [len(c["system"]) + len(c["user"]) for c in prov.calls if "EARLIER (turn" not in c["user"]]
    R["cost"] = {"engine_turn_ms_median": round(statistics.median(lat), 1), "engine_turn_ms_max": round(max(lat), 1), "prompt_chars_max": max(sizes), "prompt_tokens_estimate_max": FL.estimate_tokens("x" * max(sizes)),
                 "standard_prompt_tokens_estimate_max": FL.estimate_tokens("x" * max(std)) if std else 0,
                 "model_inference": "NOT MEASURED HERE (no Ollama in this environment)", "sentence_model_loads_in_this_process": dict(M.MODEL_STATS)}
    S = base["summary"]
    E = S["eligible"]
    R["headline"] = {"eligible_opportunities": E["n"], "useful_valid_scripted": E["success"], "rate": E["rate"], "target": 0.8, "technical_expected": E["technical_expected"], "behavioural_scripted_probes": E["behavioural_scripted_probes"],
                     "memory_use_grounded": E["memory_use_grounded"], "evidence": EVIDENCE,
                     "note": "eligible = classes 'expected' + 'memory_use'. The stand-in follows the prompt, so this is a plumbing check about the code AROUND a model; it is not a language-model result."}
    rows_by_id = {r["id"]: r for r in base["rows"]}
    consistent = all(OE.score_row(r)[0] == r["success"] for r in base["rows"]) and sum(r["success"] for r in base["rows"] if r["class"] in ("expected", "memory_use")) == E["success"]
    gates = {
        "useful_valid >= 80% of eligible scripted opportunities (mechanics only)": R["headline"]["rate"] >= 0.8,
        "grounded memory used on every memory_use case where memory was offered (stand-in)": E["memory_use_grounded"][0] >= sum(1 for r in base["rows"] if r["class"] == "memory_use" and r.get("offered_memory")) > 0,
        "zero fabricated, uncited or id-leaking references (stand-in)": all(S["quality_gates"][k] == 0 for k in ("fabricated_memory_references", "cites_unoffered_memory", "implicit_memory_use_uncited", "lead_not_from_stored_claim", "id_leaks")),
        "zero unsafe questions accepted from the ten faulty models": all(v["accepted"] == 0 and v["fabricated_memory"] == 0 for v in R["faulty_models"].values()),
        "degenerate models earn no credit (always-skip, cite-without-using)": R["degenerate_models"]["always_skips"]["expected_success"] == 0 and R["degenerate_models"]["cites_without_using"]["memory_use_success"] == 0,
        "no memory citation where memory is inappropriate": S["by_class"]["memory_inappropriate"]["cited_memory"] == 0 and S["by_class"]["memory_inappropriate"]["success"] == S["by_class"]["memory_inappropriate"]["n_strict"],
        "strict skip cases skipped (>= 80%)": (S["by_class"]["skip"]["success_rate"] or 0) >= 0.8,
        "B07 is reported as a fixture defect and scored on safety only (not counted as a skip success)": rows_by_id["B07"]["strict"] is False and any(d["id"] == "B07" for d in S["fixture_defects"]),
        "behavioural probes follow the missing STAR element": all(r["success"] for r in base["rows"] if r["mode"] == "behavioural" and r.get("strict", True)),
        "scorer self-tests (21 synthetic rows + degenerate models) all pass": all(R["scorer_selftest"].values()),
        "scorer and reporter agree (every row re-scored; eligible totals recomputed)": consistent,
        "payload consistency: no accepted question came from a self-contradicting reply": all(not r.get("payload_issues") for r in base["rows"] if r.get("accepted")),
        "technical, behavioural and mixed interviews pass their checks": all(v["passed"] for v in interviews.values()),
        "scenarios A-E pass": all(v["passed"] for v in scen.values()),
        "scenarios A, B, E with the model path on pass": all(v["passed"] for v in scen_llm.values()),
        "memory prompt stays small (< 3000 chars)": max(sizes) < 3000,
        "standard (no-memory) prompt stays under 450 estimated tokens": R["cost"]["standard_prompt_tokens_estimate_max"] < 450,
    }
    R["gates"] = {"passed": sum(gates.values()), "total": len(gates), "detail": gates}
    R["limits"] = [
        "The stand-in reads the prompt (hints, TARGET, EARLIER line); it cannot be wrong in the ways a language model can. Acceptance here says nothing about real models.",
        "Retrieval here is lexical (BM25 fallback / LexicalEmbedder) plus the vetted-concept query. With Sentence-BERT on the user's machine the candidate set can differ; the Windows run must confirm it.",
        "The expectations on each case are the author's reading, written before any model ran; they are not human-validated labels. B07 is a fixture defect (see fixture_defects): reported, not relabelled.",
        "Topic-link and relevance thresholds are heuristics, uncalibrated for Sentence-BERT.",
        "The review sheet is UNRATED: no human evaluation exists for any question in this report.",
        "'rule audit' is a second automatic code path, not an independent audit.",
    ]
    return R, transcripts


def results_md(R) -> str:
    S = R["opportunities"]["summary"]
    bc = S["by_class"]
    H = R["headline"]
    L = ["# Stage 10 scripted evaluation results (10J-10L)", "", f"**Evidence label:** {R['label']}.", "", f"Prompt `{R['prompt_version']}` · set `{R['set_version']}` (unchanged) · generated {R['generated_at']}", "",
         f"**Gates: {R['gates']['passed']} / {R['gates']['total']} passed** (mechanics only).", "",
         f"**Headline (scripted stand-in, per eligible opportunity):** {H['useful_valid_scripted']} / {H['eligible_opportunities']} = {H['rate']:.0%} (target 80%): technical expected {H['technical_expected'][0]}/{H['technical_expected'][1]}, "
         f"behavioural scripted probes {H['behavioural_scripted_probes'][0]}/{H['behavioural_scripted_probes'][1]}, grounded memory use {H['memory_use_grounded'][0]}/{H['memory_use_grounded'][1]}. {H['note']}", "",
         "## What kind of evidence each number is", "", "| metric | value | kind |", "|---|---|---|"]
    L += [f"| {e['metric']} | {e['value']} | {e['kind']} |" for e in S["evidence"]]
    L += ["", "## Per class (strict scoring; one formula, `opportunity_eval.score_row`)", "", "| class | n | strict n | success | rate | outcomes |", "|---|---|---|---|---|---|"]
    for c in OE.CLASSES:
        d = bc[c]
        L.append(f"| {c} | {d['n']} | {d['n_strict']} | {d['success']} | {d['success_rate']} | {', '.join(f'{k} {v}' for k, v in d['outcomes'].items())} |")
    L += ["", "Skip policy: " + S["scorer"]["skip_policy"], "", "## Fixture defects (reported, never relabelled)", ""]
    L += [f"- `{d['id']}`: {d['defect']} Observed outcome: `{d['observed']}`." for d in S["fixture_defects"]] or ["- none"]
    g = S["quality_gates"]
    L += ["", "## Rule audit of accepted questions (a second automatic code path; NOT an independent human audit)", "",
          f"accepted {g['accepted_questions']} · fabricated memory references {g['fabricated_memory_references']} · cites unoffered memory {g['cites_unoffered_memory']} · implicit uncited memory use {g['implicit_memory_use_uncited']} · "
          f"lead not from stored claim {g['lead_not_from_stored_claim']} · id leaks {g['id_leaks']} · repeats {g['repeats']} · unrelated {g['unrelated']} · injected {g['injected']} · accusatory {g['accusatory']} · trivial {g['trivial']}", "",
          f"Payload consistency: {S['payload_consistency']}", "", "## Memory-use cases", ""]
    L += [f"- `{r['id']}` stage `{r.get('memory_stage')}` offered {r.get('offered_memory')} success {r['success']} failure_type {r.get('failure_type')}: {r.get('question', '')[:160]}" for r in R["opportunities"]["rows"] if r["class"] == "memory_use"]
    L += ["", "## Misses (listed, not tuned away)", ""]
    L += [f"- `{m['id']}` ({m['class']}/{m['category']}): outcome {m['outcome']} · {m.get('basis')} · {m['reasons']}" for m in R["opportunities"]["misses"]] or ["- none"]
    L += ["", "## Faulty scripted models (the rules must stop them)", "", "| faulty behaviour | accepted | fabricated memory | rejection codes |", "|---|---|---|---|"]
    for k, v in R["faulty_models"].items():
        L.append(f"| {k} | {v['accepted']} | {v['fabricated_memory']} | {', '.join(f'{a} x{b}' for a, b in list(v['rejection_codes'].items())[:4])} |")
    L += ["", "## Degenerate models (valid replies that do not do the job; the scorer must give no credit)", ""] + [f"- {k}: expected success {v['expected_success']}, memory_use success {v['memory_use_success']}" for k, v in R["degenerate_models"].items()]
    L += ["", "## Scorer self-tests", ""] + [f"- {'PASS' if v else 'FAIL'} — {k}" for k, v in R["scorer_selftest"].items()]
    L += ["", "## Nine dimensions, reported separately (automatic proxies; wording is form only)", ""] + [f"- **{k}**: {v}" for k, v in S["dimensions"].items()]
    L += ["", "## Interviews", "", "| id | mode | passed | turns | memory refs |", "|---|---|---|---|---|"]
    L += [f"| {k} | {v['mode']} | {v['passed']} | {v['turns']} | {v['memory_refs']} |" for k, v in R["interviews"].items()]
    L += ["", "## Scenarios A-E (deterministic engine paths)", ""]
    for k, v in R["scenarios"].items():
        L.append(f"- **{k}** — {'PASS' if v['passed'] else 'FAIL'} — {v['description']}" + ("" if v["passed"] else f" — failing: {[a for a, b in v['checks'].items() if not b]}"))
    L += ["", "## Scenarios A, B, E with the model path on (scripted stand-in model)", ""]
    for k, v in R["scenarios_with_model_path"].items():
        L.append(f"- **{k}** — {'PASS' if v['passed'] else 'FAIL'} — {v['description']}" + ("" if v["passed"] else f" — failing: {[a for a, b in v['checks'].items() if not b]}"))
    c = R["cost"]
    L += ["", "## Cost (this container)", "", f"- engine turn time without a model: median {c['engine_turn_ms_median']} ms, max {c['engine_turn_ms_max']} ms", f"- largest follow-up prompt: {c['prompt_chars_max']} chars (about {c['prompt_tokens_estimate_max']} tokens, an estimate); "
          f"largest standard (no-memory) prompt: about {c['standard_prompt_tokens_estimate_max']} tokens",
          f"- model inference: {c['model_inference']}", f"- sentence-model loads in this process: {c['sentence_model_loads_in_this_process']}", "", "## Limits", ""]
    L += [f"- {x}" for x in R["limits"]]
    L += ["", "## Gate detail", ""] + [f"- {'PASS' if v else 'FAIL'} — {k}" for k, v in R["gates"]["detail"].items()]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "stage10_jkl_eval"))
    ap.add_argument("--transcripts", default=str(ROOT / "reports" / "stage10_jkl_transcripts"))
    ap.add_argument("--review", default=str(ROOT / "docs" / "stage10_review_jkl"))
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    R, transcripts = run(a.quick, a.review)
    out, tr = Path(a.out), Path(a.transcripts)
    out.mkdir(parents=True, exist_ok=True)
    tr.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    (out / "results.md").write_text(results_md(R), encoding="utf-8")
    suite = _suite_module()
    notes = {"technical_data_scientist": "Technical interview. The introduction states a project; a later relevant moment asks about it.", "technical_python_developer": "Technical interview for a Python Developer with no project in the introduction.",
             "behavioural": "Behavioural interview with a team project in the introduction.", "mixed": "Mixed interview: technical part, spoken transition, behavioural part."}
    for name, (s, t) in transcripts.items():
        title = {"technical_data_scientist": "Technical interview: Data Scientist", "technical_python_developer": "Technical interview: Python Developer", "behavioural": "Behavioural interview", "mixed": "Mixed interview"}.get(
            name, name.replace("scenario_", "Scenario ").replace("_", " "))
        note = notes.get(name) or next((d for n_, f_, d in list(OE.SCENARIOS) + list(OE.SCENARIOS_LLM) if "scenario_" + n_ == name), "")
        (tr / f"{name}.md").write_text(suite.md_transcript(name, s, t, title, note + " Interviewer turns come from the deterministic generators and, where marked, from a rule-based stand-in for a model."), encoding="utf-8")
    suite.review_pack({k: v for k, v in transcripts.items() if not k.startswith(("scenario_E", "scenario_A_llm", "scenario_B_llm"))}, Path(a.review) / "interviews")
    print(results_md(R))
    print(f"wrote {out}, {tr}, {a.review}")
    return 0 if R["gates"]["passed"] == R["gates"]["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
