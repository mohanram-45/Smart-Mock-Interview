"""Stage 8A: version-consistency checks (corpus vs DVC params vs served format vs indexes vs frozen files) and the retrieval experiment tracker."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.mlops import consistency

ROOT = Path(__file__).resolve().parents[2]


def _by_id(findings):
    return {f["id"]: f for f in findings}


def test_repository_state_has_no_version_disagreement():
    findings = consistency.check_all()
    assert [f for f in findings if f["status"] == "fail"] == [], findings
    ids = _by_id(findings)
    assert ids["corpus.manifest_matches_loaded_corpus"]["status"] == "pass"
    assert ids["dvc.params_doc_mode_is_the_served_format"]["status"] == "pass" and ids["frozen.challenge_queries_unchanged"]["status"] == "pass"
    assert ids["stored_results.stage2c_rankings_match_corpus"]["status"] == "pass"


def test_dvc_params_cli_and_service_agree_on_the_served_format():
    """Regression: params.yaml built `qka` and the CLI could not build `qk_concise`, while the application serves `qk_concise`."""
    import yaml

    from src.retrieval.service import DOC_MODE, MODEL_NAME

    p = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))["embedding"]
    assert (p["doc_mode"], p["model"], p["backend"]) == (DOC_MODE, MODEL_NAME, "minilm")
    helptext = subprocess.run([sys.executable, "-m", "src.retrieval.cli", "build", "--help"], capture_output=True, text=True, cwd=ROOT).stdout
    flat = " ".join(helptext.split())
    assert "{q,qk,qka,qk_concise}" in flat and "the default is the format the application serves" in flat
    dvc = (ROOT / "dvc.yaml").read_text(encoding="utf-8")
    assert "--doc-mode ${embedding.doc_mode}" in dvc


@pytest.fixture(scope="module")
def mini_root(tmp_path_factory):
    """A throw-away project root with just enough data for the corpus to load strictly, so mismatches can be created without touching the repository."""
    r = tmp_path_factory.mktemp("root")
    for rel in ("data/curated", "data/expansion"):
        shutil.copytree(ROOT / rel, r / rel)
    (r / "data/retrieval").mkdir(parents=True)
    shutil.copy(ROOT / "data/retrieval/corpus_manifest.json", r / "data/retrieval/corpus_manifest.json")
    shutil.copy(ROOT / "params.yaml", r / "params.yaml")
    return r


def test_wrong_params_are_reported_as_failures(mini_root):
    p = mini_root / "params.yaml"
    original = p.read_text(encoding="utf-8")
    try:
        p.write_text(original.replace("qk_concise", "qka"), encoding="utf-8")
        f = _by_id(consistency.check_all(mini_root))["dvc.params_doc_mode_is_the_served_format"]
        assert f["status"] == "fail" and "does not use" in f["detail"]
        p.write_text(original.replace("all-MiniLM-L6-v2", "some-other-model"), encoding="utf-8")
        assert _by_id(consistency.check_all(mini_root))["dvc.params_model_is_the_served_model"]["status"] == "fail"
    finally:
        p.write_text(original, encoding="utf-8")


def test_a_drifted_manifest_is_a_failure(mini_root):
    m = mini_root / "data/retrieval/corpus_manifest.json"
    original = m.read_text(encoding="utf-8")
    try:
        doc = json.loads(original)
        doc["corpus_sha256"] = "0" * 64
        m.write_text(json.dumps(doc), encoding="utf-8")
        assert _by_id(consistency.check_all(mini_root))["corpus.manifest_matches_loaded_corpus"]["status"] == "fail"
    finally:
        m.write_text(original, encoding="utf-8")


def test_stale_and_tampered_indexes_are_detected_and_missing_ones_are_skips_not_passes(mini_root):
    sha = json.loads((mini_root / "data/retrieval/corpus_manifest.json").read_text(encoding="utf-8"))["corpus_sha256"]
    assert _by_id(consistency.check_all(mini_root))["index.built"]["status"] == "skip"
    d = mini_root / "data/retrieval/index/fake_qk_concise"
    d.mkdir(parents=True)
    (d / "index.faiss").write_bytes(b"not really an index")
    import hashlib

    good = hashlib.sha256(b"not really an index").hexdigest()

    def meta(corpus_sha, file_sha):
        (d / "index_meta.json").write_text(
            json.dumps(
                {
                    "doc_mode": "qk_concise",
                    "n": 666,
                    "dim": 4,
                    "corpus_sha256": corpus_sha,
                    "embedder": {"backend": "fake", "model": "m"},
                    "embedder_config_id": "x",
                    "files": {"index.faiss": file_sha},
                }
            ),
            encoding="utf-8",
        )

    meta(sha, good)
    f = _by_id(consistency.check_all(mini_root))
    assert f["index.fake_qk_concise.built_from_current_corpus"]["status"] == "pass" and f["index.fake_qk_concise.file_hash"]["status"] == "pass"
    meta("1" * 64, good)
    assert _by_id(consistency.check_all(mini_root))["index.fake_qk_concise.built_from_current_corpus"]["status"] == "fail"
    meta(sha, "2" * 64)
    assert _by_id(consistency.check_all(mini_root))["index.fake_qk_concise.file_hash"]["status"] == "fail"


def test_check_versions_script_exit_codes(monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("check_versions", ROOT / "scripts/check_versions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0 and "0 FAILED" in capsys.readouterr().out
    monkeypatch.setattr(consistency, "check_all", lambda: [{"id": "x", "status": "fail", "detail": "boom"}])
    assert mod.main() == 1 and "1 FAILED" in capsys.readouterr().out


# ---- the tracker ----
@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    from src.retrieval import factory

    monkeypatch.setattr(factory, "INDEX_DIR", tmp_path / "idx")  # never write into the repository's index directory
    monkeypatch.setattr(factory, "CACHE_DIR", tmp_path / "cache")
    spec = importlib.util.spec_from_file_location("mlflow_track_retrieval", ROOT / "scripts/mlflow_track_retrieval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tracker_dry_run_reports_fingerprints_and_label_provenance_and_records_nothing(tracker, capsys):
    assert tracker.main(["--backend", "dev-lsa", "--dry-run", "--eval-set", "data/retrieval/eval/stage2c_dev_v2plus.jsonl"]) == 0
    out = capsys.readouterr().out
    doc = json.loads(out[: out.index("\ndry run")])
    p = doc["params"]
    manifest_sha = json.loads((ROOT / "data/retrieval/corpus_manifest.json").read_text(encoding="utf-8"))["corpus_sha256"]
    assert p["retrieval.doc_mode"] == "qk_concise" and len(p["index.faiss_sha256"]) == 64 and p["index.corpus_sha256"] == manifest_sha
    assert "NOT human ground truth" in p["labels.provenance"] and len(p["eval.stage2c_dev_v2plus.sha256"]) == 64 and p["embedder.model"] == "tfidf-svd"
    assert "stage2c_dev_v2plus.success@1" in doc["metrics"] and "dry run: nothing was recorded" in out


def test_tracker_refuses_to_run_when_versions_disagree(tracker, monkeypatch, capsys):
    monkeypatch.setattr(
        consistency,
        "check_all",
        lambda verify_hashes=True: [{"id": "dvc.params_doc_mode_is_the_served_format", "status": "fail", "detail": "qka vs qk_concise"}],
    )
    assert tracker.main(["--backend", "dev-lsa", "--dry-run"]) == 1
    assert "refused" in capsys.readouterr().out
    assert tracker.main(["--backend", "dev-lsa", "--dry-run", "--allow-mismatch", "--eval-set", "data/retrieval/eval/stage2c_dev_v2plus.jsonl"]) == 0
    assert '"consistency.mismatches_overridden": "true"' in capsys.readouterr().out


def test_tracker_without_a_cached_model_exits_2_and_never_downloads(tracker, monkeypatch, capsys):
    from src.retrieval import factory

    def boom(*a, **k):
        raise factory.ModelLoadError("model not in the local cache (simulated)")

    monkeypatch.setattr(factory, "make_embedder", boom)
    assert tracker.main(["--backend", "minilm", "--local-files-only", "--dry-run"]) == 2
    assert "cannot run" in capsys.readouterr().out


def test_tracker_records_a_live_run_tagged_not_imported(tracker, tmp_path, monkeypatch):
    pytest.importorskip("mlflow")
    pytest.importorskip("sqlalchemy")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "sqlite:///" + (tmp_path / "m.db").as_posix())
    monkeypatch.setenv("SMART_MLFLOW_ARTIFACTS", str(tmp_path / "art"))
    assert tracker.main(["--backend", "dev-lsa", "--experiment", "smart-test-retrieval", "--eval-set", "data/retrieval/eval/stage2c_dev_v2plus.jsonl"]) == 0
    import mlflow

    from src.mlops import tracking

    mlflow.set_tracking_uri(tracking.tracking_uri())
    c = mlflow.MlflowClient()
    (run,) = c.search_runs([c.get_experiment_by_name("smart-test-retrieval").experiment_id])
    assert run.data.tags[tracking.TAG_PROV] == tracking.PROVENANCE_LIVE and run.data.tags["smart.human_validated"] == "false"
    assert run.data.tags["smart.label_source"] == "ai_pooled_not_ground_truth" and "smart.consistency" not in run.data.tags
    assert run.data.metrics["stage2c_dev_v2plus.success_at_1"] > 0 and run.data.params["retrieval.doc_mode"] == "qk_concise"
