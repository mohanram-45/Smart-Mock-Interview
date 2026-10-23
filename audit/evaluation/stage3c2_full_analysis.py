"""Stage 3C-2.1 full-run analysis (Mission 1). READ-ONLY over the frozen results; writes full_analysis.json / full_analysis.md next to them.

  ../rag_venv/bin/python audit/evaluation/stage3c2_full_analysis.py data/evaluation/stage3c2_results/<run>/results.json

Everything computed here is MECHANICAL or AI-provisional. Nothing is human-validated. The AI expectations are used only to group answers by kind and to
show whether a score falls inside the AI-drafted band ("consistent with the AI expectation"), never as accuracy. No threshold is changed and nothing is
re-scored: the frozen decision stays whatever the frozen rule says."""
import json, re, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
D = ROOT / "data" / "evaluation" / "stage3c2"

from src.evaluation.modular.claims import content_stems            # frozen stemmer, used as-is (its recall limits are part of the finding)
from src.evaluation.modular.review.diagnostics import abstain_taxonomy, verdict_diagnostics, disagreement_report, essential_blockers


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", (s or "").lower())).strip()


def _load(rel):
    return [json.loads(l) for l in (D / rel).read_text(encoding="utf-8").splitlines() if l.strip()]


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def spearman(a, b):
    def rank(x):
        o = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]: j += 1
            for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    if len(a) < 3: return None
    ra, rb = rank(a), rank(b); ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(num / den, 3) if den else None


def analyse(doc, sample, exp, recs, criteria, a2):
    out = {"scope_of_claims": "mechanical + AI-provisional only; NOTHING here is human-validated"}
    mod, leg = doc["modular"], doc["legacy"]
    by = defaultdict(dict)
    for m in mod: by[m["sample_id"]][m["repeat"]] = m
    legacy = {l["sample_id"]: l for l in leg}
    kind = {sid: exp[sid]["kind"] for sid in sample}

    # ------------------------------------------------------------------ 1. grounding (mechanical)
    span_bad, quote_total, quote_found, quote_missing = [], 0, 0, []
    pos_support, neg_support = [], []
    for m in mod:
        sid, r = m["sample_id"], m["result"]
        ans = sample[sid]["answer_text"]; claims = {c["id"]: c for c in r["claims"]}
        rec = recs[sample[sid]["question_id"]]
        refblob = _norm(" ".join([rec.get("canonical_answer") or ""] + list(rec.get("alternative_answers") or []) + [json.dumps(rec.get("key_concepts") or [], ensure_ascii=False),
                                  json.dumps(rec.get("common_mistakes") or [], ensure_ascii=False), json.dumps(rec.get("rubric_points") or [], ensure_ascii=False)]))
        for c in r["claims"]:
            if ans[c["start"]:c["end"]] != c["text"]: span_bad.append((sid, m["repeat"], c["id"]))
        for v in r["verdicts"]:
            for e in v.get("evidence", []):
                c = claims.get(e["claim_id"])
                if c is None or ans[e["start"]:e["end"]] != e["text"]: span_bad.append((sid, m["repeat"], v["requirement_id"], e["claim_id"]))
            q = v.get("reference_quote") or ""
            if q:
                quote_total += 1
                if _norm(q) in refblob: quote_found += 1
                else: quote_missing.append((sid, m["repeat"], v["requirement_id"], q[:100]))
            if v["state"] in ("states_correctly", "states_incorrectly") and v.get("evidence"):
                ms = content_stems(v["member"]) if v["member"] != "__other_valid__" else set()
                cs = set()
                for e in v["evidence"]: cs |= content_stems(e["text"])
                if v["state"] == "states_correctly":
                    share = (len(ms & cs) / len(ms)) if ms else None
                    pos_support.append({"sample_id": sid, "repeat": m["repeat"], "req": v["requirement_id"], "member": v["member"], "share": None if share is None else round(share, 2),
                                        "claim": v["evidence"][0]["text"][:120]})
                else:
                    rq = content_stems(v["member"]) | content_stems(v.get("reference_quote") or "")
                    share = len(rq & cs) / len(rq) if rq else None
                    neg_support.append({"sample_id": sid, "repeat": m["repeat"], "req": v["requirement_id"], "member": v["member"], "tier": next((o["tier"] for o in r["outcomes"] if o["requirement_id"] == v["requirement_id"]), None),
                                        "share": None if share is None else round(share, 2), "claim": v["evidence"][0]["text"][:120], "explanation": (v.get("explanation") or "")[:120]})
    out["grounding"] = {"claim_or_evidence_span_mismatches": span_bad, "reference_quotes_total": quote_total, "reference_quotes_found_in_reference": quote_found,
                        "reference_quotes_not_found": quote_missing,
                        "positive_credit_verdicts": len(pos_support), "positive_credit_with_zero_member_stem_support": [p for p in pos_support if p["share"] == 0.0],
                        "positive_credit_with_partial_support_lt_half": [p for p in pos_support if p["share"] is not None and 0 < p["share"] < 0.5],
                        "negative_verdicts": len(neg_support), "negative_with_zero_overlap_to_member_or_quote": [p for p in neg_support if p["share"] == 0.0]}

    # ------------------------------------------------------------------ 2. per-answer table + categories
    rows = []
    for sid in sample:
        r0, r1 = by[sid][0]["result"], by[sid][1]["result"]; l = legacy[sid]["result"]
        lo, hi = exp[sid].get("expected_score_min"), exp[sid].get("expected_score_max")
        mods = [r0["score"], r1["score"]]
        inband = lambda s: None if (s is None or lo is None) else (lo <= s <= hi)
        rows.append({"sample_id": sid, "question_id": sample[sid]["question_id"], "kind": kind[sid], "ai_band": [lo, hi],
                     "modular_r0": r0["score"], "modular_r1": r1["score"], "modular_status": [r0["status"], r1["status"]], "modular_mean": _mean(mods),
                     "legacy": l["provisional_score"], "legacy_status": l["evaluation_status"], "legacy_conf": l["confidence"],
                     "modular_in_ai_band": [inband(s) for s in mods], "legacy_in_ai_band": inband(l["provisional_score"]),
                     "legacy_missing": l["missing_concepts"], "legacy_errors": [e["claim_quote"][:80] for e in l["factual_errors"]]})
    out["per_answer"] = rows
    cat = {}
    for k in sorted(set(kind.values())):
        rs = [x for x in rows if x["kind"] == k]
        cat[k] = {"answers": len(rs), "ids": [x["sample_id"] for x in rs],
                  "modular_scored_rows": sum(s == "scored" for x in rs for s in x["modular_status"]), "modular_abstained_rows": sum(s == "abstained" for x in rs for s in x["modular_status"]),
                  "modular_scores": [[x["modular_r0"], x["modular_r1"]] for x in rs], "legacy_scores": [x["legacy"] for x in rs]}
    out["by_kind"] = cat

    # ------------------------------------------------------------------ 3. modular vs legacy on matched answers
    both = [x for x in rows if x["modular_mean"] is not None and x["legacy"] is not None and x["modular_status"] == ["scored", "scored"]]
    diffs = [x["modular_mean"] - x["legacy"] for x in both]
    out["modular_vs_legacy"] = {
        "answers_both_scored_in_both_repeats": [x["sample_id"] for x in both], "n": len(both),
        "mean_signed_diff_modular_minus_legacy": _mean(diffs), "mean_abs_diff": _mean([abs(d) for d in diffs]),
        "modular_higher": sum(d > 0 for d in diffs), "legacy_higher": sum(d < 0 for d in diffs), "equal": sum(d == 0 for d in diffs),
        "spearman_rank_correlation": spearman([x["modular_mean"] for x in both], [x["legacy"] for x in both]),
        "legacy_graded_all_20": sum(x["legacy_status"] in ("graded", "graded_low_confidence") for x in rows),
        "legacy_low_confidence": sum(x["legacy_status"] == "graded_low_confidence" for x in rows),
        "modular_abstained_in_at_least_one_repeat": [x["sample_id"] for x in rows if "abstained" in x["modular_status"]],
        "legacy_score_on_modular_abstentions": {x["sample_id"]: x["legacy"] for x in rows if "abstained" in x["modular_status"]},
        "caveat": "No human score exists; 'higher' is not 'more accurate'."}

    # ------------------------------------------------------------------ 4. consistency with the AI-provisional band (NOT accuracy)
    def band(sysname):
        n = hit = 0; over = []; under = []
        for x in rows:
            vals = [x["modular_r0"], x["modular_r1"]] if sysname == "modular" else [x["legacy"]]
            for s in vals:
                if s is None or x["ai_band"][0] is None: continue
                n += 1; ok = x["ai_band"][0] <= s <= x["ai_band"][1]; hit += ok
                if s > x["ai_band"][1]: over.append((x["sample_id"], s, x["ai_band"]))
                if s < x["ai_band"][0]: under.append((x["sample_id"], s, x["ai_band"]))
        return {"numeric_scores_compared": n, "inside_ai_band": hit, "above_band": over, "below_band": under}
    out["ai_provisional_band_consistency"] = {"label": "AI-authored provisional bands; consistency with them is NOT grading accuracy", "modular": band("modular"), "legacy": band("legacy")}

    # ------------------------------------------------------------------ 5. abstention taxonomy + blockers
    tax = []
    for m in mod:
        r = m["result"]
        if r["status"] != "scored":
            tax.append({"sample_id": m["sample_id"], "repeat": m["repeat"], "kind": kind[m["sample_id"]], **abstain_taxonomy(r)})
    out["abstention_taxonomy"] = tax
    out["abstention_primary_cause_counts"] = dict(Counter(t["primary"] for t in tax))
    out["abstention_by_kind"] = {k: dict(Counter(t["primary"] for t in tax if t["kind"] == k)) for k in sorted({t["kind"] for t in tax})}

    # ------------------------------------------------------------------ 6. verdict diagnostics (all downgrades, with the evidence the gate looked at)
    diag = []
    for m in mod:
        for d in verdict_diagnostics(m["result"], m.get("verifier_trace")):
            diag.append({"sample_id": m["sample_id"], "repeat": m["repeat"], **d})
    out["downgrade_diagnostics"] = [d for d in diag if d["downgrade_reason"]]
    out["model_unverified_diagnostics"] = [d for d in diag if d["origin"] == "model_unverified"]
    out["repeat_disagreements"] = disagreement_report({sid: {rep: m["result"] for rep, m in reps.items()} for sid, reps in by.items()})

    # ------------------------------------------------------------------ 7. on-topic flag reliability
    ot = []
    for m in mod:
        raw = json.loads(m["verifier_trace"][0]["raw"]); rel = next(q for q in m["result"]["dimensions"] if q["name"] == "relevance")
        ot.append({"sample_id": m["sample_id"], "repeat": m["repeat"], "kind": kind[m["sample_id"]], "model_on_topic": raw.get("on_topic"), "lexical_overlap": rel["inputs"].get("lexical_overlap"), "relevance_level": rel["level"]})
    wrong_off = [o for o in ot if o["model_on_topic"] == "off_topic" and o["kind"] != "off_topic"]
    out["on_topic_flag"] = {"rows": len(ot), "model_said_off_topic_for_answers_not_labelled_off_topic": wrong_off,
                            "true_off_topic_rows_flagged": [o for o in ot if o["kind"] == "off_topic" and o["model_on_topic"] == "off_topic"]}

    # ------------------------------------------------------------------ 8. reasoning dimension (model must tag a reasoning claim)
    rs = []
    for m in mod:
        rd = next(q for q in m["result"]["dimensions"] if q["name"] == "reasoning")
        rs.append({"sample_id": m["sample_id"], "repeat": m["repeat"], "level": rd["level"], "expected": rd["inputs"].get("expected"), "derivation": rd["derivation"]})
    out["reasoning_dimension"] = {"rows": rs, "expected_but_level_le_1": [r for r in rs if r["expected"] and r["level"] is not None and r["level"] <= 1],
                                  "full_marks_by_convention": sum(1 for r in rs if r["expected"] is False and r["level"] == 4)}

    # ------------------------------------------------------------------ 9. latency & resources (from the run, incl. cold-call detection done by analyze_v2)
    out["frozen_criteria_result"] = {"decision": a2.get("decision"), "criteria": a2.get("criteria")}
    out["run_facts"] = {k: doc["meta"].get(k) for k in ("started_utc", "finished_utc", "total_wall_s", "model_load_s", "ollama_version", "platform", "freeze_manifest_sha256", "partial_run")}
    return out


def md(a):
    L = ["# Stage 3C-2.1 full-run analysis (mechanical + AI-provisional; NOT human-validated)", ""]
    L += ["## Run", "```", json.dumps(a["run_facts"], indent=1), "```", ""]
    fc = a["frozen_criteria_result"]
    L += ["## Frozen decision", "", str(fc.get("decision")), ""]
    L += ["## Per answer", "", "| id | kind | AI band | modular r0/r1 | legacy (conf) | modular in AI band | legacy in AI band |", "|---|---|---|---|---|---|---|"]
    for x in a["per_answer"]:
        L.append(f"| {x['sample_id']} | {x['kind']} | {x['ai_band']} | {x['modular_r0']} / {x['modular_r1']} ({'/'.join(s[:3] for s in x['modular_status'])}) | {x['legacy']} ({x['legacy_conf']}) | {x['modular_in_ai_band']} | {x['legacy_in_ai_band']} |")
    L += ["", "## Modular vs legacy (matched)", "```", json.dumps(a["modular_vs_legacy"], indent=1), "```", ""]
    L += ["## AI-band consistency (NOT accuracy)", "```", json.dumps(a["ai_provisional_band_consistency"], indent=1), "```", ""]
    L += ["## Abstention causes", "", "```", json.dumps({"primary": a["abstention_primary_cause_counts"], "by_kind": a["abstention_by_kind"]}, indent=1), "```", ""]
    L += ["| id | rep | kind | primary | blockers |", "|---|---|---|---|---|"]
    for t in a["abstention_taxonomy"]:
        L.append(f"| {t['sample_id']} | {t['repeat']} | {t['kind']} | {t['primary']} | {'; '.join(f'{b['requirement_id']}:{b['origin']}' for b in t['blockers'])} |")
    L += ["", "## Grounding", "```", json.dumps({k: (v if not isinstance(v, list) else v[:12]) for k, v in a["grounding"].items()}, indent=1, ensure_ascii=False), "```", ""]
    L += ["## On-topic flag", "```", json.dumps(a["on_topic_flag"], indent=1), "```", ""]
    L += ["## Reasoning dimension", "```", json.dumps({k: v for k, v in a["reasoning_dimension"].items() if k != "rows"}, indent=1), "```", ""]
    L += ["## Repeat disagreements", "```", json.dumps(a["repeat_disagreements"], indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(L)


def main(argv=None):
    path = Path((argv or sys.argv[1:])[0])
    doc = json.loads(path.read_text(encoding="utf-8"))
    sample = {s["sample_id"]: s for s in _load("sample.jsonl")}; exp = {e["sample_id"]: e for e in _load("provisional_ai_expectations.jsonl")}
    from src.retrieval.corpus import load_corpus
    recs = {r["question_id"]: r for r in load_corpus()["records"]}
    criteria = json.loads((D / "acceptance_criteria.json").read_text(encoding="utf-8"))
    a2p = path.parent / "analysis_v2.json"
    a2 = json.loads(a2p.read_text(encoding="utf-8")) if a2p.exists() else {}
    res = analyse(doc, sample, exp, recs, criteria, a2)
    (path.parent / "full_analysis.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (path.parent / "full_analysis.md").write_text(md(res), encoding="utf-8")
    print("wrote", path.parent / "full_analysis.json", "and .md")


if __name__ == "__main__":
    main()
