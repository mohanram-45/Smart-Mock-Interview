"""Explicit, deterministic rubric. The MODEL judges each dimension on a 0-4 scale; CODE turns levels into the 0-100 score,
applies caps, and records every adjustment, so the number is reproducible from the levels and never a free-form model output."""
from __future__ import annotations

from typing import Dict, List, Tuple

from .schema import FactualError, RubricScores

RUBRIC_VERSION = "3a.1"
WEIGHTS: Dict[str, int] = {"correctness": 40, "completeness": 30, "relevance": 15, "reasoning": 15}   # sums to 100
assert sum(WEIGHTS.values()) == 100

LEVEL_ANCHORS = """Levels (apply to each dimension independently):
4 = fully meets the dimension for this question
3 = mostly meets; small gaps
2 = partly meets; clear gaps
1 = barely meets
0 = does not meet / not present"""

DIMENSION_GUIDE = {
    "correctness": "Are the claims the candidate makes technically accurate? Judge claims, not wording. A correct alternative explanation "
                   "that differs from the reference is still correct. Only penalise statements that are actually wrong; mark each wrong "
                   "statement as a factual error (minor = imprecise/slightly wrong, major = materially wrong or misleading). "
                   "Omissions are NOT factual errors.",
    "completeness": "Does the answer cover what this question needs (use the key concepts and reference as a guide, not a checklist)? "
                    "A short answer that covers what the question asks is complete. Length itself earns nothing.",
    "relevance": "Does the answer address the question that was asked? Off-topic or generic text scores 0-1 however fluent it is.",
    "reasoning": "Does the candidate explain why/how (mechanism, trade-offs, justification) rather than just naming terms? "
                 "Scale this to the question type: a one-line definition question needs little.",
}

BANDS: List[Tuple[int, str]] = [(85, "excellent"), (70, "good"), (50, "fair"), (25, "weak"), (0, "very_weak")]


def band(score: int) -> str:
    for floor, name in BANDS:
        if score >= floor:
            return name
    return "very_weak"


def raw_score(r: RubricScores) -> int:
    total = sum(WEIGHTS[k] * getattr(r, k).level / 4 for k in WEIGHTS)
    return int(round(total))


def apply_caps(r: RubricScores, factual_errors: List[FactualError]) -> Tuple[int, List[str]]:
    """Returns (final_score, adjustments). Caps are deliberately few and explainable."""
    notes: List[str] = []
    score = raw_score(r)
    majors = [e for e in factual_errors if e.severity == "major"]
    if r.relevance.level == 0:
        cap = 10
        if score > cap:
            notes.append(f"relevance=0 (off-topic): score capped {score}->{cap}")
            score = cap
    if majors:
        cap = 60
        if score > cap:
            notes.append(f"{len(majors)} major factual error(s): score capped {score}->{cap}")
            score = cap
        if r.correctness.level > 1:
            notes.append(f"major factual error(s) contradict correctness={r.correctness.level}; recomputed with correctness=1")
            fixed = RubricScores(**{**r.model_dump(), "correctness": {"level": 1, "justification": r.correctness.justification}})
            score = min(score, raw_score(fixed))
    elif factual_errors and r.correctness.level == 4:
        notes.append("minor factual error(s) listed but correctness=4; recomputed with correctness=3")
        fixed = RubricScores(**{**r.model_dump(), "correctness": {"level": 3, "justification": r.correctness.justification}})
        score = min(score, raw_score(fixed))
    return max(0, min(100, score)), notes


def rubric_prompt_text() -> str:
    lines = ["Score each of these four dimensions as an integer level 0-4. Do NOT output an overall score; it is computed from your levels.",
             LEVEL_ANCHORS, ""]
    for k, w in WEIGHTS.items():
        lines.append(f"- {k} (weight {w}%): {DIMENSION_GUIDE[k]}")
    return "\n".join(lines)
