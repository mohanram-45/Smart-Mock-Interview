"""Flask observability hooks: request counters/latency, structured JSON access logs, /healthz, /readyz, /metrics.

What is logged: timestamp, request id, HTTP method, ROUTE TEMPLATE (e.g. /demo/api/session/<sid>/answer, never the real URL), status, duration.
What is never logged or recorded: query strings, request/response bodies, answers, reference answers, session ids, cookies, headers other than the id.
Legacy routes are unchanged: GET /health keeps returning {"status": "ok"}."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict

from flask import Flask, Response, g, jsonify, request

from . import version
from .metrics import METRICS, gauge, inc, observe

access_log = logging.getLogger("smart.access")


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Only fixed fields + the `extra` dict passed by this module are emitted; exception text is truncated."""

    def format(self, record: logging.LogRecord) -> str:
        out: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage()[:300],
        }
        extra = getattr(record, "smart", None)
        if isinstance(extra, dict):
            out.update(extra)
        return json.dumps(out, separators=(",", ":"), default=str)


def configure_json_access_log() -> None:
    """Attach a JSON stderr handler to the `smart.access` logger only (the rest of the app's logging is untouched). Idempotent."""
    if any(getattr(h, "_smart_json", False) for h in access_log.handlers):
        return
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    h._smart_json = True  # type: ignore[attr-defined]
    access_log.addHandler(h)
    access_log.setLevel(logging.INFO)
    access_log.propagate = False


def _enabled(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _status_class(code: int) -> str:
    return f"{code // 100}xx"


def probe_models() -> Dict[str, Any]:
    """Model availability WITHOUT training, downloading or importing torch: the registry's cheap readiness check, plus an optional 1-second Ollama
    reachability probe only when SMART_OBS_PROBE_OLLAMA=1 (default off, so /readyz never makes a network call unasked)."""
    out: Dict[str, Any] = {"scorers": {}}
    try:
        import sys

        sys.path.insert(0, str(version.ROOT / "src" / "model"))
        import model_registry as MR

        for key in MR.MODEL_CHOICES:
            r = MR.readiness(key)
            ok = bool(r.get("ready"))
            out["scorers"][key] = {"ready": ok, "reason": None if ok else str(r.get("reason", ""))[:160]}
            gauge("smart_model_available", 1 if ok else 0, model=key)
    except Exception as e:
        out["scorers_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    if _enabled("SMART_OBS_PROBE_OLLAMA", "0"):
        host = (os.environ.get("SMART_DEMO_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").strip()
        host = host if host.startswith("http") else "http://" + host
        up = False
        try:
            import urllib.request

            with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=1.0) as r:  # fixed path, GET only, no data sent
                up = r.status == 200
        except Exception:
            up = False
        out["ollama"] = {"reachable": up, "probed": True}
        gauge("smart_model_available", 1 if up else 0, model="ollama")
    else:
        out["ollama"] = {"reachable": None, "probed": False, "note": "set SMART_OBS_PROBE_OLLAMA=1 to probe"}
    return out


def readiness() -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    info = version.corpus_info()
    checks["corpus_manifest"] = {"ok": "error" not in info, "record_count": info.get("record_count")}
    d = os.environ.get("SMART_DEMO_DATA_DIR") or str(version.ROOT / "results" / "demo_sessions")
    try:
        os.makedirs(d, exist_ok=True)
        probe = os.path.join(d, f".ready-{uuid.uuid4().hex[:8]}")
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        checks["session_dir_writable"] = {"ok": True}
    except Exception as e:
        checks["session_dir_writable"] = {"ok": False, "error": f"{type(e).__name__}"}
    ok = all(c["ok"] for c in checks.values())  # scorers/Ollama are optional components: reported, never required for "ready"
    return {"ready": ok, "checks": checks, "optional": probe_models()}


def _set_build_info() -> None:
    """One smart_build_info series with one fixed label set (a second label set would show up as a duplicate series)."""
    gauge(
        "smart_build_info",
        1,
        app_version=version.APP_VERSION,
        commit=version.git_commit()[:12],
        pipeline=version.evaluator_versions().get("pipeline", "na"),
        freeze=str(version.freeze_info().get("version", "na")),
    )


def init_observability(app: Flask) -> None:
    """Idempotent. Adds request hooks and the /healthz, /readyz, /metrics routes."""
    if app.extensions.get("smart_obs"):
        return
    app.extensions["smart_obs"] = True
    if _enabled("SMART_JSON_LOGS", "1"):
        configure_json_access_log()
    log_requests = _enabled("SMART_ACCESS_LOG", "1")
    _set_build_info()

    @app.before_request
    def _obs_start():
        g._obs_t0 = time.perf_counter()
        rid = (request.headers.get("X-Request-ID") or "")[:36]
        g._obs_rid = rid if rid and all(c.isalnum() or c == "-" for c in rid) else uuid.uuid4().hex[:16]

    @app.after_request
    def _obs_end(resp: Response):
        try:
            t0 = getattr(g, "_obs_t0", None)
            dt = (time.perf_counter() - t0) if t0 is not None else 0.0
            rule = request.url_rule.rule if request.url_rule is not None else "unmatched"
            if rule.startswith("/static") or rule.endswith("/static/<path:filename>"):
                rule = "static"
            inc("smart_http_requests_total", method=request.method, endpoint=rule, status=_status_class(resp.status_code))
            observe("smart_http_request_seconds", dt, endpoint=rule)
            resp.headers.setdefault("X-Request-ID", getattr(g, "_obs_rid", ""))
            if log_requests and rule not in ("/healthz", "/metrics", "static"):
                access_log.info(
                    "request",
                    extra={
                        "smart": {
                            "event": "request",
                            "request_id": getattr(g, "_obs_rid", ""),
                            "method": request.method,
                            "endpoint": rule,
                            "status": resp.status_code,
                            "ms": round(dt * 1000, 1),
                        }
                    },
                )
        except Exception:
            pass
        return resp

    @app.route("/healthz", methods=["GET"])
    def healthz():
        """Liveness: the process is up and can build a response. No I/O, no model probe (cheap enough for a container HEALTHCHECK)."""
        return jsonify({"status": "ok", **version.build_info(light=True)}), 200

    @app.route("/readyz", methods=["GET"])
    def readyz():
        """Readiness: corpus manifest present and the session directory writable. Optional models are reported, never required."""
        r = readiness()
        return jsonify(r), (200 if r["ready"] else 503)

    @app.route("/metrics", methods=["GET"])
    def metrics():
        if not _enabled("SMART_METRICS_ENABLED", "1"):
            return jsonify({"error": "Endpoint not found"}), 404
        if request.args.get("format") == "prometheus":
            _set_build_info()
            return Response(METRICS.prometheus(), mimetype="text/plain; version=0.0.4")
        _set_build_info()
        snap = METRICS.snapshot()
        snap["build"] = version.build_info()
        return jsonify(snap), 200
