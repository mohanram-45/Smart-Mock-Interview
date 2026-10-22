"""Stage 6B: MLflow tracking and historical import. Skipped when MLflow is not installed (pip install -r requirements-mlops.txt)."""

import json
import os
import shutil
from pathlib import Path

import pytest

mlflow = pytest.importorskip("mlflow")
pytest.importorskip("sqlalchemy")  # full `mlflow` (requirements-mlops.txt); mlflow-skinny has no SQL backend

from src.mlops import historical, tracking, verify  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def _imported_template(tmp_path_factory):
    """Import the 30 historical runs ONCE per module into a template store (the slow part); each test then works on its own copy."""
    d = tmp_path_factory.mktemp("mlflow_template")
    os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///" + (d / "m.db").as_posix()
    os.environ["SMART_MLFLOW_ARTIFACTS"] = str(d / "art")
    try:
        historical.import_all()
    finally:
        os.environ.pop("MLFLOW_TRACKING_URI", None)
        os.environ.pop("SMART_MLFLOW_ARTIFACTS", None)
    return d


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "sqlite:///" + (tmp_path / "m.db").as_posix())
    monkeypatch.setenv("SMART_MLFLOW_ARTIFACTS", str(tmp_path / "art"))
    return tmp_path


@pytest.fixture()
def imported(_imported_template, tmp_path, monkeypatch):
    """A fresh private copy of the already-imported store."""
    shutil.copy(_imported_template / "m.db", tmp_path / "m.db")
    if (_imported_template / "art").exists():
        shutil.copytree(_imported_template / "art", tmp_path / "art")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "sqlite:///" + (tmp_path / "m.db").as_posix())
    monkeypatch.setenv("SMART_MLFLOW_ARTIFACTS", str(tmp_path / "art"))
    return tmp_path


def _runs(exp):
    mlflow.set_tracking_uri(tracking.tracking_uri())
    client = mlflow.MlflowClient()
    e = client.get_experiment_by_name(exp)
    return client.search_runs([e.experiment_id], max_results=500) if e else []


def test_metric_key_sanitiser():
    assert tracking.metric_key("success@1") == "success_at_1" and tracking.metric_key("mrr@10") == "mrr_at_10"
    assert tracking._clean_metrics({"a": float("nan"), "b": True, "c": "x", "d": 2}) == {"b": 1.0, "d": 2.0}


def test_all_historical_specs_are_extractable_without_running_anything():
    specs = historical.all_specs()
    keys = [s.key for s in specs]
    assert len(keys) == len(set(keys)) and len(specs) == 30
    assert sum(k.startswith("stage2c:") for k in keys) == 25 and sum(k.startswith("stage3b_") for k in keys) == 4 and "stage3c2:20261015T120208Z" in keys
    for s in specs:
        assert s.source_path and len(s.source_sha256) == 64 and s.metrics


def test_import_is_idempotent_and_verified(store):
    r1 = historical.import_all()
    assert r1["created"] == 30 and r1["exists"] == 0
    r2 = historical.import_all()
    assert r2["created"] == 0 and r2["exists"] == 30
    v = verify.verify_history()
    assert v["ok"], v["problems"]
    assert v["metrics_checked"] > 500


def test_every_imported_run_is_labelled_historical_and_never_human_validated(imported):
    for exp in ("smart-retrieval", "smart-evaluation"):
        for r in _runs(exp):
            t = r.data.tags
            assert t["smart.provenance"] == "imported_historical"
            assert t["smart.human_validated"] == "false"
            assert len(t["smart.source_sha256"]) == 64 and t["smart.source_path"]
            assert t["mlflow.note.content"].startswith("IMPORTED HISTORICAL RESULT")
            assert "label_source" in "".join(t) or t["smart.label_source"]


def test_frozen_3c2_run_reproduces_source_numbers_and_decision(imported):
    (run,) = [r for r in _runs("smart-evaluation") if r.data.tags["smart.import_key"].startswith("stage3c2:")]
    src = json.loads((ROOT / "data/evaluation/stage3c2_results/20261015T120208Z/analysis_v2.json").read_text(encoding="utf-8"))["metrics"]
    m = run.data.metrics
    assert m["abstain_rate"] == src["abstain_rate"] == 0.45
    assert m["valid_output_rate"] == src["valid_output_rate"] and m["median_answer_latency_s"] == src["median_answer_latency_s"]
    assert m["criterion_abstain_rate_max_pass"] == 0.0 and m["criteria_failed"] == 1.0
    assert run.data.tags["smart.decision"] == "DO NOT ADVANCE"
    assert run.data.params["modular_pipeline_version"] == "3c1.0" and run.data.params["temperature"] == "0.0" and run.data.params["num_ctx"] == "8192"


def test_stage2c_retrieval_metrics_match_source_and_carry_context(imported):
    src = json.loads((ROOT / "data/retrieval/stage2c/eval_results.json").read_text(encoding="utf-8"))
    run = [r for r in _runs("smart-retrieval") if r.data.tags["smart.import_key"] == "stage2c:dev_v2:dense_qka"][0]
    want = src["sets"]["dev_v2"]["systems"]["dense_qka"]
    assert run.data.metrics["success_at_1"] == want["success@1"] and run.data.metrics["mrr_at_10"] == want["mrr@10"]
    p = run.data.params
    assert p["embedder_model"] == "sentence-transformers/all-MiniLM-L6-v2" and p["corpus_sha256"] == src["corpus_sha256"] and p["doc_format"] == "qka"
    assert "not recorded" in p["embedder_revision"]  # revision is NOT invented
    assert run.data.tags["smart.label_source"].startswith("ai_authored")


def test_no_accuracy_is_invented_for_the_experimental_evaluator(imported):
    for r in _runs("smart-evaluation"):
        assert not any("accuracy" in k or "agreement_with_human" in k or "human_agreement" in k for k in r.data.metrics)


def test_drift_in_a_frozen_source_file_is_detected(imported):
    specs = historical.all_specs()
    s = next(x for x in specs if x.key == "stage3c2:20261015T120208Z")
    s.source_sha256 = "0" * 64
    with pytest.raises(tracking.ImportDrift):
        tracking.record(s, provenance=tracking.PROVENANCE_IMPORTED)


def test_verify_detects_a_tampered_metric(imported):
    mlflow.set_tracking_uri(tracking.tracking_uri())
    client = mlflow.MlflowClient()
    run = [r for r in _runs("smart-evaluation") if r.data.tags["smart.import_key"].startswith("stage3c2:")][0]
    client.log_metric(run.info.run_id, "abstain_rate", 0.10)  # a later, different value
    v = verify.verify_history()
    assert not v["ok"] and any("abstain_rate" in p for p in v["problems"])


def test_live_run_adds_standard_tags_and_fingerprints(store):
    with tracking.live_run("smart-test", "demo run", params={"k": 5}) as run:
        run.log_metrics({"success@1": 0.5})
    (r,) = _runs("smart-test")
    assert r.data.tags["smart.provenance"] == "live" and r.data.tags["smart.human_validated"] == "false"
    assert r.data.params["k"] == "5" and r.data.params["corpus.record_count"] == "666" and r.data.params["freeze.version"] == "3c2.1"
    assert len(r.data.params["corpus.manifest_sha256"]) == 64 and r.data.metrics["success_at_1"] == 0.5
    assert r.info.status == "FINISHED"


def test_live_run_marks_failure(store):
    with pytest.raises(ValueError):
        with tracking.live_run("smart-test", "bad"):
            raise ValueError("x")
    (r,) = _runs("smart-test")
    assert r.info.status == "FAILED"


def test_importer_does_not_modify_any_frozen_file(store):
    watched = [ROOT / h.source_path for h in historical.all_specs()]
    before = {p: p.stat().st_mtime_ns for p in watched}
    historical.import_all()
    assert before == {p: p.stat().st_mtime_ns for p in watched}


@pytest.fixture()
def built_index():
    """data/retrieval/index is git-ignored, so a fresh clone (CI) has none. Build the offline dev-LSA stand-in (seconds, no download) only if the tree has no index at all,
    and remove exactly what was built. A real index on a developer machine is never touched."""
    import subprocess
    import sys

    idx, cache = ROOT / "data/retrieval/index", ROOT / "data/retrieval/cache"
    if idx.exists() and any(idx.glob("*/index.faiss")):
        yield
        return
    had_cache = cache.exists()
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    p = subprocess.run(
        [sys.executable, "-m", "src.retrieval.cli", "build", "--backend", "dev-lsa", "--doc-mode", "qka"], capture_output=True, text=True, cwd=ROOT, env=env
    )
    try:
        assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]
        yield
    finally:
        shutil.rmtree(idx, ignore_errors=True)
        if not had_cache:
            shutil.rmtree(cache, ignore_errors=True)


def test_provenance_script_records_fingerprints(store, monkeypatch, built_index):
    import subprocess
    import sys

    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    p = subprocess.run([sys.executable, str(ROOT / "scripts/mlflow_log_provenance.py")], capture_output=True, text=True, cwd=ROOT, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    (r,) = _runs("smart-provenance")
    assert r.data.metrics["corpus_loader_strict_ok"] == 1.0 and r.data.metrics["index_hashes_match_recorded"] == 1.0
    assert any(k.endswith(".faiss_sha256_actual") for k in r.data.params)


def test_no_mlflow_import_in_the_web_app_path():
    """The Flask app must run without MLflow installed: nothing under main/, src/demo, src/retrieval, report_delivery may import it."""
    import ast

    for base in (
        "main",
        "src/demo",
        "src/retrieval",
        "src/components",
        "report_delivery",
        "src/model",
        "src/codeeval",
        "src/mlops/metrics.py",
        "src/mlops/obs.py",
        "src/mlops/version.py",
    ):
        paths = [ROOT / base] if (ROOT / base).is_file() else list((ROOT / base).rglob("*.py"))
        for f in paths:
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                assert not any(n.split(".")[0] == "mlflow" or n.endswith("mlops.tracking") for n in names), f"{f} imports mlflow/tracking"
