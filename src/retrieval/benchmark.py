"""Benchmark lexical vs semantic retrieval on the independent eval set; writes JSON + Markdown."""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .corpus import load_corpus
from .evaluate import evaluate_retriever, load_eval_set
from .factory import CACHE_DIR, EVAL_PATH, ROOT, index_dir, make_embedder
from .index import VectorIndex
from .hybrid import HybridRetriever
from .retriever import LexicalRetriever, SemanticRetriever

METRICS = ["success@1", "success@3", "success@5", "recall@1", "recall@3", "recall@5", "mrr@10", "ndcg@5"]


def _rss_mb() -> Optional[float]:
    """Peak process memory in MB, or None when it cannot be measured on this platform.

    `resource` is Unix-only (absent on Windows), so it is imported lazily. Order: resource (Linux/macOS peak RSS),
    then psutil if already installed (Windows peak working set, else current RSS), else None. Never raises.
    """
    try:
        import resource  # Unix only
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024
    except Exception:
        pass
    try:
        import psutil  # optional; not a project requirement
        mi = psutil.Process().memory_info()
        return getattr(mi, "peak_wset", mi.rss) / (1024 * 1024)
    except Exception:
        return None


def _dir_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in p.glob("*") if f.is_file())


def run(backend: str = "minilm", model_name: str = "sentence-transformers/all-MiniLM-L6-v2", doc_modes=("q", "qk", "qka"), eval_path: Path = EVAL_PATH,
        union_path: Path | None = None, use_cache: bool = True, local_files_only: bool = False) -> Dict[str, Any]:
    corpus = load_corpus()
    R = corpus["records"]
    ev = load_eval_set(eval_path)
    union = load_eval_set(union_path) if union_path and Path(union_path).exists() else None
    out: Dict[str, Any] = {
        "backend": backend, "env": {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count()},
        "corpus_sha256": corpus["manifest"]["corpus_sha256"], "n_records": len(R), "n_queries": len(ev),
        "eval_set": str(Path(eval_path).relative_to(ROOT)) if Path(eval_path).is_relative_to(ROOT) else str(eval_path),
        "systems": {}}
    for mode in doc_modes:
        t0 = time.perf_counter()
        lex = LexicalRetriever(R, mode)
        lex_build = time.perf_counter() - t0
        res = evaluate_retriever(lex, ev)
        res["build_seconds"] = round(lex_build, 4)
        if union:
            res["sensitivity_union_labels"] = evaluate_retriever(lex, union)["overall"]
        out["systems"][f"bm25_{mode}"] = res
        t0 = time.perf_counter()
        emb = make_embedder(backend, R, mode, model_name, local_files_only=local_files_only)
        load_s = time.perf_counter() - t0
        rss0 = _rss_mb()
        vi = VectorIndex.build(R, emb, mode, cache_dir=CACHE_DIR / "bench" if use_cache else None)
        d = index_dir(backend, mode, emb.config())
        vi.save(d)
        sem = SemanticRetriever(R, vi, emb)
        res = evaluate_retriever(sem, ev)
        res["embedder"] = emb.config()
        res["model_load_seconds"] = round(load_s, 3)
        res["index_build"] = vi.meta["build_stats"]
        res["index_bytes"] = _dir_bytes(d)
        res["vector_bytes_theoretical"] = len(R) * vi.index.d * 4
        rss = _rss_mb()
        res["peak_rss_mb_after_build"] = None if rss is None else round(rss, 1)
        if union:
            res["sensitivity_union_labels"] = evaluate_retriever(sem, union)["overall"]
        out["systems"][f"{backend}_{mode}"] = res
        hyb = HybridRetriever(lex, sem)
        hres = evaluate_retriever(hyb, ev)
        hres["fusion"] = {"method": "rrf", "rrf_k": hyb.rrf_k, "depth": hyb.depth, "weights": list(hyb.weights)}
        out["systems"][f"hybrid_{backend}_{mode}"] = hres
    out["model"] = model_name if backend == "minilm" else "dev-lsa (tfidf+svd, NOT a SentenceTransformer)"
    return out


def _f(x) -> str:
    return "-" if x is None else f"{x:.3f}"


def to_markdown(out: Dict[str, Any]) -> str:
    L = [f"# Retrieval benchmark ({out['backend']})", "",
         f"Corpus {out['n_records']} records (sha {out['corpus_sha256'][:12]}), {out['n_queries']} queries, python {out['env']['python']}, {out['env']['cpus']} CPUs.", "",
         "## Overall (primary relevance = grade 2, consensus labels)", "",
         "| System | " + " | ".join(METRICS) + " | lat p50 ms | lat p95 ms | unjudged@10 |", "|---|" + "---:|" * (len(METRICS) + 3)]
    for name, r in out["systems"].items():
        o = r["overall"]
        L.append(f"| {name} | " + " | ".join(_f(o[m]) for m in METRICS) + f" | {r['latency_ms']['median']:.2f} | {r['latency_ms']['p95']:.2f} | {_f(r['unjudged_fraction_in_top10'])} |")
    for name, r in out["systems"].items():
        L += ["", f"### {name}: by category", "", "| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |", "|---|---:|---:|---:|---:|---:|"]
        for c, o in r["by_category"].items():
            L.append(f"| {c} | {o['n_queries']} | {_f(o['success@1'])} | {_f(o['success@5'])} | {_f(o['mrr@10'])} | {_f(o['ndcg@5'])} |")
        L += ["", f"{name}: by domain", "", "| domain | n | success@1 | success@5 | mrr@10 |", "|---|---:|---:|---:|---:|"]
        for c, o in r["by_domain"].items():
            L.append(f"| {c} | {o['n_answerable']} | {_f(o['success@1'])} | {_f(o['success@5'])} | {_f(o['mrr@10'])} |")
        na = r["no_answer"]
        L += ["", f"{name}: no-answer queries n={na['n']}; top-1 score AUROC (answerable vs no-answer) = {_f(na['top1_score_auroc_answerable_vs_no_answer'])}; "
              f"share of no-answer queries scoring above the answerable median = {_f(na['frac_no_answer_top1_above_answerable_median'])}"]
    return "\n".join(L) + "\n"
