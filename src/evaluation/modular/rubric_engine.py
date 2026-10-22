"""Deterministic rubric engine (stage E). Weights are the established ones (40/30/15/15, reused from rubric.WEIGHTS).

Every level is derived from VERIFIED findings by a fixed rule and the rule text is stored with the level. The engine never calls a
model, never reads the reference, and NEVER lowers a dimension because evidence is missing or unverifiable: an undetermined
dimension is None and the whole result abstains (score=None) instead of defaulting to a low number.

Completeness (only ESSENTIAL requirements, only when penalty_mode == 'full'):
  concept   satisfied=states_correctly, missing=not_stated, incorrect=states_incorrectly (not demonstrated, but reported as a correctness finding, never as 'missing'), undetermined=unverified
  group     satisfied when >= min_required members are correct (any valid member counts, incl. verifier-proposed '__other_valid__');
            missing only if even counting every unverified member it cannot reach k AND the verifier explicitly found no other valid member
  The level is computed for the pessimistic and the optimistic reading of the undetermined items; if they differ the dimension is undetermined.
Supporting and background concepts never enter completeness. In 'advisory' mode completeness is not scored at all.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..rubric import WEIGHTS
from .claims import Segmentation, lexical_overlap
from .requirements import OTHER_VALID, Requirement, RequirementSet, Tier
from .verification import ConceptState, VerifiedVerdict

ENGINE_VERSION = "3c1.0"
OFF_TOPIC_LEXICAL_MAX = 0.15
STRUCTURED_TYPES = {"scenario", "design", "debugging", "evaluation", "business_case"}
C, X, N, U = ConceptState.STATES_CORRECTLY, ConceptState.STATES_INCORRECTLY, ConceptState.NOT_STATED, ConceptState.UNVERIFIED


@dataclass(frozen=True)
class RequirementOutcome:
    requirement_id: str
    label: str
    tier: str
    kind: str
    status: str                 # satisfied | missing (essential only) | not_demonstrated (supporting) | incorrect | undetermined
    detail: Dict


@dataclass(frozen=True)
class Dimension:
    name: str
    weight: int
    level: Optional[int]
    level_min: Optional[int]
    level_max: Optional[int]
    derivation: str
    inputs: Dict

    @property
    def determined(self) -> bool:
        return self.level is not None


def _lvl(f: float) -> int:
    return 4 if f >= 0.999999 else 3 if f >= 0.75 else 2 if f >= 0.5 else 1 if f > 0 else 0


def requirement_outcomes(req_set: RequirementSet, verdicts: Tuple[VerifiedVerdict, ...]) -> List[RequirementOutcome]:
    by: Dict[str, List[VerifiedVerdict]] = {}
    for v in verdicts:
        by.setdefault(v.requirement_id, []).append(v)
    out = []
    for r in req_set.requirements:
        vs = by.get(r.id, [])
        if not r.is_group:
            st = vs[0].state if vs else U
            status = {C: "satisfied", N: "missing", X: "incorrect", U: "undetermined"}[st]
            if r.tier is not Tier.ESSENTIAL and status == "missing":
                status = "not_demonstrated"          # supporting concepts are never 'missing': absence is neutral, never an omission
            out.append(RequirementOutcome(r.id, r.label, r.tier.value, r.kind, status, {"state": st.value, "claim_ids": list(vs[0].claim_ids) if vs else []}))
            continue
        listed = [v for v in vs if v.member != OTHER_VALID]
        other = [v for v in vs if v.member == OTHER_VALID]
        correct = [v for v in listed if v.state is C] + [v for v in other if v.state is C]
        unv = [v for v in listed if v.state is U]
        wrong = [v for v in listed if v.state is X]
        other_absent = any(v.state is N for v in other) and not any(v.state is U for v in other)
        if len(correct) >= r.min_required:
            status = "satisfied"
        elif not other_absent:
            status = "undetermined"
        elif len(correct) + len(unv) < r.min_required:
            status = "missing"
        else:
            status = "undetermined"
        out.append(RequirementOutcome(r.id, r.label, r.tier.value, r.kind, status, {
            "min_required": r.min_required, "correct_members": [v.member if v.member != OTHER_VALID else v.proposed_member for v in correct],
            "unverified_members": [v.member for v in unv], "incorrect_members": [v.member for v in wrong], "other_valid_absent_confirmed": other_absent}))
    return out


def correctness(verdicts: Tuple[VerifiedVerdict, ...]) -> Dimension:
    c = len([v for v in verdicts if v.state is C])
    xs = [v for v in verdicts if v.state is X]
    i = len(xs)
    inp = {"verified_correct": c, "verified_incorrect": i, "major_errors": sum(1 for v in xs if v.severity == "major")}
    if c == 0 and i == 0:
        return Dimension("correctness", WEIGHTS["correctness"], None, None, None, "no statement about any requirement was verified either way (insufficient evidence; not scored as low)", inp)
    if i == 0:
        lvl, why = 4, f"{c} requirement statement(s) verified correct, none verified incorrect"
    elif inp["major_errors"]:
        lvl, why = (1 if c else 0), f"{inp['major_errors']} verified major error(s); {c} correct"
    else:
        share = c / (c + i)
        lvl, why = (3 if share >= 0.75 else 2 if share >= 0.5 else 1), f"{i} verified minor error(s) vs {c} correct (share {share:.2f})"
    return Dimension("correctness", WEIGHTS["correctness"], lvl, lvl, lvl, why, inp)


def completeness(req_set: RequirementSet, outcomes: List[RequirementOutcome]) -> Dimension:
    ess = [o for o in outcomes if o.tier == Tier.ESSENTIAL.value]
    counts = {k: sum(1 for o in ess if o.status == k) for k in ("satisfied", "missing", "incorrect", "undetermined")}
    if req_set.penalty_mode != "full":
        return Dimension("completeness", WEIGHTS["completeness"], None, None, None,
                         "advisory only: this record's concept tiers are not penalty-eligible, so omissions are reported but not scored", {**counts, "mode": "advisory"})
    # An essential concept stated INCORRECTLY is not demonstrated, so it does not count as satisfied; it is still reported as 'incorrect'
    # (a correctness finding), never as 'missing'. Only unverified items are left out of the pessimistic/optimistic bounds.
    total = counts["satisfied"] + counts["missing"] + counts["incorrect"] + counts["undetermined"]
    if total == 0:
        return Dimension("completeness", WEIGHTS["completeness"], None, None, None, "no essential requirement could be assessed", {**counts, "mode": "full"})
    lo, hi = _lvl(counts["satisfied"] / total), _lvl((counts["satisfied"] + counts["undetermined"]) / total)
    inp = {**counts, "mode": "full", "considered": total}
    if lo == hi:
        return Dimension("completeness", WEIGHTS["completeness"], lo, lo, hi, f"{counts['satisfied']}/{total} essential requirement(s) demonstrated correctly, {counts['missing']} confirmed missing, {counts['incorrect']} stated incorrectly", inp)
    return Dimension("completeness", WEIGHTS["completeness"], None, lo, hi,
                     f"undetermined: {counts['undetermined']} essential requirement(s) unverified; level would be {lo}..{hi} (not scored as low)", inp)


def relevance(verdicts: Tuple[VerifiedVerdict, ...], on_topic: str, lexical: float) -> Dimension:
    credited = any(v.state is C for v in verdicts)
    blamed = any(v.state is X for v in verdicts)
    inp = {"credited": credited, "blamed": blamed, "on_topic_verifier": on_topic, "lexical_overlap": round(lexical, 3)}
    if credited:
        return Dimension("relevance", WEIGHTS["relevance"], 4, 4, 4, "answer demonstrably addresses at least one requirement (verified)", inp)
    if blamed:
        return Dimension("relevance", WEIGHTS["relevance"], 3, 3, 3, "answer engages the topic but only with verified errors", inp)
    if on_topic == "off_topic" and lexical < OFF_TOPIC_LEXICAL_MAX:
        return Dimension("relevance", WEIGHTS["relevance"], 0, 0, 0, f"verifier says off-topic and lexical overlap {lexical:.2f} < {OFF_TOPIC_LEXICAL_MAX} corroborates it", inp)
    return Dimension("relevance", WEIGHTS["relevance"], None, None, None, "no verified engagement and no corroborated off-topic finding (insufficient evidence; not scored as low)", inp)


def reasoning(req_set: RequirementSet, reasoning_ids: Optional[Tuple[str, ...]]) -> Dimension:
    if not req_set.reasoning_expected:
        return Dimension("reasoning", WEIGHTS["reasoning"], 4, 4, 4, "question does not call for a mechanism or trade-off; full marks by rubric convention (no penalty)", {"expected": False})
    need = 2 if req_set.question_type in STRUCTURED_TYPES else 1
    if reasoning_ids is None:
        return Dimension("reasoning", WEIGHTS["reasoning"], None, None, None, "reasoning expected but the verifier did not assess it (insufficient evidence)", {"expected": True, "needed": need})
    n = len(reasoning_ids)
    lvl = 4 if n >= need else 3 if n >= 1 else 1
    return Dimension("reasoning", WEIGHTS["reasoning"], lvl, lvl, lvl, f"{n} verified reasoning claim(s); {need} needed for full level", {"expected": True, "needed": need, "claim_ids": list(reasoning_ids)})


def _score(levels: Dict[str, int]) -> int:
    return int(round(sum(WEIGHTS[k] * levels[k] / 4 for k in WEIGHTS)))


def _cap(score: int, levels: Dict[str, int], verdicts: Tuple[VerifiedVerdict, ...]) -> Tuple[int, List[str]]:
    notes = []
    if levels["relevance"] == 0 and score > 10:
        notes.append(f"relevance=0 (verified off-topic): score capped {score}->10"); score = 10
    if any(v.state is X and v.severity == "major" for v in verdicts) and score > 60:
        notes.append(f"verified major factual error: score capped {score}->60"); score = 60
    return score, notes


@dataclass(frozen=True)
class RubricResult:
    score: Optional[int]
    score_range: Optional[Tuple[int, int]]
    dimensions: Tuple[Dimension, ...]
    adjustments: Tuple[str, ...]
    abstain_reasons: Tuple[str, ...]


def compute(req_set: RequirementSet, outcomes: List[RequirementOutcome], verdicts: Tuple[VerifiedVerdict, ...], on_topic: str,
            reasoning_ids: Optional[Tuple[str, ...]], seg: Segmentation, question: str) -> RubricResult:
    terms = question + " " + " ".join(r.label for r in req_set.requirements)
    dims = (correctness(verdicts), completeness(req_set, outcomes), relevance(verdicts, on_topic, lexical_overlap(terms, seg)), reasoning(req_set, reasoning_ids))
    undetermined = [d for d in dims if not d.determined]
    if req_set.penalty_mode != "full":
        return RubricResult(None, None, dims, (), ("advisory_only: scope tiers not penalty-eligible",))
    if undetermined:
        rng = None
        if all(d.level_min is not None and d.level_max is not None for d in dims):
            lo = _score({d.name: d.level_min for d in dims}); hi = _score({d.name: d.level_max for d in dims})
            rng = (lo, hi)
        return RubricResult(None, rng, dims, (), tuple(f"{d.name} undetermined" for d in undetermined))
    levels = {d.name: d.level for d in dims}
    s = _score(levels)
    s, notes = _cap(s, levels, verdicts)
    return RubricResult(max(0, min(100, s)), None, dims, tuple(notes), ())
