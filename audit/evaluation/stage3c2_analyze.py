"""Stage 3C-2 analysis of one results.json (mechanical criteria only; human-label criteria stay PENDING_HUMAN).

  python audit/evaluation/stage3c2_analyze.py data/evaluation/stage3c2_results/<run>/results.json

Writes analysis.json and analysis.md next to the results. The AI expectations are shown side by side for reading ONLY: no agreement rate or accuracy
is computed from them, and nothing here is human-validated. Thresholds come from data/evaluation/stage3c2/acceptance_criteria.json (frozen)."""
import json, statistics, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "evaluation" / "stage3c2"
REACHED = lambda r: r["status"] not in ("not_gradable", "scope_unavailable")


def _pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))] if xs else None


def analyze(doc: dict, expectations: dict, criteria: dict) -> dict:
    mod, leg = doc.get("modular", []), doc.get("legacy", [])
    reached = [m for m in mod if REACHED(m["result"])]
    status = Counter(m["result"]["status"] for m in mod)
    bad = [m for m in reached if m["result"]["status"] in ("invalid_response", "provider_error")]
    verdicts = [(m, v) for m in mod for v in m["result"]["verdicts"]]
    model_stated = [(m, v) for m, v in verdicts if (v.get("original_state") or v["state"]) != "unverified"]
    downgraded = [(m, v) for m, v in model_stated if v.get("downgrade_reason")]
    reasons = Counter((v.get("downgrade_reason") or "")[:80] for _, v in downgraded)
    reasons.update((d.split(":")[0][:80]) for m in mod for d in m["result"]["provenance"].get("dropped_verdicts", []))

    unsupported, no_deriv, bad_ids, inj_ev, abst_no_reason, missing_pen = [], [], [], [], [], 0
    for m in mod:
        r = m["result"]; ids = {c["id"] for c in r["claims"]}; flagged = {c["id"] for c in r["claims"] if "possible_instruction" in c["flags"]}
        vmap = {(v["requirement_id"], v["member"]): v for v in r["verdicts"]}
        for v in r["verdicts"]:
            for e in v.get("evidence", []):
                if e["claim_id"] not in ids: bad_ids.append((m["sample_id"], v["requirement_id"], e["claim_id"]))
                if e["claim_id"] in flagged: inj_ev.append((m["sample_id"], v["requirement_id"], e["claim_id"]))
        if r["penalty_mode"] == "full":
            for o in r["outcomes"]:
                if o["tier"] == "essential" and o["status"] == "missing":
                    missing_pen += 1
                    vs = [v for (rid, _), v in vmap.items() if rid == o["requirement_id"]]
                    ok = any(v["member"] == "__other_valid__" and v["state"] == "not_stated" for v in vs) if o["kind"] == "group" else bool(vs) and all(v["state"] == "not_stated" for v in vs)
                    if not ok: unsupported.append((m["sample_id"], o["requirement_id"]))
        if r["status"] == "scored" and any(not d.get("derivation") for d in r["dimensions"]): no_deriv.append(m["sample_id"])
        if r["status"] == "abstained" and not r["abstain_reasons"]: abst_no_reason.append(m["sample_id"])

    by = {}
    for m in mod: by.setdefault(m["sample_id"], {})[m["repeat"]] = m["result"]
    agree = tot = 0; deltas, flips = [], 0
    for sid, reps in by.items():
        if 0 in reps and 1 in reps:
            a = {(v["requirement_id"], v["member"]): v["state"] for v in reps[0]["verdicts"]}; b = {(v["requirement_id"], v["member"]): v["state"] for v in reps[1]["verdicts"]}
            for k in a.keys() & b.keys():
                tot += 1; agree += a[k] == b[k]
            if reps[0]["score"] is not None and reps[1]["score"] is not None: deltas.append(abs(reps[0]["score"] - reps[1]["score"]))
            elif (reps[0]["score"] is None) != (reps[1]["score"] is None): flips += 1
    lat = [m["wall_ms"] / 1000 for m in mod]; llat = [m["wall_ms"] / 1000 for m in leg]
    calls = [t for m in mod for t in m["verifier_trace"]]
    tps = [t["usage"]["eval_count"] / (t["usage"]["eval_duration"] / 1e9) for t in calls if t.get("usage") and t["usage"].get("eval_count") and t["usage"].get("eval_duration")]
    vram = [mm.get("size_vram") for m in mod for mm in (m.get("ollama_ps") or {}).get("models", []) if isinstance(mm, dict)]

    metrics = {
        "answers": len(by), "modular_rows": len(mod), "legacy_rows": len(leg), "partial_run": bool(doc["meta"].get("partial_run")),
        "modular_status": dict(status), "reached_verifier": len(reached),
        "valid_output_rate": round(1 - len(bad) / len(reached), 4) if reached else None,
        "provider_errors": sum(1 for m in mod if m["result"]["status"] == "provider_error"),
        "invalid_responses": sum(1 for m in mod if m["result"]["status"] == "invalid_response"),
        "verdicts_total": len(verdicts), "verdict_states_after_gate": dict(Counter(v["state"] for _, v in verdicts)),
        "verdict_states_as_returned_by_model": dict(Counter((v.get("original_state") or v["state"]) for _, v in verdicts)),
        "model_stated_non_unverified": len(model_stated), "gate_downgrades": len(downgraded),
        "gate_downgrade_rate": round(len(downgraded) / len(model_stated), 4) if model_stated else 0.0, "evidence_rejection_reasons": dict(reasons),
        "essential_missing_penalties": missing_pen, "unsupported_completeness_penalties": len(unsupported), "unsupported_detail": unsupported,
        "scored_results_without_derivation": len(no_deriv), "evidence_claim_ids_not_in_answer": len(bad_ids),
        "injection_flagged_claims_used_as_evidence": len(inj_ev), "abstentions_without_recorded_reason": len(abst_no_reason),
        "abstain_rate": round(status["abstained"] / max(1, status["abstained"] + status["scored"]), 4),
        "median_answer_latency_s": round(statistics.median(lat), 2) if lat else None, "p95_answer_latency_s": _pct(lat, .95), "max_answer_latency_s": round(max(lat), 2) if lat else None,
        "legacy_median_latency_s": round(statistics.median(llat), 2) if llat else None, "median_decode_tokens_per_s": round(statistics.median(tps), 1) if tps else None,
        "repeat_member_state_agreement": round(agree / tot, 4) if tot else None, "repeat_score_delta_max_points": max(deltas) if deltas else None,
        "repeat_scored_vs_abstained_flips": flips, "peak_ollama_size_vram_bytes": max([v for v in vram if v] or [0]),
        "gpu_snapshots": sorted({m.get("gpu") for m in mod if m.get("gpu")})[:6],
    }
    c = criteria["mechanical"]
    chk = lambda name, ok, val: {"criterion": name, "value": val, "result": "NA" if val is None else ("PASS" if ok else "FAIL")}
    results = [
        chk("valid_output_rate_min", (metrics["valid_output_rate"] or 0) >= c["valid_output_rate_min"], metrics["valid_output_rate"]),
        chk("provider_errors_max", metrics["provider_errors"] <= c["provider_errors_max"], metrics["provider_errors"]),
        chk("gate_downgrade_rate_max", metrics["gate_downgrade_rate"] <= c["gate_downgrade_rate_max"], metrics["gate_downgrade_rate"]),
        chk("unsupported_completeness_penalties_max", metrics["unsupported_completeness_penalties"] <= c["unsupported_completeness_penalties_max"], metrics["unsupported_completeness_penalties"]),
        chk("scored_results_without_derivation_max", metrics["scored_results_without_derivation"] <= c["scored_results_without_derivation_max"], metrics["scored_results_without_derivation"]),
        chk("evidence_claim_ids_not_in_answer_max", metrics["evidence_claim_ids_not_in_answer"] <= c["evidence_claim_ids_not_in_answer_max"], metrics["evidence_claim_ids_not_in_answer"]),
        chk("injection_flagged_claims_used_as_evidence_max", metrics["injection_flagged_claims_used_as_evidence"] <= c["injection_flagged_claims_used_as_evidence_max"], metrics["injection_flagged_claims_used_as_evidence"]),
        chk("abstentions_without_recorded_reason_max", metrics["abstentions_without_recorded_reason"] <= c["abstentions_without_recorded_reason_max"], metrics["abstentions_without_recorded_reason"]),
        chk("abstain_rate_max", metrics["abstain_rate"] <= c["abstain_rate_max"], metrics["abstain_rate"]),
        chk("median_answer_latency_s_max", (metrics["median_answer_latency_s"] or 0) <= c["median_answer_latency_s_max"], metrics["median_answer_latency_s"]),
        chk("max_answer_latency_s_max", (metrics["max_answer_latency_s"] or 0) <= c["max_answer_latency_s_max"], metrics["max_answer_latency_s"]),
        chk("repeat_member_state_agreement_min", (metrics["repeat_member_state_agreement"] or 0) >= c["repeat_member_state_agreement_min"], metrics["repeat_member_state_agreement"]),
        chk("repeat_score_delta_max_points", (metrics["repeat_score_delta_max_points"] or 0) <= c["repeat_score_delta_max_points"], metrics["repeat_score_delta_max_points"] if deltas else None),
    ]
    human = [{"criterion": k, "result": "PENDING_HUMAN"} for k in criteria["needs_human_labels"] if not k.startswith("_")]
    failed = [r["criterion"] for r in results if r["result"] == "FAIL"]
    na = [r["criterion"] for r in results if r["result"] == "NA"]
    dr = criteria["decision_rule"]
    if metrics["partial_run"]:
        decision = "PARTIAL RUN: not the frozen experiment; no decision."
    elif failed:
        decision = dr["any_mechanical_fail"]
    elif na:
        decision = "INCOMPLETE: criteria not measurable (" + ", ".join(na) + "); no decision."
    else:
        decision = dr["all_mechanical_pass_but_no_human_labels"]

    side = []
    for sid in sorted(by):
        e = expectations.get(sid, {}); r0 = by[sid].get(0)
        lg = next((l["result"] for l in leg if l["sample_id"] == sid), None)
        side.append({"sample_id": sid, "question_id": r0.get("question_id"), "ai_provisional_kind": e.get("kind"), "ai_provisional_score_range": [e.get("expected_score_min"), e.get("expected_score_max")],
                     "modular_status": r0["status"], "modular_score": r0["score"], "modular_confidence": r0.get("confidence"),
                     "modular_dims": {d["name"]: d["level"] for d in r0["dimensions"]}, "modular_abstain_reasons": r0["abstain_reasons"],
                     "modular_essential_outcomes": {o["label"]: o["status"] for o in r0["outcomes"] if o["tier"] == "essential"},
                     "legacy_status": lg and lg["evaluation_status"], "legacy_score": lg and lg["provisional_score"],
                     "legacy_completeness_level": lg and lg.get("rubric") and lg["rubric"]["completeness"]["level"], "legacy_missing_concepts": lg and lg["missing_concepts"],
                     "legacy_score_adjustments": lg and lg["score_adjustments"]})
    return {"disclaimer": "Exploratory. n is tiny; AI expectations are provisional and not human-reviewed; nothing here is grading accuracy or human agreement.",
            "metrics": metrics, "mechanical_criteria": results, "human_criteria": human, "decision": decision, "side_by_side_for_reading_only": side}


def to_markdown(a: dict) -> str:
    m = a["metrics"]
    L = ["# Stage 3C-2 analysis (mechanical criteria only)", "", f"> {a['disclaimer']}", "", f"**Decision under the frozen rule:** {a['decision']}", "",
         "## Mechanical criteria", "", "| criterion | value | result |", "|---|---|---|"]
    L += [f"| {r['criterion']} | {r['value']} | {r['result']} |" for r in a["mechanical_criteria"]]
    L += ["", "## Needs human labels", ""] + [f"- {r['criterion']}: {r['result']}" for r in a["human_criteria"]]
    L += ["", "## Metrics", "", "```json", json.dumps({k: v for k, v in m.items() if k != "unsupported_detail"}, indent=1), "```", "",
          "## Side by side (for reading; AI expectations are provisional)", "", "| id | q | AI kind | AI range | modular | score | legacy | score | modular dims | legacy missing |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in a["side_by_side_for_reading_only"]:
        L.append(f"| {s['sample_id']} | {s['question_id']} | {s['ai_provisional_kind']} | {s['ai_provisional_score_range']} | {s['modular_status']} | {s['modular_score']} | {s['legacy_status']} | {s['legacy_score']} | {s['modular_dims']} | {s['legacy_missing_concepts']} |")
    return "\n".join(L) + "\n"


def main(argv):
    p = Path(argv[1])
    doc = json.loads(p.read_text(encoding="utf-8"))
    exp = {json.loads(l)["sample_id"]: json.loads(l) for l in (D / "provisional_ai_expectations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    a = analyze(doc, exp, json.loads((D / "acceptance_criteria.json").read_text(encoding="utf-8")))
    (p.parent / "analysis.json").write_text(json.dumps(a, indent=1, ensure_ascii=False), encoding="utf-8")
    (p.parent / "analysis.md").write_text(to_markdown(a), encoding="utf-8")
    print(to_markdown(a)[:3500])


if __name__ == "__main__":
    main(sys.argv)
