"""Consistency checking (stage D). Deterministic; runs AFTER `verification.validate`.

It can only move a verdict to UNVERIFIED (never to correct/incorrect/missing) and records why:
  * the same assertion must not get correct AND incorrect credit: via the same normalised label in two requirements, or via one claim
    cited as correct for a concept and as incorrect for an overlapping concept
  * a verdict whose own explanation echoes a candidate instruction ("ignore previous instructions", ...) is not trusted
  * on_topic='off_topic' is inconsistent with any credited concept
  * claims used as evidence of an error cannot also count as reasoning evidence
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

from ..injection import detect_injection
from .claims import Segmentation, content_stems
from .requirements import OTHER_VALID
from .verification import ConceptState, Validated, VerifiedVerdict

C, X, N, U = ConceptState.STATES_CORRECTLY, ConceptState.STATES_INCORRECTLY, ConceptState.NOT_STATED, ConceptState.UNVERIFIED


@dataclass(frozen=True)
class Consistent:
    verdicts: Tuple[VerifiedVerdict, ...]
    on_topic: str
    reasoning_claim_ids: Optional[Tuple[str, ...]]
    flags: Tuple[str, ...]
    adjustments: Tuple[str, ...]


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", (s or "").lower()).strip()


def _down(v: VerifiedVerdict, why: str) -> VerifiedVerdict:
    return replace(v, state=U, claim_ids=(), evidence=(), severity="minor", downgrade_reason=why, original_state=v.original_state or v.state.value)


def check(validated: Validated, seg: Segmentation) -> Consistent:
    vs: List[VerifiedVerdict] = list(validated.verdicts)
    adj: List[str] = []
    flags = list(validated.flags)

    # 1. echoed instructions in verifier explanations
    for i, v in enumerate(vs):
        if v.explanation and detect_injection(v.explanation):
            vs[i] = _down(v, "verdict_echoes_candidate_instruction"); adj.append(f"{v.requirement_id}/{v.member}: echoes instruction")
            flags.append("verifier_output_echoes_instruction")

    # 2. same normalised label in several requirements must agree
    by_label: Dict[str, List[int]] = {}
    for i, v in enumerate(vs):
        if v.member != OTHER_VALID:
            by_label.setdefault(_norm(v.member), []).append(i)
    for label, idxs in by_label.items():
        states = {vs[i].state for i in idxs} - {U}
        if len(states) > 1:
            for i in idxs:
                if vs[i].state is not U:
                    adj.append(f"{vs[i].requirement_id}/{vs[i].member}: inconsistent across requirements"); vs[i] = _down(vs[i], "inconsistent_across_requirements")
            flags.append("contradictory_verdicts")

    # 3. one claim credited AND blamed for overlapping concepts
    for i, a in enumerate(vs):
        if a.state is not C:
            continue
        for j, b in enumerate(vs):
            if b.state is not X or i == j or not (set(a.claim_ids) & set(b.claim_ids)):
                continue
            sa, sb = content_stems(a.member), content_stems(b.member)
            if sa and sb and len(sa & sb) / len(sa | sb) >= 0.5:
                adj.append(f"claim shared: {a.member} credited and {b.member} blamed")
                vs[i] = _down(vs[i], "same_claim_correct_and_incorrect"); vs[j] = _down(vs[j], "same_claim_correct_and_incorrect")
                flags.append("contradictory_verdicts")
                break
    # mixed claims (credited for one concept, blamed for a different one) are legitimate but lower confidence
    credited = {c for v in vs if v.state is C for c in v.claim_ids}
    blamed = {c for v in vs if v.state is X for c in v.claim_ids}
    if credited & blamed:
        flags.append("mixed_claim_correct_and_incorrect")

    on_topic = validated.on_topic
    if on_topic == "off_topic" and any(v.state is C for v in vs):
        on_topic = "unclear"; flags.append("off_topic_contradicted_by_credit"); adj.append("on_topic off_topic -> unclear")
    rc = validated.reasoning_claim_ids
    if rc is not None:
        rc = tuple(i for i in rc if i not in blamed)
    return Consistent(tuple(vs), on_topic, rc, tuple(dict.fromkeys(flags)), tuple(adj))
