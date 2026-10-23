"""Concept verification contract (stage C) and the gate that turns raw verifier output into VERIFIED verdicts.

A verifier answers one narrow question per requirement member: does some claim state it correctly, incorrectly, is it not stated,
or can't it tell? It only ever returns claim IDS; every quotation shown later is looked up from the segmentation by code, so a
verifier cannot invent a quotation. Nothing a verifier returns is trusted until `validate` has checked it:

  * evidence ids must exist; claims flagged as instructions never count as evidence
  * states_incorrectly needs an explanation AND a quote that really occurs in the reference material (else it is an unsupported
    allegation -> UNVERIFIED, never an error)
  * not_stated must not cite evidence and must not be contradicted by a lexical cross-check (cross-check can only downgrade to UNVERIFIED)
  * anything missing, malformed or inconsistent becomes UNVERIFIED = no credit, no penalty, lower confidence. It is NEVER turned into
    'incorrect' or 'missing'.
Deterministic string matching is used only as a safety cross-check here; it is not accepted as proof of technical correctness.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..evaluator import SELF_CONTRADICTING_ERROR_RX, _contains
from .claims import Claim, Segmentation, content_stems
from .reference import ReferenceMaterial
from .requirements import OTHER_VALID, Requirement, RequirementSet, Tier


class ConceptState(str, Enum):
    STATES_CORRECTLY = "states_correctly"
    STATES_INCORRECTLY = "states_incorrectly"
    NOT_STATED = "not_stated"
    UNVERIFIED = "unverified"


ON_TOPIC_VALUES = ("on_topic", "off_topic", "unclear")


# ------------------------------------------------------------------------------------------------- errors
class VerifierError(Exception):
    code = "verifier_error"
    retryable = False

    def __init__(self, message: str = "", *, cause: BaseException | None = None):
        super().__init__(message or self.code)
        self.cause = cause


class VerifierProviderError(VerifierError):
    code = "verifier_provider_error"

    def __init__(self, message: str = "", *, cause: BaseException | None = None, retryable: bool = False):
        super().__init__(message, cause=cause)
        self.retryable = retryable


class VerifierInvalidResponse(VerifierError):
    code = "verifier_invalid_response"


# ------------------------------------------------------------------------------------------------- raw contract
@dataclass(frozen=True)
class RawVerdict:
    requirement_id: str
    member: str
    state: str
    claim_ids: Tuple[str, ...] = ()
    explanation: str = ""
    reference_quote: str = ""
    severity: str = "minor"
    proposed_member: str = ""            # only for OTHER_VALID on a group


@dataclass(frozen=True)
class RawVerification:
    verdicts: Tuple[RawVerdict, ...]
    on_topic: str = "unclear"
    reasoning_claim_ids: Optional[Tuple[str, ...]] = None     # None = verifier did not assess reasoning
    notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationRequest:
    question_id: str
    question: str
    question_type: str
    requirements: Tuple[Requirement, ...]          # essential + supporting only; background is never sent
    claims: Tuple[Claim, ...]                      # gradable claims only (instruction-flagged claims are withheld)
    reference: ReferenceMaterial
    alternatives: Tuple[Tuple[str, str], ...] = ()

    def expected_keys(self) -> List[Tuple[str, str]]:
        keys = []
        for r in self.requirements:
            for m in r.members:
                keys.append((r.id, m))
            if r.is_group:
                keys.append((r.id, OTHER_VALID))
        return keys


class ConceptVerifier(ABC):
    """Narrow provider-facing interface. Implementations: MockVerifier (scripted, deterministic) and LLMConceptVerifier (adapter over an
    existing LLMProvider). They return RawVerification or raise VerifierError; they never score and never write feedback."""
    name = "verifier"
    is_mock = False
    paid = False
    model = ""

    @abstractmethod
    def verify(self, request: VerificationRequest) -> RawVerification: ...


def build_request(req_set: RequirementSet, question: str, seg: Segmentation, reference: ReferenceMaterial) -> VerificationRequest:
    return VerificationRequest(question_id=req_set.question_id, question=question, question_type=req_set.question_type,
                               requirements=tuple(r for r in req_set.requirements), claims=seg.gradable_claims,
                               reference=reference, alternatives=req_set.alternatives)


# ------------------------------------------------------------------------------------------------- verified contract
@dataclass(frozen=True)
class Evidence:
    claim_id: str
    text: str            # copied from the segmentation by code, never from the verifier
    start: int
    end: int


@dataclass(frozen=True)
class VerifiedVerdict:
    requirement_id: str
    member: str
    state: ConceptState
    claim_ids: Tuple[str, ...] = ()
    evidence: Tuple[Evidence, ...] = ()
    explanation: str = ""
    reference_quote: str = ""
    severity: str = "minor"
    proposed_member: str = ""
    original_state: str = ""
    downgrade_reason: Optional[str] = None     # set when the gate changed the verifier's state
    flags: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Validated:
    verdicts: Tuple[VerifiedVerdict, ...]
    on_topic: str
    reasoning_claim_ids: Optional[Tuple[str, ...]]
    flags: Tuple[str, ...]
    dropped: Tuple[str, ...] = ()


def _unverified(key, why, original="", explanation="") -> VerifiedVerdict:
    return VerifiedVerdict(key[0], key[1], ConceptState.UNVERIFIED, original_state=original, downgrade_reason=why, explanation=explanation)


def _lexically_present(member: str, claims: Tuple[Claim, ...]) -> bool:
    ms = content_stems(member)
    if not ms:
        return False
    have = set()
    for c in claims:
        have |= content_stems(c.text)
    need = len(ms) if len(ms) < 3 else -(-4 * len(ms) // 5)      # all stems for short labels, >= 80% for longer ones
    return len(ms & have) >= need


def _gate(v: RawVerdict, claims: Dict[str, Claim], request: VerificationRequest, ref_text: str) -> VerifiedVerdict:
    key = (v.requirement_id, v.member)
    try:
        state = ConceptState(v.state)
    except ValueError:
        return _unverified(key, "invalid_state", str(v.state))
    original = state.value
    if state is ConceptState.UNVERIFIED:
        return VerifiedVerdict(*key, ConceptState.UNVERIFIED, explanation=v.explanation, original_state=original)
    if state is ConceptState.NOT_STATED:
        if v.claim_ids:
            return _unverified(key, "not_stated_with_evidence", original)
        if v.member != OTHER_VALID and _lexically_present(v.member, tuple(claims.values())):
            return _unverified(key, "omission_contradicted_by_lexical_check", original, v.explanation)
        return VerifiedVerdict(*key, ConceptState.NOT_STATED, explanation=v.explanation, original_state=original)
    ids = tuple(dict.fromkeys(v.claim_ids))
    good = tuple(i for i in ids if i in claims)
    if not good:
        return _unverified(key, "no_valid_evidence" if not ids else "unknown_claim_ids", original)
    usable = tuple(i for i in good if "possible_instruction" not in claims[i].flags)
    if not usable:
        return _unverified(key, "evidence_only_instruction_text", original)
    ev = tuple(Evidence(i, claims[i].text, claims[i].start, claims[i].end) for i in usable)
    fl = []
    if len(usable) < len(ids):
        fl.append("some_evidence_ids_dropped")
    if all("list_only" in claims[i].flags for i in usable):
        fl.append("evidence_is_list_only")
    if state is ConceptState.STATES_INCORRECTLY:
        if not v.explanation.strip():
            return _unverified(key, "unsupported_error_allegation", original, "no explanation")
        if SELF_CONTRADICTING_ERROR_RX.search(v.explanation):
            return _unverified(key, "self_contradicting_error_allegation", original, v.explanation)
        if not _contains(ref_text, v.reference_quote):
            return _unverified(key, "error_quote_not_in_reference", original, v.explanation)
        sev = v.severity if v.severity in ("minor", "major") else "minor"
        return VerifiedVerdict(*key, state, usable, ev, v.explanation.strip(), v.reference_quote.strip(), sev, "", original, None, tuple(fl))
    if v.member == OTHER_VALID and not v.proposed_member.strip():
        return _unverified(key, "other_member_without_name", original)
    return VerifiedVerdict(*key, state, usable, ev, v.explanation.strip(), "", "minor", v.proposed_member.strip(), original, None,
                           tuple(fl + (["model_proposed_member_not_in_sidecar"] if v.member == OTHER_VALID else [])))


def validate(request: VerificationRequest, raw: RawVerification) -> Validated:
    claims = {c.id: c for c in request.claims}
    ref_text = request.reference.quote_corpus()
    expected = request.expected_keys()
    exp_set = set(expected)
    dropped: List[str] = []
    by_key: Dict[Tuple[str, str], List[RawVerdict]] = {}
    for v in raw.verdicts:
        k = (v.requirement_id, v.member)
        if k not in exp_set:
            dropped.append(f"unknown_requirement_or_member:{v.requirement_id}/{v.member}")
            continue
        by_key.setdefault(k, []).append(v)
    out: List[VerifiedVerdict] = []
    flags: List[str] = []
    for k in expected:
        vs = by_key.get(k)
        if not vs:
            out.append(_unverified(k, "verifier_omitted"))
            continue
        if k[1] == OTHER_VALID:
            seen = set()
            for v in vs:
                g = _gate(v, claims, request, ref_text)
                name = re.sub(r"\W+", " ", g.proposed_member.lower()).strip()
                if g.state is ConceptState.STATES_CORRECTLY:
                    listed = {re.sub(r"\W+", " ", m.lower()).strip() for r in request.requirements if r.id == k[0] for m in r.members}
                    if name in listed or name in seen:
                        dropped.append(f"duplicate_other_member:{g.proposed_member}")
                        continue
                    seen.add(name)
                out.append(g)
            continue
        states = {v.state for v in vs}
        if len(vs) > 1 and len(states) > 1:
            out.append(_unverified(k, "contradictory_duplicate_verdicts", ",".join(sorted(map(str, states)))))
            flags.append("verifier_contradicted_itself")
            continue
        if len(vs) > 1:
            m = vs[0]
            vs = [RawVerdict(m.requirement_id, m.member, m.state, tuple(dict.fromkeys(i for x in vs for i in x.claim_ids)), m.explanation, m.reference_quote, m.severity)]
        out.append(_gate(vs[0], claims, request, ref_text))
    on_topic = raw.on_topic if raw.on_topic in ON_TOPIC_VALUES else "unclear"
    rc = None
    if raw.reasoning_claim_ids is not None:
        rc = tuple(i for i in dict.fromkeys(raw.reasoning_claim_ids) if i in claims and "possible_instruction" not in claims[i].flags)
    return Validated(tuple(out), on_topic, rc, tuple(flags), tuple(dropped))
