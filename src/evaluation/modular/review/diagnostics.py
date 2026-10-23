"""Diagnostics over SAVED modular results (plain dicts, as written by the experiment runner). Reporting only: nothing here changes a verdict or a score.

  abstain_taxonomy      why did a result not get a number? (provider failure vs confirmed off-topic vs the model's own uncertainty vs the evidence gate)
  verdict_diagnostics   for every verdict: who produced the final state (model vs gate), the gate's reason, the evidence it looked at
  disagreement_report   repeat-to-repeat disagreements before and after the gate, with their cause
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from ..claims import content_stems
from ..lexnorm import content_stems_v31

NOT_SCORED_BY_DESIGN = {"advisory_only", "not_gradable", "scope_unavailable"}
PROVIDER_FAILURES = {"provider_error", "invalid_response"}
OFF_TOPIC_LEXICAL_MAX = 0.15       # mirrors rubric_engine.OFF_TOPIC_LEXICAL_MAX (reported, never used to score here)


def _dim(result, name):
    return next((d for d in result.get("dimensions", []) if d["name"] == name), None)


def verdict_origin(v: Dict[str, Any]) -> str:
    """Who is responsible for this verdict's FINAL state."""
    if v.get("downgrade_reason"):
        return "gate_downgraded"
    if (v.get("original_state") or v["state"]) == "unverified":
        return "model_unverified"
    return "model_stated"


def essential_blockers(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Requirements whose outcome is 'undetermined' (they are what stops a dimension from being derived), with the origin of each unresolved verdict."""
    vmap: Dict[str, List[Dict[str, Any]]] = {}
    for v in result.get("verdicts", []):
        vmap.setdefault(v["requirement_id"], []).append(v)
    out = []
    for o in result.get("outcomes", []):
        if o["status"] != "undetermined":
            continue
        unresolved = [v for v in vmap.get(o["requirement_id"], []) if v["state"] == "unverified"]
        for v in unresolved or [{"member": o["label"], "state": "unverified", "original_state": "unverified"}]:
            origin = verdict_origin(v)
            out.append({"requirement_id": o["requirement_id"], "tier": o["tier"], "member": v.get("member"), "origin": origin,
                        "reason": v.get("downgrade_reason") or ("model returned unverified" if origin == "model_unverified" else ""),
                        "model_said": v.get("original_state") or v["state"]})
    return out


def abstain_taxonomy(result: Dict[str, Any]) -> Dict[str, Any]:
    """Primary cause + every contributing cause for a result that has no score. Off-topic, genuine uncertainty and provider failures are kept apart."""
    status = result.get("status")
    flags = list(result.get("flags", [])) + list(result.get("uncertainty_flags", []))
    base = {"status": status, "score_range": result.get("score_range"), "abstain_reasons": result.get("abstain_reasons", []), "modifiers": [], "blockers": []}
    if status == "scored":
        return {**base, "primary": "scored"}
    if status in PROVIDER_FAILURES:
        return {**base, "primary": "provider_failure", "error": result.get("error")}
    if status in NOT_SCORED_BY_DESIGN:
        return {**base, "primary": "not_scored_by_design"}
    blockers = essential_blockers(result)
    rel = _dim(result, "relevance")
    off_topic = bool(rel and rel["level"] == 0 and rel["inputs"].get("on_topic_verifier") == "off_topic" and (rel["inputs"].get("lexical_overlap") or 0) <= OFF_TOPIC_LEXICAL_MAX)
    mods = [f for f in flags if f == "injection_detected" or f.startswith("scope_ambiguity") or f == "code_or_sql_not_executed" or f == "contradictory_verdicts"]
    origins = {b["origin"] for b in blockers}
    if off_topic:
        primary = "off_topic_confirmed"
    elif not blockers:
        primary = "undetermined_other"
    elif origins == {"model_unverified"}:
        primary = "model_uncertain"
    elif origins == {"gate_downgraded"}:
        primary = "evidence_gate"
    else:
        primary = "mixed_model_and_gate"
    return {**base, "primary": primary, "modifiers": mods, "blockers": blockers, "has_score_range": result.get("score_range") is not None}


def raw_verdicts(trace) -> Dict[tuple, Dict[str, Any]]:
    """The model's own verdicts (before any gate), keyed by (requirement_id, member), from a runner `verifier_trace` list. Empty if unavailable."""
    import json
    out: Dict[tuple, Dict[str, Any]] = {}
    for t in trace or []:
        try:
            for v in json.loads(t.get("raw") or "{}").get("verdicts", []):
                out[(v.get("requirement_id"), v.get("member"))] = v
        except (ValueError, AttributeError):
            continue
    return out


def verdict_diagnostics(result: Dict[str, Any], trace=None) -> List[Dict[str, Any]]:
    """One row per verdict: origin of the final state and the evidence the gate looked at. Pass the runner's `verifier_trace` to also see the claim ids the model
    itself cited (the gate clears them when it downgrades). For `omission_contradicted_by_lexical_check` the row shows WHICH claim contained the member's words and
    which stems matched: naming a term is not stating it, and a human decides which it was."""
    claims = {c["id"]: c for c in result.get("claims", [])}
    tier = {o["requirement_id"]: o["tier"] for o in result.get("outcomes", [])}
    raw = raw_verdicts(trace)
    rows = []
    for v in result.get("verdicts", []):
        origin = verdict_origin(v)
        mv = raw.get((v["requirement_id"], v["member"]), {})
        row = {"requirement_id": v["requirement_id"], "tier": tier.get(v["requirement_id"]), "member": v["member"], "model_state": v.get("original_state") or v["state"],
               "final_state": v["state"], "origin": origin, "downgrade_reason": v.get("downgrade_reason"), "claim_ids": list(v.get("claim_ids", [])),
               "model_claim_ids": list(mv.get("claim_ids", [])) if mv else None, "explanation": (v.get("explanation") or mv.get("explanation") or "")[:200]}
        why = v.get("downgrade_reason")
        if why == "omission_contradicted_by_lexical_check":
            ms = content_stems(v["member"]); best = None
            for c in claims.values():
                hit = ms & content_stems(c["text"])
                if hit and (best is None or len(hit) > len(best[1])):
                    best = (c, hit)
            if best:
                row["matched_claim"] = {"id": best[0]["id"], "text": best[0]["text"][:200], "matched_stems": sorted(best[1]), "member_stems": sorted(ms)}
            row["note"] = "the model said the concept was never mentioned, but its words appear in the answer; the gate cannot tell naming from stating"
        elif why == "no_valid_evidence":
            row["note"] = "the model asserted a verdict about the answer without citing any claim id"
        elif why == "same_claim_correct_and_incorrect" and raw:
            mine = set(mv.get("claim_ids", []))
            row["shares_claim_with"] = [f"{k[0]}:{k[1]}:{x.get('state')}" for k, x in raw.items() if k != (v["requirement_id"], v["member"]) and mine & set(x.get("claim_ids", []))]
            row["note"] = "one claim was credited for one concept and blamed for an overlapping one"
        if v["state"] == "states_correctly" and v["member"] != "__other_valid__":
            row.update(credit_support(v, claims))
        from .findings import classify_verdict
        row["finding_class"] = classify_verdict(v, row.get("credit_support", ""))
        rows.append(row)
    return rows


def credit_support(v: Dict[str, Any], claims: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """REPORTING ONLY (no gate, no score effect): does the claim the model cited for a CREDIT actually contain the concept's words? The gate checks that the cited
    claim id exists, not that it says anything about the concept. 'none'/'partial' is a prompt for a human, never proof of a false credit (paraphrase and code
    have no lexical anchor); `found_in_other_claims` shows where the words DO occur, e.g. a concept named only as a 'fix' when it was credited as a 'cause'."""
    ms = content_stems_v31(v["member"])
    cited = [claims[i] for i in (e["claim_id"] for e in v.get("evidence", [])) if i in claims]
    have = set()
    for c in cited:
        have |= content_stems_v31(c["text"])
    share = round(len(ms & have) / len(ms), 2) if ms else None
    other = [c["id"] for c in claims.values() if c["id"] not in {x["id"] for x in cited} and ms and len(ms & content_stems_v31(c["text"])) / len(ms) >= 0.8]
    if share is None:
        level = "not_checkable"
    elif share >= 0.8:
        level = "corroborated"
    elif share > 0:
        level = "partial"
    else:
        level = "none"
    if level != "corroborated" and cited and all(c.get("kind") == "code" for c in cited):
        level = "code_claim_not_lexically_checkable"
    return {"credit_support": level, "credit_support_share": share, "found_in_other_claims": other}


def disagreement_report(by_sample: Dict[str, Dict[int, Dict[str, Any]]]) -> Dict[str, Any]:
    """Repeat-to-repeat verdict disagreements. `by_sample[sample_id][repeat] = result dict`. Each mismatch is classified:
    model_flip (the model's own raw states differ), gate_induced (raw states agree, the gate changed one), model_flip_and_gate."""
    rows, tot, agree_post, agree_pre = [], 0, 0, 0
    for sid, reps in sorted(by_sample.items()):
        if 0 not in reps or 1 not in reps:
            continue
        a = {(v["requirement_id"], v["member"]): v for v in reps[0]["verdicts"]}
        b = {(v["requirement_id"], v["member"]): v for v in reps[1]["verdicts"]}
        tier = {o["requirement_id"]: o["tier"] for o in reps[0]["outcomes"]}
        for k in sorted(a.keys() & b.keys()):
            tot += 1
            pa, pb = a[k]["state"], b[k]["state"]
            ra, rb = a[k].get("original_state") or pa, b[k].get("original_state") or pb
            agree_post += pa == pb; agree_pre += ra == rb
            if pa != pb:
                cause = "model_flip_and_gate" if (ra != rb and (pa != ra or pb != rb)) else "model_flip" if ra != rb else "gate_induced"
                rows.append({"sample_id": sid, "requirement": k[0], "tier": tier.get(k[0]), "member": k[1], "model": [ra, rb], "final": [pa, pb], "cause": cause,
                             "gate_reasons": [a[k].get("downgrade_reason"), b[k].get("downgrade_reason")],
                             "status_effect": [reps[0]["status"], reps[1]["status"]], "score_effect": [reps[0]["score"], reps[1]["score"]]})
    return {"members_compared": tot, "agreement_after_gate": round(agree_post / tot, 4) if tot else None, "agreement_before_gate": round(agree_pre / tot, 4) if tot else None,
            "mismatches": rows, "by_cause": dict(Counter(r["cause"] for r in rows)), "mismatch_on_essential": sum(r["tier"] == "essential" for r in rows)}
