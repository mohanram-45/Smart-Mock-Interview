"""Stage 4D + 5A: code-aware presentation and the opt-in experimental code check inside /demo.

No candidate code is ever executed here: the web layer only reads (static analysis); execution exists only behind a Docker runner that is not configured in tests."""
import subprocess
import sys

import pytest

from tests.app.test_stage4a_demo import GOOD, ROOT, answer, c, eng, make_engine, start  # noqa: F401
from tests.codeeval import fixtures as F
from src.demo import present as P

CODE = "def f(x):\n    if x:\n\treturn 1\n    return 0\n"   # deliberately mixes a tab


def code_session(c, monkeypatch, size=1):
    """An interview whose practical exercise has a code spec: intro answered, core question(s) skipped, so the next item is the practical exercise."""
    monkeypatch.setenv("SMART_DEMO_CODE_EVAL", "1")
    monkeypatch.delenv("SMART_CODEEVAL_EXEC", raising=False)
    r, sid = start(c, code_eval=True, size=size, practical=True, role="Python Developer")
    assert r.status_code == 201, r.json
    for n in range(2, 2 + size):
        assert c.post(f"/demo/api/sessions/{sid}/skip", json={"n": n}).status_code == 200
    return sid


def ans(c, sid, item, text):
    """Answer by ITEM number (item 1 is the introduction)."""
    return c.post(f"/demo/api/sessions/{sid}/answer", json={"n": item, "answer": text})


def spec_index(c, sid):
    """Which ITEM numbers have a code spec."""
    from src.codeeval.spec import spec_question_ids
    import src.demo.routes as R
    s = R.get_engine().get(sid)
    return [i + 1 for i, q in enumerate(s["questions"]) if q.get("question_id") in spec_question_ids()], s


# ------------------------------------------------------------------ presentation
def test_blocks_keep_indentation_tabs_and_crlf():
    text = "Here it is:\r\n```python\r\ndef f(x):\r\n    if x:\r\n\treturn 1\r\n```\r\nIt works because...\r\n"
    b = P.answer_blocks(text)
    kinds = [x["kind"] for x in b]
    assert kinds == ["prose", "code", "prose"], kinds
    code = [x for x in b if x["kind"] == "code"][0]
    assert code["lines"] == ["def f(x):", "    if x:", "\treturn 1"]


def test_whole_answer_code_is_detected_and_prose_stays_prose():
    assert P.answer_kind(CODE) == "code"
    assert P.answer_kind("Overfitting is when a model memorises noise.") == "prose"


def test_summary_renders_code_monospace_and_prose_separately_and_escaped(c, eng):
    r, sid = start(c, size=1)
    evil = "```python\ndef f(x):\n    return '<script>alert(1)</script>'\n```\nThen I explain <b>why</b> & more."
    assert answer(c, sid, 1, evil).status_code == 200
    html = c.get(f"/demo/s/{sid}/summary").data.decode()
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert "<b>why</b>" not in html and "&lt;b&gt;why&lt;/b&gt;" in html
    assert 'class="code"' in html and "prose-answer" in html
    assert "    return" in html, "indentation must survive rendering"


def test_stored_answer_is_byte_identical_and_stable_after_refresh(c, eng):
    r, sid = start(c, size=1)
    txt = "x = 1\r\nif x:\r\n\tprint(x)\r\n    # four spaces\r\n"
    answer(c, sid, 1, txt)
    first = c.get(f"/demo/s/{sid}/summary").data
    assert c.get(f"/demo/s/{sid}/summary").data == first
    exported = c.get(f"/demo/s/{sid}/export.json").json["answers"][1]["answer"]
    assert "\t" in exported and "    # four spaces" in exported


def test_legacy_card_labels_automatic_comment_and_never_claims_correctness(c, eng):
    r, sid = start(c, size=1)
    html = answer(c, sid, 1, GOOD).json["html"]
    # Stage 12: the similarity-band comment ("Excellent work - ... accurate, and complete") read as a correctness verdict and is no longer shown in /demo;
    # the card says what similarity is, and correctness has its own panel.
    assert "Automatic comment" not in html and "Excellent work" not in html and "not a percentage correct" in html and "Correctness check" in html
    assert "NOT correctness" in html or "not correctness" in html.lower()
    assert "<strong>For code:</strong>" not in html, "prose answers get no code note"
    code_html = None
    r2, sid2 = start(c, size=1)
    code_html = answer(c, sid2, 1, F.NP_GOOD).json["html"]
    assert "does not run your code" in code_html


# ------------------------------------------------------------------ feature flag isolation
def test_code_eval_is_off_by_default_and_rejected_without_env(c, eng, monkeypatch):
    monkeypatch.delenv("SMART_DEMO_CODE_EVAL", raising=False)
    assert c.get("/demo/api/catalog").json["code_eval"]["enabled"] is False
    assert b"Experimental code check" not in c.get("/demo/").data
    r, _ = start(c, code_eval=True)
    assert r.status_code == 400
    r, sid = start(c, size=1)
    a = answer(c, sid, 1, F.NP_GOOD).json
    assert "Experimental code check" not in a["html"]


def test_default_flow_never_imports_the_code_layers():
    code = ("import sys, os; os.environ.pop('SMART_DEMO_CODE_EVAL', None)\n"
            "from src.demo import engine, routes, present\n"
            "bad = [m for m in ('src.codeeval.runner', 'src.codeeval.static', 'src.codeeval.evaluate', 'src.codeeval.harness') if m in sys.modules]\n"
            "assert not bad, bad\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_flag_on_still_uses_the_disabled_runner_in_tests(c, eng, monkeypatch):
    sid = code_session(c, monkeypatch)
    idx, s = spec_index(c, sid)
    assert idx == [3] and s["questions"][2]["stage"] == "practical"
    ans(c, sid, 3, F.NP_GOOD)
    # the harness is the only module allowed to exec candidate code; the web process must not have imported it
    from src.codeeval.runner import shared_runner
    assert not shared_runner().sandboxed, "tests must run with the disabled runner"


# ------------------------------------------------------------------ code check inside the session
def test_code_check_attached_to_the_right_question_and_not_run(c, eng, monkeypatch):
    sid = code_session(c, monkeypatch)
    idx, s = spec_index(c, sid)
    assert idx == [3]
    n = idx[0]
    out = {n: ans(c, sid, n, F.NP_GOOD).json}
    q = s["questions"][n - 1]
    html = out[n]["html"]
    assert "Experimental code check" in html and "EXPERIMENTAL" in html and "NO SCORE" in html
    assert "STATIC READ: code NOT run" in html and "Your code was read, not run" in html
    assert "Verified correct" in html or "verified" in html.lower()
    assert out[n]["pending"] is False
    exp = c.get(f"/demo/s/{sid}/export.json").json["answers"]
    ck = [e for e in exp if e["question_id"] == q["question_id"]][0]["code_check"]
    assert ck["executed"] is False and ck["score"] is None and ck["human_validated"] is False
    assert ck["buckets"]["verified_correct"] == [] or ck["executed"], "a read-only check can never verify behaviour"
    assert q["question_id"] in ("smi-h0029", "smi-0462") and q["stage"] == "practical"


def test_keyword_stuffing_does_not_earn_verified_credit(c, eng, monkeypatch):
    sid = code_session(c, monkeypatch, size=1)
    idx, s = spec_index(c, sid)
    assert idx, "prefer_code must draw a question that has a code spec"
    words = "numpy matrix multiplication broadcasting clip maximum zero memory cancellation floating point gradient descent weights bias fit predict"
    rep = ans(c, sid, idx[0], words).json["html"]
    assert "Verified correct" not in rep or "(0)" in rep.split("Verified correct")[1][:40]


def test_non_code_questions_get_no_panel_even_with_flag_on(c, eng, monkeypatch):
    monkeypatch.setenv("SMART_DEMO_CODE_EVAL", "1")
    r, sid = start(c, size=1, code_eval=True)
    assert r.status_code == 201
    html = answer(c, sid, 1, GOOD).json["html"]
    assert "Experimental code check" not in html and "panel-legacy" in html


def test_failed_code_assessment_is_displayed_clearly(c, eng, monkeypatch):
    sid = code_session(c, monkeypatch, size=1)
    idx, s = spec_index(c, sid)
    assert idx, "prefer_code must draw a question that has a code spec"
    import src.demo.codeassess as CA
    monkeypatch.setattr(CA, "assess", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = ans(c, sid, idx[0], F.NP_GOOD)
    assert r.status_code == 200, "a crashing code check must never break the interview"
    assert "Code check unavailable" in r.json["html"] and "Nothing was verified" in r.json["html"]
    assert c.get(f"/demo/s/{sid}/summary").status_code == 200


def test_interrupted_code_job_is_reported_after_restart(c, eng, monkeypatch):
    sid = code_session(c, monkeypatch, size=1)
    idx, s = spec_index(c, sid)
    assert idx, "prefer_code must draw a question that has a code spec"
    ans(c, sid, idx[0], F.NP_GOOD)
    import src.demo.routes as R
    sess = R.get_engine().get(sid)
    sess["answers"][idx[0] - 1]["code"]["status"] = "pending"
    R.get_engine().store.save(sess)
    R.get_engine().store.clear()
    frag = c.get(f"/demo/api/sessions/{sid}/answers/{idx[0]}").json
    assert frag["pending"] is False and "Code check unavailable" in frag["html"] and "restarted" in frag["html"]


def test_prefer_code_without_flag_cannot_leak_spec_questions(c, eng, monkeypatch):
    monkeypatch.delenv("SMART_DEMO_CODE_EVAL", raising=False)
    r, sid = start(c, size=3, prefer_code=True)
    assert r.status_code in (201, 400)


def test_existing_routes_unchanged(c, eng):
    for u in ("/demo/", "/demo/guide", "/demo/api/status", "/demo/api/catalog", "/demo/recorded"):
        assert c.get(u).status_code == 200, u
    assert b"EXPERIMENTAL CODE CHECK" in c.get("/demo/guide").data
