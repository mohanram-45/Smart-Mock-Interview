"""Local MLflow tracking for SMART Mock Interview.

* Backend: a local SQLite database (default ``mlflow/mlflow.db``) with artifacts under ``mlflow/artifacts``. Both live OUTSIDE Git (see .gitignore) and
  are rebuilt by ``scripts/mlflow_import_history.py`` from the files that ARE in the repository. Override with MLFLOW_TRACKING_URI.
* Every run carries ``smart.provenance`` = ``live`` (measured by a tracked run) or ``imported_historical`` (copied from a result file that was produced
  earlier, in its original context). Imported runs also record the source file path and sha256 and are never presented as new measurements.
* ``smart.human_validated`` is always ``false``: nothing in this project has been validated against human graders, and AI-authored labels are tagged as such.
* No tracking call can change scoring or interview behaviour; failures to track raise TrackingError only in the scripts that ask for tracking."""

from __future__ import annotations

import importlib.util
import math
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from . import version

ROOT = version.ROOT
PROVENANCE_LIVE = "live"
PROVENANCE_IMPORTED = "imported_historical"
TAG_PROV, TAG_KEY, TAG_SHA, TAG_SRC = "smart.provenance", "smart.import_key", "smart.source_sha256", "smart.source_path"
_KEY_RE = re.compile(r"[^A-Za-z0-9_\-. /]")


class TrackingError(RuntimeError):
    pass


class ImportDrift(TrackingError):
    """A historical source file's sha256 differs from the one already imported under the same key (a frozen file changed)."""


def available() -> bool:
    """MLflow is importable AND, for the default SQLite backend, SQLAlchemy is present (the full `mlflow` package brings it; `mlflow-skinny` does not)."""
    spec = importlib.util.find_spec("mlflow")
    if spec is None or spec.origin is None:  # origin None = a namespace package: the project's own mlflow/ store folder, which is not MLflow
        return False
    if tracking_uri().startswith("sqlite") and importlib.util.find_spec("sqlalchemy") is None:
        return False
    return True


def tracking_uri() -> str:
    env = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
    return env or "sqlite:///" + (ROOT / "mlflow" / "mlflow.db").as_posix()


def artifact_root() -> Path:
    return Path(os.environ.get("SMART_MLFLOW_ARTIFACTS", str(ROOT / "mlflow" / "artifacts")))


def metric_key(name: str) -> str:
    """MLflow keys may contain only alphanumerics, _ - . space / ; '@' becomes '_at_' (success@1 -> success_at_1)."""
    return _KEY_RE.sub("_", name.replace("@", "_at_"))[:240]


def _clean_metrics(m: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, v in m.items():
        if isinstance(v, bool):
            v = 1.0 if v else 0.0
        if isinstance(v, (int, float)) and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            out[metric_key(k)] = float(v)
    return out


def _clean_params(p: Dict[str, Any]) -> Dict[str, str]:
    return {metric_key(k): ("" if v is None else str(v))[:500] for k, v in p.items() if v is not None}


def _client():
    if not available():
        raise TrackingError("MLflow is not installed. Run: pip install -r requirements-mlops.txt")
    import mlflow

    mlflow.set_tracking_uri(tracking_uri())
    return mlflow, mlflow.MlflowClient()


def ensure_experiment(name: str) -> str:
    mlflow, client = _client()
    exp = client.get_experiment_by_name(name)
    if exp is not None:
        return exp.experiment_id
    loc = artifact_root() / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    loc.mkdir(parents=True, exist_ok=True)
    return client.create_experiment(name, artifact_location=loc.resolve().as_uri())


def standard_tags(provenance: str) -> Dict[str, str]:
    ev = version.evaluator_versions()
    return {
        TAG_PROV: provenance,
        "smart.human_validated": "false",
        "smart.app_version": version.APP_VERSION,
        "smart.git_commit": version.git_commit(),
        "smart.pipeline_version": ev.get("pipeline", "unknown"),
        "smart.frozen_3c_decision": "DO NOT ADVANCE (3C-2: abstain rate 0.45 > 0.40)",
    }


@dataclass
class RunSpec:
    experiment: str
    run_name: str
    key: str  # stable identity -> idempotent import
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    source_path: Optional[str] = None  # repo-relative
    source_sha256: Optional[str] = None
    artifacts: List[Tuple[str, str]] = field(default_factory=list)  # (repo-relative path, artifact subdir) - small files only
    description: str = ""


def find_run(experiment_id: str, key: str):
    mlflow, client = _client()
    runs = client.search_runs([experiment_id], filter_string=f"tags.`{TAG_KEY}` = '{key}'", max_results=5)
    return runs[0] if runs else None


def record(spec: RunSpec, *, provenance: str, allow_drift: bool = False) -> Tuple[str, str]:
    """Create the run (or find the identical one). Returns (run_id, 'created'|'exists'). For imported runs a changed source sha256 raises ImportDrift."""
    mlflow, client = _client()
    exp_id = ensure_experiment(spec.experiment)
    existing = find_run(exp_id, spec.key)
    if existing is not None:
        old_sha = existing.data.tags.get(TAG_SHA)
        if spec.source_sha256 and old_sha and old_sha != spec.source_sha256 and not allow_drift:
            raise ImportDrift(
                f"{spec.key}: source {spec.source_path} changed since it was imported (was {old_sha[:12]}, now {spec.source_sha256[:12]}). "
                f"Frozen result files must not change; investigate, or re-import with --allow-drift into a fresh store."
            )
        if old_sha == spec.source_sha256 or not spec.source_sha256:
            return existing.info.run_id, "exists"
    tags = {**standard_tags(provenance), **spec.tags, TAG_KEY: spec.key}
    if spec.source_path:
        tags[TAG_SRC] = spec.source_path
    if spec.source_sha256:
        tags[TAG_SHA] = spec.source_sha256
    if spec.description:
        tags["mlflow.note.content"] = spec.description
    run = client.create_run(exp_id, tags={**tags, "mlflow.runName": spec.run_name})
    rid = run.info.run_id
    try:
        for k, v in _clean_params(spec.params).items():
            client.log_param(rid, k, v)
        for k, v in _clean_metrics(spec.metrics).items():
            client.log_metric(rid, k, v)
        for rel, sub in spec.artifacts:
            p = ROOT / rel
            if p.is_file() and p.stat().st_size <= 5_000_000:
                client.log_artifact(rid, str(p), sub or None)
        client.set_terminated(rid, "FINISHED")
    except Exception:
        client.set_terminated(rid, "FAILED")
        raise
    return rid, "created"


@contextmanager
def live_run(experiment: str, run_name: str, params: Optional[Dict[str, Any]] = None, tags: Optional[Dict[str, str]] = None) -> Iterator[Any]:
    """For FUTURE experiments:  with live_run('smart-retrieval', 'minilm qk_concise') as run: run.log_metrics({...}); run.log_params({...})

    Adds the standard tags (code version, evaluator version, human_validated=false) plus the corpus and freeze fingerprints automatically."""
    mlflow, client = _client()
    exp_id = ensure_experiment(experiment)
    run = client.create_run(exp_id, tags={**standard_tags(PROVENANCE_LIVE), **(tags or {}), "mlflow.runName": run_name})
    rid = run.info.run_id

    class _H:
        run_id = rid

        def log_params(self, p: Dict[str, Any]) -> None:
            for k, v in _clean_params(p).items():
                client.log_param(rid, k, v)

        def log_metrics(self, m: Dict[str, Any], step: Optional[int] = None) -> None:
            for k, v in _clean_metrics(m).items():
                client.log_metric(rid, k, v, step=step) if step is not None else client.log_metric(rid, k, v)

        def log_file(self, path: str, subdir: Optional[str] = None) -> None:
            client.log_artifact(rid, path, subdir)

    h = _H()
    try:
        h.log_params({**provenance_params(), **(params or {})})
        yield h
        client.set_terminated(rid, "FINISHED")
    except BaseException:
        client.set_terminated(rid, "FAILED")
        raise


def provenance_params(verify_indexes: bool = False) -> Dict[str, Any]:
    """Fingerprint parameters for a run: corpus manifest sha + record count, per-component fingerprints, each built index (embedder identity and
    recorded/actual index.faiss sha256), the Stage 3C-2 freeze manifest, evaluator versions."""
    p: Dict[str, Any] = {}
    c = version.corpus_info()
    p["corpus.record_count"] = c.get("record_count")
    p["corpus.manifest_sha256"] = c.get("manifest_sha256")
    for name, comp in (c.get("components") or {}).items():
        p[f"corpus.component.{name}.fingerprint"] = (comp.get("fingerprint") or "")[:64]
    for row in version.index_fingerprints():
        tag = f"index.{row['dir']}"
        p[f"{tag}.embedder"] = f"{row.get('backend')}/{row.get('model')}@{row.get('revision') or 'no-revision-recorded'}"
        p[f"{tag}.doc_mode"] = row.get("doc_mode")
        p[f"{tag}.faiss_sha256_recorded"] = row.get("index_faiss_sha256_recorded")
        if verify_indexes:
            f = ROOT / "data/retrieval/index" / row["dir"] / "index.faiss"
            p[f"{tag}.faiss_sha256_actual"] = version.sha256_file(f) if f.is_file() else "missing"
    fz = version.freeze_info()
    p["freeze.version"], p["freeze.manifest_sha256"] = fz.get("version"), fz.get("manifest_sha256")
    for k, v in version.evaluator_versions().items():
        p[f"evaluator.{k}"] = v
    return p
