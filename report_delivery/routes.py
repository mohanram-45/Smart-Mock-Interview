"""Flask endpoints for downloading and emailing completed reports."""
import json
import re
import smtplib
from io import BytesIO
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from .email_sender import send_report_email, validate_email
from .pdf_generator import build_pdf

delivery_blueprint = Blueprint("report_delivery", __name__)
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
    data = request.get_json(silent=True) or {}
    recipient = str(data.get("email") or "").strip()
    if not validate_email(recipient):
        return jsonify({"error": "Enter a valid email address."}), 400
    try:
        report = _load_report(interview_id)
        pdf_bytes = build_pdf(report, PDF_DIR / f"{interview_id}_report.pdf")
        send_report_email(recipient, report, pdf_bytes)
        return jsonify({"message": f"Report sent successfully to {recipient}."}), 200
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "error": "Gmail authentication failed. Generate a fresh 16-character App Password, save it in report_delivery/.env, and restart Flask."
        }), 503
    except (RuntimeError, OSError, smtplib.SMTPException) as error:
        return jsonify({"error": str(error)}), 503
