"""Optional feedback (stage F). Runs AFTER scoring, reads only a finished ModularResult (or its JSON dict), and cannot change it.

Deterministic feedback is built from VERIFIED findings only: correct concepts (with the candidate's own quoted claim), missing essential
concepts, verified factual errors (candidate claim + reference quote + explanation), and items that could not be verified (never
presented as mistakes). Because it takes a plain dict payload it can run later or in another process (asynchronous use); an optional
FeedbackProvider can phrase it, and if that provider fails the deterministic text is returned instead.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .pipeline import ModularResult


@dataclass(frozen=True)
class FeedbackReport:
    question_id: str
    source: str                         # deterministic | llm
    advisory: bool                      # True when concept tiers are not penalty-eligible (omissions are possible gaps, not penalties)
    correct_concepts: List[Dict[str, Any]]
    missing_essential_concepts: List[Dict[str, Any]]
    factual_errors: List[Dict[str, Any]]
    could_not_verify: List[Dict[str, Any]]
    suggestions: List[str]
    notes: List[str]
    text: str


class FeedbackProvider(ABC):
    name = "feedback_provider"
    is_mock = False

    @abstractmethod
    def phrase(self, payload: Dict[str, Any]) -> str: ...


def feedback_payload(result: ModularResult) -> Dict[str, Any]:
    """JSON-serialisable input for (possibly deferred) feedback. Carries verified findings only."""
    d = result.to_dict()
    return {"question_id": d["question_id"], "status": d["status"], "penalty_mode": d["penalty_mode"], "outcomes": d["outcomes"], "verdicts": d["verdicts"],
            "uncertainty_flags": d["uncertainty_flags"], "background_concepts": d["background_concepts"], "claims": d["claims"]}


def build_feedback(payload: Dict[str, Any], provider: Optional[FeedbackProvider] = None) -> FeedbackReport:
    advisory = payload["penalty_mode"] != "full"
    claim = {c["id"]: c["text"] for c in payload["claims"]}
    correct, errors, unver = [], [], []
    for v in payload["verdicts"]:
        label = v["proposed_member"] if v["member"] == "__other_valid__" else v["member"]
        if v["state"] == "states_correctly":
            correct.append({"concept": label, "your_words": [e["text"] for e in v["evidence"]]})
        elif v["state"] == "states_incorrectly":
            errors.append({"concept": label, "your_words": [e["text"] for e in v["evidence"]], "why_wrong": v["explanation"], "reference_says": v["reference_quote"], "severity": v["severity"]})
        elif v["state"] == "unverified" and v["member"] != "__other_valid__":
            unver.append({"concept": v["member"], "reason": v.get("downgrade_reason") or "verifier could not tell"})
    missing = [{"requirement": o["label"], "tier": o["tier"], "kind": o["kind"]} for o in payload["outcomes"] if o["tier"] == "essential" and o["status"] == "missing"]
    sugg = []
    for m in missing:
        sugg.append(f"Consider adding: {m['requirement']}." + (" (Possible gap: this record's requirements are AI-drafted and not human-verified.)" if advisory else ""))
    for e in errors:
        sugg.append(f"Revisit what you said about {e['concept']}: {e['why_wrong']}")
    if unver:
        sugg.append("Some points could not be checked automatically; this is not a judgement that they are wrong.")
    notes = ["Feedback is separate from scoring and does not change it."]
    if advisory:
        notes.append("Advisory feedback: concept requirements for this question are not penalty-eligible, so no automatic score was produced.")
    lines = ["What you covered: " + ("; ".join(c["concept"] for c in correct) if correct else "nothing verified yet.")]
    if missing:
        lines.append("Possibly missing: " + "; ".join(m["requirement"] for m in missing))
    for e in errors:
        lines.append(f"Incorrect: \"{e['your_words'][0]}\" - {e['why_wrong']}")
    if unver:
        lines.append("Could not verify: " + "; ".join(u["concept"] for u in unver))
    lines += sugg
    det = FeedbackReport(payload["question_id"], "deterministic", advisory, correct, missing, errors, unver, sugg, notes, "\n".join(lines))
    if provider is None:
        return det
    try:
        txt = provider.phrase(payload)
        if not isinstance(txt, str) or not txt.strip():
            raise ValueError("empty feedback")
    except Exception as e:                                   # feedback must never break or alter a result
        return FeedbackReport(det.question_id, "deterministic", advisory, correct, missing, errors, unver, sugg, notes + [f"feedback_provider_failed:{type(e).__name__}"], det.text)
    return FeedbackReport(det.question_id, "llm", advisory, correct, missing, errors, unver, sugg, notes, txt.strip())
