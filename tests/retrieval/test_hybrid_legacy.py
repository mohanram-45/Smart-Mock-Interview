import pytest

from src.retrieval.hybrid import HybridRetriever, rrf_fuse
from src.retrieval.index import VectorIndex
from src.retrieval.retriever import LexicalRetriever, SemanticRetriever


def test_rrf_known_values():
    out = dict(rrf_fuse([["a", "b", "c"], ["b", "a", "d"]], rrf_k=60))
    assert out["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert out["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert out["c"] == pytest.approx(1 / 63) and out["d"] == pytest.approx(1 / 63)


def test_rrf_deterministic_ties_and_order():
    a = rrf_fuse([["x", "y"], ["y", "x"]])
    assert [i for i, _ in a] == ["x", "y"]  # exact tie -> id order
    assert a == rrf_fuse([["x", "y"], ["y", "x"]])


def test_rrf_weights_and_duplicates():
    out = rrf_fuse([["a", "a", "b"]], rrf_k=10)
    assert dict(out)["a"] == pytest.approx(1 / 11)  # duplicate counted once
    w = rrf_fuse([["a"], ["b"]], weights=[2.0, 1.0])
    assert w[0][0] == "a"


@pytest.mark.parametrize("bad", [0, -1, True, 1.5])
def test_rrf_invalid_k(bad):
    with pytest.raises(ValueError):
        rrf_fuse([["a"]], rrf_k=bad)


def test_rrf_invalid_weights():
    with pytest.raises(ValueError):
        rrf_fuse([["a"]], weights=[1, 2])
    with pytest.raises(ValueError):
        rrf_fuse([["a"]], weights=[-1])


@pytest.fixture
def hybrid(records, embedder):
    vi = VectorIndex.build(records, embedder, "qka")
    return HybridRetriever(LexicalRetriever(records, "qka"), SemanticRetriever(records, vi, embedder))


def test_hybrid_search_shape_and_components(hybrid, records):
    hits = hybrid.search(records[0]["question"], k=3)
    assert 1 <= len(hits) <= 3
    assert [h["rank"] for h in hits] == list(range(1, len(hits) + 1))
    assert set(hits[0]["components"]) == {"bm25_rank", "bm25_score", "semantic_rank", "semantic_score"}
    assert hits == hybrid.search(records[0]["question"], k=3)


def test_hybrid_domain_filter_and_invalid(hybrid, records):
    dom = records[0]["domain"]
    assert all(h["domain"] == dom for h in hybrid.search(records[0]["question"], k=5, domain=dom))
    with pytest.raises(ValueError):
        hybrid.search("   ")
    with pytest.raises(ValueError):
        hybrid.search("x", domain="Nope")


def test_hybrid_rejects_mismatched_retrievers(records, embedder):
    vi = VectorIndex.build(records, embedder, "qka")
    sem = SemanticRetriever(records, vi, embedder)
    lex = LexicalRetriever(list(reversed(records)), "qka")
    with pytest.raises(ValueError):
        HybridRetriever(lex, sem)


def test_legacy_guard_real_corpus(real_root):
    from src.retrieval.corpus import load_corpus
    from src.retrieval import legacy_guard as g
    if not g.TRIAGE.exists() or not g.LEGACY_JSON.exists():
        pytest.skip("legacy files not present")
    rep = g.check_disjoint(load_corpus()["records"])
    assert rep["ok"], rep["problems"]
    assert rep["counts"]["boilerplate"] == 3618 and rep["counts"]["legacy"] == 4085


def test_legacy_guard_detects_clash(tmp_path):
    import csv, json
    from src.retrieval import legacy_guard as g
    leg = [{"id": 1, "domain": "SQL", "difficulty": "Easy", "question": "What is X?", "reference_answer": "A good answer covers X."}]
    (tmp_path / "l.json").write_text(json.dumps(leg))
    with open(tmp_path / "t.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["id", "status"]); w.writeheader(); w.writerow({"id": "1", "status": "EXCLUDE_TEMPLATE"})
    rec = [{"question_id": "smi-0001", "question": "what is  X?", "canonical_answer": "other"}]
    rep = g.check_disjoint(rec, tmp_path / "l.json", tmp_path / "t.csv")
    assert not rep["ok"] and rep["counts"]["question_clashes"] == 1
