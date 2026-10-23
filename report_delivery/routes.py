"""Flask endpoints for downloading and emailing completed reports."""
import json
import re
import smtplib
from io import BytesIO
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from src.security.local_guard import SendLimiter, check_request, valid_recipient

from .email_sender import send_report_email
from .pdf_generator import build_pdf

delivery_blueprint = Blueprint("report_delivery", __name__)
_LIMITER = SendLimiter()


@delivery_blueprint.before_request
def _local_only():
    """Stage 13: reports are private. Only pages on this computer (or a script on it) may download or email them; see src/security/local_guard.py."""
    if check_request(request) is not None:
        return jsonify({"error": "Forbidden."}), 403
    return None
ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "results" / "reports"
PDF_DIR = ROOT / "output" / "pdf"
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _load_report(interview_id: str):
    if not SAFE_ID.fullmatch(interview_id or ""):
        raise ValueError("Invalid interview ID.")
    path = REPORTS_DIR / f"{interview_id}_report.json"
    if not path.is_file():
        raise FileNotFoundError("Completed report not found.")
    return json.loads(path.read_text(encoding="utf-8"))


@delivery_blueprint.get("/api/reports/<interview_id>/pdf")
def download_report_pdf(interview_id: str):
    try:
        report = _load_report(interview_id)
        output_path = PDF_DIR / f"{interview_id}_report.pdf"
        pdf_bytes = build_pdf(report, output_path)
        role_name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(report.get("interview_role") or "Interview"))
        return send_file(
            BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True,
            download_name=f"SMART_{role_name}_Report.pdf",
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404


@delivery_blueprint.post("/api/reports/<interview_id>/email")
def email_report(interview_id: str):
    if not request.is_json:                                    # a cross-site form post cannot send JSON without a CORS preflight
        return jsonify({"error": "Send a JSON body."}), 415
    data = request.get_json(silent=True)
    recipient = str(data.get("email") or "") if isinstance(data, dict) else ""
    if not valid_recipient(recipient):
        return jsonify({"error": "Enter a valid email address."}), 400
    try:
        report = _load_report(interview_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    wait = _LIMITER.allow(interview_id)
    if wait is not None:
        return jsonify({"error": f"Too many emails. Try again in {wait} seconds."}), 429
    try:
        pdf_bytes = build_pdf(report, PDF_DIR / f"{interview_id}_report.pdf")
        send_report_email(recipient, report, pdf_bytes)
        return jsonify({"message": "Report sent successfully."}), 200
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "error": "Gmail authentication failed. Generate a fresh 16-character App Password, save it in report_delivery/.env, and restart Flask."
        }), 503
    except RuntimeError as error:                              # our own configuration guidance (no server detail)
        return jsonify({"error": str(error)}), 503
    except (OSError, smtplib.SMTPException):                   # network/SMTP detail stays in the server, not the response
        return jsonify({"error": "The email could not be sent. Check the SMTP settings and try again."}), 503
