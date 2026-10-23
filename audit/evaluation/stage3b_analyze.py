"""Stage 3B analysis: compares recorded model outputs with the SEPARATE expectations file.

    python audit/evaluation/stage3b_analyze.py data/evaluation/stage3b/runs_<model>.json

Every expectation is AI-authored (Claude) and unreviewed by humans: agreement here is agreement with those labels, NOT accuracy
against ground truth. Keyword matching for errors/concepts is a rough heuristic and is reported as such. The review sheet CSV has
blank columns for YOUR judgment, which is the only human signal in this stage.
"""
import csv, json, re, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "data" / "evaluation" / "bench_v1"
SCORED = {"graded", "graded_low_confidence"}


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def pct(x, n):
    return None if not n else round(100 * x / n, 1)


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9²]+", " ", (s or "").lower()).split())


def match_concept(expected, found_list):
    e = norm(expected)
    toks = [t for t in e.split() if len(t) > 3] or e.split()
    for f in found_list:
        n = norm(f)
        if e in n or n in e or (toks and all(any(t[:5] == w[:5] for w in n.split()) for t in toks)):
            return True
    return False


def leaked(text, ref):
    from src.evaluation.evaluator import AnswerEvaluator
    return bool(text and ref and AnswerEvaluator._copies_reference(text, ref, window=60))


def q(vals, p):
    v = sorted(vals)
    return None if not v else v[min(len(v) - 1, int(p * len(v)))]


def main(path):
    from src.retrieval.corpus import load_corpus
    runs = json.loads(Path(path).read_text(encoding="utf-8"))
    meta, rs = runs["meta"], runs["runs"]
    items = {i["item_id"]: i for i in jl(BENCH / "items.jsonl")}
    exps = {e["item_id"]: e for e in jl(BENCH / "expectations.jsonl")}
    recs = {r["question_id"]: r for r in load_corpus()["records"]}
    main_runs = [r for r in rs if r["temperature"] == 0.0]
    stress = [r for r in rs if r["temperature"] != 0.0]
    A = {"meta": meta, "n_calls": len(rs), "n_temp0_calls": len(main_runs), "n_stress_calls": len(stress),
         "label_provenance": "expectations are AI-authored (Claude), unreviewed by humans; NOT ground truth"}
    if meta.get("is_mock"):
        print("\n" + "!" * 70 + "\n MOCK SELFTEST DATA: these numbers say NOTHING about any real model.\n" + "!" * 70)

    # ---- status / schema
    st = Counter(r["result"]["evaluation_status"] for r in main_runs)
    reached_model = [r for r in main_runs if r["result"]["provenance"]["attempts"] > 0]
    scored = [r for r in reached_model if r["result"]["evaluation_status"] in SCORED]
    first_try = [r for r in reached_model if r["result"]["provenance"]["attempts"] == 1 and r["result"]["evaluation_status"] not in ("provider_error", "invalid_response")]
    A["status_counts"] = dict(st)
    A["schema"] = {"calls_that_reached_the_model": len(reached_model), "valid_on_first_attempt": len(first_try),
                   "valid_on_first_attempt_pct": pct(len(first_try), len(reached_model)),
                   "needed_repair": sum(1 for r in reached_model if r["result"]["provenance"]["attempts"] > 1 and r["result"]["evaluation_status"] not in ("provider_error", "invalid_response")),
                   "invalid_response": st.get("invalid_response", 0), "provider_error": st.get("provider_error", 0),
                   "errors": Counter((r["result"].get("error") or {}).get("code") for r in main_runs if r["result"].get("error"))}
    A["schema"]["errors"] = dict(A["schema"]["errors"])

    # ---- status expectations
    ok = bad = 0; status_miss = []
    for r in main_runs:
        e = exps[r["item_id"]]; s = r["result"]["evaluation_status"]
        if s in e["expected_status_in"]: ok += 1
        else: bad += 1; status_miss.append({"item": r["item_id"], "got": s, "expected": e["expected_status_in"], "category": e["category"]})
    A["status_vs_expectation"] = {"match": ok, "mismatch": bad, "mismatches": status_miss}

    # ---- score vs expected band
    by_cat = defaultdict(lambda: {"n": 0, "in_range": 0, "below": 0, "above": 0, "scores": []})
    off = []
    for r in scored:
        e = exps[r["item_id"]]
        if e["score_min"] is None: continue
        s = r["result"]["provisional_score"]; c = by_cat[e["category"]]
        c["n"] += 1; c["scores"].append(s)
        if s < e["score_min"]: c["below"] += 1; off.append({"item": r["item_id"], "cat": e["category"], "score": s, "expected": [e["score_min"], e["score_max"]], "dir": "below"})
        elif s > e["score_max"]: c["above"] += 1; off.append({"item": r["item_id"], "cat": e["category"], "score": s, "expected": [e["score_min"], e["score_max"]], "dir": "above"})
        else: c["in_range"] += 1
    A["score_vs_expected_band"] = {k: {"n": v["n"], "in_range": v["in_range"], "below": v["below"], "above": v["above"], "mean_score": round(statistics.mean(v["scores"]), 1) if v["scores"] else None} for k, v in sorted(by_cat.items())}
    tot = sum(v["n"] for v in by_cat.values()); inr = sum(v["in_range"] for v in by_cat.values())
    A["score_in_band_overall"] = {"n": tot, "in_band": inr, "pct": pct(inr, tot)}
    A["out_of_band"] = off

    # ---- factual-error detection and false penalties
    seeded = [r for r in scored if exps[r["item_id"]]["seeded_errors"]]
    det_item = det_spec = spec_total = 0; missed = []
    for r in seeded:
        fe = r["result"]["factual_errors"]
        if fe: det_item += 1
        else: missed.append(r["item_id"])
        for s in exps[r["item_id"]]["seeded_errors"]:
            spec_total += 1
            if any(any(k.lower() in (f["claim_quote"] + " " + f["explanation"]).lower() for k in s["probe_keywords"]) for f in fe): det_spec += 1
    clean = [r for r in scored if exps[r["item_id"]]["no_errors_expected"]]
    fp_any = [r["item_id"] for r in clean if r["result"]["factual_errors"]]
    fp_major = [r["item_id"] for r in clean if any(f["severity"] == "major" for f in r["result"]["factual_errors"])]
    A["factual_errors"] = {"items_with_seeded_errors": len(seeded), "item_level_detection": det_item, "item_level_detection_pct": pct(det_item, len(seeded)),
                           "specific_error_matched_by_keyword_heuristic": det_spec, "specific_total": spec_total, "missed_items": missed,
                           "clean_items": len(clean), "false_error_flags_any": len(fp_any), "false_error_flags_major": len(fp_major),
                           "false_flag_items": fp_any}
    fpen = [r for r in clean if exps[r["item_id"]]["category"] in ("valid_alternative", "correct", "short_sufficient") and r["result"]["provisional_score"] < exps[r["item_id"]]["score_min"]]
    alt = [r for r in clean if exps[r["item_id"]]["category"] == "valid_alternative"]
    A["false_penalties"] = {"correct_alt_short_items_scored_below_band": [(r["item_id"], r["result"]["provisional_score"]) for r in fpen],
                            "valid_alternative_n": len(alt), "valid_alternative_below_band": sum(1 for r in alt if r["result"]["provisional_score"] < exps[r["item_id"]]["score_min"])}

    # ---- missing / demonstrated concepts
    me = mf = de = df = 0; extra_missing = 0
    for r in scored:
        e = exps[r["item_id"]]; res = r["result"]
        for c in e["expected_missing_concepts"]:
            me += 1; mf += match_concept(c, res["missing_concepts"])
        for c in e["expected_demonstrated_concepts"]:
            de += 1; df += match_concept(c, [x["concept"] for x in res["correct_concepts"]])
        for c in e["expected_demonstrated_concepts"]:
            if match_concept(c, res["missing_concepts"]): extra_missing += 1
    A["concepts"] = {"expected_missing": me, "found_missing": mf, "missing_recall_pct": pct(mf, me), "expected_demonstrated": de, "found_demonstrated": df,
                     "demonstrated_recall_pct": pct(df, de), "demonstrated_concepts_wrongly_listed_missing": extra_missing,
                     "note": "fuzzy keyword matching; small counts"}

    # ---- evidence verification
    dropped = Counter(); claimed_total = 0
    for r in scored:
        d = r["result"]["flags"].get("dropped_unverifiable", {})
        for k, v in d.items(): dropped[k] += v
    kept = sum(len(r["result"]["correct_concepts"]) + len(r["result"]["factual_errors"]) + len(r["result"]["supporting_evidence"]) for r in scored)
    A["evidence"] = {"dropped_unverifiable": dict(dropped), "kept": kept, "dropped_share_pct": pct(sum(dropped.values()), sum(dropped.values()) + kept)}

    # ---- rubric consistency (model contradicting itself -> code adjusted)
    adj = [r["item_id"] for r in scored if r["result"]["score_adjustments"]]
    cap30 = [r["item_id"] for r in scored if any("verifiable" in a for a in r["result"]["score_adjustments"])]
    A["rubric_consistency"] = {"scored_calls": len(scored), "calls_needing_code_adjustment": len(adj), "adjustment_pct": pct(len(adj), len(scored)),
                               "unsupported_credit_cap_triggered": len(cap30), "items": sorted(set(adj))}

    # ---- repeat consistency (temperature 0 repeats, then stress)
    def consistency(rr):
        g = defaultdict(list)
        for r in rr:
            g[r["item_id"]].append(r["result"])
        rows = []
        for iid, lst in g.items():
            if len(lst) < 2: continue
            sc = [x["provisional_score"] for x in lst if x["provisional_score"] is not None]
            rows.append({"item": iid, "n": len(lst), "scores": sc, "range": (max(sc) - min(sc)) if len(sc) > 1 else 0,
                         "sd": round(statistics.pstdev(sc), 2) if len(sc) > 1 else 0, "status_flip": len({x["evaluation_status"] for x in lst}) > 1,
                         "error_flag_flip": len({bool(x["factual_errors"]) for x in lst}) > 1})
        return rows
    for name, rr in (("repeat_consistency_temp0", main_runs), ("repeat_consistency_stress", stress)):
        rows = consistency(rr)
        A[name] = {"items_with_repeats": len(rows), "mean_sd": round(statistics.mean(x["sd"] for x in rows), 2) if rows else None,
                   "max_range": max((x["range"] for x in rows), default=None), "items_range_gt10": [x["item"] for x in rows if x["range"] > 10],
                   "status_flips": [x["item"] for x in rows if x["status_flip"]], "error_flag_flips": [x["item"] for x in rows if x["error_flag_flip"]]}

    # ---- injection
    inj = []
    for r in main_runs:
        e = exps[r["item_id"]]
        if not e["injection_present"]: continue
        res = r["result"]; ref = recs[items[r["item_id"]]["question_id"]]["canonical_answer"]
        texts = [res["improved_example_answer"], res["score_rationale"], res["follow_up_question"], " ".join(res["strengths"]), " ".join(res["improvement_suggestions"])]
        lv = [res["rubric"][k]["level"] for k in ("correctness", "completeness", "relevance", "reasoning")] if res["rubric"] else None
        inj.append({"item": r["item_id"], "repeat": r["repeat"], "status": res["evaluation_status"], "score": res["provisional_score"], "expected": [e["score_min"], e["score_max"]],
                    "within_expected": res["provisional_score"] is not None and e["score_min"] <= res["provisional_score"] <= e["score_max"],
                    "injection_flagged": res["flags"].get("injection_suspected"), "reference_leaked": any(leaked(t, ref) for t in texts),
                    "all_levels_4": lv == [4, 4, 4, 4], "confidence": res["confidence"]})
    A["injection"] = {"calls": len(inj), "details": inj, "obeyed_or_leaked": [d for d in inj if d["reference_leaked"] or d["all_levels_4"] or (d["score"] is not None and d["score"] > d["expected"][1])]}

    # reference leak anywhere in the benchmark (not only injection items)
    leaks = []
    for r in main_runs:
        res = r["result"]; ref = recs[items[r["item_id"]]["question_id"]]["canonical_answer"]
        if any(leaked(t, ref) for t in (res["improved_example_answer"], res["score_rationale"])): leaks.append(r["item_id"])
    A["reference_copied_into_output_items"] = sorted(set(leaks))

    # ---- confidence on weak-reference item
    wk = [r for r in scored if exps[r["item_id"]]["confidence_must_not_be_high"]]
    A["weak_reference_confidence"] = [(r["item_id"], r["result"]["confidence"]) for r in wk]
    A["confidence_distribution"] = dict(Counter(r["result"]["confidence"] for r in scored))

    # ---- latency / resources
    ms = [r["wall_ms"] for r in reached_model]
    toks = [(r["provider_log"][-1]["usage"] or {}) for r in reached_model if r["provider_log"] and r["provider_log"][-1].get("ok")]
    tps = [u["eval_count"] / (u["eval_duration"] / 1e9) for u in toks if u.get("eval_count") and u.get("eval_duration")]
    pe = [u["prompt_eval_count"] for u in toks if u.get("prompt_eval_count")]
    nctx = meta.get("num_ctx") or 0
    A["latency_and_resources"] = {"calls": len(ms), "wall_s_median": round(q(ms, .5) / 1000, 1) if ms else None, "wall_s_p90": round(q(ms, .9) / 1000, 1) if ms else None,
                                  "wall_s_max": round(max(ms) / 1000, 1) if ms else None, "total_minutes": round(sum(ms) / 60000, 1),
                                  "output_tokens_per_s_median": round(statistics.median(tps), 1) if tps else None,
                                  "prompt_tokens_median": statistics.median(pe) if pe else None, "prompt_tokens_max": max(pe) if pe else None,
                                  "possible_context_truncation_calls": sum(1 for p in pe if nctx and p >= nctx * 0.98),
                                  "ollama_ps_after_first_call": next((r.get("ollama_ps_after_first_call") for r in rs if r.get("ollama_ps_after_first_call")), None),
                                  "cost": "0 (local model); hosted/paid APIs not used"}
    out = Path(path).with_name(Path(path).stem.replace("runs_", "analysis_") + ".json")
    out.write_text(json.dumps(A, indent=1, ensure_ascii=False), encoding="utf-8")

    # ---- human review sheet (blank columns are for Mohan)
    sheet = Path(path).with_name(Path(path).stem.replace("runs_", "review_sheet_") + ".csv")
    with open(sheet, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "category", "question_id", "question", "candidate_answer", "ai_expected_score_band", "model_status", "model_score", "model_confidence",
                    "model_rationale", "factual_errors_flagged", "missing_concepts", "improvement_suggestions", "follow_up", "HUMAN_score_reasonable(y/n)", "HUMAN_feedback_quality(1-5)", "HUMAN_notes"])
        for r in main_runs:
            if r["repeat"] != 0: continue
            it, e, res = items[r["item_id"]], exps[r["item_id"]], r["result"]
            w.writerow([it["item_id"], it["category"], it["question_id"], recs[it["question_id"]]["question"], it["candidate_answer"], f"{e['score_min']}-{e['score_max']}",
                        res["evaluation_status"], res["provisional_score"], res["confidence"], res["score_rationale"],
                        " | ".join(f"{x['severity']}: {x['claim_quote']} -> {x['explanation']}" for x in res["factual_errors"]), " | ".join(res["missing_concepts"]),
                        " | ".join(res["improvement_suggestions"]), res["follow_up_question"], "", "", ""])

    # ---- print summary
    S = A
    print(f"\nMODEL {meta['model']}  mock={meta.get('is_mock')}  calls={S['n_calls']} (temp0 {S['n_temp0_calls']}, stress {S['n_stress_calls']})")
    print("status:", S["status_counts"])
    print("schema:", {k: S['schema'][k] for k in ('calls_that_reached_the_model', 'valid_on_first_attempt_pct', 'needed_repair', 'invalid_response', 'provider_error')})
    print("status vs AI-expectation:", S["status_vs_expectation"]["match"], "match /", S["status_vs_expectation"]["mismatch"], "mismatch", S["status_vs_expectation"]["mismatches"])
    print("score in AI-expected band:", S["score_in_band_overall"])
    for k, v in S["score_vs_expected_band"].items(): print("  ", k, v)
    print("factual errors:", {k: v for k, v in S["factual_errors"].items() if k != "false_flag_items"}, "false-flag items:", S["factual_errors"]["false_flag_items"])
    print("false penalties:", S["false_penalties"])
    print("concepts:", S["concepts"])
    print("evidence dropped:", S["evidence"])
    print("rubric consistency:", S["rubric_consistency"])
    print("consistency t0:", S["repeat_consistency_temp0"]); print("consistency stress:", S["repeat_consistency_stress"])
    print("injection obeyed/leaked:", S["injection"]["obeyed_or_leaked"], "of", S["injection"]["calls"], "calls; flagged:", [d["injection_flagged"] for d in S["injection"]["details"]])
    print("reference copied into outputs:", S["reference_copied_into_output_items"])
    print("weak-reference confidence:", S["weak_reference_confidence"], "dist:", S["confidence_distribution"])
    print("latency/resources:", S["latency_and_resources"])
    print("\nwritten:", out, "\n         ", sheet)


if __name__ == "__main__":
    main(sys.argv[1])
