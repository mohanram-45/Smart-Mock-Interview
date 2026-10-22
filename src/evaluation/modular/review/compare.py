"""Import completed human-review sheets and compare the modular evaluator and the legacy evaluator against the HUMAN judgement.

Everything computed here that uses a human label is labelled HUMAN-VALIDATED (with the number of reviewers). Nothing here changes a frozen criterion: the five
`needs_human_labels` criteria are evaluated with the definitions pre-registered below, written BEFORE any human label exists.

Pre-registered definitions (a requirement-level "judgement" pairs the modular outcome for one essential requirement with the human's per-requirement call):
  false_credit_rate                 modular states_correctly where the human says not_stated / stated_incorrectly  /  modular states_correctly with a human call
  false_error_rate                  modular states_incorrectly where the human says stated_correctly  /  modular states_incorrectly with a human call
  essential_missing_contradicted    modular essential outcome 'missing' (not_stated) where the human says the requirement WAS stated (correctly or not)   [must be 0]
  credit_rate_on_human_correct      among answers the human rates technical_correctness=correct (and, when AI kinds are supplied, whose AI kind is concise_sufficient or
                                    valid_alternative): modular states_correctly / requirements the human says were stated_correctly
  modular_unsupported_penalties     modular (essential missing contradicted + false errors) must be <= legacy's (legacy missing concepts that match a requirement the human
                                    says was stated + legacy factual errors on answers the human rates correct); legacy matching is lexical and therefore approximate
Score-level "false credit" / "false penalty" are descriptive: a system score at least 15 points above / below the human consensus score."""
from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..lexnorm import content_stems_v31
from .recovery import atomic_write_text

SCORE_GAP = 15
H_STATES = ("stated_correctly", "stated_incorrectly", "not_stated")
_SYN = {"stated_correctly": "stated_correctly", "correct": "stated_correctly", "stated correctly": "stated_correctly", "yes": "stated_correctly", "ok": "stated_correctly",
        "stated_incorrectly": "stated_incorrectly", "incorrect": "stated_incorrectly", "stated incorrectly": "stated_incorrectly", "wrong": "stated_incorrectly",
        "not_stated": "not_stated", "not stated": "not_stated", "missing": "not_stated", "absent": "not_stated", "no": "not_stated"}
_TECH = {"correct", "partly_correct", "incorrect", "cannot_judge"}
_COMP = {"complete", "partial", "minimal", "cannot_judge"}


# ------------------------------------------------------------------------------------------------------------- import
def _col(header: List[str], prefix: str) -> Optional[int]:
    for i, h in enumerate(header):
        if h.strip().lower().startswith(prefix):
            return i
    return None


def parse_requirement_judgements(cell: str) -> Tuple[Dict[str, str], List[str]]:
    out, bad = {}, []
    for part in re.split(r"[\n;]+", cell or ""):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([EGS]\d+)\s*[:=\-]\s*([A-Za-z_ ]+)", part)
        if not m:
            bad.append(part); continue
        st = _SYN.get(re.sub(r"\s+", " ", m.group(2).strip().lower()).replace("  ", " "))
        if st is None:
            bad.append(part); continue
        out[m.group(1)] = st
    return out, bad


def import_human_sheets(paths: Iterable[Path]) -> Dict[str, Any]:
    """Read one or more completed blind sheets. Returns {reviews: {review_id: [review,...]}, problems: [...], rows_read, rows_incomplete}. Never guesses: an
    unreadable or out-of-range cell is reported and left empty."""
    reviews: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    problems, rows, incomplete = [], 0, 0
    for p in map(Path, paths):
        with open(p, encoding="utf-8-sig", newline="") as f:
            rd = csv.reader(f)
            header = next(rd)
            ix = {k: _col(header, k) for k in ("review_id", "technical_correctness", "completeness", "requirement_judgements", "reviewer_score_0_100", "reviewer_comments", "reviewer_id")}
            if ix["review_id"] is None or ix["reviewer_score_0_100"] is None:
                problems.append(f"{p.name}: header lacks review_id / reviewer_score_0_100"); continue
            for n, r in enumerate(rd, 2):
                if not r or not r[ix["review_id"]].strip():
                    continue
                rows += 1
                get = lambda k: (r[ix[k]].strip() if ix[k] is not None and ix[k] < len(r) else "")
                rid = get("review_id")
                rec: Dict[str, Any] = {"review_id": rid, "reviewer_id": get("reviewer_id") or p.stem, "file": p.name, "comments": get("reviewer_comments")}
                s = get("reviewer_score_0_100")
                try:
                    v = float(s) if s != "" else None
                    if v is not None and not 0 <= v <= 100:
                        problems.append(f"{p.name} row {n} ({rid}): score {s} outside 0-100"); v = None
                except ValueError:
                    problems.append(f"{p.name} row {n} ({rid}): score {s!r} is not a number"); v = None
                rec["score"] = v
                for k, allowed in (("technical_correctness", _TECH), ("completeness", _COMP)):
                    x = get(k).lower().replace(" ", "_")
                    if x and x not in allowed:
                        problems.append(f"{p.name} row {n} ({rid}): {k} {x!r} not in {sorted(allowed)}"); x = ""
                    rec["tech" if k.startswith("tech") else "comp"] = x or None
                req, bad = parse_requirement_judgements(get("requirement_judgements"))
                problems += [f"{p.name} row {n} ({rid}): cannot read requirement judgement {b!r}" for b in bad]
                rec["req"] = req
                if rec["score"] is None and rec["tech"] is None and not req:
                    incomplete += 1; continue
                if rec["score"] is None:
                    incomplete += 1
                reviews[rid].append(rec)
    return {"reviews": dict(reviews), "problems": problems, "rows_read": rows, "rows_incomplete": incomplete}


def consensus(reviews: Dict[str, List[Dict[str, Any]]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """One record per review_id: mean score, majority categorical (ties -> None), per-requirement majority. Also inter-reviewer agreement when >= 2 reviewers."""
    out, spreads, tech_agree, tech_n = {}, [], 0, 0
    for rid, rs in reviews.items():
        scores = [r["score"] for r in rs if r["score"] is not None]
        techs = [r["tech"] for r in rs if r["tech"]]
        req: Dict[str, str] = {}
        for k in {k for r in rs for k in r["req"]}:
            c = Counter(r["req"][k] for r in rs if k in r["req"]).most_common()
            req[k] = c[0][0] if len(c) == 1 or c[0][1] > c[1][1] else None       # a tie is not guessed
        tc = Counter(techs).most_common()
        out[rid] = {"score": round(statistics.mean(scores), 1) if scores else None, "tech": (tc[0][0] if tc and (len(tc) == 1 or tc[0][1] > tc[1][1]) else None),
                    "req": {k: v for k, v in req.items() if v}, "n_reviewers": len(rs), "score_spread": (max(scores) - min(scores)) if len(scores) > 1 else None,
                    "reviewers_disagree": bool(len(scores) > 1 and max(scores) - min(scores) > SCORE_GAP), "comments": " | ".join(r["comments"] for r in rs if r["comments"])}
        if len(scores) > 1: spreads.append(max(scores) - min(scores))
        if len(techs) > 1: tech_n += 1; tech_agree += len(set(techs)) == 1
    inter = {"items_with_multiple_reviewers": len(spreads), "mean_score_spread": round(statistics.mean(spreads), 1) if spreads else None,
             "max_score_spread": max(spreads) if spreads else None, "technical_correctness_agreement": round(tech_agree / tech_n, 3) if tech_n else None}
    return out, inter


# ------------------------------------------------------------------------------------------------------------- helpers
def _spearman(a: List[float], b: List[float]) -> Optional[float]:
    if len(a) < 3:
        return None
    def rank(x):
        o = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]: j += 1
            for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = rank(a), rank(b); ma, mb = statistics.mean(ra), statistics.mean(rb)
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / den, 3) if den else None


def outcome_state(o: Dict[str, Any]) -> str:
    """Modular outcome -> the same vocabulary as a verdict state."""
    st = o["status"]
    if o["kind"] == "concept":
        return (o.get("detail") or {}).get("state") or {"satisfied": "states_correctly", "missing": "not_stated", "incorrect": "states_incorrectly", "undetermined": "unverified", "not_demonstrated": "not_stated"}[st]
    return {"satisfied": "states_correctly", "missing": "not_stated", "incorrect": "states_incorrectly", "undetermined": "unverified", "not_demonstrated": "not_stated"}.get(st, "unverified")


def _rate(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


def _score_block(pairs: List[Tuple[float, Optional[float]]], ranges: Optional[List[Any]] = None) -> Dict[str, Any]:
    """pairs = (human score, system score or None when it abstained)."""
    scored = [(h, s) for h, s in pairs if s is not None]
    abst = [h for h, s in pairs if s is None]
    d = [s - h for h, s in scored]
    out = {"answers": len(pairs), "scored": len(scored), "abstained": len(abst),
           "mean_abs_error": round(statistics.mean(abs(x) for x in d), 1) if d else None, "mean_signed_error": round(statistics.mean(d), 1) if d else None,
           "within_10": sum(abs(x) <= 10 for x in d), "within_15": sum(abs(x) <= 15 for x in d),
           "inflated_ge15": sum(x >= SCORE_GAP for x in d), "deflated_ge15": sum(x <= -SCORE_GAP for x in d),
           "spearman": _spearman([h for h, _ in scored], [s for _, s in scored]),
           "abstained_human_scores": sorted(abst)}
    if ranges is not None:
        inside = [r is not None and r[0] <= h <= r[1] for (h, s), r in zip(pairs, ranges) if s is None]
        has = [r is not None for (h, s), r in zip(pairs, ranges) if s is None]
        out["abstained_with_range"] = sum(has); out["abstained_range_contains_human"] = sum(inside)
    return out


def _legacy_matches(legacy_missing: List[str], label: str, members: Iterable[str] = ()) -> bool:
    ls = content_stems_v31(label)
    for m in legacy_missing:
        ms = content_stems_v31(m)
        if ls and ms and (len(ls & ms) / len(ls) >= 0.8 or len(ls & ms) / len(ls | ms) >= 0.5):
            return True
    return False


# ------------------------------------------------------------------------------------------------------------- main comparison
def compare(results: Dict[str, Any], key: Dict[str, str], cons: Dict[str, Dict[str, Any]], inter: Dict[str, Any], *, kinds: Optional[Dict[str, str]] = None,
            requirement_labels: Optional[Dict[str, Dict[str, str]]] = None, criteria: Optional[Dict[str, Any]] = None, mechanical: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """results: runner results.json; key: review_id -> sample_id; cons: consensus per review_id; kinds: sample_id -> AI answer kind (grouping only)."""
    mod: Dict[str, Dict[int, Dict[str, Any]]] = defaultdict(dict)
    for m in results.get("modular", []):
        mod[m["sample_id"]][m["repeat"]] = m["result"]
    leg = {l["sample_id"]: l["result"] for l in results.get("legacy", [])}
    items = []
    for rid, c in sorted(cons.items()):
        sid = key.get(rid)
        if sid is None or sid not in mod or c["score"] is None:
            continue
        items.append((rid, sid, c))
    pairs_mod, pairs_mod_rep, pairs_leg, rng, table = [], {0: [], 1: []}, [], [], []
    conf = Counter(); fc = fe = fm = me = om = 0; n_credit = n_err = 0; unver_by_h = Counter(); decided = agree = total_req = 0
    credit_num = credit_den = 0; ess_missing_contra = 0
    leg_unsup = 0; mod_unsup_missing = 0; abst_rows = abst_clear = 0; abst_legacy_err = []
    for rid, sid, c in items:
        h = c["score"]; reps = mod[sid]
        for rep, r in reps.items():
            s = r["score"]; pairs_mod_rep.setdefault(rep, []).append((h, s))
        ms = [r["score"] for r in reps.values() if r["score"] is not None]
        pairs_mod.append((h, round(statistics.mean(ms), 1) if len(ms) == len(reps) and ms else None))
        rng.append(next((r["score_range"] for r in reps.values() if r["score_range"] is not None), None))
        lr = leg.get(sid)
        pairs_leg.append((h, lr["provisional_score"] if lr and lr.get("provisional_score") is not None else None))
        table.append({"review_id": rid, "sample_id": sid, "ai_kind": (kinds or {}).get(sid), "human_score": h, "human_tech": c["tech"], "modular": [reps[k]["score"] for k in sorted(reps)],
                      "modular_status": [reps[k]["status"] for k in sorted(reps)], "modular_range": [reps[k]["score_range"] for k in sorted(reps)],
                      "legacy": pairs_leg[-1][1], "reviewers": c["n_reviewers"], "reviewers_disagree": c["reviewers_disagree"]})
        # abstentions
        for r in reps.values():
            if r["status"] == "abstained":
                abst_rows += 1
                if c["tech"] in ("correct", "incorrect") or h <= 25 or h >= 85:
                    abst_clear += 1
                    if pairs_leg[-1][1] is not None:
                        abst_legacy_err.append(abs(pairs_leg[-1][1] - h))
        # requirement level (modular)
        for rep, r in reps.items():
            for o in r.get("outcomes", []):
                if o["tier"] != "essential" or o["requirement_id"] not in c["req"]:
                    continue
                H, S = c["req"][o["requirement_id"]], outcome_state(o)
                conf[(H, S)] += 1; total_req += 1
                if S == "unverified":
                    unver_by_h[H] += 1
                else:
                    decided += 1; agree += (S == "states_correctly" and H == "stated_correctly") or (S == "states_incorrectly" and H == "stated_incorrectly") or (S == "not_stated" and H == "not_stated")
                if S == "states_correctly":
                    n_credit += 1; fc += H != "stated_correctly"
                if S == "states_incorrectly":
                    n_err += 1; fe += H == "stated_correctly"; om += H == "not_stated"
                if S == "not_stated":
                    fm += H != "not_stated"
                    if o["status"] == "missing": ess_missing_contra += H != "not_stated"
                if H == "stated_incorrectly" and S in ("states_correctly", "not_stated"):
                    me += 1
        # legacy penalties contradicted by the human
        lr = leg.get(sid)
        if lr:
            labels = (requirement_labels or {}).get(sid, {})
            for rq, H in c["req"].items():
                if H == "stated_correctly" and rq in labels and _legacy_matches(lr.get("missing_concepts", []), labels[rq]):
                    leg_unsup += 1
            if c["tech"] == "correct":
                leg_unsup += len(lr.get("factual_errors", []))
        # credit rate on human-correct concise / alternative answers
        if c["tech"] == "correct" and (kinds is None or kinds.get(sid) in ("concise_sufficient", "valid_alternative")):
            for r in reps.values():
                for o in r.get("outcomes", []):
                    if o["tier"] == "essential" and c["req"].get(o["requirement_id"]) == "stated_correctly":
                        credit_den += 1; credit_num += outcome_state(o) == "states_correctly"
    mod_unsup = ess_missing_contra + fe
    n_reviewers = max((c["n_reviewers"] for c in cons.values()), default=0)
    res = {
        "label": f"HUMAN-VALIDATED ({n_reviewers} reviewer{'s' if n_reviewers != 1 else ''} per item at most; {len(items)} answers compared)",
        "items": len(items), "inter_reviewer": inter,
        "score_level": {"modular_mean_of_repeats": _score_block(pairs_mod, rng), "modular_repeat0": _score_block(pairs_mod_rep[0]), "modular_repeat1": _score_block(pairs_mod_rep[1]),
                        "legacy": _score_block(pairs_leg), "gap_used_for_inflated_deflated_points": SCORE_GAP},
        "requirement_level_modular": {"judgements": total_req, "decided_by_modular": decided, "coverage": _rate(decided, total_req), "agreement_when_decided": _rate(agree, decided),
                                      "confusion_human_x_modular": {f"{h}|{s}": n for (h, s), n in sorted(conf.items())}, "unverified_by_human_call": dict(unver_by_h),
                                      "false_credit": fc, "credits": n_credit, "false_error": fe, "errors_called": n_err, "omission_called_an_error": om,
                                      "false_missing": fm, "missed_error": me},
        "abstentions": {"abstained_repeats_compared": abst_rows, "abstained_where_human_judgement_was_clear": abst_clear,
                        "legacy_abs_error_on_those_clear_cases_mean": round(statistics.mean(abst_legacy_err), 1) if abst_legacy_err else None},
        "per_answer": table,
        "criteria_inputs": {"false_credit_rate": _rate(fc, n_credit), "false_error_rate": _rate(fe, n_err), "essential_missing_contradicted": ess_missing_contra,
                            "credit_rate_on_human_correct": _rate(credit_num, credit_den), "credit_rate_denominator": credit_den,
                            "modular_unsupported_penalties": mod_unsup, "legacy_unsupported_penalties_approx": leg_unsup},
    }
    if criteria is not None:
        res["frozen_human_criteria"] = evaluate_human_criteria(res["criteria_inputs"], criteria, mechanical)
    return res


def evaluate_human_criteria(ci: Dict[str, Any], criteria: Dict[str, Any], mechanical: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t = criteria.get("needs_human_labels", {})
    def chk(name, val, ok):
        return {"value": val, "threshold": t.get(name), "result": "NO_DATA" if val is None else ("PASS" if ok else "FAIL")}
    rows = {
        "false_credit_rate_max": chk("false_credit_rate_max", ci["false_credit_rate"], (ci["false_credit_rate"] or 0) <= t.get("false_credit_rate_max", 1)),
        "false_error_rate_max": chk("false_error_rate_max", ci["false_error_rate"], (ci["false_error_rate"] or 0) <= t.get("false_error_rate_max", 1)),
        "credit_rate_on_human_correct_concise_or_alternative_answers_min": chk("credit_rate_on_human_correct_concise_or_alternative_answers_min", ci["credit_rate_on_human_correct"],
                                                                              (ci["credit_rate_on_human_correct"] or 0) >= t.get("credit_rate_on_human_correct_concise_or_alternative_answers_min", 0)),
        "essential_missing_penalties_contradicted_by_human_max": chk("essential_missing_penalties_contradicted_by_human_max", ci["essential_missing_contradicted"],
                                                                     ci["essential_missing_contradicted"] <= t.get("essential_missing_penalties_contradicted_by_human_max", 0)),
        "modular_unsupported_penalties_not_more_than_legacy": {"value": [ci["modular_unsupported_penalties"], ci["legacy_unsupported_penalties_approx"]], "threshold": "modular <= legacy",
                                                               "result": "PASS" if ci["modular_unsupported_penalties"] <= ci["legacy_unsupported_penalties_approx"] else "FAIL",
                                                               "note": "legacy side is matched lexically and is approximate"},
    }
    out = {"criteria": rows, "all_human_criteria_pass": all(r["result"] == "PASS" for r in rows.values())}
    if mechanical is not None:
        mech_fail = [k for k, v in mechanical.items() if str(v).startswith("FAIL")]
        out["mechanical_failures_from_frozen_run"] = mech_fail
        out["decision_under_frozen_rule"] = ("DO NOT ADVANCE: a mechanical criterion failed (" + ", ".join(mech_fail) + "); human labels are for diagnosis, not for re-opening the decision" if mech_fail
                                             else ("ADVANCE (larger human-labelled study only)" if out["all_human_criteria_pass"] else "DO NOT ADVANCE: a human-label criterion failed"))
    return out


def to_markdown(res: Dict[str, Any]) -> str:
    L = [f"# Human comparison: {res['label']}", "", "Every number below that depends on a human score or call is HUMAN-VALIDATED; the model results themselves remain AI-verified.", ""]
    sl = res["score_level"]
    L += ["## Score level (human consensus score vs system)", "", "| system | answers | scored | abstained | MAE | signed | within 10 | within 15 | inflated >=15 | deflated >=15 | Spearman |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("modular_mean_of_repeats", "modular_repeat0", "modular_repeat1", "legacy"):
        b = sl[k]; L.append(f"| {k} | {b['answers']} | {b['scored']} | {b['abstained']} | {b['mean_abs_error']} | {b['mean_signed_error']} | {b['within_10']} | {b['within_15']} | {b['inflated_ge15']} | {b['deflated_ge15']} | {b['spearman']} |")
    rq = res["requirement_level_modular"]
    L += ["", "## Requirement level (modular vs human per-requirement calls)", "", "```", json.dumps({k: v for k, v in rq.items() if k != "confusion_human_x_modular"}, indent=1), "```", "",
          "Confusion (human | modular):", "", "```", json.dumps(rq["confusion_human_x_modular"], indent=1), "```", "", "## Abstentions", "", "```", json.dumps(res["abstentions"], indent=1), "```", "",
          "## Frozen human-label criteria", ""]
    fh = res.get("frozen_human_criteria")
    if fh:
        for k, v in fh["criteria"].items():
            L.append(f"- {k}: **{v['result']}** (value {v['value']}, threshold {v['threshold']})")
        if "decision_under_frozen_rule" in fh:
            L += ["", f"**Decision under the frozen rule:** {fh['decision_under_frozen_rule']}"]
    L += ["", "## Per answer", "", "| review | sample | AI kind (grouping only) | human | human tech | modular r0 / r1 | legacy | reviewers |", "|---|---|---|---|---|---|---|---|"]
    for t in res["per_answer"]:
        L.append(f"| {t['review_id']} | {t['sample_id']} | {t['ai_kind']} | {t['human_score']} | {t['human_tech']} | {t['modular']} ({'/'.join(s[:3] for s in t['modular_status'])}) | {t['legacy']} | {t['reviewers']}{' ⚠ disagree' if t['reviewers_disagree'] else ''} |")
    return "\n".join(L)
