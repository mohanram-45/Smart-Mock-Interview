"""Persistent exact FAISS index (IndexFlatIP on L2-normalised vectors) with stable id mapping.

Files written to the index directory (atomically, via a temp dir + rename):
  index.faiss        the FAISS index
  index_meta.json    ordered question ids, corpus fingerprint, embedder config,
                     doc_mode, dim, counts, faiss version, per-file sha256

Row i of the index is always ``ids[i]`` from the metadata; ids are the dataset
question ids. ``load`` verifies file hashes, dimensions, id order and (when a
corpus is supplied) the corpus fingerprint, and raises ``IndexMismatchError``
otherwise. ``ensure_index`` rebuilds when anything relevant changed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .corpus import corpus_fingerprint
from .documents import build_documents
from .embeddings import config_id, embed_texts

META_VERSION = 1


class IndexMismatchError(RuntimeError):
    """Index files are missing, corrupt, or do not match the corpus/embedder configuration."""


def _faiss():
    try:
        import faiss
        return faiss
    except ImportError as exc:  # pragma: no cover
        raise ImportError("faiss-cpu is required: pip install -r requirements-rag.txt") from exc


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class VectorIndex:
    def __init__(self, index, ids: List[str], domains: List[str], meta: Dict[str, Any]):
        self.index = index
        self.ids = ids
        self.domains = domains
        self.meta = meta
        self.row_of = {q: i for i, q in enumerate(ids)}
        self._domain_rows: Dict[str, np.ndarray] = {}
        for d in sorted(set(domains)):
            self._domain_rows[d] = np.array([i for i, x in enumerate(domains) if x == d], dtype=np.int64)

    # ---- build ----
    @classmethod
    def build(cls, records, embedder, doc_mode: str = "qka", cache_dir=None, batch_size: int = 32) -> "VectorIndex":
        faiss = _faiss()
        docs = build_documents(records, doc_mode, getattr(embedder, "count_tokens", None), int(getattr(embedder, "max_seq_length", 0) or 256))
        t0 = time.perf_counter()
        vecs, stats = embed_texts(embedder, [d["text"] for d in docs], batch_size, cache_dir)
        idx = faiss.IndexFlatIP(vecs.shape[1])
        idx.add(vecs)
        if idx.ntotal != len(docs):
            raise IndexMismatchError("index size != document count")
        cfg = embedder.config()
        meta = {"meta_version": META_VERSION, "ids": [d["doc_id"] for d in docs],
                "domains": [d["metadata"]["domain"] for d in docs], "corpus_sha256": corpus_fingerprint(records),
                "doc_mode": doc_mode, "embedder": cfg, "embedder_config_id": config_id(cfg), "dim": int(vecs.shape[1]),
                "n": len(docs), "faiss_version": faiss.__version__, "metric": "inner_product_on_unit_vectors",
                "build_stats": {**stats, "total_build_seconds": round(time.perf_counter() - t0, 3)}}
        return cls(idx, meta["ids"], meta["domains"], meta)

    # ---- persistence ----
    def save(self, directory: Path | str) -> Path:
        faiss = _faiss()
        d = Path(directory)
        d.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(dir=d.parent, prefix=d.name + ".tmp"))
        try:
            faiss.write_index(self.index, str(tmp / "index.faiss"))
            meta = dict(self.meta)
            meta["files"] = {"index.faiss": _sha(tmp / "index.faiss")}
            (tmp / "index_meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
            if d.exists():
                backup = d.with_name(d.name + ".old")
                if backup.exists():
                    shutil.rmtree(backup)
                os.replace(d, backup)
                os.replace(tmp, d)
                shutil.rmtree(backup, ignore_errors=True)
            else:
                os.replace(tmp, d)
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return d

    @classmethod
    def load(cls, directory: Path | str, records=None, embedder_config: Optional[Dict[str, Any]] = None,
             doc_mode: Optional[str] = None) -> "VectorIndex":
        faiss = _faiss()
        d = Path(directory)
        try:
            meta = json.loads((d / "index_meta.json").read_text(encoding="utf-8"))
            fpath = d / "index.faiss"
            if meta.get("meta_version") != META_VERSION:
                raise IndexMismatchError("unsupported index meta version")
            if _sha(fpath) != meta["files"]["index.faiss"]:
                raise IndexMismatchError("index.faiss hash differs from metadata (corrupt or modified)")
            index = faiss.read_index(str(fpath))
        except IndexMismatchError:
            raise
        except Exception as exc:
            raise IndexMismatchError(f"cannot read index at {d}: {exc}") from exc
        ids, domains = meta["ids"], meta["domains"]
        if index.ntotal != len(ids) or index.d != meta["dim"] or len(domains) != len(ids) or meta["n"] != len(ids):
            raise IndexMismatchError("index size/dimension does not match metadata")
        if len(set(ids)) != len(ids):
            raise IndexMismatchError("duplicate ids in index metadata")
        if records is not None:
            if meta["corpus_sha256"] != corpus_fingerprint(records):
                raise IndexMismatchError("index was built from a different corpus (fingerprint mismatch)")
            if ids != [r["question_id"] for r in records]:
                raise IndexMismatchError("index id order differs from corpus order")
        if embedder_config is not None and meta["embedder_config_id"] != config_id(embedder_config):
            raise IndexMismatchError("index was built with a different embedder configuration")
        if doc_mode is not None and meta["doc_mode"] != doc_mode:
            raise IndexMismatchError("index was built with a different doc_mode")
        return cls(index, ids, domains, meta)

    # ---- search ----
    def search(self, qvec: np.ndarray, k: int, domain: Optional[str] = None):
        """Exact top-k by inner product; optional domain restriction. Returns (rows, scores)."""
        faiss = _faiss()
        q = np.ascontiguousarray(np.asarray(qvec, dtype=np.float32).reshape(1, -1))
        if q.shape[1] != self.index.d:
            raise ValueError(f"query dimension {q.shape[1]} != index dimension {self.index.d}")
        params = None
        pool = self.index.ntotal
        if domain is not None:
            rows = self._domain_rows.get(domain)
            if rows is None:
                raise ValueError(f"unknown domain {domain!r}; valid: {sorted(self._domain_rows)}")
            pool = len(rows)
            params = faiss.SearchParametersIVF() if False else faiss.SearchParameters()
            params.sel = faiss.IDSelectorBatch(rows)
        kk = max(1, min(k, pool))
        scores, ids = self.index.search(q, kk, params=params) if params is not None else self.index.search(q, kk)
        keep = [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]
        return [i for i, _ in keep], [s for _, s in keep]


def ensure_index(records, embedder, directory: Path | str, doc_mode: str = "qka", cache_dir=None, force: bool = False):
    """Load the index if it matches corpus + embedder + doc_mode; otherwise rebuild and persist it. Returns (index, rebuilt)."""
    if not force:
        try:
            return VectorIndex.load(directory, records, embedder.config(), doc_mode), False
        except (IndexMismatchError, FileNotFoundError):
            pass
    vi = VectorIndex.build(records, embedder, doc_mode, cache_dir)
    vi.save(directory)
    return vi, True
