"""Experimental hybrid retrieval: Reciprocal Rank Fusion (RRF) of BM25 and semantic rankings.

RRF score(d) = sum_i  w_i / (rrf_k + rank_i(d))   over the rankers that returned d (rank starts at 1).
Rank-based, so BM25 scores and cosine scores never need calibrating against each other.
Consequence: the fused score is NOT a relevance confidence; it cannot be used for no-answer detection.
Each hit therefore also carries the component scores/ranks so callers can apply a component threshold.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .retriever import _Base, validate_query


def rrf_fuse(rankings: Sequence[Sequence[str]], rrf_k: int = 60, weights: Optional[Sequence[float]] = None) -> List[tuple]:
    """Fuse ranked id lists. Returns [(id, score)] sorted by score desc, ties broken by id (deterministic)."""
    if isinstance(rrf_k, bool) or not isinstance(rrf_k, int) or rrf_k < 1:
        raise ValueError("rrf_k must be a positive integer")
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights length must match number of rankings")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    score: Dict[str, float] = {}
    for ranking, w in zip(rankings, weights):
        seen = set()
        for pos, qid in enumerate(ranking, 1):
            if qid in seen:  # a duplicate within one ranking must not be counted twice
                continue
            seen.add(qid)
            score[qid] = score.get(qid, 0.0) + w / (rrf_k + pos)
    return sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))


class HybridRetriever(_Base):
    name = "hybrid_rrf"

    def __init__(self, lexical, semantic, depth: int = 50, rrf_k: int = 60, weights: Sequence[float] = (1.0, 1.0)):
        if lexical.records is not semantic.records and [r["question_id"] for r in lexical.records] != [
                r["question_id"] for r in semantic.records]:
            raise ValueError("lexical and semantic retrievers must index the same records in the same order")
        super().__init__(semantic.records)
        if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
            raise ValueError("depth must be a positive integer")
        self.lexical, self.semantic, self.depth, self.rrf_k, self.weights = lexical, semantic, depth, rrf_k, tuple(weights)

    def search(self, query: str, k: int = 5, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        q = validate_query(query, k)
        self._check_domain(domain)
        d = max(self.depth, k)
        lex = self.lexical.search(q, d, domain)
        sem = self.semantic.search(q, d, domain)
        lrank = {h["question_id"]: h for h in lex}
        srank = {h["question_id"]: h for h in sem}
        fused = rrf_fuse([[h["question_id"] for h in lex], [h["question_id"] for h in sem]], self.rrf_k, self.weights)
        out = []
        for qid, sc in fused[:k]:
            row = self._row(qid)
            h = self._hit(len(out) + 1, row, sc)
            h["components"] = {"bm25_rank": lrank[qid]["rank"] if qid in lrank else None,
                               "bm25_score": lrank[qid]["score"] if qid in lrank else None,
                               "semantic_rank": srank[qid]["rank"] if qid in srank else None,
                               "semantic_score": srank[qid]["score"] if qid in srank else None}
            out.append(h)
        return out

    def _row(self, qid: str) -> int:
        if not hasattr(self, "_rows"):
            self._rows = {r["question_id"]: i for i, r in enumerate(self.records)}
        return self._rows[qid]
