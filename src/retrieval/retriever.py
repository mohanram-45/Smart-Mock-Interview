"""Retrievers sharing one interface: semantic (SentenceTransformer + FAISS) and lexical (BM25)."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from .documents import build_documents
from .embeddings import l2_normalise
from .index import VectorIndex
from .lexical import BM25, tokenize

MAX_QUERY_CHARS = 4000


def validate_query(query: Any, k: Any = 5) -> str:
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    q = query.strip()
    if not q:
        raise ValueError("query is empty")
    if len(q) > MAX_QUERY_CHARS:
        raise ValueError(f"query longer than {MAX_QUERY_CHARS} characters")
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")
    return q


class _Base:
    name = "base"

    def __init__(self, records: List[Dict[str, Any]]):
        self.records = records
        self.by_id = {r["question_id"]: r for r in records}
        self.domains = sorted({r["domain"] for r in records})

    def _hit(self, rank: int, row: int, score: float) -> Dict[str, Any]:
        r = self.records[row]
        return {"rank": rank, "score": round(float(score), 6), "question_id": r["question_id"], "domain": r["domain"],
                "record": r}

    def _check_domain(self, domain: Optional[str]) -> None:
        if domain is not None and domain not in self.domains:
            raise ValueError(f"unknown domain {domain!r}; valid: {self.domains}")


class SemanticRetriever(_Base):
    name = "semantic"

    def __init__(self, records, vindex: VectorIndex, embedder, batch_size: int = 32):
        super().__init__(records)
        if vindex.ids != [r["question_id"] for r in records]:
            raise ValueError("index id order does not match records")
        self.vindex, self.embedder = vindex, embedder

    def encode_query(self, query: str) -> np.ndarray:
        v = np.asarray(self.embedder.encode_raw([query], 1), dtype=np.float32).reshape(1, -1)
        if v.shape[1] != self.vindex.index.d:
            raise ValueError(f"embedder dimension {v.shape[1]} != index dimension {self.vindex.index.d}")
        return l2_normalise(v)[0]

    def search(self, query: str, k: int = 5, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        q = validate_query(query, k)
        self._check_domain(domain)
        qv = self.encode_query(q)
        if not np.any(qv):  # query shares nothing with the embedder vocabulary (dev backend only)
            return []
        rows, scores = self.vindex.search(qv, k, domain)
        return [self._hit(i + 1, r, s) for i, (r, s) in enumerate(zip(rows, scores))]


class LexicalRetriever(_Base):
    name = "bm25"

    def __init__(self, records, doc_mode: str = "qka"):
        super().__init__(records)
        self.doc_mode = doc_mode
        self.bm25 = BM25([d["text"] for d in build_documents(records, doc_mode)])
        self._dom = np.array([r["domain"] for r in records])

    def search(self, query: str, k: int = 5, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        q = validate_query(query, k)
        self._check_domain(domain)
        s = self.bm25.scores(q)
        if domain is not None:
            s = np.where(self._dom == domain, s, -1.0)
        order = np.lexsort((np.arange(len(s)), -s))  # score desc, ties by corpus row (deterministic)
        out = []
        for row in order[:k]:
            if s[row] <= 0:
                break
            out.append(self._hit(len(out) + 1, int(row), s[row]))
        return out
