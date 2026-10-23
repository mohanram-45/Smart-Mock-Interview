import numpy as np
import pytest

from src.retrieval.documents import build_documents, search_text
from src.retrieval.embeddings import EmbeddingCache, config_id, embed_texts, l2_normalise, text_hash
from .conftest import FakeEmbedder, make_record


def test_doc_modes_content(records):
    r = records[0]
    q, qk, qka = (search_text(r, m) for m in ("q", "qk", "qka"))
    assert r["question"] in q and "Key concepts" not in q and r["canonical_answer"] not in q
    assert "Key concepts: inner join; keys" in qk and r["canonical_answer"] not in qk
    assert r["canonical_answer"] in qka and qka.index(r["question"]) < qka.index(r["canonical_answer"])


def test_invalid_doc_mode(records):
    with pytest.raises(ValueError):
        search_text(records[0], "qa")


def test_one_document_per_record_no_alternative_duplication(records):
    records[0]["alternative_answers"] = {"concise": "short alt", "practical": "practical alt"}
    docs = build_documents(records)
    assert len(docs) == len(records)
    assert "short alt" not in docs[0]["text"] and "practical alt" not in docs[0]["text"]
    assert docs[0]["metadata"]["alternative_answers"]["concise"] == "short alt"  # kept as response metadata


def test_candidate_answers_never_indexed():
    bad = make_record("cand-1", "SQL", "t", "q?", "a", ["c"], origin="candidate_answer")
    with pytest.raises(ValueError, match="not a reference-corpus record"):
        build_documents([bad])


def test_duplicate_doc_ids_rejected(records):
    with pytest.raises(ValueError):
        build_documents(records + [records[0]])


def test_embedding_dimension_and_normalisation(records, embedder):
    texts = [search_text(r) for r in records]
    v, stats = embed_texts(embedder, texts)
    assert v.shape == (len(records), 64) and v.dtype == np.float32
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-5)
    assert stats["embedded"] == len(records)


def test_unnormalised_model_output_is_normalised(records):
    v, _ = embed_texts(FakeEmbedder(scale=37.5), [search_text(r) for r in records])
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-5)


def test_wrong_dimension_rejected(records):
    class Bad(FakeEmbedder):
        def encode_raw(self, texts, batch_size=32):
            return super().encode_raw(texts)[:, :10]
    with pytest.raises(ValueError, match="shape"):
        embed_texts(Bad(), [search_text(r) for r in records])


def test_nan_embeddings_rejected(records):
    class Nan(FakeEmbedder):
        def encode_raw(self, texts, batch_size=32):
            x = super().encode_raw(texts)
            x[0, 0] = np.nan
            return x
    with pytest.raises(ValueError):
        embed_texts(Nan(), [search_text(r) for r in records])


def test_empty_input_rejected(embedder):
    with pytest.raises(ValueError):
        embed_texts(embedder, [])


def test_deterministic_embeddings(records):
    t = [search_text(r) for r in records]
    a, _ = embed_texts(FakeEmbedder(), t)
    b, _ = embed_texts(FakeEmbedder(), t)
    assert np.array_equal(a, b)


def test_cache_hit_and_incremental_add(records, tmp_path):
    t = [search_text(r) for r in records]
    e1 = FakeEmbedder()
    v1, s1 = embed_texts(e1, t[:4], cache_dir=tmp_path)
    assert s1["cache_hits"] == 0 and e1.calls == 4
    e2 = FakeEmbedder()
    v2, s2 = embed_texts(e2, t, cache_dir=tmp_path)
    assert s2["cache_hits"] == 4 and s2["embedded"] == 2 and e2.calls == 2  # only the new records are embedded
    assert np.array_equal(v1, v2[:4])
    e3 = FakeEmbedder()
    v3, s3 = embed_texts(e3, t, cache_dir=tmp_path)
    assert s3["embedded"] == 0 and e3.calls == 0 and np.array_equal(v2, v3)


def test_cache_keyed_by_embedder_config(records, tmp_path):
    t = [search_text(r) for r in records]
    embed_texts(FakeEmbedder(tag="a"), t, cache_dir=tmp_path)
    e = FakeEmbedder(tag="b")
    _, s = embed_texts(e, t, cache_dir=tmp_path)
    assert s["cache_hits"] == 0 and e.calls == len(t)  # different config -> cache not reused
    assert config_id(FakeEmbedder(tag="a").config()) != config_id(e.config())


def test_changed_text_not_served_from_cache(records, tmp_path):
    t = [search_text(r) for r in records]
    embed_texts(FakeEmbedder(), t, cache_dir=tmp_path)
    t2 = t[:]
    t2[0] += " extra words"
    e = FakeEmbedder()
    _, s = embed_texts(e, t2, cache_dir=tmp_path)
    assert s["embedded"] == 1


def test_corrupt_cache_is_ignored(records, tmp_path):
    t = [search_text(r) for r in records]
    embed_texts(FakeEmbedder(), t, cache_dir=tmp_path)
    for f in tmp_path.glob("emb_*.npz"):
        f.write_bytes(b"not an npz")
    e = FakeEmbedder()
    v, s = embed_texts(e, t, cache_dir=tmp_path)
    assert s["embedded"] == len(t) and v.shape[0] == len(t)


def test_duplicate_texts_embedded_once(tmp_path):
    e = FakeEmbedder()
    v, s = embed_texts(e, ["same text", "same text", "other"], cache_dir=tmp_path)
    assert e.calls == 2 and np.array_equal(v[0], v[1])


def test_l2_normalise_zero_vector_safe():
    out = l2_normalise(np.zeros((2, 4)))
    assert np.all(out == 0)
