import hashlib
import json
import shutil

import numpy as np
import pytest

from src.retrieval.index import IndexMismatchError, VectorIndex, ensure_index
from src.retrieval.retriever import LexicalRetriever, SemanticRetriever, validate_query
from .conftest import FakeEmbedder


def _build(records, embedder, mode="qka"):
    return VectorIndex.build(records, embedder, mode)


def test_stable_id_to_vector_mapping(records, embedder):
    vi = _build(records, embedder)
    assert vi.ids == [r["question_id"] for r in records]
    assert vi.index.ntotal == len(records) and vi.index.d == 64
    for i, r in enumerate(records):
        assert vi.row_of[r["question_id"]] == i


def test_search_returns_complete_metadata_and_scores(records, embedder):
    vi = _build(records, embedder)
    s = SemanticRetriever(records, vi, embedder)
    hits = s.search("detect data drift in production features", k=3)
    assert hits[0]["question_id"] == "smi-l0001"
    h = hits[0]
    assert h["rank"] == 1 and 0.0 < h["score"] <= 1.0 + 1e-5
    assert h["record"]["canonical_answer"] and h["record"]["verification"]["human_reviewed"] is False
    assert [x["score"] for x in hits] == sorted([x["score"] for x in hits], reverse=True)


def test_exact_search_matches_brute_force(records, embedder):
    vi = _build(records, embedder)
    s = SemanticRetriever(records, vi, embedder)
    q = "how are lists and tuples different"
    qv = s.encode_query(q)
    from src.retrieval.embeddings import embed_texts
    from src.retrieval.documents import search_text
    V, _ = embed_texts(embedder, [search_text(r) for r in records])
    expect = np.argsort(-(V @ qv))[:4]
    assert [vi.row_of[h["question_id"]] for h in s.search(q, 4)] == list(expect)


def test_domain_filter(records, embedder):
    vi = _build(records, embedder)
    s = SemanticRetriever(records, vi, embedder)
    hits = s.search("index join table rows", k=5, domain="SQL")
    assert hits and all(h["domain"] == "SQL" for h in hits) and len(hits) == 2
    assert {h["question_id"] for h in hits} == {"smi-0001", "smi-0002"}
    only = s.search("drift", k=5, domain="MLOps & Model Deployment")
    assert [h["question_id"] for h in only] == ["smi-l0001"]


def test_domain_filter_equals_post_filtered_full_ranking(records, embedder):
    vi = _build(records, embedder)
    s = SemanticRetriever(records, vi, embedder)
    q = "overfitting memorises noise table rows"
    full = [h["question_id"] for h in s.search(q, k=len(records))]
    for dom in {r["domain"] for r in records}:
        expect = [i for i in full if s.by_id[i]["domain"] == dom]
        assert [h["question_id"] for h in s.search(q, k=len(records), domain=dom)] == expect


def test_unknown_domain_rejected(records, embedder):
    vi = _build(records, embedder)
    for r in (SemanticRetriever(records, vi, embedder), LexicalRetriever(records)):
        with pytest.raises(ValueError, match="unknown domain"):
            r.search("anything", domain="Cooking")


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
def test_empty_queries_rejected(records, embedder, bad):
    vi = _build(records, embedder)
    for r in (SemanticRetriever(records, vi, embedder), LexicalRetriever(records)):
        with pytest.raises(ValueError, match="empty"):
            r.search(bad)


@pytest.mark.parametrize("bad", [None, 5, ["a"], b"bytes"])
def test_non_string_query_rejected(bad):
    with pytest.raises(TypeError):
        validate_query(bad)


@pytest.mark.parametrize("k", [0, -1, True, 2.5, "3", None])
def test_invalid_k_rejected(records, embedder, k):
    vi = _build(records, embedder)
    with pytest.raises(ValueError, match="positive integer"):
        SemanticRetriever(records, vi, embedder).search("drift", k=k)


def test_overlong_query_rejected():
    with pytest.raises(ValueError, match="longer"):
        validate_query("a" * 5000)


def test_k_larger_than_corpus_is_clamped(records, embedder):
    vi = _build(records, embedder)
    assert len(SemanticRetriever(records, vi, embedder).search("table", k=1000)) == len(records)


def test_query_with_no_known_terms_lexical_empty(records):
    assert LexicalRetriever(records).search("zzzqqq xxyyzz") == []


def test_lexical_deterministic_and_ranked(records):
    lex = LexicalRetriever(records)
    a, b = lex.search("clustered index rows", 3), lex.search("clustered index rows", 3)
    assert [h["question_id"] for h in a] == [h["question_id"] for h in b]
    assert a[0]["question_id"] == "smi-0002" and a[0]["score"] > 0


def test_save_load_roundtrip_identical_results(records, embedder, tmp_path):
    vi = _build(records, embedder)
    vi.save(tmp_path / "idx")
    vi2 = VectorIndex.load(tmp_path / "idx", records, embedder.config(), "qka")
    assert vi2.ids == vi.ids and vi2.index.ntotal == vi.index.ntotal
    q = SemanticRetriever(records, vi, embedder).encode_query("python tuple immutable")
    assert vi.search(q, 6) == vi2.search(q, 6)
    meta = json.loads((tmp_path / "idx" / "index_meta.json").read_text())
    assert meta["embedder"]["model"] == "hashed-bow" and meta["dim"] == 64 and meta["n"] == len(records)


def test_load_missing_index(tmp_path):
    with pytest.raises(IndexMismatchError):
        VectorIndex.load(tmp_path / "nope")


def test_corrupt_index_file_detected(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    f = tmp_path / "idx" / "index.faiss"
    f.write_bytes(f.read_bytes()[:-20] + b"\x00" * 20)
    with pytest.raises(IndexMismatchError, match="hash differs"):
        VectorIndex.load(tmp_path / "idx")


def test_truncated_index_file_detected(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    f = tmp_path / "idx" / "index.faiss"
    f.write_bytes(f.read_bytes()[:50])
    with pytest.raises(IndexMismatchError):
        VectorIndex.load(tmp_path / "idx")


def _tamper_meta(path, fn):
    p = path / "index_meta.json"
    m = json.loads(p.read_text())
    fn(m)
    p.write_text(json.dumps(m))


def test_metadata_id_count_mismatch_detected(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    _tamper_meta(tmp_path / "idx", lambda m: (m["ids"].pop(), m["domains"].pop()))
    with pytest.raises(IndexMismatchError, match="does not match metadata"):
        VectorIndex.load(tmp_path / "idx")


def test_metadata_duplicate_ids_detected(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    _tamper_meta(tmp_path / "idx", lambda m: m["ids"].__setitem__(1, m["ids"][0]))
    with pytest.raises(IndexMismatchError, match="duplicate"):
        VectorIndex.load(tmp_path / "idx")


def test_metadata_dimension_mismatch_detected(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    _tamper_meta(tmp_path / "idx", lambda m: m.__setitem__("dim", 99))
    with pytest.raises(IndexMismatchError):
        VectorIndex.load(tmp_path / "idx")


def test_corrupt_metadata_json(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    (tmp_path / "idx" / "index_meta.json").write_text("{not json")
    with pytest.raises(IndexMismatchError):
        VectorIndex.load(tmp_path / "idx")


def test_stale_corpus_detected(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    changed = [dict(r) for r in records]
    changed[0] = {**changed[0], "canonical_answer": "different answer"}
    with pytest.raises(IndexMismatchError, match="different corpus"):
        VectorIndex.load(tmp_path / "idx", changed)
    with pytest.raises(IndexMismatchError):
        VectorIndex.load(tmp_path / "idx", records[:-1])


def test_embedder_config_and_doc_mode_mismatch_detected(records, embedder, tmp_path):
    _build(records, embedder).save(tmp_path / "idx")
    with pytest.raises(IndexMismatchError, match="embedder"):
        VectorIndex.load(tmp_path / "idx", records, FakeEmbedder(tag="other").config())
    with pytest.raises(IndexMismatchError, match="doc_mode"):
        VectorIndex.load(tmp_path / "idx", records, embedder.config(), "q")


def test_ensure_index_rebuilds_only_when_needed(records, embedder, tmp_path):
    d = tmp_path / "idx"
    vi, rebuilt = ensure_index(records, embedder, d, "qka", tmp_path / "cache")
    assert rebuilt
    _, rebuilt = ensure_index(records, embedder, d, "qka", tmp_path / "cache")
    assert not rebuilt
    changed = records[:-1]
    vi3, rebuilt = ensure_index(changed, embedder, d, "qka", tmp_path / "cache")
    assert rebuilt and vi3.index.ntotal == len(changed)
    _, rebuilt = ensure_index(changed, embedder, d, "qka", tmp_path / "cache")
    assert not rebuilt
    _, rebuilt = ensure_index(changed, FakeEmbedder(tag="z"), d, "qka", tmp_path / "cache")
    assert rebuilt


def test_ensure_index_recovers_from_corrupt_index(records, embedder, tmp_path):
    d = tmp_path / "idx"
    ensure_index(records, embedder, d)
    (d / "index.faiss").write_bytes(b"junk")
    _, rebuilt = ensure_index(records, embedder, d)
    assert rebuilt
    VectorIndex.load(d, records, embedder.config(), "qka")


def test_deterministic_rebuild_identical_bytes(records, tmp_path):
    ha = []
    for n in range(2):
        vi = _build(records, FakeEmbedder())
        vi.save(tmp_path / f"i{n}")
        ha.append(hashlib.sha256((tmp_path / f"i{n}" / "index.faiss").read_bytes()).hexdigest())
    assert ha[0] == ha[1]


def test_save_is_atomic_and_leaves_no_temp_dirs(records, embedder, tmp_path):
    vi = _build(records, embedder)
    vi.save(tmp_path / "idx")
    vi.save(tmp_path / "idx")  # overwrite
    assert sorted(p.name for p in tmp_path.iterdir()) == ["idx"]


def test_semantic_retriever_rejects_mismatched_index(records, embedder):
    vi = _build(records, embedder)
    with pytest.raises(ValueError, match="id order"):
        SemanticRetriever(list(reversed(records)), vi, embedder)


def test_query_dimension_mismatch(records, embedder):
    vi = _build(records, embedder)
    with pytest.raises(ValueError, match="dimension"):
        SemanticRetriever(records, vi, FakeEmbedder(dim=32)).search("drift")
