"""Process-wide retrieval service for the Flask integration (curated mode only).

* Corpus is loaded and integrity-checked once (strict). Failure -> CorpusUnavailable (HTTP 503), never a silent legacy fallback.
* The embedding model and FAISS index are loaded ONCE, lazily on the first semantic search (or via warm()), under a lock.
* If the model/faiss/index cannot be used, the service degrades to BM25 over the SAME curated records and says so
  (``mode == 'bm25_fallback'`` + ``degraded_reason``) in every response. A stale/corrupt index gets ONE rebuild attempt.
* Only the retrieval stack is touched here; no scoring code is imported.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DOC_MODE = "qk_concise"               # Stage 2C-final selected embedding-text format (override: SMART_RETRIEVAL_DOC_FORMAT=qka|qk)
DOC_FORMATS_ALLOWED = ("qk_concise", "qka", "qk")      # 'question'-only is deliberately not offered: measurably worse
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class CorpusUnavailable(RuntimeError):
    """The curated corpus failed to load or validate."""


class RetrievalInputError(ValueError):
    """Bad caller input (maps to HTTP 400)."""


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


class RetrievalService:
    def __init__(self, root: Optional[Path] = None, backend: Optional[str] = None, model_name: Optional[str] = None,
                 local_files_only: Optional[bool] = None, index_root: Optional[Path] = None, cache_dir: Optional[Path] = None,
                 doc_mode: Optional[str] = None):
        self.root = Path(root) if root else None
        self.backend = backend or os.environ.get("SMART_RETRIEVAL_BACKEND", "minilm")
        self.model_name = model_name or os.environ.get("SMART_RETRIEVAL_MODEL", MODEL_NAME)
        # default True: a request must never trigger a surprise network download of the model
        self.local_files_only = _env_bool("SMART_RETRIEVAL_LOCAL_ONLY", True) if local_files_only is None else local_files_only
        self.doc_mode = doc_mode or os.environ.get("SMART_RETRIEVAL_DOC_FORMAT", DOC_MODE)
        if self.doc_mode not in DOC_FORMATS_ALLOWED:
            raise ValueError(f"SMART_RETRIEVAL_DOC_FORMAT must be one of {DOC_FORMATS_ALLOWED}, got {self.doc_mode!r}")
        self.index_root = index_root
        self.cache_dir = cache_dir
        self._lock = threading.RLock()
        self._corpus: Optional[Dict[str, Any]] = None
        self._corpus_error: Optional[str] = None
        self._semantic = None
        self._lexical = None
        self._sem_error: Optional[str] = None
        self._sem_attempted = False
        self.index_rebuilt = False
        self.timings: Dict[str, float] = {}
        self.sem_loads = 0                 # how many times the model+index were built/loaded (must stay <= 1 per reset)
        self.requests = 0

    # ---------------- corpus ----------------
    def corpus(self) -> Dict[str, Any]:
        if self._corpus is not None:
            return self._corpus
        with self._lock:
            if self._corpus is not None:
                return self._corpus
            if self._corpus_error is not None:
                raise CorpusUnavailable(self._corpus_error)
            t0 = time.perf_counter()
            try:
                from .corpus import load_corpus
                self._corpus = load_corpus(self.root, strict=True)
            except Exception as exc:                                    # integrity failure of ANY kind
                self._corpus_error = f"curated corpus unavailable: {type(exc).__name__}: {str(exc)[:300]}"
                logger.error(self._corpus_error)
                raise CorpusUnavailable(self._corpus_error) from exc
            self.timings["corpus_load_s"] = round(time.perf_counter() - t0, 3)
            self._by_id = {r["question_id"]: r for r in self._corpus["records"]}
            self.domains = sorted({r["domain"] for r in self._corpus["records"]})
            return self._corpus

    def records(self) -> List[Dict[str, Any]]:
        return self.corpus()["records"]

    def get(self, question_id: str) -> Optional[Dict[str, Any]]:
        self.corpus()
        return self._by_id.get(question_id)

    # ---------------- retrievers ----------------
    def _lex(self):
        if self._lexical is None:
            with self._lock:
                if self._lexical is None:
                    from .retriever import LexicalRetriever
                    t0 = time.perf_counter()
                    self._lexical = LexicalRetriever(self.records(), "qka")     # BM25 fallback: full text, needs no tokenizer
                    self.timings["bm25_build_s"] = round(time.perf_counter() - t0, 4)
        return self._lexical

    def _load_semantic(self):
        """Build/load embedder + index exactly once. Never raises: failure is recorded and BM25 is used."""
        with self._lock:
            if self._sem_attempted:
                return self._semantic
            self._sem_attempted = True
            records = self.records()
            try:
                from .factory import index_dir, make_embedder, CACHE_DIR
                from .index import ensure_index
                from .retriever import SemanticRetriever
                t0 = time.perf_counter()
                emb = make_embedder(self.backend, records, self.doc_mode, self.model_name, local_files_only=self.local_files_only) \
                    if self.backend == "minilm" else make_embedder(self.backend, records, self.doc_mode, self.model_name)
                self.timings["model_load_s"] = round(time.perf_counter() - t0, 3)
                d = index_dir(self.backend, self.doc_mode, emb.config())
                if self.index_root is not None:
                    d = Path(self.index_root) / d.name
                t0 = time.perf_counter()
                vi, rebuilt = ensure_index(records, emb, d, self.doc_mode, cache_dir=self.cache_dir or (CACHE_DIR / "service"))
                self.timings["index_ready_s"] = round(time.perf_counter() - t0, 3)
                self.index_rebuilt = rebuilt
                self._semantic = SemanticRetriever(records, vi, emb)
                self.sem_loads += 1
                logger.info("semantic retrieval ready (backend=%s, rebuilt_index=%s)", self.backend, rebuilt)
            except Exception as exc:                                    # ImportError(faiss), ModelLoadError, IndexMismatchError, ...
                self._sem_error = f"{type(exc).__name__}: {str(exc)[:240]}"
                self._semantic = None
                logger.warning("semantic retrieval unavailable, using BM25 fallback: %s", self._sem_error)
            return self._semantic

    def warm(self) -> Dict[str, Any]:
        self._load_semantic()
        return self.status()

    def reset(self, corpus_too: bool = False) -> None:
        with self._lock:
            self._semantic = None
            self._lexical = None
            self._sem_error = None
            self._sem_attempted = False
            self.index_rebuilt = False
            self.sem_loads = 0
            if corpus_too:
                self._corpus = None
                self._corpus_error = None

    # ---------------- status ----------------
    def status(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"backend": self.backend, "model": self.model_name if self.backend == "minilm" else f"{self.backend} (dev stand-in)",
                               "doc_mode": self.doc_mode, "bm25_fallback_doc_mode": "qka", "requests_served": self.requests, "timings_s": dict(self.timings)}
        try:
            c = self.corpus()
            out.update({"corpus_ok": True, "n_records": len(c["records"]), "corpus_sha256": c["manifest"]["corpus_sha256"], "domains": self.domains})
        except CorpusUnavailable as exc:
            out.update({"corpus_ok": False, "error": str(exc)})
            out.update({"mode": "unavailable"})
            return out
        if self._sem_attempted:
            out["mode"] = "semantic" if self._semantic is not None else "bm25_fallback"
            out["degraded_reason"] = self._sem_error
        else:
            out["mode"] = "not_loaded"      # lazy: nothing loaded until first semantic search or warm()
        out["index_rebuilt"] = self.index_rebuilt
        out["semantic_loads"] = self.sem_loads
        return out

    # ---------------- search ----------------
    def search(self, query: Any, k: Any = 5, domain: Optional[str] = None, difficulty: Optional[str] = None,
               min_score: Optional[float] = None) -> Dict[str, Any]:
        from .retriever import validate_query
        try:
            q = validate_query(query, k)
        except (TypeError, ValueError) as exc:
            raise RetrievalInputError(str(exc)) from exc
        if min_score is not None and (isinstance(min_score, bool) or not isinstance(min_score, (int, float))):
            raise RetrievalInputError("min_score must be a number")
        self.corpus()
        if domain is not None and domain not in self.domains:
            raise RetrievalInputError(f"unknown domain {domain!r}; valid: {self.domains}")
        if difficulty is not None and difficulty not in ("Easy", "Medium", "Hard"):
            raise RetrievalInputError("difficulty must be Easy, Medium or Hard")
        self.requests += 1
        t0 = time.perf_counter()
        sem = self._load_semantic()
        retriever = sem if sem is not None else self._lex()
        # over-fetch when difficulty-filtering (FAISS filters by domain natively; difficulty is applied after)
        depth = k if difficulty is None else max(k * 8, 50)
        hits = retriever.search(q, k=depth, domain=domain)
        if difficulty is not None:
            hits = [h for h in hits if h["record"]["difficulty"] == difficulty][:k]
        mode = "semantic" if sem is not None else "bm25_fallback"
        score_type = "cosine" if sem is not None else "bm25"
        thr_applied = min_score is not None and sem is not None
        results = [self._public(h, rank, score_type) for rank, h in enumerate(hits, 1)]
        if thr_applied:
            results = [r for r in results if r["score"] >= float(min_score)]
        return {"query": q, "mode": mode, "score_type": score_type, "degraded_reason": self._sem_error if mode == "bm25_fallback" else None,
                "k": k, "domain": domain, "difficulty": difficulty,
                "threshold": {"min_score": min_score, "applied": thr_applied,
                              "note": ("no calibrated default exists; the Stage 2B value was derived on the 166-query set and is not validated"
                                       if thr_applied else ("threshold ignored: only valid for cosine scores" if min_score is not None else None))},
                "no_answer": not results,                    # true whenever nothing is returned (empty retrieval, or all below an EXPLICIT min_score)
                "latency_ms": round((time.perf_counter() - t0) * 1000, 3), "results": results}

    def diagnose(self, query: Any, k: Any = 5, domain: Optional[str] = None) -> Dict[str, Any]:
        """Stage 8B: why did retrieval return what it did? Identifiers, scores, evidence band, provenance, index/model fingerprints and a BM25 cross-check.

        Built on the same search() call as normal retrieval (no second code path). Contains NO reference answers, key concepts, question text or candidate answers."""
        from . import evidence
        res = self.search(query, k, domain)
        sem = self._semantic if res["mode"] == "semantic" else None
        emb = getattr(sem, "embedder", None)
        count_tokens = getattr(emb, "count_tokens", None)
        max_len = int(getattr(emb, "max_seq_length", 0) or 256)
        sha = self.corpus()["manifest"]["corpus_sha256"]
        bm25_ids: List[str] = []
        try:
            bm25_ids = [h["question_id"] for h in self._lex().search(res["query"], k=10, domain=domain)]
        except Exception:                                           # a BM25 problem must not break diagnostics
            bm25_ids = []
        bm25_rank = evidence.rank_map(bm25_ids)
        rows = []
        for r in res["results"]:
            rec = self._by_id[r["question_id"]]
            prov = evidence.hit_provenance(rec, corpus_sha256=sha, doc_mode=self.doc_mode if sem is not None else "qka", rank_in_other=bm25_rank.get(r["question_id"]))
            cov = evidence.embedding_coverage(rec, self.doc_mode, count_tokens, max_len) if sem is not None else {"status": "not_applicable", "note": "BM25 fallback reads the full text"}
            if sem is not None and count_tokens is not None:
                cov["token_counter"] = "model tokenizer" if self.backend == "minilm" else "approximate (dev stand-in, not the real tokenizer)"
            rows.append(evidence.public_diagnostic_hit(r, prov, cov))
        meta = sem.vindex.meta if sem is not None else {}
        return {"query_chars": len(res["query"]), "mode": res["mode"], "score_type": res["score_type"], "degraded_reason": res["degraded_reason"], "k": res["k"], "domain": domain,
                "latency_ms": res["latency_ms"], "no_answer": res["no_answer"],
                "evidence": evidence.assess_evidence([r["score"] for r in res["results"]], res["score_type"]),
                "agreement": evidence.agreement([r["question_id"] for r in res["results"]], bm25_ids),
                "versions": {"corpus_sha256": sha, "embedder_config_id": meta.get("embedder_config_id"), "embedder": meta.get("embedder"), "doc_mode": meta.get("doc_mode", self.doc_mode),
                             "index_faiss_sha256": (meta.get("files") or {}).get("index.faiss"), "index_corpus_sha256": meta.get("corpus_sha256"),
                             "index_matches_corpus": (meta.get("corpus_sha256") == sha) if meta else None, "faiss_version": meta.get("faiss_version")},
                "results": rows}

    @staticmethod
    def _public(hit: Dict[str, Any], rank: int, score_type: str) -> Dict[str, Any]:
        r = hit["record"]
        return {"rank": rank, "score": hit["score"], "score_type": score_type, "question_id": r["question_id"], "domain": r["domain"],
                "topic": r["topic"], "difficulty": r["difficulty"], "question": r["question"], "key_concepts": list(r["key_concepts"]),
                "reference_answer": r["canonical_answer"]}


_service: Optional[RetrievalService] = None
_service_lock = threading.Lock()


def get_service() -> RetrievalService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = RetrievalService()
    return _service


def set_service(svc: Optional[RetrievalService]) -> None:
    """Test/demo hook."""
    global _service
    with _service_lock:
        _service = svc
