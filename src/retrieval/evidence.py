"""Retrieval evidence, provenance and diagnostics (Stage 8B). Pure functions: no model, no index, no network.

What this is for
  * ``assess_evidence``  a DESCRIPTIVE band for how strong the best cosine score is. It is not a calibrated probability and never filters results.
  * ``embedding_coverage``  how much of a record's reference answer the embedding text actually contained (MiniLM reads only the first 256 word-pieces).
  * ``hit_provenance``  where a hit came from (question id, corpus origin, corpus fingerprint, document format) without exposing reference text.

Evidence for the band thresholds (stored Stage 2C MiniLM rankings, ``dense_qk_concise``; AI-generated pooled labels, NOT human ground truth):
  dev set (20 no-answer / 146 answerable queries): top score < 0.40 for 19/20 no-answer and 4/146 answerable queries.
  frozen challenge set (18 no-answer / 40 answerable, chosen BEFORE looking at it): < 0.40 for 10/18 no-answer and 1/40 answerable; 4/18 no-answer
  queries still scored >= 0.45. So the band catches many off-corpus queries but is not a reliable no-answer detector. It is reported as a hint only.
  The margin between the first two hits is informational only: on the dev set its median was 0.066 for correct and 0.032 for wrong top-1 hits (heavy overlap).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

BAND_INSUFFICIENT_BELOW = 0.40
BAND_WEAK_BELOW = 0.45
BAND_BASIS = (
    "descriptive, uncalibrated: chosen on the 166-query dev set (AI-pooled labels), re-checked once on the frozen challenge set where it caught 10/18 "
    "no-answer queries; not validated against human judgements; never used to hide results"
)


def assess_evidence(scores: Sequence[float], score_type: str) -> Dict[str, Any]:
    """Describe how strong the retrieved evidence looks. ``scores`` are the hit scores in rank order."""
    base = {"calibrated": False, "basis": BAND_BASIS}
    if score_type != "cosine":
        return {**base, "band": "not_available", "reason": f"{score_type} scores are not comparable across queries; no evidence band is computed (fallback mode)",
                "top_score": float(scores[0]) if scores else None, "margin": None}
    if not scores:
        return {**base, "band": "insufficient", "reason": "no results were returned", "top_score": None, "margin": None}
    top = float(scores[0])
    margin = round(top - float(scores[1]), 6) if len(scores) > 1 else None
    if top < BAND_INSUFFICIENT_BELOW:
        band, why = "insufficient", f"best cosine {top:.3f} is below {BAND_INSUFFICIENT_BELOW}: the corpus probably has no close match"
    elif top < BAND_WEAK_BELOW:
        band, why = "weak", f"best cosine {top:.3f} is between {BAND_INSUFFICIENT_BELOW} and {BAND_WEAK_BELOW}: treat the match as tentative"
    else:
        band, why = "adequate", f"best cosine {top:.3f} is at least {BAND_WEAK_BELOW}: a close match exists (this does not prove it is the right question)"
    return {**base, "band": band, "reason": why, "top_score": round(top, 6), "margin": margin}


def embedding_coverage(record: Dict[str, Any], doc_mode: str, count_tokens: Optional[Callable[[str], int]] = None, max_seq_length: int = 256) -> Dict[str, Any]:
    """How much of ``record`` the embedding text covered. Without a tokenizer (the offline stand-in backend) the answer is reported as ``unknown``.

    ``answer_sentences_embedded`` / ``answer_sentences_total`` are only meaningful for ``qk_concise`` (whole leading sentences) and ``qk`` (zero)."""
    from .doc_formats import build_text, split_sentences

    total = len(split_sentences(record.get("canonical_answer", "")))
    out: Dict[str, Any] = {"doc_mode": doc_mode, "max_seq_length": max_seq_length, "answer_sentences_total": total}
    if doc_mode == "qk":
        return {**out, "status": "answer_not_embedded", "answer_sentences_embedded": 0, "head_over_budget": None}
    if count_tokens is None:
        return {**out, "status": "unknown", "answer_sentences_embedded": None, "head_over_budget": None,
                "note": "this backend has no tokenizer, so truncation cannot be measured"}
    if doc_mode == "qk_concise":
        b = build_text(record, "qk_concise", count_tokens, max_seq_length)
        f = b["flags"]
        status = "head_truncated" if f["head_over_budget"] else ("answer_partial" if f["answer_sentences"] < total or f["answer_cut"] else "answer_complete")
        return {**out, "status": status, "answer_sentences_embedded": f["answer_sentences"], "head_over_budget": f["head_over_budget"], "answer_cut_mid_sentence": f["answer_cut"],
                "tokens": count_tokens(b["text"])}
    full = build_text(record, "qka", None, max_seq_length)["text"]
    n = count_tokens(full)
    return {**out, "status": "answer_complete" if n <= max_seq_length - 2 else "truncated_by_model", "tokens": n,
            "answer_sentences_embedded": None, "head_over_budget": None,
            "note": "qka is cut by the model itself, at an arbitrary word-piece"}


def hit_provenance(record: Dict[str, Any], *, corpus_sha256: str, doc_mode: str, rank_in_other: Optional[int] = None) -> Dict[str, Any]:
    """Where a hit comes from. Contains NO reference answer text, alternative answers or key concepts."""
    prov = record.get("provenance") or {}
    out = {"question_id": record["question_id"], "origin": prov.get("origin"), "corpus_sha256": corpus_sha256[:16], "indexed_as": doc_mode}
    if rank_in_other is not None:
        out["bm25_rank"] = rank_in_other
    return out


def agreement(semantic_ids: Sequence[str], bm25_ids: Sequence[str], k: int = 3) -> Dict[str, Any]:
    """Do the two independent rankers agree? Informational only; earlier experiments did not show that fusing them is better."""
    s, b = list(semantic_ids)[:k], list(bm25_ids)[:k]
    return {"k": k, "top1_same": bool(s and b and s[0] == b[0]), "overlap_at_k": len(set(s) & set(b)), "bm25_returned": len(bm25_ids)}


def rank_map(ids: Sequence[str]) -> Dict[str, int]:
    return {q: i for i, q in enumerate(ids, 1)}


def public_diagnostic_hit(hit: Dict[str, Any], provenance: Dict[str, Any], coverage: Dict[str, Any]) -> Dict[str, Any]:
    """A diagnostics row. Deliberately omits the question text, reference answer and key concepts: only identifiers, scores and provenance."""
    return {"rank": hit["rank"], "score": hit["score"], "question_id": hit["question_id"], "domain": hit["domain"], "topic": hit["topic"],
            "difficulty": hit["difficulty"], "provenance": provenance, "embedding_coverage": coverage}


def list_of_ids(hits: List[Dict[str, Any]]) -> List[str]:
    return [h["question_id"] for h in hits]
