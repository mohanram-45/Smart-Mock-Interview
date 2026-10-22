"""Stage 8D: the real-index verifier's checks, exercised offline with hand-made index directories (no model, no download)."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("verify_real_index", ROOT / "scripts" / "verify_real_index.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


@pytest.fixture(scope="module")
def corpus():
    from src.retrieval.corpus import load_corpus

    return load_corpus(strict=True)


def _make_index(d: Path, corpus, **over):
    faiss = pytest.importorskip("faiss")
    import numpy as np

    n = len(corpus["records"])
    v = np.random.default_rng(0).standard_normal((n, 384)).astype("float32")
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    ix = faiss.IndexFlatIP(384)
    ix.add(v)
    d.mkdir(parents=True)
    faiss.write_index(ix, str(d / "index.faiss"))
    meta = {
        "ids": [r["question_id"] for r in corpus["records"]],
        "n": n,
        "corpus_sha256": corpus["manifest"]["corpus_sha256"],
        "doc_mode": "qk_concise",
        "embedder": {"model": V.REPO, "dim": 384, "max_seq_length": 256, "normalised": True},
        "files": {"index.faiss": V.sha256_file(d / "index.faiss")},
    }
    meta.update(over)
    (d / "index_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


def _status(findings):
    return {f["name"]: f["status"] for f in findings}


def test_expected_directory_is_the_one_next_to_the_existing_real_indexes():
    # same embedder configuration id as the q/qk/qka indexes recorded in data/retrieval/index on the Windows machine
    assert V.expected_index_dir_name(V.REPO) == "minilm_d14b0073_qk_concise"


def test_a_correct_index_passes_every_static_check(tmp_path, corpus):
    st = _status(V.verify_index_dir(_make_index(tmp_path / "ok", corpus), corpus))
    assert set(st.values()) == {"pass"}, st


@pytest.mark.parametrize(
    "over,failing",
    [
        ({"corpus_sha256": "0" * 64}, "index.corpus_fingerprint"),
        ({"doc_mode": "qka"}, "index.document_format"),
        ({"embedder": {"model": "other/model", "dim": 384, "max_seq_length": 256, "normalised": True}}, "index.embedder_configuration"),
        ({"ids": ["smi-0001"], "n": 1}, "index.row_order_matches_corpus"),
        ({"files": {"index.faiss": "f" * 64}}, "index.checksum_matches_manifest"),
    ],
)
def test_each_kind_of_mismatch_is_detected(tmp_path, corpus, over, failing):
    st = _status(V.verify_index_dir(_make_index(tmp_path / "bad", corpus, **over), corpus))
    assert st[failing] == "fail"


def test_a_tampered_index_file_is_detected(tmp_path, corpus):
    d = _make_index(tmp_path / "t", corpus)
    with open(d / "index.faiss", "ab") as f:
        f.write(b"x")
    assert _status(V.verify_index_dir(d, corpus))["index.checksum_matches_manifest"] == "fail"


def test_missing_files_fail_instead_of_crashing(tmp_path, corpus):
    (tmp_path / "empty").mkdir()
    assert _status(V.verify_index_dir(tmp_path / "empty", corpus)) == {"index.files_present": "fail"}


def test_comparison_with_recorded_rankings_flags_disagreement():
    stored = {"Q1": [["a", 0.8], ["b", 0.5]], "Q2": [["c", 0.7], ["d", 0.4]]}
    same = V.compare_with_stored({"Q1": ["a", "b"], "Q2": ["c", "d"]}, {"Q1": 0.8001, "Q2": 0.7}, stored)
    assert same["top1_agreement"] == 1.0 and same["max_abs_top1_score_delta"] < 1e-3
    diff = V.compare_with_stored({"Q1": ["b", "a"], "Q2": ["c", "d"]}, {"Q1": 0.5, "Q2": 0.7}, stored)
    assert diff["top1_agreement"] == 0.5 and diff["disagreeing_query_ids"] == ["Q1"]


def test_tree_hashes_exclude_the_target_directory_and_detect_changes(tmp_path):
    (tmp_path / "old").mkdir()
    (tmp_path / "old/f").write_bytes(b"1")
    (tmp_path / "new").mkdir()
    (tmp_path / "new/g").write_bytes(b"2")
    before = V.tree_hashes(tmp_path, exclude_dirs=("new",))
    assert list(before) == ["old/f"]
    (tmp_path / "new/g").write_bytes(b"3")  # building the new index must not count as a change to frozen artifacts
    assert V.tree_hashes(tmp_path, exclude_dirs=("new",)) == before
    (tmp_path / "old/f").write_bytes(b"changed")
    assert V.tree_hashes(tmp_path, exclude_dirs=("new",)) != before


def test_read_only_run_loads_no_model_and_leaves_the_tree_unchanged():
    """Without the model cache the default run must pass with skips (never download, never fail) and must not create the index."""
    idx = ROOT / "data/retrieval/index"
    before = sorted(p.name for p in idx.iterdir()) if idx.is_dir() else []
    r = subprocess.run([sys.executable, str(ROOT / "scripts/verify_real_index.py")], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "frozen historical index artifacts" in r.stdout and "[FAIL]" not in r.stdout
    assert (sorted(p.name for p in idx.iterdir()) if idx.is_dir() else []) == before
