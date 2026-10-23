"""DEV-ONLY stand-in embedder (TF-IDF + truncated SVD, "LSA").

This is NOT a SentenceTransformer and NOT the Stage 2A production model. It
exists so the FAISS/cache/index/evaluation plumbing can be exercised and
benchmarked in environments where the Hugging Face model cannot be downloaded.
Results obtained with it must always be labelled ``dev-lsa``. It must never be
used to claim anything about all-MiniLM-L6-v2 performance.

The vectors depend on the corpus the vectoriser is fitted on, so the fit-corpus
fingerprint is part of the embedder config (and therefore of the cache key).
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Sequence

import numpy as np


def approx_count_tokens(text: str) -> int:
    """DEV APPROXIMATION of word-piece count (regex tokens x 1.25). Never a substitute for the real MiniLM tokenizer."""
    import re
    return int(len(re.findall(r"\w+|[^\w\s]", text)) * 1.25)


class DevLsaEmbedder:
    backend = "dev-lsa"

    def __init__(self, fit_texts: Sequence[str], dim: int = 192, seed: int = 0):
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vec = TfidfVectorizer(lowercase=True, stop_words="english", sublinear_tf=True, ngram_range=(1, 2), min_df=2)
        X = self.vec.fit_transform(list(fit_texts))
        self.dim = int(min(dim, X.shape[1] - 1, X.shape[0] - 1))
        self.svd = TruncatedSVD(n_components=self.dim, random_state=seed)
        self.svd.fit(X)
        self._fit_sha = hashlib.sha256("\n".join(fit_texts).encode()).hexdigest()
        self.seed = seed

    def config(self) -> Dict[str, Any]:
        return {"backend": self.backend, "model": "tfidf-svd", "dim": self.dim, "max_seq_length": 0,
                "normalised": True, "fit_corpus_sha256": self._fit_sha, "params": {"seed": self.seed}}

    count_tokens = staticmethod(approx_count_tokens)

    def encode_raw(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        return self.svd.transform(self.vec.transform(list(texts))).astype(np.float32)
