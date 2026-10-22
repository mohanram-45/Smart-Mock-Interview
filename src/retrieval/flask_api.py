"""Flask glue for the feature-flagged curated retrieval integration.

Importing this module is cheap (no faiss / torch / numpy); the heavy stack is only touched on a curated request.

Flag:  SMART_QUESTION_SOURCE = legacy (default) | curated         (process default)
       "question_source" in POST /api/start-interview              (per-session override, locked for the session)
Other env: SMART_RETRIEVAL_ENABLED=1 (expose /api/retrieval/* while the default source is legacy),
           SMART_RETRIEVAL_WARMUP=1 (load model+index in a background thread at start-up instead of on first search),
           SMART_RETRIEVAL_EXPOSE_REFERENCE=1 (include reference answers in HTTP retrieval responses; default: redacted),
           SMART_RETRIEVAL_BACKEND / SMART_RETRIEVAL_MODEL / SMART_RETRIEVAL_LOCAL_ONLY (see service.py).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

SOURCES = ("legacy", "curated")
retrieval_blueprint = Blueprint("retrieval", __name__)
_sessions: Dict[str, Any] = {}


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def default_source() -> str:
    v = os.environ.get("SMART_QUESTION_SOURCE", "legacy").strip().lower() or "legacy"
    if v not in SOURCES:
        raise ValueError(f"SMART_QUESTION_SOURCE must be one of {SOURCES}, got {v!r}")
    return v


def resolve_source(requested: Optional[str]) -> str:
    """Per-request value wins over the env default. Invalid values raise ValueError (-> HTTP 400); never silently coerced."""
    if requested is None:
        return default_source()
    if not isinstance(requested, str) or requested.strip().lower() not in SOURCES:
        raise ValueError(f"Invalid question_source: {requested!r}. Choose from: {list(SOURCES)}")
    return requested.strip().lower()


def make_provider(source: str):
    """None for legacy (=> existing code path, no new imports). Curated -> provider bound to the shared service."""
    if source == "legacy":
        return None
    from .question_source import CuratedQuestionProvider
    from .service import get_service
    return CuratedQuestionProvider(get_service())


def question_meta(session: Any, q: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extra response fields. EMPTY for legacy sessions so legacy responses stay byte-identical."""
    if q is None or getattr(session, "question_source", "legacy") != "curated":
        return {}
    return {"question_source": "curated", "domain": q.get("domain"), "difficulty": q.get("difficulty"), "topic": q.get("topic")}


def _retrieval_enabled() -> bool:
    return _truthy("SMART_RETRIEVAL_ENABLED") or os.environ.get("SMART_QUESTION_SOURCE", "legacy").strip().lower() == "curated"


def _not_found():
    return jsonify({"error": "Endpoint not found"}), 404


def _redact(payload: Dict[str, Any]) -> Dict[str, Any]:
    if _truthy("SMART_RETRIEVAL_EXPOSE_REFERENCE"):
        return payload
    for r in payload.get("results", []):
        r.pop("reference_answer", None)
    return payload


def _service_call(fn):
    from .service import CorpusUnavailable, RetrievalInputError
    try:
        return fn(), 200
    except RetrievalInputError as exc:
        return {"error": str(exc)}, 400
    except CorpusUnavailable as exc:
        try:
            from ..mlops.metrics import inc
            inc("smart_retrieval_failures_total", kind="corpus_unavailable", surface="retrieval_api")
        except Exception:
            pass
        return {"error": str(exc), "question_source": "curated"}, 503


@retrieval_blueprint.route("/api/retrieval/status", methods=["GET"])
def retrieval_status():
    if not _retrieval_enabled():
        return _not_found()
    from .service import get_service
    return jsonify({"default_question_source": default_source(), **get_service().status()}), 200


@retrieval_blueprint.route("/api/retrieval/search", methods=["POST"])
def retrieval_search():
    if not _retrieval_enabled():
        return _not_found()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object body required"}), 400
    from .service import get_service
    body, code = _service_call(lambda: get_service().search(data.get("query"), data.get("k", 5), data.get("domain"),
                                                            data.get("difficulty"), data.get("min_score")))
    return jsonify(_redact(body) if code == 200 else body), code


@retrieval_blueprint.route("/api/retrieval/diagnostics", methods=["POST"])
def retrieval_diagnostics():
    """Stage 8B experimental: scores, evidence band, provenance and index/model fingerprints for one query. Never returns reference answers (no opt-in exists)."""
    if not _retrieval_enabled():
        return _not_found()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object body required"}), 400
    from .service import get_service
    body, code = _service_call(lambda: get_service().diagnose(data.get("query"), data.get("k", 5), data.get("domain")))
    return jsonify(body), code


@retrieval_blueprint.route("/api/retrieval/session-context", methods=["GET"])
def session_context():
    """Knowledge related to the session's CURRENT question (curated sessions only). Excludes the question itself."""
    sid = request.args.get("session_id")
    session = _sessions.get(sid) if sid else None
    if session is None:
        return jsonify({"error": "Invalid session"}), 400
    if getattr(session, "question_source", "legacy") != "curated":
        return jsonify({"error": "Session is not using the curated question source", "question_source": getattr(session, "question_source", "legacy")}), 409
    q = session._get_current_question()
    if not q:
        return jsonify({"error": "Interview finished or no more questions"}), 400
    try:
        k = int(request.args.get("k", 5))
    except ValueError:
        return jsonify({"error": "k must be a positive integer"}), 400
    from .service import get_service

    def go():
        res = get_service().search(q["question"], k + 1, domain=None)
        res["results"] = [r for r in res["results"] if r["question_id"] != q["id"]][:k]
        for i, r in enumerate(res["results"], 1):
            r["rank"] = i
        res["k"] = k
        res["for_question_id"] = q["id"]
        return res
    body, code = _service_call(go)
    return jsonify(_redact(body) if code == 200 else body), code


def init_retrieval(app, sessions: Dict[str, Any]) -> None:
    """Register the blueprint and share the app's in-memory session dict."""
    global _sessions
    _sessions = sessions
    app.register_blueprint(retrieval_blueprint)
    if _truthy("SMART_RETRIEVAL_WARMUP") and _retrieval_enabled():
        import threading

        def _warm():
            from .service import get_service
            try:
                get_service().warm()
            except Exception:                       # warm() records failures itself; never crash app start-up
                logger.exception("retrieval warm-up failed")
        threading.Thread(target=_warm, name="retrieval-warmup", daemon=True).start()
