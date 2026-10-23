"""Stage 14: the /demo interview as a report dict for the existing PDF generator (report_delivery/pdf_generator.py).

Nothing is graded here: the technical verdicts are the Stage 12 assessments (src/demo/assessment.py) exactly as the summary page shows them, and similarity is passed on a 0-1
scale labelled as not a grade. Reuses the legacy report layout (strengths, areas for improvement, recommendations) so the PDF looks like the one the legacy app produces."""
from __future__ import annotations

from typing import Any, Dict, List

from . import assessment as AS
from . import interview as I

NOTE = ("Correctness is judged by an automatic check of your answer against the question's key concepts (a local model, not human-validated). "
        "'Not assessed' means the check was off or unavailable - nothing was assumed. Similarity is a separate figure and is not a grade.")


def build(s: Dict[str, Any], summary: Dict[str, Any]) -> Dict[str, Any]:
    ov = AS.session_overview(s)
    items: List[Dict[str, Any]] = []
    sims: List[float] = []
    for row in ov["rows"]:
        r = row["assessment"]
        q = s["questions"][row["n"] - 1]
        if r["similarity"].get("available"):
            sims.append(r["similarity"]["value"])
        items.append({"n": row["n"], "topic": row["topic"], "question": q.get("question"), "verdict": r["verdict"], "label": r["label"],
                      "similarity": r["similarity"]["display"] if r["similarity"].get("available") else None,
                      "correct": list(r["correct_concepts"]), "missing": list(r["missing_concepts"]),
                      "misconceptions": [{k: m.get(k) for k in ("claim", "reference_says", "why")} for m in r["misconceptions"]],
                      "feedback": list(r["feedback"]) or (["No answer was recorded for this question (skipped or not reached)."] if r["reason"] in ("skipped", "not_reached") else [])})
    strengths = [{"topic": str(i["topic"] or "")} for i in items if i["verdict"] == "correct"]
    weak = [{"question": f"{i['topic']}: {i['label']}"} for i in items if i["verdict"] in ("partially_correct", "incorrect")]
    skipped = [{"question": i["topic"]} for i, (q, a) in ((i, (s["questions"][i["n"] - 1], s["answers"][i["n"] - 1])) for i in items) if a and a.get("skipped")]
    recs: List[str] = []
    for i in items:
        if i["verdict"] in ("partially_correct", "incorrect"):
            for line in i["feedback"][:2]:
                if line not in recs:
                    recs.append(line)
    return {
        "interview_role": (s.get("config") or {}).get("role") or "Interview",
        "questions_answered": summary.get("answered", 0), "questions_skipped": summary.get("skipped", 0) + summary.get("unanswered", 0),
        "average_score": 0, "scoring_model": "Sentence-BERT similarity (0-1)",
        "analysis": {"performance_label": "Interview completed", "strengths": {"demonstrated_topics": strengths},
                     "weaknesses": {"weak_questions": weak, "skipped_questions": skipped}, "recommendations": recs[:8], "technical_focus": [], "learning_plan": []},
        "correctness": {"note": NOTE, "counts": ov["counts"], "assessed": ov["assessed"], "items": items, "similarity_average": f"{sum(sims) / len(sims):.2f}" if sims else None},
    }


def is_available() -> bool:
    try:
        import reportlab  # noqa: F401
        return True
    except ImportError:
        return False
