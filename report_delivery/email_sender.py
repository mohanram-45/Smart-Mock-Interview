"""Send a professional HTML report email with its PDF attached."""
import re
import smtplib
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import Any, Dict

from dotenv import dotenv_values

SMTP_CONFIG_PATH = Path(__file__).with_name(".env")


def _smtp_config() -> Dict[str, str]:
    """Read the dedicated SMTP file fresh for every send operation."""
    return {
        key: str(value or "").strip()
        for key, value in dotenv_values(SMTP_CONFIG_PATH).items()
    }

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_email(address: str) -> bool:
    return bool(address and len(address) <= 254 and EMAIL_PATTERN.fullmatch(address))


def _html(report: Dict[str, Any]) -> str:
    role = escape(str(report.get("interview_role") or "Interview"))
    score = float(report.get("average_score") or 0)
    rating = escape(str((report.get("analysis") or {}).get("performance_label") or "Completed"))
    recommendations = (report.get("analysis") or {}).get("recommendations") or []
    items = "".join(f"<li style='margin:0 0 10px'>{escape(str(item))}</li>" for item in recommendations[:4])
    return f"""<!doctype html><html><body style="margin:0;background:#f3f7f5;font-family:Arial,sans-serif;color:#15211d">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f7f5;padding:30px 12px"><tr><td align="center">
    <table role="presentation" width="620" cellspacing="0" cellpadding="0" style="max-width:620px;background:#fff;border:1px solid #dfe8e4;border-radius:18px;overflow:hidden">
      <tr><td style="background:#176b52;padding:28px 34px;color:#fff"><div style="font-size:12px;font-weight:bold;letter-spacing:1.5px;opacity:.8">SMART MOCK INTERVIEW ASSISTANT</div><h1 style="margin:8px 0 0;font-size:26px">Your interview report is ready</h1></td></tr>
      <tr><td style="padding:30px 34px"><p style="margin-top:0;font-size:16px">Hello,</p><p style="line-height:1.6;color:#3f514a">Your <b>{role}</b> mock-interview report has been completed and is attached as a professionally formatted PDF.</p>
      <table role="presentation" width="100%" style="margin:24px 0;background:#edf7f3;border-radius:12px;padding:18px"><tr><td><b>Overall score</b><br><span style="font-size:26px;color:#176b52">{score:.1f}%</span></td><td><b>Performance</b><br><span style="color:#176b52">{rating}</span></td></tr></table>
      <h2 style="font-size:16px">Priority recommendations</h2><ul style="padding-left:20px;line-height:1.5;color:#3f514a">{items}</ul>
      <p style="margin:26px 0 0;line-height:1.6;color:#3f514a">Open the attached PDF for your complete technical study guide, learning plan, practice tasks, and mastery checks.</p></td></tr>
      <tr><td style="padding:18px 34px;background:#f8faf9;color:#70817a;font-size:12px">Generated privately by SMART MOCK INTERVIEW ASSISTANT. This mailbox is not monitored.</td></tr>
    </table></td></tr></table></body></html>"""


def send_report_email(recipient: str, report: Dict[str, Any], pdf_bytes: bytes) -> None:
    if not validate_email(recipient):
        raise ValueError("Enter a valid email address.")

    config = _smtp_config()
    host = config.get("SMTP_HOST")
    username = config.get("SMTP_USERNAME")
    password = config.get("SMTP_PASSWORD")
    sender = config.get("SMTP_FROM") or username or ""
    port = int(config.get("SMTP_PORT") or "587")
    use_ssl = (config.get("SMTP_USE_SSL") or "false").lower() == "true"
    if not host or not sender:
        raise RuntimeError("Email delivery is not configured. Set SMTP_HOST, SMTP_FROM, and optional SMTP credentials.")

    # Google displays App Passwords in four groups. Accept either the grouped
    # or compact form, but never allow a normal Gmail password to reach SMTP.
    if username and username.lower().endswith("@gmail.com"):
        password = "".join((password or "").split())
        if len(password) != 16:
            raise RuntimeError(
                "Gmail requires a 16-character App Password. Create one in your Google Account security settings, "
                "place it in SMTP_PASSWORD, and restart the Flask backend. Do not use your normal Gmail password."
            )

    role = str(report.get("interview_role") or "Interview")
    message = EmailMessage()
    message["Subject"] = f"Your {role} Interview Report"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("Your SMART MOCK INTERVIEW ASSISTANT report is attached as a PDF.")
    message.add_alternative(_html(report), subtype="html")
    filename = f"SMART_{re.sub(r'[^A-Za-z0-9_-]+', '_', role)}_Report.pdf"
    message.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(host, port, timeout=15) as smtp:
        if not use_ssl:
            smtp.starttls()
        if username and password:
            try:
                smtp.login(username, password)
            except smtplib.SMTPAuthenticationError as error:
                raise RuntimeError(
                    "Gmail rejected the App Password. Confirm that 2-Step Verification is enabled, generate a new "
                    "16-character App Password for Mail, update SMTP_PASSWORD, and restart Flask."
                ) from error
        smtp.send_message(message)
