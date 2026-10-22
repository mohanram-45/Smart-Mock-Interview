"""MOCK verifiers (offline contract testing). Their outputs say NOTHING about real verification quality: ScriptedVerifier returns exactly
what a test scripted, and LexicalMockVerifier is a deliberately weak stand-in that can only credit obvious word overlap and otherwise
abstains. Every result produced through them carries provenance.is_mock = True. They are never evidence of grading accuracy."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

from .claims import content_stems
from .requirements import OTHER_VALID
from .verification import (ConceptState, ConceptVerifier, RawVerdict, RawVerification, VerificationRequest, VerifierError)

Behaviour = Union[RawVerification, BaseException, Callable[[VerificationRequest], RawVerification]]


class ScriptedVerifier(ConceptVerifier):
    name = "mock_scripted"
    is_mock = True
    model = "mock-scripted"

    def __init__(self, behaviour: Behaviour | Sequence[Behaviour]):
        self.script = list(behaviour) if isinstance(behaviour, (list, tuple)) else [behaviour]
        self.requests: List[VerificationRequest] = []

    def verify(self, request: VerificationRequest) -> RawVerification:
        i = len(self.requests)
        self.requests.append(request)
        item = self.script[min(i, len(self.script) - 1)]
        if callable(item) and not isinstance(item, (RawVerification, BaseException)):
            item = item(request)
        if isinstance(item, BaseException):
            raise item
        return item


def _resolve_claims(request: VerificationRequest, sel) -> Tuple[str, ...]:
    """sel: claim id ('c2'), 'text:<substring>' (first claim containing it), or a list of those."""
    out = []
    for s in ([sel] if isinstance(sel, str) else list(sel or [])):
        if s.startswith("text:"):
            sub = s[5:].lower()
            out += [c.id for c in request.claims if sub in c.text.lower()][:1]
        else:
            out.append(s)
    return tuple(out)


def scripted(spec: Dict[str, tuple], *, default: str = "unverified", on_topic: str = "on_topic",
             reasoning: Optional[Sequence[str]] = None, notes: Sequence[str] = ()) -> Callable[[VerificationRequest], RawVerification]:
    """Build a behaviour from a readable spec: {member_label: (state, claim_selector, [explanation, reference_quote, severity])}.
    Keys may be a member/concept label or 'requirement_label::member'. '__other_valid__' keys: ('states_correctly', sel, name)."""
    def run(request: VerificationRequest) -> RawVerification:
        verdicts = []
        for rid, member in request.expected_keys():
            req = next(r for r in request.requirements if r.id == rid)
            hit = spec.get(f"{req.label}::{member}") or spec.get(member if member != OTHER_VALID else f"{req.label}::{OTHER_VALID}") or spec.get(rid + "::" + member)
            if hit is None:
                verdicts.append(RawVerdict(rid, member, default)); continue
            state, sel, *rest = hit
            expl = rest[0] if rest else ""
            quote = rest[1] if len(rest) > 1 else ""
            sev = rest[2] if len(rest) > 2 else "minor"
            prop = expl if member == OTHER_VALID else ""
            verdicts.append(RawVerdict(rid, member, state, _resolve_claims(request, sel), "" if member == OTHER_VALID else expl, quote, sev, prop))
        rc = None if reasoning is None else _resolve_claims(request, list(reasoning))
        return RawVerification(tuple(verdicts), on_topic, rc, tuple(notes))
    return run


class LexicalMockVerifier(ConceptVerifier):
    """Weak mock for contract/coverage runs only. Credits a member when (almost) all of its content stems occur in one claim; otherwise
    returns UNVERIFIED. It NEVER returns not_stated or states_incorrectly because word overlap cannot establish technical correctness
    or absence, so a run through it mostly demonstrates abstention behaviour."""
    name = "mock_lexical"
    is_mock = True
    model = "mock-lexical"

    def verify(self, request: VerificationRequest) -> RawVerification:
        out = []
        for rid, member in request.expected_keys():
            if member == OTHER_VALID:
                out.append(RawVerdict(rid, member, "unverified")); continue
            ms = content_stems(member)
            hit = None
            for c in request.claims:
                cs = content_stems(c.text)
                if ms and len(ms & cs) >= max(1, -(-4 * len(ms) // 5)):
                    hit = c.id; break
            out.append(RawVerdict(rid, member, "states_correctly", (hit,)) if hit else RawVerdict(rid, member, "unverified"))
        return RawVerification(tuple(out), "unclear", None, ("lexical mock: overlap is not verification",))
