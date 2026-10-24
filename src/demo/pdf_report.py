"""Stage 14: the /demo interview as a report dict for the existing PDF generator (report_delivery/pdf_generator.py).

Nothing is graded here: the technical verdicts are the Stage 12 assessments (src/demo/assessment.py) exactly as the summary page shows them, and similarity is passed on a 0-1
scale labelled as not a grade. Reuses the legacy report layout (strengths, areas for improvement, recommendations) so the PDF looks like the one the legacy app produces."""
from __future__ import annotations

from typing import Any, Dict, List

from . import assessment as AS
from . import insights as INS
from . import interview as I

NOTE = ("Correctness is judged by an automatic check of your answer against the question's key concepts (a local model, not human-validated). "
        "'Not assessed' means the check was off or unavailable - nothing was assumed. Similarity is a separate figure and is not a grade.")


OFF_NOTICE = ("Correctness was not assessed. The optional correctness check was off for this interview, so this report describes what you did and wrote, not whether your answers were right. "
              "Similarity, where shown, is closeness to a reference answer and is not a grade.")
SIMILARITY_NOTE = "Average similarity to the reference answers (0-1). It compares wording and meaning, is not a grade, and has not been validated against human markers."


def _overview(s: Dict[str, Any], summary: Dict[str, Any], ov: Dict[str, Any]) -> Dict[str, Any]:
    """The compact report used when the correctness check did not run: statistics, topics, factual observations, practice prompts and skipped questions. No verdicts, no per-answer cards."""
    dg = INS.digest(s)
    sims = [row["assessment"]["similarity"]["value"] for row in ov["rows"] if row["assessment"]["similarity"].get("available")]
    cov = I.coverage(s.get("questions") or [], s.get("answers") or [])
    return {"notice": OFF_NOTICE,
            "stats": [("Answered", str(summary.get("answered", 0))), ("Skipped or not reached", str(summary.get("skipped", 0) + summary.get("unanswered", 0))),
                      ("Topics covered", str(len(cov))), ("Time spent", INS.clock(dg.get("seconds")))],
            "followups": summary.get("followups", 0),
            "similarity": {"average": f"{sum(sims) / len(sims):.2f}", "n": len(sims), "note": SIMILARITY_NOTE} if sims else None,
            "topics": [{"topic": c["topic"], "domain": c["domain"],
                        "status": ", ".join(x for x in (f"{c['answered']} answered" if c["answered"] else "", f"{c['skipped']} skipped" if c["skipped"] else "",
                                                          f"{c['not_reached']} not reached" if c["not_reached"] else "") if x)} for c in cov],
            "observations": [{"n": o["n"], "topic": o["topic"], "text": o["text"]} for o in INS.observations(s) if o["kind"] == "answer"],
            "practice": [{"n": p["n"], "topic": p["text"], "text": p["detail"]} for p in INS.practice_prompts(s)],
            "skipped": [{"n": x["n"], "topic": x["text"], "state": x["detail"]} for x in INS.skipped_questions(s)]}


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
    if not ov["assessed"]:                                                       # correctness check off / unavailable for every answer: one notice, no empty "Not assessed" cards, no 0/0
        return {"interview_role": (s.get("config") or {}).get("role") or "Interview", "questions_answered": summary.get("answered", 0),
                "questions_skipped": summary.get("skipped", 0) + summary.get("unanswered", 0), "average_score": 0, "scoring_model": "Sentence-BERT similarity (0-1)",
                "analysis": {"performance_label": "Interview summary"}, "overview": _overview(s, summary, ov)}
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
