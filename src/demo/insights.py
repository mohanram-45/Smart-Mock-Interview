"""Read-only summaries of saved interviews for the dashboard, history and summary pages. Pure functions over session dicts.

Rules (each is tested):
  * only numbers that were actually recorded are aggregated; nothing is estimated, smoothed or filled in
  * the only score aggregated is the legacy similarity score, and every consumer labels it as similarity, not as a grade
  * a digest never contains answer text, question text or reference answers (it feeds list pages and a JSON endpoint)
  * experimental findings are reported separately and only when the experimental evaluator actually produced a verdict
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from . import interview as I

ELAPSED_CAP_S = 1800          # time on one question counts at most 30 minutes (leaving the tab open is not practice time)
MIN_POINTS_FOR_TREND = 2
MIN_ANSWERS_FOR_DOMAIN = 1


def _mean(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 1) if xs else None


def capped_seconds(a: Optional[Dict[str, Any]]) -> Optional[int]:
    v = (a or {}).get("elapsed_s")
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
        return None
    return int(min(v, ELAPSED_CAP_S))


def digest(s: Dict[str, Any]) -> Dict[str, Any]:
    """Metadata and numbers of one saved interview. No question or answer text."""
    qs, ans = s.get("questions") or [], s.get("answers") or []
    scored: List[float] = []
    by_domain: Dict[str, List[float]] = {}
    by_level: Dict[str, List[float]] = {}
    secs: List[int] = []
    answered = skipped = 0
    n_tech = 0
    for q, a in zip(qs, ans):
        if not I.is_question(q):                                  # introduction and follow-up turns are conversation, not counted questions
            continue
        n_tech += 1
        if not a:
            continue
        if a.get("skipped"):
            skipped += 1
        else:
            answered += 1
            t = capped_seconds(a)
            if t is not None:
                secs.append(t)
        leg = a.get("legacy") or {}
        if leg.get("status") == "scored" and isinstance(leg.get("score"), (int, float)):
            scored.append(float(leg["score"]))
            by_domain.setdefault(q.get("domain", "?"), []).append(float(leg["score"]))
            by_level.setdefault(q.get("difficulty", "?"), []).append(float(leg["score"]))
    cfg = s.get("config") or {}
    return {"id": s.get("id"), "created_at": s.get("created_at"), "finished_at": s.get("finished_at"), "status": s.get("status"),
            "role": cfg.get("role"), "domains": list(cfg.get("domains") or []), "difficulty": cfg.get("difficulty"), "asked": n_tech,
            "answered": answered, "skipped": skipped, "unanswered": sum(1 for q, a in zip(qs, ans) if a is None and I.is_question(q)),
            "legacy_scored": len(scored), "legacy_average": _mean(scored), "legacy_scores": scored,
            "by_domain": {k: v for k, v in by_domain.items()}, "by_level": {k: _mean(v) for k, v in by_level.items()},
            "seconds": sum(secs) if secs else None, "timed_answers": len(secs),
            "modular_mode": cfg.get("modular_mode", "off"), "code_eval": bool(cfg.get("code_eval")), "legacy_model": cfg.get("legacy_model")}


def public_digest(d: Dict[str, Any]) -> Dict[str, Any]:
    """The digest as sent to the browser: per-answer score lists stay on the server."""
    return {k: v for k, v in d.items() if k not in ("legacy_scores", "by_domain")}


def overview(digests: Iterable[Dict[str, Any]], trend_limit: int = 12) -> Dict[str, Any]:
    ds = sorted(digests, key=lambda d: d.get("created_at") or "")
    finished = [d for d in ds if d["status"] == "finished"]
    all_scores = [x for d in ds for x in d["legacy_scores"]]
    pts = [{"id": d["id"], "when": d["finished_at"] or d["created_at"], "value": d["legacy_average"], "n": d["legacy_scored"], "label": d.get("role") or "Custom topics"}
           for d in finished if d["legacy_average"] is not None]
    pts = pts[-trend_limit:]
    dom: Dict[str, List[float]] = {}
    for d in ds:
        for k, v in d["by_domain"].items():
            dom.setdefault(k, []).extend(v)
    domains = sorted(({"domain": k, "average": _mean(v), "answers": len(v)} for k, v in dom.items() if len(v) >= MIN_ANSWERS_FOR_DOMAIN),
                     key=lambda x: (x["average"] if x["average"] is not None else 0))
    secs = [d["seconds"] for d in finished if d["seconds"] is not None]
    answered = sum(d["answered"] for d in ds)
    timed = sum(d["timed_answers"] for d in ds)
    return {"interviews": len(ds), "finished": len(finished), "in_progress": sum(1 for d in ds if d["status"] == "active"), "answers": answered,
            "legacy_average": _mean(all_scores), "legacy_scored": len(all_scores), "trend": pts, "trend_ready": len(pts) >= MIN_POINTS_FOR_TREND,
            "domains": domains, "minutes": round(sum(secs) / 60, 1) if secs else None, "seconds": sum(secs) if secs else None,
            "avg_seconds_per_answer": round(sum(d["seconds"] or 0 for d in ds) / timed) if timed else None}


# ------------------------------------------------------------------------------------------------ one interview
def concept_findings(view: Optional[Dict[str, Any]]) -> Optional[Dict[str, List[str]]]:
    """Concept-level findings of an EXPERIMENTAL evaluation, only if the evaluator produced verdicts. None otherwise (never an empty 'all good')."""
    if not view or not view.get("verdicts"):
        return None
    out: Dict[str, List[str]] = {"stated": [], "wrong": [], "not_found": [], "undecided": []}
    key = {"states_correctly": "stated", "states_incorrectly": "wrong", "not_stated": "not_found", "unverified": "undecided"}
    for v in view["verdicts"]:
        k = key.get(v.get("final_state"))
        if k and v.get("member") and v["member"] not in out[k]:
            out[k].append(str(v["member"]))
    return out


_EXAMPLE_RX = re.compile(r"\b(?:for example|for instance|e\.g\.|such as|say you|imagine|suppose|in practice)\b|`|\w+\(\)", re.I)
PRACTICE_MIN_WORDS = 30          # an answer shorter than this gets a "say a little more" prompt; it is a fact about length, not a judgement


def answer_facts(a: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Plain facts about one recorded answer: its length, whether it contains an example, and the curated key terms it wrote out as written. Nothing about correctness."""
    text = (a or {}).get("answer", "") or ""
    t = (a or {}).get("terms") or {}
    return {"words": I.word_count(text), "has_example": bool(_EXAMPLE_RX.search(text)), "terms_used": list(t.get("found") or [])}


def practice_prompts(session: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Next-practice prompts tied to the questions that were actually asked. They are driven by two recorded facts only (a short answer, or an answer without an example), never by a
    judgement of what was right or wrong and never by missing exact terms."""
    qs, ans = session.get("questions") or [], session.get("answers") or []
    out: List[Dict[str, Any]] = []
    for i, (q, a) in enumerate(zip(qs, ans)):
        if not a or a.get("skipped") or not I.is_question(q):
            continue
        f = answer_facts(a)
        if f["words"] < PRACTICE_MIN_WORDS:
            why = f"your answer was {f['words']} word{'s' if f['words'] != 1 else ''}"
        elif not f["has_example"]:
            why = "your answer did not include a concrete example"
        else:
            continue
        topic = q.get("topic") or q.get("domain") or "this topic"
        out.append({"n": i + 1, "text": topic, "detail": f"Try explaining it again in your own words with one concrete example ({why}).", "question": q.get("question")})
    return out[:limit]


def skipped_questions(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Technical questions with no recorded answer. Not weaknesses: nothing was said, so nothing can be read."""
    qs, ans = session.get("questions") or [], session.get("answers") or []
    return [{"n": i + 1, "text": q.get("topic") or q.get("domain"), "detail": "skipped" if a else "not reached"}
            for i, (q, a) in enumerate(zip(qs, ans)) if I.is_question(q) and (a is None or a.get("skipped"))]


def improvement_areas(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """What to practise next, derived only from what was recorded in this interview. Each entry names its source so experimental items stay separate.
    Final polish: exact-term gaps and 'lowest similarity' are NOT listed here (they read as verdicts); they stay available as optional technical details. Skipped questions are
    returned by `skipped_questions` and shown apart from practice prompts."""
    qs, ans = session.get("questions") or [], session.get("answers") or []
    out: List[Dict[str, Any]] = []
    prompts = practice_prompts(session)
    if prompts:
        out.append({"source": "practice", "title": "Prompts for your next practice session",
                    "note": "Based on what you wrote (its length and whether it had an example). They do not say that an answer was right or wrong.", "items": prompts})
    miss: List[Dict[str, Any]] = []
    for i, a in enumerate(ans):
        if not a or a.get("skipped"):
            continue
        cf = concept_findings((a.get("modular") or {}).get("view"))
        if cf and (cf["not_found"] or cf["wrong"]):
            miss.append({"n": i + 1, "text": qs[i]["topic"] or qs[i]["domain"],
                         "detail": "; ".join(([f"not found: {', '.join(cf['not_found'][:3])}"] if cf["not_found"] else []) + ([f"flagged as wrong: {', '.join(cf['wrong'][:3])}"] if cf["wrong"] else []))})
    if miss:
        out.append({"source": "experimental", "title": "Concepts the experimental evaluator did not find",
                    "note": "Experimental and not validated against human markers. Treat as prompts to check, not as verdicts.", "items": miss[:6]})
    code_gaps: List[Dict[str, Any]] = []
    for i, a in enumerate(ans):
        c = (a or {}).get("code") or {}
        rep = c.get("report") or {}
        if c.get("requested") and rep.get("status") == "assessed":
            missing = [r["label"] for r in rep.get("requirements", []) if r.get("bucket") == "missing"]
            if missing:
                code_gaps.append({"n": i + 1, "text": qs[i]["topic"] or qs[i]["domain"], "detail": "not found in the code: " + "; ".join(missing[:3])})
    if code_gaps:
        out.append({"source": "code", "title": "Required parts not found in your code", "note": "Read from the text of the code; the code was not necessarily run.", "items": code_gaps[:6]})
    return out


def term_diagnostics(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """OPTIONAL technical detail: the exact-words check against the curated key terms, per answered question. A term 'not written out' is split into 'the same idea seems to be discussed
    in other words' and 'no sign of it', both guesses by word matching, neither a verdict."""
    out: List[Dict[str, Any]] = []
    for i, (q, a) in enumerate(zip(session.get("questions") or [], session.get("answers") or [])):
        t = (a or {}).get("terms")
        if not t or a.get("skipped") or not I.is_question(q) or not (t.get("found") or t.get("missing")):
            continue
        text = a.get("answer", "")
        missing = list(t.get("missing") or [])
        other = [c for c in missing if I.concept_covered_loosely(c, text)]
        out.append({"n": i + 1, "topic": q.get("topic") or q.get("domain"), "written": list(t.get("found") or []), "other_words": other, "no_sign": [c for c in missing if c not in other]})
    return out


def term_gaps(session: Dict[str, Any], min_missing: int = 2) -> List[Dict[str, Any]]:
    """Answered technical questions where at least `min_missing` curated key terms (and at least half of them) were not found as written. Technical diagnostics only."""
    out: List[Dict[str, Any]] = []
    for i, (q, a) in enumerate(zip(session.get("questions") or [], session.get("answers") or [])):
        t = (a or {}).get("terms")
        if not t or a.get("skipped") or not I.is_question(q):
            continue
        total = len(t["found"]) + len(t["missing"])
        if total and len(t["missing"]) >= min_missing and len(t["missing"]) * 2 >= total:
            out.append({"n": i + 1, "text": q.get("topic") or q.get("domain"), "detail": "not used: " + ", ".join(t["missing"][:4])})
    return out


def observations(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Facts about what was said, one row per answered technical question, each tied to the answer it comes from. Nothing here judges correctness and no missing term is listed. [{n, topic, text}]"""
    out: List[Dict[str, Any]] = []
    qs, ans = session.get("questions") or [], session.get("answers") or []
    for i, (q, a) in enumerate(zip(qs, ans)):
        if not a or a.get("skipped") or not I.is_question(q):
            continue
        f = answer_facts(a)
        parts = [f"You wrote {f['words']} word{'s' if f['words'] != 1 else ''}" + (" and included an example." if f["has_example"] else ".")]
        if f["terms_used"]:
            parts.append("Key terms you wrote out: " + ", ".join(f["terms_used"][:6]) + ".")
        out.append({"n": i + 1, "topic": q.get("topic"), "kind": "answer", "text": " ".join(parts)})
    for i, (q, a) in enumerate(zip(qs, ans)):
        if I.stage_of(q) == I.FOLLOW_UP and a and not a.get("skipped"):
            out.append({"n": i + 1, "topic": q.get("topic"), "kind": "follow_up",
                        "text": f"You answered the follow-up on \"{q.get('concept') or 'that answer'}\" ({I.word_count(a.get('answer', ''))} words)."})
    return out


def per_question(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for i, (q, a) in enumerate(zip(session.get("questions") or [], session.get("answers") or [])):
        if not I.is_question(q):
            continue
        state = "not reached" if a is None else "skipped" if a.get("skipped") else "answered"
        leg = (a or {}).get("legacy") or {}
        rows.append({"index": i, "n": i + 1, "topic": q.get("topic"), "domain": q.get("domain"), "difficulty": q.get("difficulty"), "state": state,
                     "legacy": leg.get("score") if leg.get("status") == "scored" else None, "seconds": capped_seconds(a)})
    return rows


def clock(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def trend_geometry(points: List[Dict[str, Any]], width: int = 680, height: int = 270, pad_l: int = 40, pad_r: int = 16, pad_t: int = 16, pad_b: int = 30) -> Dict[str, Any]:
    """Coordinates for the dashboard line chart. The y axis always spans the full similarity range (stored 0-100, labelled 0-1), so the line cannot exaggerate small changes."""
    n = len(points)
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b
    pts = []
    for i, p in enumerate(points):
        x = pad_l + (iw * i / (n - 1) if n > 1 else iw / 2)
        y = pad_t + ih * (1 - max(0.0, min(100.0, float(p["value"]))) / 100)
        pts.append({**p, "x": round(x, 1), "y": round(y, 1), "number": i + 1})
    grid = [{"y": round(pad_t + ih * (1 - v / 100), 1), "label": f"{v / 100:.2f}"} for v in (0, 25, 50, 75, 100)]   # Stage 12: similarity is shown 0-1, never as a percentage
    floor = round(pad_t + ih, 1)
    d = " ".join(("M" if i == 0 else "L") + f"{p['x']},{p['y']}" for i, p in enumerate(pts))
    area = (d + f" L{pts[-1]['x']},{floor} L{pts[0]['x']},{floor} Z") if pts else ""
    return {"width": width, "height": height, "pad_l": pad_l, "pad_r": width - pad_r, "points": pts, "grid": grid, "path": " ".join(f"{p['x']},{p['y']}" for p in pts),
            "path_d": d, "area_d": area, "base": pad_t + ih + 20}
