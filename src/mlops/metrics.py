"""Tiny in-process operational metrics (counters, latency summaries, gauges). No external service, no candidate data.

Privacy rule: label VALUES must be low-cardinality identifiers chosen by the code (route template, scorer key, status word). `record_*` sanitises every
label to a short [a-z0-9_.:/<>-] token (enough for route templates like /demo/api/sessions/<sid>/answer) and caps the number of distinct label sets per metric, so a bug cannot leak an answer, a session id or a free-text
string into the metrics by accident. Metric functions never raise."""

from __future__ import annotations

import re
import threading
import time
from typing import Any, Dict, Tuple

_MAX_SERIES_PER_METRIC = 200
_LABEL_RE = re.compile(r"[^a-z0-9_.:/<>\-]")

# name -> help text. Only names listed here may be recorded (a typo cannot create a new, unreviewed series).
KNOWN: Dict[str, Tuple[str, str]] = {
    "smart_http_requests_total": ("counter", "HTTP requests by method, route template and status class"),
    "smart_http_request_seconds": ("summary", "HTTP request latency by route template"),
    "smart_interviews_started_total": ("counter", "Interviews started, by surface (demo|legacy)"),
    "smart_interviews_completed_total": ("counter", "Interviews finished, by surface"),
    "smart_answers_submitted_total": ("counter", "Answers submitted (not their content), by surface"),
    "smart_scorer_failures_total": ("counter", "Legacy similarity scorer failures, by scorer and stage (load|score)"),
    "smart_scorer_unavailable_total": ("counter", "Interviews/answers where the chosen scorer was not ready"),
    "smart_retrieval_failures_total": (
        "counter",
        "Retrieval/curated-corpus failures, by kind (there is deliberately NO silent fallback to another question source)",
    ),
    "smart_experimental_evaluations_total": ("counter", "Experimental modular evaluations by outcome (scored|abstained|failed)"),
    "smart_experimental_abstentions_total": ("counter", "Experimental evaluations that abstained"),
    "smart_code_assessments_total": ("counter", "Static code assessments by outcome (done|failed)"),
    "smart_sessions_deleted_total": ("counter", "Demo sessions deleted by the user"),
    "smart_followups_total": ("counter", "Follow-up proposals by mode (deterministic|mock|live) and outcome (llm|mock|skip|fallback); never their text"),
    "smart_memory_items_total": ("counter", "Interview-memory items by outcome (added|merged|conflicts|rejected); never their text"),
    "smart_memory_references_total": ("counter", "Interviewer questions that referred back to a stored candidate statement, by kind"),
    "smart_policy_decisions_total": (
        "counter",
        "Adaptive-policy decisions by code (deeper|clarify|explore_related|revisit|new_competency|practical|wrapup|continue)",
    ),
    "smart_behavioural_probes_total": ("counter", "Behavioural follow-up probes by kind (action|result|measure|reflection|situation|clarification)"),
    "smart_embedding_model_loads_total": (
        "counter",
        "Embedding-model loads by component and outcome (loaded|cache_hit|failed); a rising 'loaded' count means unnecessary re-initialisation",
    ),
    "smart_followup_opportunities_total": (
        "counter",
        "Live follow-up opportunities by class: gap_open (a curated concept looks open), covered (all look covered), related_unknown",
    ),
    "smart_followup_skips_total": ("counter", "Follow-up skips by reason code (covered|off_topic|nothing_to_add) and who decided (rules|model)"),
    "smart_followup_repairs_total": ("counter", "One-shot repair attempts after a fixable wording rejection, by outcome (ok|failed); never text"),
    "smart_followup_rejections_total": ("counter", "Validator rejections by first reason code (no text)"),
    "smart_followup_memory_stage_total": (
        "counter",
        "Memory use in a live follow-up by stage: none_offered|offered_no_usable_lead|used|declined|not_connected|not_used|rejected|citation_invalid|not_reached|not_applicable (codes only)",
    ),
    "smart_followup_memory_citations_total": ("counter", "Model memory citations by validity (valid|dropped|rejected)"),
    "smart_followup_latency_seconds": (
        "summary",
        "Live follow-up call latency by model and phase (first_call|later_call; the one-off model load is measured separately by the warm-up)",
    ),
    "smart_model_available": ("gauge", "1 if a scorer/provider was ready at the last probe, else 0 (label: model)"),
    "smart_build_info": ("gauge", "Always 1; labels identify the running code/experiment version"),
}


def _clean(v: Any) -> str:
    return _LABEL_RE.sub("_", str(v).lower())[:64] or "_"


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: Dict[str, Dict[Tuple[Tuple[str, str], ...], Any]] = {}
        self.started = time.time()

    def _series(self, name: str, labels: Dict[str, Any]):
        key = tuple(sorted((_clean(k), _clean(v)) for k, v in labels.items()))
        bucket = self._values.setdefault(name, {})
        if key not in bucket and len(bucket) >= _MAX_SERIES_PER_METRIC:
            key = (("overflow", "true"),)
        return bucket, key

    def inc(self, name: str, n: float = 1, **labels: Any) -> None:
        try:
            if name not in KNOWN or KNOWN[name][0] != "counter":
                return
            with self._lock:
                b, k = self._series(name, labels)
                b[k] = b.get(k, 0) + n
        except Exception:
            pass

    def observe(self, name: str, seconds: float, **labels: Any) -> None:
        try:
            if name not in KNOWN or KNOWN[name][0] != "summary":
                return
            with self._lock:
                b, k = self._series(name, labels)
                cur = b.get(k) or {"count": 0, "sum": 0.0, "max": 0.0}
                cur["count"] += 1
                cur["sum"] += float(seconds)
                cur["max"] = max(cur["max"], float(seconds))
                b[k] = cur
        except Exception:
            pass

    def set(self, name: str, value: float, **labels: Any) -> None:
        try:
            if name not in KNOWN or KNOWN[name][0] != "gauge":
                return
            with self._lock:
                b, k = self._series(name, labels)
                b[k] = float(value)
        except Exception:
            pass

    def reset(self) -> None:
        with self._lock:
            self._values.clear()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            out: Dict[str, Any] = {}
            for name, series in self._values.items():
                rows = []
                for key, val in series.items():
                    row: Dict[str, Any] = {"labels": dict(key)}
                    if isinstance(val, dict):
                        row.update(
                            count=val["count"],
                            sum_seconds=round(val["sum"], 6),
                            max_seconds=round(val["max"], 6),
                            mean_seconds=round(val["sum"] / val["count"], 6) if val["count"] else None,
                        )
                    else:
                        row["value"] = val
                    rows.append(row)
                out[name] = {"type": KNOWN[name][0], "help": KNOWN[name][1], "series": rows}
            return {"uptime_seconds": round(time.time() - self.started, 1), "metrics": out}

    def prometheus(self) -> str:
        lines = []
        with self._lock:
            for name, series in sorted(self._values.items()):
                kind, help_ = KNOWN[name]
                lines.append(f"# HELP {name} {help_}")
                lines.append(f"# TYPE {name} {kind if kind != 'summary' else 'summary'}")
                for key, val in series.items():
                    lab = ",".join(f'{k}="{v}"' for k, v in key)
                    lab = "{" + lab + "}" if lab else ""
                    if isinstance(val, dict):
                        lines.append(f"{name}_count{lab} {val['count']}")
                        lines.append(f"{name}_sum{lab} {val['sum']:.6f}")
                    else:
                        lines.append(f"{name}{lab} {val:g}")
        return "\n".join(lines) + "\n"


METRICS = Metrics()


def inc(name: str, n: float = 1, **labels: Any) -> None:
    METRICS.inc(name, n, **labels)


def observe(name: str, seconds: float, **labels: Any) -> None:
    METRICS.observe(name, seconds, **labels)


def gauge(name: str, value: float, **labels: Any) -> None:
    METRICS.set(name, value, **labels)
