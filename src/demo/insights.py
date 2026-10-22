"""Read-only summaries of saved interviews for the dashboard, history and summary pages. Pure functions over session dicts.

Rules (each is tested):
  * only numbers that were actually recorded are aggregated; nothing is estimated, smoothed or filled in
  * the only score aggregated is the legacy similarity score, and every consumer labels it as similarity, not as a grade
  * a digest never contains answer text, question text or reference answers (it feeds list pages and a JSON endpoint)
  * experimental findings are reported separately and only when the experimental evaluator actually produced a verdict
"""
from __future__ import annotations

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


def improvement_areas(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """What to look at again, derived only from what was recorded in this interview. Each entry names its source so experimental items stay separate."""
    qs, ans = session.get("questions") or [], session.get("answers") or []
    scored = [(a["legacy"]["score"], i) for i, (q, a) in enumerate(zip(qs, ans)) if a and not a.get("skipped") and (a.get("legacy") or {}).get("status") == "scored"]
    out: List[Dict[str, Any]] = []
    terms = term_gaps(session)
    if terms:
        out.append({"source": "terms", "title": "Key terms from the question bank that your answer did not use",
                    "note": "An exact-words check against the curated key concepts of each question. A missing term may still be covered in other words; it is a prompt to re-read, not a mistake.",
                    "items": terms[:6]})
    if len(scored) >= 2:
        low = sorted(scored)[:3]
        out.append({"source": "legacy", "title": "Lowest similarity to the reference answer",
                    "note": "Similarity is closeness of wording and meaning, not correctness. Re-read these against your own answer.",
                    "items": [{"n": i + 1, "text": qs[i]["topic"] or qs[i]["domain"], "detail": f"{s:.0f}%"} for s, i in low]})
    skipped = [i for i, a in enumerate(ans) if a and a.get("skipped") and I.is_question(qs[i])]
    unreached = [i for i, a in enumerate(ans) if a is None and I.is_question(qs[i])]
    if skipped or unreached:
        out.append({"source": "session", "title": "Skipped or not reached", "note": "No answer was recorded for these.",
                    "items": [{"n": i + 1, "text": qs[i]["topic"] or qs[i]["domain"], "detail": "skipped" if i in skipped else "not reached"} for i in skipped + unreached]})
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


def term_gaps(session: Dict[str, Any], min_missing: int = 2) -> List[Dict[str, Any]]:
    """Answered technical questions where at least `min_missing` curated key terms (and at least half of them) were not found as written."""
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
    """Facts about what was said, one row per answered technical question, each tied to the answer it comes from. Nothing here judges correctness. [{n, topic, text}]"""
    out: List[Dict[str, Any]] = []
    qs, ans = session.get("questions") or [], session.get("answers") or []
    for i, (q, a) in enumerate(zip(qs, ans)):
        if not a or a.get("skipped") or not I.is_question(q):
            continue
        words = I.word_count(a.get("answer", ""))
        t = a.get("terms") or {}
        parts = []
        if words < 12:
            parts.append(f"Your answer was brief ({words} words), which leaves little to review.")
        if t.get("found"):
            parts.append("Key terms you used: " + ", ".join(t["found"][:6]) + ".")
        if t.get("missing") and words >= 12:
            parts.append("Key terms not found as written: " + ", ".join(t["missing"][:5]) + ".")
        if parts:
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
    """Coordinates for the dashboard line chart. The y axis is always 0-100 (a similarity percentage), so the line cannot exaggerate small changes."""
    n = len(points)
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b
    pts = []
    for i, p in enumerate(points):
        x = pad_l + (iw * i / (n - 1) if n > 1 else iw / 2)
        y = pad_t + ih * (1 - max(0.0, min(100.0, float(p["value"]))) / 100)
        pts.append({**p, "x": round(x, 1), "y": round(y, 1), "number": i + 1})
    grid = [{"y": round(pad_t + ih * (1 - v / 100), 1), "label": str(v)} for v in (0, 25, 50, 75, 100)]
    floor = round(pad_t + ih, 1)
    d = " ".join(("M" if i == 0 else "L") + f"{p['x']},{p['y']}" for i, p in enumerate(pts))
    area = (d + f" L{pts[-1]['x']},{floor} L{pts[0]['x']},{floor} Z") if pts else ""
    return {"width": width, "height": height, "pad_l": pad_l, "pad_r": width - pad_r, "points": pts, "grid": grid, "path": " ".join(f"{p['x']},{p['y']}" for p in pts),
            "path_d": d, "area_d": area, "base": pad_t + ih + 20}
