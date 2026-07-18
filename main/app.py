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
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

sessions = {}
report_jobs = {}


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

        session_id = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        try:
            session = AdaptiveInterviewSession(session_id, role, custom_domains, model_choice=model_choice)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        if not session.load_questions():
            return jsonify({"error": "Failed to load questions for selected domains"}), 400

        first_question = session.start_round("Easy")
        if not first_question:
            return jsonify({"error": "No questions available for Easy round"}), 400

        sessions[session_id] = session

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
                "total_in_round": len(session.round_questions["Easy"])
            }
        }

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
        "current_round": session.current_round_name
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
                    "total_in_round": len(session.round_questions[session.current_round_name])
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
                    "total_in_round": len(session.round_questions[next_round])
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
        "current_round": session.current_round_name
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
        "question": question.get("question")
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
    logger.info("Starting SMART Mock Interview - Adaptive System")
    # reloader disabled: it watches every imported module including
    # transformers, which restarts the server mid-request on first BERT load
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )
