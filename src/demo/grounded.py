"""Stage 9C: GROUNDED written feedback built from the experimental modular evaluator's view. Pure functions, no model calls.

Six separate sections (never blended into one score):
  1 answer        what the candidate wrote (sanitised text, split into the claims the evaluator read)
  2 evidence      the curated material this question is judged against (concept labels, scope flags; the reference text only when the server exposes it)
  3 supported     curated concepts the answer states, each with the candidate's OWN words as evidence
  4 maybe_missing curated concepts not found in the answer. "Not found" is a prompt to look again; it may be stated in other words
  5 errors        technical errors that survived EVERY evidence check: the question is penalty-eligible, the finding is an evidence-checked 'incorrect', it quotes the candidate's words
                  AND it has the curated reference statement it contradicts. Rare by design
  6 uncertain     everything else: undecided or unverifiable findings, possible concerns on advisory-only questions, and why the evaluator abstained

No numeric grade is produced or returned here (numeric_grade is always None). When the evaluator abstains the result says so plainly and keeps sections 3-6 honest about what could
not be decided; abstention is never turned into a pass. Nothing here is human-validated and the output is labelled that way.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import experimental as MA

SUPPORTED_CLASSES = ("correct_supported", "correct_weakly_supported")
UNSUPPORTED_CREDIT = ("correct_unsupported", "correct_unchecked", "unsupported_credit")
UNDECIDED_CLASSES = ("unverified_by_model", "unverified_by_gate", "unsupported_penalty", "omission_labelled_as_error")
LABEL = {"essential": "essential", "supporting": "supporting", "bonus": "extra", "": ""}


def _claim_text(view: Dict[str, Any]) -> Dict[str, str]:
    return {c["id"]: c["text"] for c in (view.get("claims") or [])}


def _words(v: Dict[str, Any], claims: Dict[str, str]) -> List[str]:
    return [claims[i] for i in (v.get("claim_ids") or []) if i in claims][:2]


def build(view: Optional[Dict[str, Any]], *, answer: str = "", reference: Optional[str] = None, provenance: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """The grounded feedback for ONE technical answer, or None when no experimental view was genuinely returned (nothing is invented)."""
    if not view or view.get("status") in (None, "provider_error", "invalid_response", "scope_unavailable"):
        return None
    state = MA.describe_state(view)
    req = view.get("requirements") or {}
    penalty_full = req.get("penalty_mode") == "full"
    claims = _claim_text(view)
    verdicts = view.get("verdicts") or []
    outcome_by_req = {o["requirement_id"]: o for o in (view.get("outcomes") or [])}
    supported, missing, errors, uncertain = [], [], [], []
    seen_missing = set()
    for v in verdicts:
        cls = v.get("finding_class")
        rid, member, tier = v.get("requirement_id"), v.get("member"), v.get("tier") or ""
        base = {"id": rid, "concept": member, "tier": LABEL.get(tier, tier)}
        if cls in SUPPORTED_CLASSES:
            supported.append({**base, "your_words": _words(v, claims), "strength": "clearly stated" if cls == "correct_supported" else "stated, but only weakly supported by your wording"})
        elif cls == "omitted":
            if rid not in seen_missing:
                seen_missing.add(rid)
                missing.append({**base, "note": "Not found in your answer. It may be covered in other words; treat this as a prompt to check, not a mistake."})
        elif cls == "incorrect":
            quote = (view.get("feedback") or {}).get("factual_errors") or []
            ref_says = next((e.get("reference_says") for e in quote if e.get("concept") == member and e.get("reference_says")), None)
            words = _words(v, claims)
            if penalty_full and words and ref_says:
                errors.append({**base, "your_words": words, "reference_says": ref_says, "why": v.get("explanation") or "", "label": "possible technical error, evidence shown; check it against your own knowledge"})
            else:
                uncertain.append({**base, "your_words": words, "reason": "A possible concern was raised but it did not meet the evidence bar for calling it an error."
                                  + ("" if penalty_full else " This question is advisory-only, so no mistakes are asserted.")})
        elif cls in UNSUPPORTED_CREDIT:
            uncertain.append({**base, "your_words": _words(v, claims), "reason": "The model said you covered this, but the evidence checks could not confirm it, so it is not counted."})
        elif cls in UNDECIDED_CLASSES:
            uncertain.append({**base, "your_words": _words(v, claims), "reason": "The evaluator could not decide this one; no judgement is made."})
    fb = view.get("feedback") or {}
    have = {u["concept"] for u in uncertain} | {x["concept"] for x in supported} | {x["concept"] for x in missing} | {x["concept"] for x in errors}
    for item in fb.get("could_not_verify") or []:
        if (item.get("concept") or item.get("claim")) in have:
            continue
        uncertain.append({"id": None, "concept": item.get("concept") or item.get("claim") or "a statement", "tier": "", "your_words": [item.get("your_words")] if isinstance(item.get("your_words"), str) else list(item.get("your_words") or [])[:2],
                          "reason": item.get("reason") or "Could not be checked against the curated material."})
    abstained = view.get("status") == "abstained"
    total = len(outcome_by_req) or len(verdicts)
    if abstained:
        headline = "The evaluator could not reach a firm judgement on this answer. The notes below show only what was checked."
    elif state["state"] == "advisory":
        headline = f"{len(supported)} of {total} curated concepts were found supported in your answer. This question is advisory-only: nothing here is a grade."
    else:
        headline = f"{len(supported)} of {total} curated concepts were found supported in your answer; {len(missing)} not found; {len(uncertain)} could not be decided."
    out = {"available": True, "experimental": True, "human_validated": False, "numeric_grade": None, "status": state["state"], "headline": headline, "abstention": state["text"] if abstained else None,
           "answer": {"text": (view.get("answer") or answer or "")[:4000], "claims": [c["text"] for c in (view.get("claims") or [])][:12]},
           "evidence": {"concepts": [{"id": r["id"], "label": r["label"], "tier": LABEL.get(r["tier"], r["tier"])} for r in (req.get("requirements") or [])],
                        "scope_flags": list(req.get("flags") or []), "alternatives_note": (req.get("alternatives") or [""])[0],
                        "reference": reference, "provenance": provenance or {}, "penalty_mode": req.get("penalty_mode")},
           "supported": supported, "maybe_missing": missing, "errors": errors, "uncertain": uncertain,
           "source": (view.get("source") or {}).get("kind"), "mock": "MOCK VERIFIER" in ((view.get("source") or {}).get("tags") or []),
           "caveats": ["Concept lists were written by AI and checked only by AI, not by a human.", "A concept not found is not a mistake; alternative correct wording is possible.", "Not validated against human judgement."]}
    return out
