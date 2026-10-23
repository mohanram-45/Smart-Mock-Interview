"""Embedding backends and a local, content-addressed embedding cache.

* ``SentenceTransformerEmbedder`` is the production backend (default
  ``sentence-transformers/all-MiniLM-L6-v2``, CPU, no paid API). It imports
  sentence-transformers lazily so the rest of the package (and the tests) work
  without it.
* Any object with ``config()``, ``dim`` and ``encode_raw(texts, batch_size)`` can
  be used; ``embeddings_dev.py`` provides a dev-only stand-in.
* All vectors returned by ``embed_texts`` are float32, L2-normalised and
  dimension-checked, so inner product == cosine similarity.
* The cache stores one vector per (embedder-config, sha256(text)). Adding
  records embeds only the new texts; changing the embedder config or a record's
  text changes the key, so stale vectors are never reused.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
NORM_TOL = 1e-3


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def l2_normalise(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (x / n).astype(np.float32)


class SentenceTransformerEmbedder:
    """Production embedder. Loads the model once; offline-capable once the model is cached locally."""

    backend = "sentence-transformers"

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = "cpu", max_seq_length: Optional[int] = None,
                 local_files_only: bool = False):
        try:
            import sentence_transformers
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("sentence-transformers is required: pip install -r requirements-rag.txt") from exc
        self.model_name = model_name
        self._st_version = sentence_transformers.__version__
        kwargs = {"device": device}
        if local_files_only:
            kwargs["local_files_only"] = True
        self.model = SentenceTransformer(model_name, **kwargs)
        if max_seq_length:
            self.model.max_seq_length = max_seq_length
        self.max_seq_length = int(self.model.max_seq_length)
        getdim = getattr(self.model, "get_embedding_dimension", None) or self.model.get_sentence_embedding_dimension
        self.dim = int(getdim())
        self.device = device

    def config(self) -> Dict[str, Any]:
        try:
            import torch
            tv = torch.__version__
        except Exception:  # pragma: no cover
            tv = "unknown"
        return {"backend": self.backend, "model": self.model_name, "dim": self.dim,
                "max_seq_length": self.max_seq_length, "normalised": True,
                "sentence_transformers": self._st_version, "torch": tv, "device": self.device}

    def encode_raw(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        return self.model.encode(list(texts), batch_size=batch_size, convert_to_numpy=True,
                                 normalize_embeddings=True, show_progress_bar=False)

    def count_tokens(self, text: str) -> int:
        """Word-pieces the model's own tokenizer produces, WITHOUT the [CLS]/[SEP] specials (used to size embedding text)."""
        return len(self.model.tokenizer(text, add_special_tokens=False)["input_ids"])


def config_id(config: Dict[str, Any]) -> str:
    """Stable id for an embedder configuration (version fields excluded so a patch upgrade does not drop the cache)."""
    keys = {k: v for k, v in config.items() if k in ("backend", "model", "dim", "max_seq_length", "normalised", "fit_corpus_sha256", "params")}
    return hashlib.sha256(json.dumps(keys, sort_keys=True).encode()).hexdigest()[:16]


class EmbeddingCache:
    def __init__(self, cache_dir: Path | str, cfg_id: str):
        self.path = Path(cache_dir) / f"emb_{cfg_id}.npz"
        self.keys: Dict[str, int] = {}
        self.vecs: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        if self.path.exists():
            try:
                z = np.load(self.path, allow_pickle=False)
                ks = [str(k) for k in z["keys"]]
                self.vecs = z["vecs"].astype(np.float32)
                self.keys = {k: i for i, k in enumerate(ks)}
            except Exception:  # corrupt cache: ignore and rebuild
                self.keys, self.vecs = {}, np.zeros((0, 0), dtype=np.float32)

    def get(self, h: str) -> Optional[np.ndarray]:
        i = self.keys.get(h)
        return None if i is None else self.vecs[i]

    def add(self, hashes: Sequence[str], vecs: np.ndarray) -> None:
        if not len(hashes):
            return
        new = [(h, v) for h, v in zip(hashes, vecs) if h not in self.keys]
        if not new:
            return
        nv = np.stack([v for _, v in new]).astype(np.float32)
        self.vecs = nv if self.vecs.size == 0 else np.vstack([self.vecs, nv])
        for h, _ in new:
            self.keys[h] = len(self.keys)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(self.keys, key=self.keys.get)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        os.close(fd)
        with open(tmp, "wb") as f:
            np.savez(f, keys=np.array(ordered), vecs=self.vecs)
        os.replace(tmp, self.path)


def embed_texts(embedder, texts: Sequence[str], batch_size: int = 32, cache_dir: Optional[Path | str] = None
                ) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Embed texts in the given order (batched, cached). Returns (vectors [n, dim], stats)."""
    if not len(texts):
        raise ValueError("no texts to embed")
    cfg = embedder.config()
    dim = int(cfg["dim"])
    hashes = [text_hash(t) for t in texts]
    cache = EmbeddingCache(cache_dir, config_id(cfg)) if cache_dir else None
    out = np.zeros((len(texts), dim), dtype=np.float32)
    missing: List[int] = []
    hits = 0
    for i, h in enumerate(hashes):
        v = cache.get(h) if cache else None
        if v is not None and v.shape[0] == dim:
            out[i] = v
            hits += 1
        else:
            missing.append(i)
    t0 = time.perf_counter()
    if missing:
        # unique texts only, deterministic order
        uniq: Dict[str, int] = {}
        for i in missing:
            uniq.setdefault(hashes[i], i)
        order = list(uniq.values())
        raw = embedder.encode_raw([texts[i] for i in order], batch_size)
        raw = np.asarray(raw, dtype=np.float32)
        if raw.ndim != 2 or raw.shape != (len(order), dim):
            raise ValueError(f"embedding shape {raw.shape}, expected ({len(order)}, {dim})")
        raw = l2_normalise(raw)
        by_hash = {hashes[i]: raw[j] for j, i in enumerate(order)}
        for i in missing:
            out[i] = by_hash[hashes[i]]
        if cache:
            cache.add(list(by_hash), np.stack(list(by_hash.values())))
            cache.save()
    elapsed = time.perf_counter() - t0
    norms = np.linalg.norm(out, axis=1)
    if not np.all(np.isfinite(out)) or np.abs(norms - 1).max() > NORM_TOL:
        raise ValueError("embeddings are not finite and unit-normalised")
    return out, {"n": len(texts), "cache_hits": hits, "embedded": len(missing), "embed_seconds": round(elapsed, 3),
                 "config_id": config_id(cfg)}
