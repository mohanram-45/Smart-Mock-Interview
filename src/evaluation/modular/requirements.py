"""Question-specific requirements (stage B). Built from the sidecar only; no model involved.

Tiers: ESSENTIAL (may affect completeness, but only when the record is penalty-eligible), SUPPORTING (credit/feedback only),
BACKGROUND (feedback only; never sent to the verifier, never an omission). Label concepts restate the question topic and are dropped.
Groups express "any k of n". Uncertainty is explicit: every ambiguity flag becomes a flag on the set.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from .scope import ScopeRecord

OTHER_VALID = "__other_valid__"     # sentinel member of every group: "a valid member that is not in the sidecar list"


class Tier(str, Enum):
    ESSENTIAL = "essential"
    SUPPORTING = "supporting"


@dataclass(frozen=True)
class Requirement:
    id: str                          # E1.. (essential concept), G1.. (essential group), S1.. (supporting concept)
    kind: str                        # 'concept' | 'group'
    tier: Tier
    label: str
    members: Tuple[str, ...]         # concept: (label,); group: the listed members (OTHER_VALID is added by the verifier request)
    min_required: int = 1

    @property
    def is_group(self) -> bool:
        return self.kind == "group"


@dataclass(frozen=True)
class RequirementSet:
    question_id: str
    question_type: str
    requirements: Tuple[Requirement, ...]
    background: Tuple[str, ...]                    # feedback only
    alternatives: Tuple[Tuple[str, str], ...]      # (text, basis)
    penalty_mode: str                              # 'full' | 'advisory'
    scope_status: str                              # verification_status of the record (never human)
    scope_flags: Tuple[str, ...]                   # uncertainty flags (informational + blocking)
    reasoning_expected: bool
    human_verified: bool = False

    def essentials(self) -> Tuple[Requirement, ...]:
        return tuple(r for r in self.requirements if r.tier is Tier.ESSENTIAL)

    def supporting(self) -> Tuple[Requirement, ...]:
        return tuple(r for r in self.requirements if r.tier is Tier.SUPPORTING)

    def get(self, rid: str) -> Requirement:
        for r in self.requirements:
            if r.id == rid:
                return r
        raise KeyError(rid)


_REASONING_RX = re.compile(r"\b(why|how|explain|justify|trade-?offs?|compare|difference|versus|vs\.?|design|would you|root cause|debug|diagnos\w+|evaluate|evaluation|strategy|approach)\b", re.I)


def reasoning_expected(question: str, question_type: str) -> bool:
    """Deterministic: does the question call for a mechanism / trade-off / justification? (Definition-style questions do not.)"""
    if question_type in {"scenario", "design", "debugging", "evaluation", "business_case"}:
        return True
    return bool(_REASONING_RX.search(question or ""))


def build_requirements(scope: ScopeRecord, question: str) -> RequirementSet:
    reqs = []
    for i, c in enumerate(scope.essential_concepts, 1):
        reqs.append(Requirement(f"E{i}", "concept", Tier.ESSENTIAL, c, (c,)))
    for i, g in enumerate(scope.essential_groups, 1):
        reqs.append(Requirement(f"G{i}", "group", Tier.ESSENTIAL, g.label, tuple(g.concepts), g.min_required))
    for i, c in enumerate(scope.supporting_concepts, 1):
        reqs.append(Requirement(f"S{i}", "concept", Tier.SUPPORTING, c, (c,)))
    flags = []
    for f in scope.ambiguity_flags:
        flags.append(f"scope_ambiguity:{f}")
    if scope.human_review_required:
        flags.append("scope_requires_human_review")
    if scope.verification_status == "ai_heuristic_draft":
        flags.append("scope_unreviewed_heuristic_tiers")
    flags.append("scope_ai_reviewed_not_human_verified" if scope.verification_status == "ai_reviewed_pilot" else "scope_not_human_verified")
    if not scope.has_essentials:
        flags.append("no_essential_requirements")
    return RequirementSet(
        question_id=scope.question_id, question_type=scope.question_type, requirements=tuple(reqs), background=tuple(scope.background_concepts),
        alternatives=tuple((a.text, a.basis) for a in scope.alternatives), penalty_mode="full" if scope.penalty_eligible else "advisory",
        scope_status=scope.verification_status, scope_flags=tuple(flags), reasoning_expected=reasoning_expected(question, scope.question_type))
