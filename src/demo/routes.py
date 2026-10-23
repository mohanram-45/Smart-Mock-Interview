"""Flask blueprint for the demonstration (mounted at /demo). Pages are server-rendered (Jinja2, autoescaped); a little vanilla JS enhances them.
JSON endpoints live under /demo/api. The legacy /api/* routes are not touched."""
from __future__ import annotations

import ipaddress
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Blueprint, abort, jsonify, make_response, redirect, render_template, request, url_for

from . import assessment as AS, behavioural as B, codeassess as CA, experimental as MA, grounded as G, insights as INS, interview as I, present as P
from .engine import DemoEngine, DemoError

logger = logging.getLogger(__name__)
demo_blueprint = Blueprint("demo", __name__, url_prefix="/demo", template_folder="templates", static_folder="static", static_url_path="/static")
_engine: Optional[DemoEngine] = None
_engine_lock = threading.Lock()
_recorded_cache: Dict[str, Any] = {}


def get_engine() -> DemoEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = DemoEngine()
        return _engine


def set_engine(e: Optional[DemoEngine]) -> None:
    """Test hook."""
    global _engine
    with _engine_lock:
        _engine = e
    _recorded_cache.clear()


@demo_blueprint.after_request
def _headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Cache-Control", "no-store")
    if resp.mimetype == "text/html":
        resp.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    return resp


@demo_blueprint.app_template_global("describe_state")
def _describe_state(view):
    return MA.describe_state(view)


@demo_blueprint.app_template_global("highlight")
def _highlight(view, answer=None):
    return MA.highlight_html(view, answer)


@demo_blueprint.app_template_global("answer_blocks")
def _answer_blocks(text):
    return P.answer_blocks(text)


@demo_blueprint.app_template_global("answer_kind")
def _answer_kind(text):
    return P.answer_kind(text)


@demo_blueprint.app_template_global("expects_code")
def _expects_code(question):
    return P.expects_code(question)


@demo_blueprint.app_template_global("finding_label")
def _finding_label(cls):
    return MA.finding_label(cls)


@demo_blueprint.app_template_global("clock")
def _clock(seconds):
    return INS.clock(seconds)


@demo_blueprint.app_template_global("trend_geometry")
def _trend_geometry(points):
    return INS.trend_geometry(points)


@demo_blueprint.app_template_global("concept_findings")
def _concept_findings(view):
    return INS.concept_findings(view)


@demo_blueprint.app_template_global("short_date")
def _short_date(iso):
    try:
        from datetime import datetime
        return datetime.fromisoformat(iso).astimezone().strftime("%d %b %H:%M")
    except (TypeError, ValueError):
        return "—"


@demo_blueprint.app_template_global("stage_label")
def _stage_label(q):
    return I.STAGE_LABELS.get(I.stage_of(q), "Question")


@demo_blueprint.app_template_global("origin_label")
def _origin_label(q):
    if q.get("origin") in ("memory_followup", "behavioural_probe", "behavioural_memory", "behavioural_bank", "adaptive_bank"):
        return I.ORIGIN_LABELS.get("behavioural_bank" if q["origin"] == "behavioural_memory" else q["origin"])
    if I.stage_of(q) == I.FOLLOW_UP:
        k = q.get("followup_kind")
        return I.ORIGIN_LABELS.get("llm" if k == "llm" else "mock" if k == "mock" else "follow_up") if k in ("llm", "mock", "curated_key_concept") else "Standard follow-up prompt (fixed wording)"
    return I.ORIGIN_LABELS.get(q.get("origin") or "bank", I.ORIGIN_LABELS["bank"])


@demo_blueprint.app_template_global("grounded")
def _grounded(a):
    """Evidence-backed written feedback built from the experimental view that was genuinely returned (None otherwise). Never raises."""
    try:
        v = ((a or {}).get("modular") or {}).get("view")
        return G.build(v, answer=(a or {}).get("answer") or "") if v else None
    except Exception:
        return None


@demo_blueprint.app_template_global("assess")
def _assess(a, q=None):
    """Stage 12: the correctness assessment of one answer (never derived from similarity). Never raises."""
    return AS.assess(a, q)


@demo_blueprint.app_template_filter("sim")
def _sim_filter(v):
    """A stored similarity (0-100, kept that way for older sessions) shown as a 0-1 resemblance value. Stage 12: never as a percentage."""
    try:
        return f"{max(0.0, min(100.0, float(v))) / 100.0:.2f}"
    except (TypeError, ValueError):
        return "\u2014"


@demo_blueprint.app_template_global("similarity_view")
def _similarity_view(legacy):
    return AS.similarity_view(legacy)


@demo_blueprint.app_template_global("interview_progress")
def _interview_progress(s):
    return I.progress(s["questions"], s["answers"], s["status"] == "finished")


@demo_blueprint.app_template_global("is_question")
def _is_question(q):
    return I.is_question(q)


@demo_blueprint.app_template_global("wrapup_message")
def _wrapup_message(s):
    return I.wrapup_text(0, 0, ended_early=(s.get("plan") or {}).get("ended_reason") not in (None, "plan_complete"))


def history_allowed() -> bool:
    """The history pages list every saved interview on this machine, so they are served only to this computer by default (the usual `127.0.0.1` launch).
    SMART_DEMO_HISTORY=1 allows other clients (for example a container whose port is published to localhost only); =0 turns the pages off."""
    env = os.environ.get("SMART_DEMO_HISTORY", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    try:
        return ipaddress.ip_address(request.remote_addr or "").is_loopback
    except ValueError:
        return False


def _history_context():
    if not history_allowed():
        return {"history_ok": False, "digests": [], "overview": None, "retention": get_engine().store.retention_days}
    eng = get_engine()
    ds = eng.digests()
    return {"history_ok": True, "digests": ds, "overview": INS.overview(ds), "retention": eng.store.retention_days}


def _json_error(e: DemoError):
    return jsonify({"error": str(e), **e.extra}), e.status


def _page_error(message: str, status: int):
    return render_template("error.html", message=message, status=status), status


# ------------------------------------------------------------------------------------------------ pages
@demo_blueprint.route("/", methods=["GET"])
def dashboard_page():
    ctx = _history_context()
    recent = ctx["digests"][:5]
    active = next((d for d in ctx["digests"] if d["status"] == "active"), None)
    bank, roles = None, {}
    try:
        cat = get_engine().catalog()                      # the same role -> topics map the setup page uses; quick-start cards start from it
        bank, roles = cat.get("total_questions"), cat.get("roles") or {}
    except DemoError:
        pass
    return render_template("dashboard.html", recent=recent, active=active, bank=bank, roles=roles, **ctx)


@demo_blueprint.route("/history", methods=["GET"])
def history_page():
    return render_template("history.html", **_history_context())


@demo_blueprint.route("/settings", methods=["GET"])
def settings_page():
    eng = get_engine()
    try:
        st = eng.status()
    except DemoError as e:
        st = {"questions": 0, "corpus_error": str(e), "modular_modes": MA.available_modes(), "followup_modes": ["deterministic"], "legacy_models": [], "recorded_results": False}
    return render_template("settings.html", st=st, code=CA.describe(), history_ok=history_allowed(), data_dir=str(eng.store.dir), retention=eng.store.retention_days,
                           expose_reference=eng.expose_reference())


@demo_blueprint.route("/new", methods=["GET"])
def setup_page():
    eng = get_engine()
    try:
        cat = eng.catalog()
        err = None
    except DemoError as e:
        cat, err = None, str(e)
    return render_template("setup.html", catalog=cat, error=err, recorded=bool(MA.find_recorded_results()))


@demo_blueprint.route("/guide", methods=["GET"])
def guide_page():
    return render_template("guide.html")


@demo_blueprint.route("/about", methods=["GET"])
def about_page():
    return render_template("about.html")


def _interview_context(eng: DemoEngine, s: Dict[str, Any]) -> Dict[str, Any]:
    cur = s["current"]
    q = s["questions"][cur]
    spent = sum(INS.capped_seconds(a) or 0 for a in s["answers"] if a and not a.get("skipped"))
    return {"s": s, "q": q, "n": cur + 1, "total": len(s["questions"]), "elapsed": eng.question_elapsed(s) or 0, "spent": spent,
            "turns": [{"n": i + 1, "q": s["questions"][i], "a": s["answers"][i]} for i in range(cur)],
            "tracker": I.tracker(s["questions"], s["answers"], cur, False), "codeq": P.expects_code(q)}


@demo_blueprint.route("/s/<sid>", methods=["GET"])
def interview_page(sid):
    eng = get_engine()
    try:
        s = eng.get(sid)
    except DemoError as e:
        return _page_error(str(e), e.status)
    if s["status"] == "finished":
        return redirect(url_for("demo.summary_page", sid=sid))
    return render_template("interview.html", **_interview_context(eng, s))


@demo_blueprint.route("/s/<sid>/summary", methods=["GET"])
def summary_page(sid):
    eng = get_engine()
    try:
        s = eng.get(sid)
    except DemoError as e:
        return _page_error(str(e), e.status)
    if s["status"] != "finished":
        return render_template("summary.html", s=s, summary=eng.summary(s), items=[], in_progress=True, expose_reference=False)
    items = []
    for i, (q, a) in enumerate(zip(s["questions"], s["answers"])):
        rec = eng.record(q["question_id"]) if (eng.expose_reference() and q.get("question_id") and I.is_scored(q)) else None
        items.append({"i": i, "n": i + 1, "q": q, "a": a, "reference": rec["canonical_answer"] if rec else None})
    digest = INS.digest(s)
    assessments = AS.session_overview(s)
    return render_template("summary.html", s=s, summary=eng.summary(s), items=items, in_progress=False, expose_reference=eng.expose_reference(),
                           digest=digest, rows=INS.per_question(s), areas=INS.improvement_areas(s), coverage=I.coverage(s["questions"], s["answers"]),
                           observations=INS.observations(s), tech=[it for it in items if I.is_question(it["q"])],
                           beh=(B.feedback(s) if (s.get("plan") or {}).get("type") in ("behavioural", "mixed") else None), assessments=assessments)


@demo_blueprint.route("/s/<sid>/export.json", methods=["GET"])
def export_json(sid):
    """The candidate's own results as a download: questions, their answers, the scores/feedback that were shown, and the labels. No reference answers, no internals."""
    eng = get_engine()
    try:
        s = eng.get(sid)
    except DemoError as e:
        return _json_error(e)
    out = {"session_id": s["id"], "status": s["status"], "created_at": s["created_at"], "finished_at": s.get("finished_at"), "config": s["config"],
           "note": "Demonstration data. Similarity (Sentence-BERT) measures resemblance to a reference answer, not correctness; experimental results are opt-in. Nothing here is human-validated.",
           "plan": s.get("plan") and {k: v for k, v in s["plan"].items() if k != "jd"},
           "summary": eng.summary(s), "answers": []}
    if (s.get("plan") or {}).get("type") in ("behavioural", "mixed"):
        out["behavioural_feedback"] = B.feedback(s)
    out["interview_memory"] = {"note": "Things you said in this interview, kept only to make the interviewer's later questions relevant. They are your own claims, not verified facts.",
                               "items": [{k: it[k] for k in ("id", "kind", "text", "quote", "turn", "confidence", "status")} for it in (s.get("memory") or {}).get("items", [])]}
    for q, a in zip(s["questions"], s["answers"]):
        item = {"n": (a or {}).get("n"), "stage": I.stage_of(q), "origin": q.get("origin", "bank"), "question_id": q.get("question_id"), "question": q["question"],
                "difficulty": q.get("difficulty"), "domain": q.get("domain"), "provenance": q.get("provenance")}
        if a:
            m = a["modular"]
            v = m.get("view") or {}
            item.update(answer=a["answer"], skipped=a["skipped"], terms=a.get("terms"), legacy={k: a["legacy"].get(k) for k in ("status", "score", "label", "feedback", "reason")},
                        experimental={"mode": m["mode"], "status": m["status"], "evaluation_status": v.get("status"), "score": v.get("score"),
                                      "source": (v.get("source") or {}).get("kind"), "human_validated": False})
            c = a.get("code") or {}
            rep = c.get("report") or {}
            if c.get("requested"):
                item["code_check"] = {"status": c.get("status"), "assessment_status": rep.get("status"), "executed": rep.get("executed"), "buckets": rep.get("buckets"), "summary": rep.get("summary"),
                                      "labels": rep.get("labels"), "human_validated": False, "score": None}
        item["assessment"] = AS.assess(a, q) if I.is_question(q) else None       # Stage 12: correctness verdict, separate from similarity (similarity stays in legacy.score, 0-100 as stored)
        out["answers"].append(item)
    resp = make_response(jsonify(out), 200)
    resp.headers["Content-Disposition"] = f'attachment; filename="{s["id"]}.json"'
    return resp


@demo_blueprint.route("/s/<sid>/report.pdf", methods=["GET"])
def report_pdf(sid):
    """Stage 14: the finished interview as a PDF (the existing report generator), including the Stage 12 correctness feedback. Similarity appears only as a labelled 0-1 figure."""
    from . import pdf_report
    eng = get_engine()
    try:
        s = eng.get(sid)
    except DemoError as e:
        return _json_error(e)
    if s["status"] != "finished":
        return jsonify({"error": "Finish the interview first; the report is built from the finished interview."}), 409
    if not pdf_report.is_available():
        return jsonify({"error": "PDF reports need the reportlab package, which is not installed."}), 503
    from report_delivery.pdf_generator import build_pdf
    pdf = build_pdf(pdf_report.build(s, eng.summary(s)))
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", str((s.get("config") or {}).get("role") or "Interview"))
    resp = make_response(pdf, 200)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="SMART_{name}_Interview_Report.pdf"'
    resp.headers["Cache-Control"] = "no-store"
    return resp


@demo_blueprint.route("/recorded", methods=["GET"])
def recorded_page():
    path = MA.find_recorded_results()
    if path is None:
        return render_template("recorded.html", data=None, error="No complete recorded run was found (data/evaluation/stage3c2_results/*/results.json)."), 200
    try:
        data = _recorded(path)
    except Exception as e:
        return render_template("recorded.html", data=None, error=f"The recorded run could not be read: {type(e).__name__}: {str(e)[:200]}"), 200
    return render_template("recorded.html", data=data, error=None)


@demo_blueprint.route("/recorded/<sample_id>", methods=["GET"])
def recorded_detail(sample_id):
    path = MA.find_recorded_results()
    if path is None:
        return _page_error("No recorded run is available.", 404)
    try:
        data = _recorded(path)
    except Exception as e:
        return _page_error(f"The recorded run could not be read: {type(e).__name__}", 500)
    v = next((x for x in data["views"] if x["sample_id"] == sample_id), None)
    if v is None:
        return _page_error("That recorded answer does not exist.", 404)
    return render_template("recorded_detail.html", v=v, data=data)


def _recorded(path: Path) -> Dict[str, Any]:
    key = f"{path}:{path.stat().st_mtime_ns}"
    if key not in _recorded_cache:
        _recorded_cache.clear()
        _recorded_cache[key] = MA.recorded_views(path)
    return _recorded_cache[key]


# ------------------------------------------------------------------------------------------------ JSON API
@demo_blueprint.route("/api/status", methods=["GET"])
def api_status():
    try:
        return jsonify(get_engine().status()), 200
    except DemoError as e:
        return _json_error(e)


@demo_blueprint.route("/api/history", methods=["GET"])
def api_history():
    """Numbers-only digests of saved interviews plus aggregates. Never contains question or answer text."""
    if not history_allowed():
        return jsonify({"error": "History is only served to this computer (set SMART_DEMO_HISTORY=1 to change that)."}), 403
    ds = get_engine().digests()
    return jsonify({"overview": INS.overview(ds), "interviews": [INS.public_digest(d) for d in ds]}), 200


@demo_blueprint.route("/api/sessions/delete-all", methods=["POST"])
def api_delete_all():
    """Erase every saved interview (memory and disk). Same access rule as the history pages."""
    if not history_allowed():
        return jsonify({"error": "Not allowed from this client."}), 403
    return jsonify({"deleted": get_engine().store.delete_all()}), 200


@demo_blueprint.route("/api/catalog", methods=["GET"])
def api_catalog():
    try:
        return jsonify(get_engine().catalog()), 200
    except DemoError as e:
        return _json_error(e)


@demo_blueprint.route("/api/scorable", methods=["GET"])
def api_scorable():
    try:
        return jsonify(get_engine().scorable_info()), 200
    except DemoError as e:
        return _json_error(e)


@demo_blueprint.route("/api/sessions", methods=["POST"])
def api_create():
    try:
        s = get_engine().create(request.get_json(silent=True))
        return jsonify({"session_id": s["id"], "url": url_for("demo.interview_page", sid=s["id"]), "questions": len(s["questions"]), "notes": s["notes"],
                        "legacy": s["legacy"]}), 201
    except DemoError as e:
        return _json_error(e)


def _public_session(eng: DemoEngine, s: Dict[str, Any]) -> Dict[str, Any]:
    cur = s["questions"][s["current"]] if s["status"] == "active" else None
    return {"session_id": s["id"], "status": s["status"], "current": s["current"] + 1 if cur else None, "total": len(s["questions"]),
            "stage": I.stage_of(cur) if cur else None,
            "question": ({"question_id": cur.get("question_id"), "domain": cur.get("domain"), "difficulty": cur.get("difficulty"), "topic": cur.get("topic"), "question": cur["question"],
                          "stage": I.stage_of(cur), "origin": cur.get("origin", "bank")} if cur else None), "summary": eng.summary(s), "config": s["config"]}


@demo_blueprint.route("/api/sessions/<sid>", methods=["GET"])
def api_get(sid):
    eng = get_engine()
    try:
        return jsonify(_public_session(eng, eng.get(sid))), 200
    except DemoError as e:
        return _json_error(e)


def _is_pending(a: Dict[str, Any]) -> bool:
    return a["modular"]["status"] == "pending" or (a.get("code") or {}).get("status") == "pending"


def _eval_fragment(s: Dict[str, Any], n: int, compact: bool = False) -> str:
    q, a = s["questions"][n - 1], s["answers"][n - 1]
    return render_template("_answer_eval.html", q=q, a=a, s=s, compact=compact)


def _next_payload(eng: DemoEngine, s: Dict[str, Any]) -> Dict[str, Any]:
    """What the page needs after an answer or a skip: the interviewer's next message (or the wrap-up), the stage tracker and the editor mode for the next prompt."""
    finished = s["status"] == "finished"
    tr = I.tracker(s["questions"], s["answers"], s["current"], finished)
    prog = I.progress(s["questions"], s["answers"], finished)
    if finished:
        html = render_template("_wrapup.html", s=s)
        return {"finished": True, "next": None, "next_html": html, "tracker_html": render_template("_tracker.html", tracker=tr), "progress": prog}
    cur = s["current"]
    q = s["questions"][cur]
    html = render_template("_prompt.html", q=q, n=cur + 1, s=s, current=True)
    return {"finished": False, "next": {"n": cur + 1, "total": len(s["questions"]), "stage": I.stage_of(q), "stage_label": I.STAGE_LABELS.get(I.stage_of(q)), "code": P.expects_code(q)},
            "next_html": html, "tracker_html": render_template("_tracker.html", tracker=tr), "progress": prog}


@demo_blueprint.route("/api/sessions/<sid>/answer", methods=["POST"])
def api_answer(sid):
    eng = get_engine()
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required"}), 400
    try:
        a = eng.submit(sid, body.get("n"), body.get("answer"))
        s = eng.get(sid)
        return jsonify({"n": a["n"], "next_url": url_for("demo.interview_page" if s["status"] == "active" else "demo.summary_page", sid=sid),
                        "html": _eval_fragment(s, a["n"]), "modular_status": a["modular"]["status"], "pending": _is_pending(a),
                        "assessment": AS.assess(s["answers"][a["n"] - 1], s["questions"][a["n"] - 1]), **_next_payload(eng, s)}), 200
    except DemoError as e:
        return _json_error(e)


@demo_blueprint.route("/api/sessions/<sid>/skip", methods=["POST"])
def api_skip(sid):
    eng = get_engine()
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required"}), 400
    try:
        a = eng.skip(sid, body.get("n"))
        s = eng.get(sid)
        return jsonify({"n": a["n"], "next_url": url_for("demo.interview_page" if s["status"] == "active" else "demo.summary_page", sid=sid), **_next_payload(eng, s)}), 200
    except DemoError as e:
        return _json_error(e)


@demo_blueprint.route("/api/sessions/<sid>/finish", methods=["POST"])
def api_finish(sid):
    eng = get_engine()
    try:
        eng.finish(sid)
        return jsonify({"finished": True, "next_url": url_for("demo.summary_page", sid=sid)}), 200
    except DemoError as e:
        return _json_error(e)


@demo_blueprint.route("/api/sessions/<sid>/delete", methods=["POST"])
def api_delete(sid):
    """Erase this interview (your answers and scores) from the server's memory and disk."""
    get_engine().delete(sid)
    return jsonify({"deleted": True, "next_url": url_for("demo.setup_page")}), 200


@demo_blueprint.route("/api/sessions/<sid>/answers/<int:n>", methods=["GET"])
def api_answer_fragment(sid, n):
    eng = get_engine()
    try:
        s = eng.get(sid)
        if not 1 <= n <= len(s["questions"]) or s["answers"][n - 1] is None:
            raise DemoError("No such answer.", 404)
        a = s["answers"][n - 1]
        return jsonify({"n": n, "modular_status": a["modular"]["status"], "pending": _is_pending(a), "html": _eval_fragment(s, n, request.args.get("compact") == "1"),
                        "assessment": AS.assess(a, s["questions"][n - 1])}), 200
    except DemoError as e:
        return _json_error(e)


def init_demo(app) -> None:
    """Register the demonstration blueprint on the existing Flask app. Idempotent."""
    if "demo" not in app.blueprints:
        app.register_blueprint(demo_blueprint)
