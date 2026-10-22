"""Check that MLflow holds exactly what the source result files contain (historical metrics reproduce), and that the source files are unchanged."""

from __future__ import annotations

from typing import Any, Dict, List

from . import historical
from .tracking import PROVENANCE_IMPORTED, TAG_PROV, TAG_SHA, _clean_metrics, _client, ensure_experiment, find_run


def verify_history(tol: float = 1e-12) -> Dict[str, Any]:
    mlflow, client = _client()
    problems: List[str] = []
    checked_metrics = 0
    specs = historical.all_specs()
    for s in specs:
        run = find_run(ensure_experiment(s.experiment), s.key)
        if run is None:
            problems.append(f"{s.key}: not imported")
            continue
        tags = run.data.tags
        if tags.get(TAG_PROV) != PROVENANCE_IMPORTED:
            problems.append(f"{s.key}: provenance tag is {tags.get(TAG_PROV)!r}, expected {PROVENANCE_IMPORTED!r}")
        if tags.get("smart.human_validated") != "false":
            problems.append(f"{s.key}: human_validated tag is not 'false'")
        if tags.get(TAG_SHA) != s.source_sha256:
            problems.append(f"{s.key}: source file changed since import ({s.source_path})")
        want = _clean_metrics(s.metrics)
        got = run.data.metrics
        for k, v in want.items():
            checked_metrics += 1
            if k not in got:
                problems.append(f"{s.key}: metric {k} missing")
            elif abs(got[k] - v) > tol * max(1.0, abs(v)):
                problems.append(f"{s.key}: metric {k} = {got[k]!r}, source says {v!r}")
        extra = set(got) - set(want)
        if extra:
            problems.append(f"{s.key}: unexpected metrics {sorted(extra)[:5]}")
        if s.key == "stage3c2:20261015T120208Z" and tags.get("smart.decision") != "DO NOT ADVANCE":
            problems.append("stage3c2 run lost its DO NOT ADVANCE decision tag")
    return {"ok": not problems, "runs_checked": len(specs), "metrics_checked": checked_metrics, "problems": problems}
