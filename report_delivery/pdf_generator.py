"""Create polished PDF interview reports using ReportLab."""
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)
from xml.sax.saxutils import escape

GREEN = colors.HexColor("#176B52")
DARK_GREEN = colors.HexColor("#0F523E")
INK = colors.HexColor("#15211D")
MUTED = colors.HexColor("#667870")
PALE = colors.HexColor("#EDF7F3")
BORDER = colors.HexColor("#DDE8E3")
RED = colors.HexColor("#C74B53")
WHITE = colors.white


def _text(value: Any) -> str:
    return escape(str(value or ""))


def _items(values: Iterable[Any], style: ParagraphStyle, bullet_color: str = "#176B52"):
    rows = []
    for value in values or []:
        rows.append(Table([
            [Paragraph(f'<font color="{bullet_color}">-</font>', style), Paragraph(_text(value), style)]
        ], colWidths=[5 * mm, 158 * mm], style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])))
    return rows


def _page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(BORDER)
    canvas.line(20 * mm, 15 * mm, width - 20 * mm, 15 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 9.5 * mm, "SMART MOCK INTERVIEW ASSISTANT")
    canvas.drawRightString(width - 20 * mm, 9.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(report: Dict[str, Any], output_path: Path | None = None) -> bytes:
    """Build the report and optionally save the exact bytes to output_path."""
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=22 * mm,
        title=f"{report.get('interview_role', 'Interview')} Report",
        author="SMART MOCK INTERVIEW ASSISTANT",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="report")
    doc.addPageTemplates(PageTemplate(id="report", frames=[frame], onPage=_page))

    base = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=INK, alignment=TA_LEFT, spaceAfter=5)
    role_style = ParagraphStyle("Role", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=GREEN)
    section = ParagraphStyle("Section", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=15, spaceAfter=8, uppercase=True)
    body = ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.2, leading=14, textColor=colors.HexColor("#3F514A"))
    small = ParagraphStyle("Small", parent=body, fontSize=8.2, leading=11, textColor=MUTED)
    card_title = ParagraphStyle("CardTitle", parent=body, fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=INK, spaceAfter=4)
    label = ParagraphStyle("Label", parent=small, fontName="Helvetica-Bold", textColor=GREEN)
    centered = ParagraphStyle("Centered", parent=body, alignment=TA_CENTER)

    analysis = report.get("analysis") or {}
    weaknesses = analysis.get("weaknesses") or {}
    score = float(report.get("average_score") or 0)
    rating = (analysis.get("performance_label") or "Interview completed").split(" (")[0]
    role = report.get("interview_role") or "Technical Interview"

    story = [
        Paragraph("INTERVIEW PERFORMANCE REPORT", ParagraphStyle("Kicker", parent=small, fontName="Helvetica-Bold", textColor=GREEN, tracking=1.2)),
        Paragraph(_text(role), title),
        Paragraph(_text(rating), role_style),
        Spacer(1, 7 * mm),
    ]

    stats = [
        [Paragraph(f"<b>{score:.1f}%</b><br/><font size='8' color='#667870'>Overall score</font>", centered),
         Paragraph(f"<b>{report.get('questions_answered', 0)}</b><br/><font size='8' color='#667870'>Answered</font>", centered),
         Paragraph(f"<b>{report.get('questions_skipped', 0)}</b><br/><font size='8' color='#667870'>Skipped</font>", centered),
         Paragraph(f"<b>{_text(report.get('scoring_model', 'AI'))}</b><br/><font size='8' color='#667870'>Scoring model</font>", centered)]
    ]
    stat_table = Table(stats, colWidths=[42.5 * mm] * 4, rowHeights=[21 * mm])
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(stat_table)

    demonstrated = ((analysis.get("strengths") or {}).get("demonstrated_topics") or [])
    if demonstrated:
        story.append(Paragraph("DEMONSTRATED STRENGTHS", section))
        story += _items(
            [str(item.get("topic") or "") for item in demonstrated],
            body,
        )

    story.append(Paragraph("AREAS FOR IMPROVEMENT", section))

    weak_lines = []
    for item in weaknesses.get("weak_questions") or []:
        weak_lines.append(item.get("question"))
    for item in weaknesses.get("skipped_questions") or []:
        weak_lines.append(f"Skipped: {item.get('question')}")
    story += _items(weak_lines or ["No significant weak areas identified."], body, "#C74B53")

    technical_focus = analysis.get("technical_focus") or []
    if technical_focus:
        story.append(Paragraph("TECHNICAL STUDY GUIDE", section))
        for item in technical_focus:
            terms = "  |  ".join(_text(term) for term in item.get("terms") or [])
            content = [
                Paragraph(_text(item.get("topic")), card_title),
                Paragraph(terms, small), Spacer(1, 2 * mm),
                Paragraph(f"<b>Practice:</b> {_text(item.get('practice_task'))}", body),
                Paragraph(f"<b>Mastery check:</b> {_text(item.get('success_criteria'))}", body),
            ]
            card = Table([[content]], colWidths=[164 * mm])
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]))
            story += [KeepTogether(card), Spacer(1, 3 * mm)]

    story.append(Paragraph("PERSONALIZED LEARNING PLAN", section))
    for phase in analysis.get("learning_plan") or []:
        phase_content = [
            Paragraph(_text(phase.get("phase")), card_title),
            Paragraph(f"<b>Focus:</b> {_text(phase.get('focus'))}", small),
            *_items(phase.get("actions") or [], body),
        ]
        story += [KeepTogether(phase_content), Spacer(1, 3 * mm)]

    story.append(Paragraph("RECOMMENDATIONS", section))
    story += _items(analysis.get("recommendations") or [], body)
    if analysis.get("next_assessment_date"):
        story += [Spacer(1, 3 * mm), Paragraph(f"<b>Suggested next assessment:</b> {_text(analysis['next_assessment_date'])}", body)]

    story += [Spacer(1, 8 * mm), Paragraph("Prepared by SMART MOCK INTERVIEW ASSISTANT", ParagraphStyle("Signoff", parent=small, alignment=TA_CENTER))]
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)
    return pdf_bytes
