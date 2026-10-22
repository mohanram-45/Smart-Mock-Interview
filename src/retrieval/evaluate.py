"""Retrieval evaluation: metric functions, benchmark runner and eval-set loading.

Eval-set record (JSONL, one query per line):
  query_id, query, category, domain (primary domain of the intended topic or null),
  relevant: {question_id: grade}  grade 2 = directly answers/covers the query,
                                  grade 1 = partially relevant / closely related,
                                  every judged id not listed has grade 0,
  judged: [question_ids that were shown to the labeller]  (pool; unjudged ids count as 0 but are reported),
  no_answer: bool  (no corpus record is relevant),
  label_method / notes: provenance of the labels.

Definitions (primary relevance = grade >= 2, "lenient" = grade >= 1):
  Success@k   fraction of answerable queries with >=1 relevant record in the top k
  Recall@k    mean over answerable queries of |relevant ∩ top-k| / |relevant|
  MRR@10      mean reciprocal rank of the first relevant record within the top 10
  nDCG@5      graded, gain = 2**grade - 1, log2 discount, ideal ranking from the labels
No-answer queries are excluded from the above and analysed separately.
"""
from __future__ import annotations

import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


def load_eval_set(path: Path | str) -> List[Dict[str, Any]]:
    out, seen = [], set()
    for ln, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        q = json.loads(line)
        for f in ("query_id", "query", "category", "relevant", "no_answer"):
            if f not in q:
                raise ValueError(f"line {ln}: missing {f}")
        if q["query_id"] in seen:
            raise ValueError(f"duplicate query_id {q['query_id']}")
        seen.add(q["query_id"])
        if q["no_answer"] and any(g > 0 for g in q["relevant"].values()):
            raise ValueError(f"{q['query_id']}: no_answer query has relevant records")
        if not q["no_answer"] and not any(g > 0 for g in q["relevant"].values()):
            raise ValueError(f"{q['query_id']}: answerable query has no relevant records")
        out.append(q)
    return out


# ---------- metric functions (pure) ----------
def _rel_set(relevant: Dict[str, int], min_grade: int) -> set:
    return {k for k, g in relevant.items() if g >= min_grade}


def success_at_k(ranked: Sequence[str], relevant: Dict[str, int], k: int, min_grade: int = 2) -> float:
    rel = _rel_set(relevant, min_grade)
    return 1.0 if rel and any(r in rel for r in ranked[:k]) else 0.0


def recall_at_k(ranked: Sequence[str], relevant: Dict[str, int], k: int, min_grade: int = 2) -> float:
    rel = _rel_set(relevant, min_grade)
    if not rel:
        return 0.0
    return len(rel & set(ranked[:k])) / len(rel)


def mrr_at_k(ranked: Sequence[str], relevant: Dict[str, int], k: int = 10, min_grade: int = 2) -> float:
    rel = _rel_set(relevant, min_grade)
    for i, r in enumerate(ranked[:k], 1):
        if r in rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: Dict[str, int], k: int = 5) -> float:
    gains = [(2 ** relevant.get(r, 0)) - 1 for r in ranked[:k]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(((2 ** g) - 1 for g in relevant.values()), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def auroc(pos: Sequence[float], neg: Sequence[float]) -> Optional[float]:
    """P(score_pos > score_neg) with ties counted half (Mann-Whitney)."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def _mean(xs: Iterable[float]) -> Optional[float]:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def _agg(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Primary metrics use queries with >=1 grade-2 record; lenient metrics and nDCG use every answerable query
    (grade >= 1 somewhere). Queries with only grade-1 records ("partial coverage") are therefore not counted as
    failures of the primary metrics."""
    ans = [r for r in rows if not r["no_answer"]]
    prim = [r for r in ans if r["has_primary"]]
    out: Dict[str, Any] = {"n_queries": len(rows), "n_answerable": len(ans), "n_primary": len(prim)}
    for k in (1, 3, 5):
        out[f"success@{k}"] = _mean(r[f"success@{k}"] for r in prim)
        out[f"recall@{k}"] = _mean(r[f"recall@{k}"] for r in prim)
        out[f"success@{k}_lenient"] = _mean(r[f"success@{k}_lenient"] for r in ans)
    out["mrr@10"] = _mean(r["mrr@10"] for r in prim)
    out["mrr@10_lenient"] = _mean(r["mrr@10_lenient"] for r in ans)
    out["ndcg@5"] = _mean(r["ndcg@5"] for r in ans)
    return out


def evaluate_retriever(retriever, eval_set: List[Dict[str, Any]], k: int = 10) -> Dict[str, Any]:
    """Run every query, return per-query rows and aggregates (overall, per category, per domain, no-answer, latency)."""
    rows, lat = [], []
    for q in eval_set:
        t0 = time.perf_counter()
        hits = retriever.search(q["query"], k=k)
        lat.append((time.perf_counter() - t0) * 1000)
        ranked = [h["question_id"] for h in hits]
        rel, judged = q["relevant"], set(q.get("judged", []))
        rows.append({
            "query_id": q["query_id"], "category": q["category"], "domain": q.get("domain"), "no_answer": q["no_answer"],
            "has_primary": any(g >= 2 for g in rel.values()),
            "ranked": ranked, "top1_score": hits[0]["score"] if hits else 0.0,
            **{f"success@{kk}": success_at_k(ranked, rel, kk) for kk in (1, 3, 5)},
            **{f"recall@{kk}": recall_at_k(ranked, rel, kk) for kk in (1, 3, 5)},
            **{f"success@{kk}_lenient": success_at_k(ranked, rel, kk, 1) for kk in (1, 3, 5)},
            "mrr@10": mrr_at_k(ranked, rel, 10), "mrr@10_lenient": mrr_at_k(ranked, rel, 10, 1),
            "ndcg@5": ndcg_at_k(ranked, rel, 5),
            "unjudged_in_top10": sum(1 for r in ranked[:10] if judged and r not in judged),
            "n_top10": len(ranked[:10]),
        })
    by_cat, by_dom = defaultdict(list), defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
        if r["domain"] and not r["no_answer"]:
            by_dom[r["domain"]].append(r)
    ans_top1 = [r["top1_score"] for r in rows if not r["no_answer"]]
    no_top1 = [r["top1_score"] for r in rows if r["no_answer"]]
    unj = sum(r["unjudged_in_top10"] for r in rows)
    tot = sum(r["n_top10"] for r in rows)
    lat_sorted = sorted(lat)
    return {
        "overall": _agg(rows),
        "by_category": {c: _agg(v) for c, v in sorted(by_cat.items())},
        "by_domain": {d: _agg(v) for d, v in sorted(by_dom.items())},
        "no_answer": {
            "n": len(no_top1),
            "mean_top1_score_no_answer": _mean(no_top1), "mean_top1_score_answerable": _mean(ans_top1),
            "top1_score_auroc_answerable_vs_no_answer": auroc(ans_top1, no_top1),
            "frac_no_answer_top1_above_answerable_median": (
                _mean(1.0 if s > statistics.median(ans_top1) else 0.0 for s in no_top1) if ans_top1 and no_top1 else None),
        },
        "unjudged_fraction_in_top10": (unj / tot) if tot else None,
        "latency_ms": {"n": len(lat), "mean": statistics.mean(lat), "median": statistics.median(lat),
                       "p95": lat_sorted[min(len(lat_sorted) - 1, int(0.95 * len(lat_sorted)))], "max": max(lat)},
        "rows": rows,
    }
