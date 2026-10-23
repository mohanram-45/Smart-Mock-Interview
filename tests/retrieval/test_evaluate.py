import json
import math

import pytest

from src.retrieval.evaluate import (auroc, evaluate_retriever, load_eval_set, mrr_at_k, ndcg_at_k, recall_at_k, success_at_k)


def test_success_and_recall_at_k():
    rel = {"a": 2, "b": 2, "c": 1}
    ranked = ["x", "a", "y", "b", "c"]
    assert success_at_k(ranked, rel, 1) == 0.0 and success_at_k(ranked, rel, 2) == 1.0
    assert recall_at_k(ranked, rel, 2) == 0.5 and recall_at_k(ranked, rel, 5) == 1.0   # primary relevant = {a, b}
    assert recall_at_k(ranked, rel, 5, min_grade=1) == 1.0 and recall_at_k(ranked, rel, 1, min_grade=1) == 0.0
    assert recall_at_k(ranked, {}, 5) == 0.0 and success_at_k(ranked, {}, 5) == 0.0


def test_mrr():
    rel = {"a": 2}
    assert mrr_at_k(["x", "y", "a"], rel) == pytest.approx(1 / 3)
    assert mrr_at_k(["a"], rel) == 1.0 and mrr_at_k(["x", "y"], rel) == 0.0
    assert mrr_at_k(["x"] * 10 + ["a"], rel, 10) == 0.0      # beyond cutoff
    assert mrr_at_k(["x", "c"], {"c": 1}) == 0.0 and mrr_at_k(["x", "c"], {"c": 1}, min_grade=1) == 0.5


def test_ndcg_known_values():
    rel = {"a": 2, "b": 1}
    assert ndcg_at_k(["a", "b"], rel) == pytest.approx(1.0)
    dcg = (2 ** 1 - 1) / math.log2(2) + (2 ** 2 - 1) / math.log2(3)
    idcg = (2 ** 2 - 1) / math.log2(2) + (2 ** 1 - 1) / math.log2(3)
    assert ndcg_at_k(["b", "a"], rel) == pytest.approx(dcg / idcg)
    assert ndcg_at_k(["x", "y"], rel) == 0.0 and ndcg_at_k(["a"], {}) == 0.0
    assert ndcg_at_k(["x", "y", "z", "w", "v", "a"], rel, k=5) == 0.0     # relevant item beyond k


def test_auroc():
    assert auroc([3, 4], [1, 2]) == 1.0 and auroc([1, 2], [3, 4]) == 0.0
    assert auroc([1, 1], [1, 1]) == 0.5 and auroc([], [1]) is None


class _Stub:
    def __init__(self, table): self.table = table
    def search(self, q, k=10, domain=None):
        return [{"question_id": i, "score": s} for i, s in self.table[q]][:k]


def _ev():
    return [
        {"query_id": "Q1", "query": "q1", "category": "paraphrase", "domain": "SQL", "relevant": {"a": 2}, "no_answer": False, "judged": ["a", "b", "c"]},
        {"query_id": "Q2", "query": "q2", "category": "paraphrase", "domain": "SQL", "relevant": {"a": 2}, "no_answer": False, "judged": ["a", "b"]},
        {"query_id": "Q3", "query": "q3", "category": "no_answer", "domain": None, "relevant": {}, "no_answer": True, "judged": ["a"]},
        {"query_id": "Q4", "query": "q4", "category": "paraphrase", "domain": "Python", "relevant": {"c": 1}, "no_answer": False, "judged": ["c", "x"]},
    ]


def test_evaluate_retriever_aggregates():
    stub = _Stub({"q1": [("a", .9), ("b", .5)], "q2": [("b", .8), ("a", .7)], "q3": [("a", .2)], "q4": [("c", .6), ("x", .1)]})
    r = evaluate_retriever(stub, _ev())
    o = r["overall"]
    assert o["n_queries"] == 4 and o["n_answerable"] == 3 and o["n_primary"] == 2     # Q4 has only grade-1 relevance
    assert o["success@1"] == 0.5 and o["success@3"] == 1.0 and o["mrr@10"] == pytest.approx(0.75)
    assert o["success@1_lenient"] == pytest.approx(2 / 3)
    assert r["by_domain"]["SQL"]["success@1"] == 0.5 and "Python" in r["by_domain"]
    assert r["no_answer"]["n"] == 1 and r["no_answer"]["top1_score_auroc_answerable_vs_no_answer"] == 1.0
    assert r["latency_ms"]["n"] == 4 and r["unjudged_fraction_in_top10"] == 0.0


def test_unjudged_counted():
    stub = _Stub({"q1": [("a", .9), ("zzz", .5)], "q2": [("a", .8)], "q3": [("a", .2)], "q4": [("c", .6)]})
    assert evaluate_retriever(stub, _ev())["unjudged_fraction_in_top10"] == pytest.approx(1 / 5)


def test_load_eval_set_validation(tmp_path):
    def write(rows):
        p = tmp_path / "e.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows))
        return p
    ok = {"query_id": "Q1", "query": "x", "category": "c", "relevant": {"a": 2}, "no_answer": False}
    assert len(load_eval_set(write([ok]))) == 1
    with pytest.raises(ValueError, match="duplicate"):
        load_eval_set(write([ok, ok]))
    with pytest.raises(ValueError, match="missing"):
        load_eval_set(write([{"query_id": "Q1"}]))
    with pytest.raises(ValueError, match="no_answer query has relevant"):
        load_eval_set(write([{**ok, "no_answer": True}]))
    with pytest.raises(ValueError, match="answerable query has no relevant"):
        load_eval_set(write([{**ok, "relevant": {}}]))


def test_real_eval_set_is_valid(real_root):
    ev = load_eval_set(real_root / "data/retrieval/eval/eval_set.jsonl")
    assert len(ev) == 166 and sum(q["no_answer"] for q in ev) == 20
    from src.retrieval.corpus import load_corpus
    ids = {r["question_id"] for r in load_corpus(real_root)["records"]}
    assert all(set(q["relevant"]) <= ids and set(q["judged"]) <= ids and set(q["relevant"]) <= set(q["judged"]) for q in ev)
