"""qk_concise as a first-class doc mode: index build/load, separation from qka, never mutating records, BM25 fallback text."""
import json
import pytest

from src.retrieval.corpus import corpus_fingerprint, load_corpus
from src.retrieval.documents import DOC_MODES, build_documents, search_text
from src.retrieval.embeddings_dev import DevLsaEmbedder, approx_count_tokens
from src.retrieval.index import IndexMismatchError, VectorIndex, ensure_index


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


def test_mode_registered_and_needs_a_counter(corpus):
    assert "qk_concise" in DOC_MODES
    with pytest.raises(ValueError, match="token counter"):
        search_text(corpus["records"][0], "qk_concise")


def test_documents_never_mutate_records_and_answers_stay_intact(corpus):
    R = corpus["records"]
    before = corpus_fingerprint(R)
    docs = build_documents(R, "qk_concise", approx_count_tokens)
    assert corpus_fingerprint(R) == before
    for d, r in zip(docs, R):
        assert d["metadata"] is r and r["canonical_answer"]                      # full record stays available after retrieval
        # every embedded answer sentence is a verbatim sentence of the record's canonical answer
        tail = d["text"].split("Key concepts:", 1)[1].split("\n", 1)
        if len(tail) > 1:
            norm = lambda t: " ".join(t.split())
            assert norm(tail[1]) in norm(r["canonical_answer"]), r["question_id"]   # verbatim leading text, no generation


def test_budget_respected_except_for_flagged_long_heads(corpus):
    from src.retrieval.doc_formats import build_text
    over = 0
    for r in corpus["records"]:
        b = build_text(r, "qk_concise", approx_count_tokens, 256)
        n = approx_count_tokens(b["text"])
        if b["flags"]["head_over_budget"]:
            over += 1
            assert b["flags"]["answer_sentences"] == 0                           # long scenario: no answer added, flagged
        else:
            assert n <= 254, r["question_id"]
    assert 0 < over < 100                                                        # a minority of long scenario records


@pytest.fixture()
def emb(corpus):
    return DevLsaEmbedder([d["text"] for d in build_documents(corpus["records"], "qk_concise", approx_count_tokens)])


def test_index_roundtrip_and_doc_mode_separation(corpus, emb, tmp_path):
    R = corpus["records"]
    vi, rebuilt = ensure_index(R, emb, tmp_path / "i", "qk_concise", cache_dir=tmp_path / "c")
    assert rebuilt and vi.meta["doc_mode"] == "qk_concise" and vi.index.ntotal == len(R) == 666
    assert vi.meta["ids"] == [r["question_id"] for r in R]                        # stable id <-> row mapping
    vi2, rebuilt2 = ensure_index(R, emb, tmp_path / "i", "qk_concise", cache_dir=tmp_path / "c")
    assert not rebuilt2 and vi2.meta["ids"] == vi.meta["ids"]
    with pytest.raises(IndexMismatchError, match="doc_mode"):                     # a qka request never silently reuses a qk_concise index
        VectorIndex.load(tmp_path / "i", R, emb.config(), "qka")


def test_service_default_and_env_override(monkeypatch):
    from src.retrieval.service import RetrievalService
    assert RetrievalService(backend="dev-lsa").doc_mode == "qk_concise"
    monkeypatch.setenv("SMART_RETRIEVAL_DOC_FORMAT", "qka")
    assert RetrievalService(backend="dev-lsa").doc_mode == "qka"
    monkeypatch.setenv("SMART_RETRIEVAL_DOC_FORMAT", "question")
    with pytest.raises(ValueError, match="SMART_RETRIEVAL_DOC_FORMAT"):
        RetrievalService(backend="dev-lsa")


def test_service_status_reports_format_and_bm25_fallback_text(tmp_path):
    from src.retrieval.service import RetrievalService
    s = RetrievalService(backend="dev-lsa", index_root=tmp_path / "i", cache_dir=tmp_path / "c")
    st = s.status()
    assert st["doc_mode"] == "qk_concise" and st["bm25_fallback_doc_mode"] == "qka"
    assert s.search("explain how bubble sort works", k=3)["mode"] == "semantic"
