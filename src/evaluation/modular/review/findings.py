"""Finding classes: keep INCORRECT, OMITTED, UNSUPPORTED and UNVERIFIED apart, and show WHO produced each one (the model, the evidence gate, a consistency rule).

Why this exists: in the 3C-2 run an omission was reported as an error (s2-f02), an unsupported credit looked like a credit (b2-028) and an unsupported penalty looked like a
penalty (b2-105). A reader of a report or an application screen must be able to tell the five situations apart. Reporting only: nothing here changes a verdict or a score.

  correct_supported            the model said the concept is stated correctly and the cited claim contains its wording (>= 80% of its content stems)
  correct_weakly_supported     credited; the cited claim contains only part of the concept's wording (paraphrase is plausible; a human should look)
  correct_unsupported          credited although the cited claim contains NONE of the concept's wording. Only a frozen-3c1.0 result can contain this: the 3c4.0 gate refuses it
  correct_unchecked            credited, but the wording check does not apply (code, no comparable words, group "other valid" member)
  incorrect                    the model alleged an error and it survived every gate
  omitted                      the model said the concept is not stated and the omission survived the lexical cross-check
  unsupported_credit           a credit the gate refused: the cited claim does not contain the concept (credit_without_concept_in_cited_claim / credit_cites_wrong_claim)
  unsupported_penalty          an error the gate refused for the same reason (error_without_concept_in_cited_claim)
  omission_labelled_as_error   an 'incorrect' finding whose own explanation describes an omission / non-use (error_alleges_omission)
  unverified_by_model          the model itself returned 'unverified'
  unverified_by_gate           any other gate / consistency downgrade (uncited verdict, contradiction, echoed instruction, omission contradicted by a word match ...)
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

CLASSES = ("correct_supported", "correct_weakly_supported", "correct_unsupported", "correct_unchecked", "incorrect", "omitted", "unsupported_credit", "unsupported_penalty", "omission_labelled_as_error",
           "unverified_by_model", "unverified_by_gate")
LABELS = {"correct_supported": "credited, evidence contains the concept", "correct_weakly_supported": "credited, evidence contains part of the concept's wording",
          "correct_unsupported": "credited, but the cited claim does not contain the concept (not refused by this engine version)", "correct_unchecked": "credited, wording check not applicable",
          "incorrect": "stated incorrectly (survived the evidence gate)", "omitted": "not stated (omission)",
          "unsupported_credit": "credit refused: cited claim does not substantiate the concept", "unsupported_penalty": "penalty refused: cited claim does not concern the concept",
          "omission_labelled_as_error": "refused as an error: the explanation describes an omission", "unverified_by_model": "the model could not decide",
          "unverified_by_gate": "rejected by the evidence gate / consistency rules"}
_UNSUPPORTED_CREDIT = {"credit_without_concept_in_cited_claim", "credit_cites_wrong_claim"}


def classify_verdict(v: Dict[str, Any], credit_support: str = "") -> str:
    """`v` is a saved verdict dict. `credit_support` is the diagnostics' lexical support level for a credit ('' when unknown)."""
    state, why = v["state"], v.get("downgrade_reason")
    if state == "states_correctly":
        return {"corroborated": "correct_supported", "partial": "correct_weakly_supported", "none": "correct_unsupported"}.get(credit_support, "correct_unchecked")
    if state == "states_incorrectly":
        return "incorrect"
    if state == "not_stated":
        return "omitted"
    if why in _UNSUPPORTED_CREDIT:
        return "unsupported_credit"
    if why == "error_without_concept_in_cited_claim":
        return "unsupported_penalty"
    if why == "error_alleges_omission":
        return "omission_labelled_as_error"
    if why:
        return "unverified_by_gate"
    return "unverified_by_model"


def classify_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    from .diagnostics import credit_support
    claims = {c["id"]: c for c in result.get("claims", [])}
    rows = []
    for v in result.get("verdicts", []):
        cs = credit_support(v, claims)["credit_support"] if v["state"] == "states_correctly" and v["member"] != "__other_valid__" else ""
        c = classify_verdict(v, cs)
        rows.append({"requirement_id": v["requirement_id"], "member": v["member"], "class": c, "label": LABELS[c], "reason": v.get("downgrade_reason")})
    return rows


def reliability_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """Counts per finding class plus the abstention taxonomy, so model errors, evidence-gate rejections and legitimate abstentions are three separate numbers."""
    from .diagnostics import abstain_taxonomy
    rows = classify_result(result)
    n = Counter(r["class"] for r in rows)
    tax = abstain_taxonomy(result)
    return {"classes": {c: n.get(c, 0) for c in CLASSES}, "model_uncertain": n.get("unverified_by_model", 0),
            "credit_unsupported_kept": n.get("correct_unsupported", 0), "gate_rejections": n.get("unsupported_credit", 0) + n.get("unsupported_penalty", 0) + n.get("omission_labelled_as_error", 0) + n.get("unverified_by_gate", 0),
            "abstention": {"primary": tax["primary"], "legitimate": tax["primary"] in ("off_topic_confirmed", "not_scored_by_design"),
                           "provider_failure": tax["primary"] == "provider_failure"}}
