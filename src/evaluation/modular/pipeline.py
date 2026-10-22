"""Modular evaluator (stages A-E). Orchestration only; each stage lives in its own module and is tested separately.

  A segment (claims.py) -> B requirements (scope.py, requirements.py) -> C verify (verification.py, via a ConceptVerifier)
  -> validate -> D consistency (consistency.py) -> E deterministic rubric (rubric_engine.py).  F feedback (feedback.py) runs AFTER, separately.

Statuses (nothing is ever scored from a failure):
  scored            eligible record, all four dimensions derived from verified findings -> numeric score
  advisory_only     record's tiers are not penalty-eligible: verified findings and feedback, NO numeric score
  abstained         eligible record but evidence insufficient/undetermined: NO numeric score (optionally an informational range)
  not_gradable      empty / non-answer / instruction-only text: no verifier call
  provider_error | invalid_response   the verifier failed: NO score, no penalty
  scope_unavailable no sidecar record for the question id
This module is NOT wired into Flask. Legacy scoring remains the default and is untouched.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from . import consistency, rubric_engine as RE
from .claims import Segmentation, segment
from .reference import ReferenceMaterial
from .requirements import RequirementSet, build_requirements
from .scope import ScopeRecord, ScopeStore, ScopeUnavailable
from .verification import (ConceptState, ConceptVerifier, VerifiedVerdict, VerifierError, VerifierInvalidResponse, VerifierProviderError, build_request, validate)

PIPELINE_VERSION = "3c1.0"
INFO_FLAGS = {"scope_ai_reviewed_not_human_verified", "scope_not_human_verified"}


class ModularStatus(str, Enum):
    SCORED = "scored"
    ADVISORY_ONLY = "advisory_only"
    ABSTAINED = "abstained"
    NOT_GRADABLE = "not_gradable"
    PROVIDER_ERROR = "provider_error"
    INVALID_RESPONSE = "invalid_response"
    SCOPE_UNAVAILABLE = "scope_unavailable"


@dataclass(frozen=True)
class ModularResult:
    question_id: str
    status: ModularStatus
    score: Optional[int]
    score_range: Optional[Tuple[int, int]]
    confidence: str                                  # high | medium | low | none
    penalty_mode: str                                # full | advisory | n/a
    dimensions: Tuple[RE.Dimension, ...] = ()
    outcomes: Tuple[RE.RequirementOutcome, ...] = ()
    verdicts: Tuple[VerifiedVerdict, ...] = ()
    claims: Tuple[Dict[str, Any], ...] = ()
    flags: Tuple[str, ...] = ()
    uncertainty_flags: Tuple[str, ...] = ()
    abstain_reasons: Tuple[str, ...] = ()
    adjustments: Tuple[str, ...] = ()
    background_concepts: Tuple[str, ...] = ()
    error: Optional[Dict[str, Any]] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        def conv(o):
            if isinstance(o, Enum):
                return o.value
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [conv(v) for v in o]
            return o
        return conv(asdict(self))

    @property
    def scored(self) -> bool:
        return self.score is not None


def _confidence(status: ModularStatus, verdicts, flags, scope_flags, seg: Segmentation) -> str:
    if status in (ModularStatus.NOT_GRADABLE, ModularStatus.PROVIDER_ERROR, ModularStatus.INVALID_RESPONSE, ModularStatus.SCOPE_UNAVAILABLE):
        return "none"
    n = max(len(verdicts), 1)
    unv = sum(1 for v in verdicts if v.state is ConceptState.UNVERIFIED)
    risky = {"contradictory_verdicts", "verifier_contradicted_itself", "verifier_output_echoes_instruction", "off_topic_contradicted_by_credit"}
    if status is ModularStatus.ABSTAINED:
        return "low"
    if unv / n >= 0.34 or (risky & set(flags)):
        return "low"
    soft = [f for f in scope_flags if f not in INFO_FLAGS] + [f for f in flags if f in {"mixed_claim_correct_and_incorrect", "model_proposed_member_not_in_sidecar"}]
    if unv or soft or "injection_detected" in seg.flags or any("evidence_is_list_only" in v.flags for v in verdicts):
        return "medium"
    return "high"


class ModularEvaluator:
    def __init__(self, scope: ScopeStore, verifier: ConceptVerifier, *, max_retries: int = 0):
        self.scope = scope
        self.verifier = verifier
        self.max_retries = max(0, int(max_retries))

    # ------------------------------------------------------------------------------------------------ helpers
    def _prov(self, scope_rec: Optional[ScopeRecord], extra: Optional[dict] = None) -> Dict[str, Any]:
        p = {"pipeline_version": PIPELINE_VERSION, "engine_version": RE.ENGINE_VERSION, "scope_sidecar_sha256": self.scope.sidecar_sha256,
             "scope_verification_status": scope_rec.verification_status if scope_rec else None,
             "scope_tier_source": scope_rec.tier_source if scope_rec else None, "scope_human_verified": False,
             "verifier": self.verifier.name, "verifier_model": getattr(self.verifier, "model", ""), "is_mock": bool(self.verifier.is_mock),
             "paid_provider": bool(self.verifier.paid), "human_validated": False}
        p.update(extra or {})
        return p

    def _fail(self, qid, status, error=None, rec=None, flags=(), scope_flags=(), claims=(), extra=None, mode="n/a") -> ModularResult:
        return ModularResult(qid, status, None, None, "none", mode, flags=tuple(flags), uncertainty_flags=tuple(scope_flags), claims=tuple(claims),
                             error=error, provenance=self._prov(rec, extra))

    # ------------------------------------------------------------------------------------------------ main
    def evaluate(self, question_id: str, question: str, candidate_answer: str, reference: ReferenceMaterial) -> ModularResult:
        try:
            rec = self.scope.get(question_id)
        except ScopeUnavailable as e:
            return self._fail(question_id, ModularStatus.SCOPE_UNAVAILABLE, {"code": "scope_unavailable", "message": str(e)})
        seg = segment(candidate_answer)
        claims_view = tuple({"id": c.id, "text": c.text, "start": c.start, "end": c.end, "kind": c.kind, "flags": list(c.flags)} for c in seg.claims)
        req_set = build_requirements(rec, question)
        if not seg.is_attempt:
            why = next((f for f in ("empty", "non_answer", "instruction_only") if f in seg.flags), "no_gradable_text")
            return self._fail(question_id, ModularStatus.NOT_GRADABLE, {"code": why, "message": f"answer is not gradable: {why}"}, rec, seg.flags,
                              req_set.scope_flags, claims_view, {"manipulation_hits": list(seg.manipulation_hits)}, req_set.penalty_mode)
        if not req_set.requirements:
            return ModularResult(question_id, ModularStatus.ABSTAINED, None, None, "low", req_set.penalty_mode, flags=seg.flags, claims=claims_view,
                                 uncertainty_flags=req_set.scope_flags, abstain_reasons=("no_requirements_in_scope",), provenance=self._prov(rec))
        request = build_request(req_set, question, seg, reference)
        t0 = time.time()
        raw, err = None, None
        for attempt in range(self.max_retries + 1):
            try:
                raw = self.verifier.verify(request); err = None; break
            except VerifierInvalidResponse as e:
                err = ("invalid_response", e); break
            except VerifierProviderError as e:
                err = ("provider_error", e)
                if not e.retryable:
                    break
            except VerifierError as e:
                err = ("provider_error", e); break
            except Exception as e:             # a verifier bug must never become a score
                err = ("provider_error", e); break
        ms = round((time.time() - t0) * 1000, 1)
        if raw is None:
            kind, e = err
            st = ModularStatus.INVALID_RESPONSE if kind == "invalid_response" else ModularStatus.PROVIDER_ERROR
            return self._fail(question_id, st, {"code": getattr(e, "code", type(e).__name__), "message": str(e)[:300], "retryable": bool(getattr(e, "retryable", False))},
                              rec, seg.flags, req_set.scope_flags, claims_view, {"verifier_ms": ms}, req_set.penalty_mode)
        validated = validate(request, raw)
        cons = consistency.check(validated, seg)
        outcomes = RE.requirement_outcomes(req_set, cons.verdicts)
        rub = RE.compute(req_set, outcomes, cons.verdicts, cons.on_topic, cons.reasoning_claim_ids, seg, question)
        flags = tuple(dict.fromkeys(list(seg.flags) + list(cons.flags) + (["code_or_sql_not_executed"] if any("code_or_sql" in f for f in req_set.scope_flags) else [])))
        if req_set.penalty_mode != "full":
            status = ModularStatus.ADVISORY_ONLY
        elif rub.score is None:
            status = ModularStatus.ABSTAINED
        else:
            status = ModularStatus.SCORED
        conf = _confidence(status, cons.verdicts, flags, req_set.scope_flags, seg)
        return ModularResult(question_id, status, rub.score, rub.score_range, conf, req_set.penalty_mode, rub.dimensions, tuple(outcomes), cons.verdicts, claims_view,
                             flags, req_set.scope_flags, rub.abstain_reasons, rub.adjustments + cons.adjustments, req_set.background, None,
                             self._prov(rec, {"verifier_ms": ms, "dropped_verdicts": list(validated.dropped)}))
