"""Flask API - Adaptive Interview System."""
import logging
import json
import threading
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "components"))

from interview_session import AdaptiveInterviewSession
from config import ROLE_MAPPING

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "model"))
from model_registry import list_models, is_valid_model, DEFAULT_MODEL, MODEL_CHOICES

sys.path.insert(0, str(Path(__file__).parent.parent))
from report_delivery.routes import delivery_blueprint
from question_provider import QuestionSourceUnavailable
from src.retrieval.flask_api import init_retrieval, make_provider, question_meta, resolve_source
from src.demo.routes import init_demo
from src.mlops.obs import init_observability
from src.security.local_guard import cors_origins
from src.mlops.metrics import inc as _metric

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.register_blueprint(delivery_blueprint)

CORS(app, resources={
    r"/api/*": {
        "origins": cors_origins(),      # Stage 13: local pages only (was "*"); extra origins via SMART_ALLOWED_ORIGINS
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-Report-Token"]
    }
})

sessions = {}
report_jobs = {}
init_retrieval(app, sessions)   # /api/retrieval/* (404 unless curated mode is enabled)
init_observability(app)         # /healthz /readyz /metrics + privacy-safe request metrics and JSON access log (never logs bodies or answers)
init_demo(app)                  # /demo/*  Stage 4A end-to-end demonstration (separate sessions; legacy /api/* routes and scoring untouched)


def _generate_report_job(session_id, session):
    """Finish a report outside the browser request so Ollama can load safely."""
    try:
        report = session.end_interview()
        if "error" in report:
            raise RuntimeError(report["error"])
        session.report_generator.save_report(report)
        report_jobs[session_id] = {"status": "complete", "report": report}
        logger.info("Background report completed for %s", session_id)
    except Exception as error:
        logger.exception("Background report failed for %s", session_id)
        report_jobs[session_id] = {"status": "failed", "error": str(error)}


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Get available interview roles and domains."""
    roles = list(ROLE_MAPPING.keys())
    return jsonify({
        "roles": roles,
        "role_mappings": ROLE_MAPPING
    }), 200


@app.route('/api/domains', methods=['GET'])
def get_domains():
    """Get all available domains."""
    all_domains = set()
    for domains in ROLE_MAPPING.values():
        all_domains.update(domains)
    return jsonify({
        "domains": sorted(list(all_domains))
    }), 200


@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available answer-scoring models the candidate can choose between.

    The chosen model is locked in for the entire session - every question in
    that session is scored with the same model.
    """
    return jsonify({
        "models": list_models(),
        "default": DEFAULT_MODEL
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# INTERVIEW ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/start-interview', methods=['POST'])
def start_interview():
    """
    Start a new adaptive interview session.

    Request:
        {
            "role": "Data Scientist",
            "custom_domains": ["Python", "ML"],  (only for "Custom Interview" role)
            "model": "bilstm"  ("bilstm" | "bert" | "tfidf" - locked for the whole session)
        }

    Response:
        {
            "session_id": "...",
            "role": "Data Scientist",
            "selected_domains": [...],
            "model": {"key": "bilstm", "label": "Siamese Bi-LSTM"},
            "current_round": "Easy",
            "first_question": {...}
        }
    """
    try:
        data = request.get_json() or {}
        role = data.get('role', 'Custom Interview')
        custom_domains = data.get('custom_domains', [])
        model_choice = data.get('model', DEFAULT_MODEL)

        if role not in ROLE_MAPPING:
            return jsonify({"error": f"Invalid role: {role}"}), 400

        if not is_valid_model(model_choice):
            return jsonify({"error": f"Invalid model: {model_choice}"}), 400

        try:
            question_source = resolve_source(data.get('question_source'))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        session_id = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        try:
            session = AdaptiveInterviewSession(session_id, role, custom_domains, model_choice=model_choice,
                                               question_provider=make_provider(question_source))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        try:
            loaded = session.load_questions()
        except QuestionSourceUnavailable as e:
            _metric("smart_retrieval_failures_total", kind="source_unavailable", surface="legacy")
            return jsonify({"error": str(e), "question_source": question_source}), 503

        if not loaded:
            return jsonify({"error": "Failed to load questions for selected domains"}), 400

        first_question = session.start_round("Easy")
        if not first_question:
            return jsonify({"error": "No questions available for Easy round"}), 400

        sessions[session_id] = session
        _metric("smart_interviews_started_total", surface="legacy")

        response = {
            "session_id": session_id,
            "role": role,
            "selected_domains": session.selected_domains,
            "model": {
                "key": model_choice,
                "label": MODEL_CHOICES[model_choice]["label"]
            },
            "started_at": session.started_at,
            "current_round": "Easy",
            "current_question": {
                "question_id": first_question.get("id"),
                "question": first_question.get("question"),
                "question_number": 1,
                "total_in_round": len(session.round_questions["Easy"]),
                **question_meta(session, first_question)
            }
        }
        if question_source != "legacy":
            response["question_source"] = question_source

        logger.info(f"Started interview session {session_id} for role {role}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error starting interview: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/current-question', methods=['GET'])
def get_current_question():
    """Get current question."""
    session_id = request.args.get('session_id')
    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400

    session = sessions[session_id]
    question = session._get_current_question()

    if not question:
        return jsonify({"error": "Interview finished or no more questions"}), 400

    return jsonify({
        "question_id": question.get("id"),
        "question": question.get("question"),
        "question_number": session.current_question_index + 1,
        "total_in_round": len(session.round_questions[session.current_round_name]),
        "current_round": session.current_round_name,
        **question_meta(session, question)
    }), 200


@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """
    Submit answer and get feedback.

    Request:
        {
            "session_id": "...",
            "answer": "..."
        }

    Response:
        {
            "similarity_score": 85.43,
            "feedback": "...",
            "question_completed": true,
            "round_complete": false
        }
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        user_answer = data.get('answer', '').strip()

        if not session_id or session_id not in sessions:
            return jsonify({"error": "Invalid session"}), 400

        if not user_answer:
            return jsonify({"error": "Answer cannot be empty"}), 400

        session = sessions[session_id]
        result = session.submit_answer(user_answer)
        _metric("smart_answers_submitted_total", surface="legacy")

        if "error" in result:
            return jsonify(result), 400

        # Check if round is complete
        completion = session.check_round_completion()

        result["round_complete"] = completion.get("action") != "continue"
        result["round_action"] = completion.get("action")

        if completion.get("action") == "next_round":
            result["next_round"] = completion.get("next_round")
            result["round_average"] = completion.get("average_score")

        return jsonify(result), 200

    except Exception as e:
        _metric("smart_scorer_failures_total", scorer="legacy_api", stage="submit_error")
        logger.error(f"Error submitting answer: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/check-round-completion', methods=['POST'])
def check_round_completion():
    """
    Check if current round is complete and determine next action.

    Request:
        {
            "session_id": "..."
        }

    Response:
        {
            "action": "continue_round" | "next_round" | "end_interview",
            "current_round": "Easy",
            "average_score": 75.5,
            "next_round": "Medium",
            "message": "..."
        }
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({"error": "Invalid session"}), 400

        session = sessions[session_id]
        completion = session.check_round_completion()

        # Handle round progression
        if completion.get("action") == "continue_round":
            # Add extra questions
            next_q = session.continue_round()
            if next_q:
                completion["next_question"] = {
                    "question_id": next_q.get("id"),
                    "question": next_q.get("question"),
                    "question_number": session.current_question_index + 1,
                    "total_in_round": len(session.round_questions[session.current_round_name]),
                    **question_meta(session, next_q)
                }

        elif completion.get("action") == "next_round":
            # Start next round
            next_round = completion.get("next_round")
            next_q = session.start_round(next_round)
            if next_q:
                completion["next_question"] = {
                    "question_id": next_q.get("id"),
                    "question": next_q.get("question"),
                    "question_number": 1,
                    "total_in_round": len(session.round_questions[next_round]),
                    **question_meta(session, next_q)
                }

        return jsonify(completion), 200

    except Exception as e:
        logger.error(f"Error checking round completion: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/next-question', methods=['POST'])
def next_question():
    """Move to next question in current round."""
    data = request.get_json() or {}
    session_id = data.get('session_id')

    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400

    session = sessions[session_id]
    next_q = session._get_current_question()

    if not next_q:
        return jsonify({"finished": True}), 200

    return jsonify({
        "question_id": next_q.get("id"),
        "question": next_q.get("question"),
        "question_number": session.current_question_index + 1,
        "total_in_round": len(session.round_questions[session.current_round_name]),
        "current_round": session.current_round_name,
        **question_meta(session, next_q)
    }), 200


@app.route('/api/skip-question', methods=['POST'])
def skip_question():
    """Skip current question."""
    data = request.get_json() or {}
    session_id = data.get('session_id')

    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400

    session = sessions[session_id]
    result = session.skip_question()

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result), 200


@app.route('/api/repeat-question', methods=['GET'])
def repeat_question():
    """Repeat current question."""
    session_id = request.args.get('session_id')

    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400

    session = sessions[session_id]
    question = session.repeat_question()

    if not question:
        return jsonify({"error": "No question to repeat"}), 400

    return jsonify({
        "question_id": question.get("id"),
        "question": question.get("question"),
        **question_meta(session, question)
    }), 200


@app.route('/api/end-interview', methods=['POST'])
def end_interview():
    """
    End interview and get final report.

    Request:
        {
            "session_id": "..."
        }

    Response:
        Complete interview report with round statistics
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')

        if session_id in report_jobs:
            job = report_jobs[session_id]
            if job["status"] == "complete":
                return jsonify(job["report"]), 200
            return jsonify({"status": job["status"], "interview_id": session_id}), 202

        if not session_id or session_id not in sessions:
            return jsonify({"error": "Invalid session"}), 400

        session = sessions.pop(session_id)
        _metric("smart_interviews_completed_total", surface="legacy")
        report_jobs[session_id] = {"status": "processing"}
        worker = threading.Thread(
            target=_generate_report_job,
            args=(session_id, session),
            name=f"report-{session_id}",
            daemon=True,
        )
        worker.start()
        return jsonify({"status": "processing", "interview_id": session_id}), 202

    except Exception as e:
        logger.error(f"Error ending interview: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reports/<interview_id>/status', methods=['GET'])
def report_status(interview_id):
    """Poll a background Ollama report until it is complete."""
    job = report_jobs.get(interview_id)
    if job:
        if job["status"] == "complete":
            return jsonify(job["report"]), 200
        if job["status"] == "failed":
            return jsonify({"status": "failed", "error": job.get("error", "Report generation failed")}), 500
        return jsonify({"status": "processing", "interview_id": interview_id}), 202

    report_path = Path(__file__).parent.parent / "results" / "reports" / f"{interview_id}_report.json"
    if report_path.is_file():
        return jsonify(json.loads(report_path.read_text(encoding="utf-8"))), 200
    return jsonify({"error": "Report job not found"}), 404


@app.route('/api/session-status', methods=['GET'])
def session_status():
    """Get current session status."""
    session_id = request.args.get('session_id')

    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400

    session = sessions[session_id]
    status = session.get_status()

    # Remove current_question detail
    status.pop('current_question', None)

    return jsonify(status), 200


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({"status": "ok"}), 200


@app.route('/', methods=['GET'])
def index():
    """API info."""
    return jsonify({
        "name": "SMART Mock Interview - Adaptive System",
        "version": "2.0.0",
        "key_endpoints": {
            "GET /api/roles": "Get available interview roles",
            "GET /api/domains": "Get available domains",
            "GET /api/models": "Get available answer-scoring models",
            "POST /api/start-interview": "Start new interview",
            "GET /api/current-question": "Get current question",
            "POST /api/submit-answer": "Submit answer and get feedback",
            "POST /api/check-round-completion": "Check if round complete and next action",
            "POST /api/next-question": "Move to next question",
            "POST /api/skip-question": "Skip current question",
            "GET /api/repeat-question": "Repeat current question",
            "POST /api/end-interview": "End interview and get report",
            "GET /api/reports/<interview_id>/status": "Check background report generation",
            "GET /api/reports/<interview_id>/pdf": "Download the completed report as PDF",
            "POST /api/reports/<interview_id>/email": "Email the completed PDF report",
            "GET /api/session-status": "Get session status"
        }
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import os
    # Local-first defaults: bind to this machine only and keep Werkzeug's interactive debugger OFF (it executes code in the browser and the interview pages hold
    # candidate answers). Both are one environment variable away from the old behaviour:  set SMART_HOST=0.0.0.0   set SMART_DEBUG=1
    host = os.environ.get("SMART_HOST", "127.0.0.1")
    port = int(os.environ.get("SMART_PORT", "5000"))
    debug = os.environ.get("SMART_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")
    logger.info("Starting SMART Mock Interview - Adaptive System")
    logger.info("Open the interview demo at  http://%s:%s/demo/", "127.0.0.1" if host in ("0.0.0.0", "::") else host, port)
    # reloader disabled: it watches every imported module including
    # transformers, which restarts the server mid-request on first BERT load
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False
    )
