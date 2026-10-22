"""Stage 2B: integrity of the pooled (v2) relevance judgements, immutability of the originals, and replay consistency.
Skipped when the Stage 2B artifacts are not present."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVD = ROOT / "data" / "retrieval" / "eval"
IMM = EVD / "immutable_pre_pooling_stage2b"
V2 = EVD / "eval_set_v2.jsonl"
pytestmark = pytest.mark.skipif(not (IMM.exists() and V2.exists()), reason="stage 2B artifacts not present")


def _jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def test_originals_are_byte_identical_to_checksums():
    sums = (IMM / "SHA256SUMS.txt").read_text().split("\n")
    n = 0
    for line in filter(None, sums):
        h, name = line.split(None, 1)
        assert hashlib.sha256((IMM / name.strip().lstrip("*")).read_bytes()).hexdigest() == h, name
        n += 1
    assert n == 4
    assert (IMM / "eval_set.jsonl").read_bytes() == (EVD / "eval_set.jsonl").read_bytes()  # live v1.1 untouched


def test_v2_preserves_original_queries_and_judgements():
    old, new = _jl(IMM / "eval_set.jsonl"), _jl(V2)
    assert [q["query_id"] for q in old] == [q["query_id"] for q in new] and len(new) == 166
    for o, n in zip(old, new):
        assert o["query"] == n["query"] and o["category"] == n["category"]
        assert all(n["relevant"].get(k) == g for k, g in o["relevant"].items()), o["query_id"]  # nothing downgraded/removed
        assert set(o["judged"]) <= set(n["judged"])
        assert set(n["relevant"]) <= set(n["judged"])
        assert n["no_answer"] == (not n["relevant"])


def test_variants_are_ordered_min_primary_max():
    p, lo, hi = _jl(V2), _jl(EVD / "eval_set_v2_min.jsonl"), _jl(EVD / "eval_set_v2_max.jsonl")
    for a, b, c in zip(lo, p, hi):
        for k in set(a["relevant"]) | set(b["relevant"]) | set(c["relevant"]):
            assert a["relevant"].get(k, 0) <= b["relevant"].get(k, 0) <= c["relevant"].get(k, 0), (a["query_id"], k)


def test_no_unjudged_top10_for_any_system_under_v2():
    bench = json.loads((IMM / "retrieval_benchmark_minilm.json").read_text(encoding="utf-8"))
    ev = {q["query_id"]: q for q in _jl(V2)}
    for name, s in bench["systems"].items():
        for r in s["rows"]:
            assert set(r["ranked"][:10]) <= set(ev[r["query_id"]]["judged"]), (name, r["query_id"])


def test_no_answer_queries_not_silently_flipped():
    rep = json.loads((EVD / "pooling_report_v2.json").read_text())
    assert rep["no_answer_to_answerable_flips (primary variant)"] == []
    assert sum(q["no_answer"] for q in _jl(V2)) == 20
    assert all(q["no_answer_original"] == q["no_answer"] for q in _jl(V2))


def test_replay_reproduces_windows_benchmark_under_original_labels():
    """The re-scoring code (same metric functions) must reproduce the Windows run's own numbers on the original labels."""
    from src.retrieval.evaluate import evaluate_retriever, load_eval_set
    bench = json.loads((IMM / "retrieval_benchmark_minilm.json").read_text(encoding="utf-8"))
    ev = load_eval_set(IMM / "eval_set.jsonl")
    qtext = {q["query_id"]: q["query"] for q in ev}

    class Replay:
        def __init__(self, rows): self.by = {qtext[r["query_id"]]: r for r in rows}
        def search(self, query, k=10, domain=None):
            r = self.by[query]
            return [{"question_id": d, "score": r["top1_score"] if i == 0 else 0.0} for i, d in enumerate(r["ranked"][:k])]

    for name, s in bench["systems"].items():
        got = evaluate_retriever(Replay(s["rows"]), ev)["overall"]
        for m, v in s["overall"].items():
            assert got[m] == pytest.approx(v, abs=1e-9), (name, m)


def test_documents_never_contain_eval_queries_or_ids():
    from src.retrieval.corpus import load_corpus
    from src.retrieval.documents import build_documents
    recs = load_corpus()["records"]
    blob = "\n".join(d["text"] for d in build_documents(recs, "qka")).lower()
    for q in _jl(V2):
        assert q["query"].lower() not in blob and q["query_id"].lower() not in blob


def test_kappa_helper():
    spec = importlib.util.spec_from_file_location("pool_label", ROOT / "audit" / "retrieval" / "pool_label.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.kappa([0, 1, 2, 0], [0, 1, 2, 0]) == pytest.approx(1.0)
    assert mod.kappa([0, 0, 1, 1], [0, 1, 0, 1], (0, 1)) == pytest.approx(0.0)
