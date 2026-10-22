"""Integration tests against a real SentenceTransformer model.

Skipped unless SMART_RAG_TEST_MODEL is set (a model name or a local model directory) and
sentence-transformers is installed. Example (real baseline model, needs the model hub or a local HF cache):
    SMART_RAG_TEST_MODEL=sentence-transformers/all-MiniLM-L6-v2 pytest tests/retrieval/test_st_integration.py
CI/sandbox use: a tiny randomly initialised local model checks the plumbing only (no semantic assertions).
"""
import os

import numpy as np
import pytest

MODEL = os.environ.get("SMART_RAG_TEST_MODEL")
pytest.importorskip("sentence_transformers")
pytestmark = pytest.mark.skipif(not MODEL, reason="SMART_RAG_TEST_MODEL not set")
SEMANTIC = os.environ.get("SMART_RAG_TEST_SEMANTIC") == "1"


@pytest.fixture(scope="module")
def st():
    from src.retrieval.embeddings import SentenceTransformerEmbedder
    return SentenceTransformerEmbedder(MODEL)


def test_config_and_dimension(st):
    c = st.config()
    assert c["backend"] == "sentence-transformers" and c["dim"] == st.dim > 0 and c["normalised"] is True
    assert c["max_seq_length"] > 0 and c["sentence_transformers"] and c["torch"]


def test_embeddings_unit_norm_and_deterministic(st, records):
    from src.retrieval.documents import search_text
    from src.retrieval.embeddings import embed_texts
    t = [search_text(r) for r in records]
    a, _ = embed_texts(st, t)
    b, _ = embed_texts(st, t, batch_size=2)       # different batching must not change vectors materially
    assert a.shape == (len(t), st.dim) and np.allclose(np.linalg.norm(a, axis=1), 1.0, atol=1e-4)
    assert np.allclose(a, b, atol=1e-4)


def test_end_to_end_index_search_roundtrip(st, records, tmp_path):
    from src.retrieval.index import ensure_index
    from src.retrieval.retriever import SemanticRetriever
    vi, rebuilt = ensure_index(records, st, tmp_path / "idx", cache_dir=tmp_path / "cache")
    assert rebuilt
    vi2, rebuilt2 = ensure_index(records, st, tmp_path / "idx", cache_dir=tmp_path / "cache")
    assert not rebuilt2
    hits = SemanticRetriever(records, vi2, st).search("how do I detect data drift in production", k=3)
    assert len(hits) == 3 and all(h["record"]["canonical_answer"] for h in hits)


@pytest.mark.skipif(not SEMANTIC, reason="semantic assertions need a trained model (SMART_RAG_TEST_SEMANTIC=1)")
def test_paraphrase_closer_than_unrelated(st):
    v = st.encode_raw(["What is overfitting in machine learning?", "Why does a model memorise training noise and generalise badly?",
                       "How do I join two tables in SQL?"])
    assert float(v[0] @ v[1]) > float(v[0] @ v[2])
