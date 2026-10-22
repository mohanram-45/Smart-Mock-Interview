"""Build evaluation inputs. The reference is ALWAYS looked up by the selected question's ID (curated corpus) or taken from the
server-side session question (legacy); it is never accepted from the client and never replaced by a retrieved neighbour."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .schema import EvaluationRequest, ReferenceBundle, SupportSnippet

logger = logging.getLogger(__name__)
SUPPORT_TEXT_CHARS = 600


def reference_from_record(rec: Dict[str, Any]) -> ReferenceBundle:
    v = rec.get("verification") or {}
    if not isinstance(v, dict):
        v = {}
    cm = rec.get("common_mistakes") or []
    return ReferenceBundle(
        reference_answer=str(rec.get("canonical_answer") or ""),
        key_concepts=[str(x) for x in (rec.get("key_concepts") or [])],
        common_mistakes=[str(x) for x in cm] if isinstance(cm, list) else [str(cm)],
        alternative_answers={str(k): str(x) for k, x in (rec.get("alternative_answers") or {}).items()},
        rubric_points=str(rec.get("rubric_points") or ""),
        source="curated",
        verification=str(v.get("verification") or ""),
        human_reviewed=bool(v.get("human_reviewed")),
        code_executed=bool(v.get("code_executed")),
        source_opened=bool(v.get("source_opened")),
        time_sensitive=bool(v.get("time_sensitive")),
        review_by=str(v.get("review_by") or ""),
        remaining_limitations=str(v.get("remaining_limitations") or ""),
        provenance=dict(rec.get("provenance") or {}) if isinstance(rec.get("provenance"), dict) else {},
    )


def reference_from_legacy(q: Dict[str, Any]) -> ReferenceBundle:
    """Legacy session question dict ({id, question, reference_answer, ...}): no key concepts, no verification metadata."""
    ref = str((q or {}).get("reference_answer") or "")
    return ReferenceBundle(reference_answer=ref, source="legacy" if ref.strip() else "missing", verification="legacy_unverified",
                           remaining_limitations="legacy question bank: provenance and verification unknown")


def support_from_service(service: Any, question_id: str, question_text: str, k: int = 3, domain: Optional[str] = None) -> List[SupportSnippet]:
    """Optional retrieved knowledge, as SUPPORT ONLY. Excludes the selected question. Any failure -> [] (support is optional)."""
    try:
        res = service.search(question_text, k + 1, domain=domain)
        out: List[SupportSnippet] = []
        for h in res.get("results", []):
            hid = h.get("question_id")
            if hid == question_id:
                continue
            rec = service.get(hid) or {}
            text = " ".join(str(rec.get("canonical_answer") or "").split())[:SUPPORT_TEXT_CHARS]
            if text:
                out.append(SupportSnippet(question_id=hid, topic=str(h.get("topic") or rec.get("topic") or ""), text=text,
                                          score=h.get("score")))
            if len(out) >= k:
                break
        return out
    except Exception as exc:                                    # retrieval is optional: never break evaluation because of it
        logger.warning("supporting-knowledge retrieval skipped: %s", exc)
        return []


def build_request(question_id: str, candidate_answer: str, *, service: Any = None, legacy_question: Optional[Dict[str, Any]] = None,
                  with_support: bool = False, support_k: int = 3) -> EvaluationRequest:
    """Curated: look the record up BY ID in the service. Legacy: use the server-side session question. Unknown id -> KeyError."""
    if legacy_question is not None:
        q = legacy_question
        return EvaluationRequest(question_id=str(q.get("id", question_id)), question=str(q.get("question", "")), domain=str(q.get("domain") or ""),
                                 difficulty=str(q.get("difficulty") or ""), candidate_answer=candidate_answer,
                                 reference=reference_from_legacy(q))
    if service is None:
        raise ValueError("a retrieval service (curated corpus) or a legacy_question is required")
    rec = service.get(question_id)
    if rec is None:
        raise KeyError(f"unknown question id {question_id!r}")
    support = support_from_service(service, question_id, rec["question"], support_k, domain=rec.get("domain")) if with_support else []
    return EvaluationRequest(question_id=rec["question_id"], question=rec["question"], domain=rec.get("domain", ""), topic=rec.get("topic", ""),
                             difficulty=rec.get("difficulty", ""), candidate_answer=candidate_answer, reference=reference_from_record(rec),
                             support=support)
