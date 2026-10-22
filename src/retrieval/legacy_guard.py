"""Read-only guard for the future Flask integration (Stage 2B design; nothing here changes app behaviour).

The running app still serves data/processed/questions_cleaned.json (4,085 legacy rows, 3,618 of them template
boilerplate). data/audit/triage.csv classifies every legacy row (status == EXCLUDE_TEMPLATE for the boilerplate).
This module (a) computes the legacy exclusion set and (b) proves the approved retrieval corpus is disjoint from it.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parents[2]
TRIAGE = ROOT / "data" / "audit" / "triage.csv"
LEGACY_JSON = ROOT / "data" / "processed" / "questions_cleaned.json"
EXPECTED_BOILERPLATE = 3618
EXPECTED_LEGACY = 4085


def _norm(t: str) -> str:
    return " ".join((t or "").lower().split())


def boilerplate_ids(triage_path: Path = TRIAGE) -> Set[str]:
    """Legacy ids (as strings, matching questions_cleaned.json) whose triage status is EXCLUDE_TEMPLATE."""
    with open(triage_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ids = {str(r["id"]) for r in rows if r["status"] == "EXCLUDE_TEMPLATE"}
    return ids


def check_disjoint(records: Iterable[Dict[str, Any]], legacy_path: Path = LEGACY_JSON, triage_path: Path = TRIAGE) -> Dict[str, Any]:
    """Return a report; raises AssertionError-free (caller decides). Keys: ok, problems, counts."""
    legacy = json.loads(Path(legacy_path).read_text(encoding="utf-8"))
    bp = boilerplate_ids(triage_path)
    legacy_by_id = {str(q["id"]): q for q in legacy}
    problems: List[str] = []
    if len(legacy) != EXPECTED_LEGACY:
        problems.append(f"legacy rows {len(legacy)} != {EXPECTED_LEGACY}")
    if len(bp) != EXPECTED_BOILERPLATE:
        problems.append(f"boilerplate ids {len(bp)} != {EXPECTED_BOILERPLATE}")
    missing = bp - set(legacy_by_id)
    if missing:
        problems.append(f"{len(missing)} boilerplate ids not present in legacy file")
    bp_questions = {_norm(legacy_by_id[i]["question"]) for i in bp if i in legacy_by_id}
    bp_answers = {_norm(legacy_by_id[i].get("reference_answer", "")) for i in bp if i in legacy_by_id}
    recs = list(records)
    id_clash = [r["question_id"] for r in recs if r["question_id"] in legacy_by_id]
    q_clash = [r["question_id"] for r in recs if _norm(r["question"]) in bp_questions]
    a_clash = [r["question_id"] for r in recs if _norm(r["canonical_answer"]) in bp_answers]
    if id_clash:
        problems.append(f"{len(id_clash)} retrieval ids collide with legacy ids")
    if q_clash:
        problems.append(f"{len(q_clash)} retrieval questions equal a boilerplate question")
    if a_clash:
        problems.append(f"{len(a_clash)} retrieval answers equal a boilerplate answer")
    return {"ok": not problems, "problems": problems,
            "counts": {"legacy": len(legacy), "boilerplate": len(bp), "retrieval_records": len(recs),
                       "id_clashes": len(id_clash), "question_clashes": len(q_clash), "answer_clashes": len(a_clash)}}
