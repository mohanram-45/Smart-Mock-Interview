"""Plain-language terminology for what a modular result does and does NOT mean.

The engine's `confidence` field (high / medium / low) is an INTERNAL-CONSISTENCY signal: no unresolved verdicts, no contradictions, no soft flags. It is not a
probability that the score is right and it is not human-verified accuracy. Renaming the stored field is an engine change (version it); this module is the
presentation layer every report, review tool and demo uses meanwhile."""
from __future__ import annotations

from typing import Any, Dict

INTERNAL_CONSISTENCY = {
    "high": "internally consistent",
    "medium": "internally consistent with open caveats",
    "low": "insufficient verified evidence",
    "none": "not applicable",
}
STANDING_CAVEAT = "Internal consistency only: not human-verified accuracy."

SOURCE_REAL = "REAL MODEL"
SOURCE_MOCK = "MOCK VERIFIER"
SOURCE_ADVISORY = "ADVISORY ONLY"
SOURCE_HUMAN = "HUMAN-VALIDATED"


def describe_confidence(conf: str, human_validated: bool = False) -> str:
    base = INTERNAL_CONSISTENCY.get(conf or "none", conf or "unknown")
    return base + ("" if human_validated else " (not human-verified)")


def source_label(result: Dict[str, Any]) -> Dict[str, Any]:
    """What kind of result is this? Every applicable tag is shown (a mock result on an advisory-only question carries BOTH tags), plus the human-validation line."""
    prov = result.get("provenance") or {}
    tags, lines = [], []
    if result.get("status") == "advisory_only" or result.get("penalty_mode") == "advisory":
        tags.append(SOURCE_ADVISORY); lines.append("ADVISORY ONLY: question is not scope-eligible for scoring; findings and feedback only, no numeric score.")
    if prov.get("is_mock"):
        tags.append(SOURCE_MOCK); lines.append("MOCK VERIFIER: a scripted rule-based test double, not a model judgement. Demonstrates the pipeline only.")
    elif prov.get("verifier"):
        tags.append(SOURCE_REAL); lines.append(f"REAL MODEL: {prov.get('verifier_model') or 'unknown model'} verified the concepts; the numbers come from fixed rules over its evidence-checked verdicts.")
    if not tags:
        tags, lines = ["UNKNOWN"], ["Provenance missing."]
    human = SOURCE_HUMAN if prov.get("human_validated") else "NOT human-validated"
    kind = " + ".join(tags)
    return {"kind": kind, "tags": tags, "text": " ".join(lines), "human": human, "caveat": STANDING_CAVEAT}
