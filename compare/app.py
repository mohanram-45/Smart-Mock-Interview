"""Standalone tool for comparing the 3 scoring models on the same
question/answer pair. Separate Flask app/port from the main interview
app - imports model_registry.py directly so results match the real
scoring models exactly.

Run: cd compare && python app.py, then open localhost:5050
"""
import json
import logging
import random
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "model"))
from model_registry import get_scorer, list_models, is_valid_model, DEFAULT_MODEL, MODEL_CHOICES  # noqa: E402

TOPIC_QUESTION_COUNT = 5

BASE_DIR = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR.parent / "data" / "processed" / "questions_cleaned.json"

with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

QUESTIONS_BY_ID = {q["id"]: q for q in ALL_QUESTIONS}
CORPUS = [q.get("reference_answer", "") for q in ALL_QUESTIONS]  # TF-IDF vectorizer corpus

logger.info(f"Loaded {len(ALL_QUESTIONS)} questions for the similarity checker")

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/topic-compare")
def topic_compare_page():
    return send_from_directory(BASE_DIR, "topic_compare.html")


@app.route("/api/models", methods=["GET"])
def api_models():
    return jsonify({"models": list_models(), "default": DEFAULT_MODEL}), 200


@app.route("/api/questions", methods=["GET"])
def api_questions():
    """Returns questions without reference answers, so users write their
    own answer instead of copying it."""
    questions = [
        {
            "id": q["id"],
            "question": q.get("question", ""),
            "difficulty": q.get("difficulty", ""),
            "domain": q.get("domain", ""),
        }
        for q in ALL_QUESTIONS
    ]
    questions.sort(key=lambda q: (q["domain"], q["difficulty"], q["id"]))
    return jsonify({"questions": questions}), 200


@app.route("/api/score", methods=["POST"])
def api_score():
    data = request.get_json(silent=True) or {}
    model_key = data.get("model")
    question_id = data.get("question_id")
    answer = (data.get("answer") or "").strip()

    if not is_valid_model(model_key):
        return jsonify({"error": f"Invalid model '{model_key}'"}), 400
    if question_id is None or question_id not in QUESTIONS_BY_ID:
        return jsonify({"error": "Invalid question_id"}), 400
    if not answer:
        return jsonify({"error": "Answer is required"}), 400

    question = QUESTIONS_BY_ID[question_id]
    reference_answer = question.get("reference_answer", "")

    try:
        scorer = get_scorer(model_key, corpus=CORPUS)
        similarity = scorer.score(reference_answer, answer)
        similarity_percent = round(max(0.0, min(1.0, similarity)) * 100, 2)
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        return jsonify({"error": f"Scoring failed: {e}"}), 500

    return jsonify({
        "model_key": model_key,
        "question": question.get("question", ""),
        "difficulty": question.get("difficulty", ""),
        "domain": question.get("domain", ""),
        "answer": answer,
        "similarity_percent": similarity_percent
    }), 200


@app.route("/api/topics", methods=["GET"])
def api_topics():
    domains = sorted({q.get("domain", "") for q in ALL_QUESTIONS if q.get("domain")})
    return jsonify({"topics": domains}), 200


@app.route("/api/topic-questions", methods=["POST"])
def api_topic_questions():
    data = request.get_json(silent=True) or {}
    domain = data.get("domain")

    pool = [q for q in ALL_QUESTIONS if q.get("domain") == domain]
    if not pool:
        return jsonify({"error": f"No questions found for topic '{domain}'"}), 400

    picked = random.sample(pool, min(TOPIC_QUESTION_COUNT, len(pool)))
    questions = [
        {"id": q["id"], "question": q.get("question", ""), "difficulty": q.get("difficulty", "")}
        for q in picked
    ]
    return jsonify({"questions": questions}), 200


@app.route("/api/topic-score", methods=["POST"])
def api_topic_score():
    """Scores one answer against all 3 models at once, for the
    side-by-side topic comparison view."""
    data = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    answer = (data.get("answer") or "").strip()

    if question_id is None or question_id not in QUESTIONS_BY_ID:
        return jsonify({"error": "Invalid question_id"}), 400
    if not answer:
        return jsonify({"error": "Answer is required"}), 400

    question = QUESTIONS_BY_ID[question_id]
    reference_answer = question.get("reference_answer", "")

    scores = {}
    for model_key in MODEL_CHOICES:
        try:
            scorer = get_scorer(model_key, corpus=CORPUS)
            similarity = scorer.score(reference_answer, answer)
            scores[model_key] = round(max(0.0, min(1.0, similarity)) * 100, 2)
        except Exception as e:
            logger.error(f"Scoring failed for model '{model_key}': {e}")
            scores[model_key] = None

    return jsonify({
        "question": question.get("question", ""),
        "difficulty": question.get("difficulty", ""),
        "domain": question.get("domain", ""),
        "answer": answer,
        "scores": scores
    }), 200


if __name__ == "__main__":
    # reloader disabled: it watches every imported module including
    # transformers/sentence-transformers and restarts mid-request
    app.run(host="0.0.0.0", port=5050, debug=True, use_reloader=False)
