"""Stage 5B/6A end-to-end tests of the /demo application on the real Flask app and the real curated corpus (stand-in scorer at the process boundary, no model called).

Each test is a whole user journey rather than a unit: new interview, five-question completion, code answers with the static check, results display, restart/resume,
failing scorer or code checker, feature isolation, deletion and hostile candidate text. No candidate code is ever executed here."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.demo.engine import DemoEngine
from src.demo.routes import set_engine
from src.demo.store import DemoStore
from tests.app.test_stage4a_demo import GOOD, Overlap, make_engine
from tests.codeeval import fixtures as F

ROOT = Path(__file__).resolve().parents[2]
NP_QID, LR_QID = "smi-h0029", "smi-0462"


@pytest.fixture()
def eng(tmp_path, monkeypatch):
    for k in ("SMART_DEMO_LIVE_MODULAR", "SMART_RETRIEVAL_EXPOSE_REFERENCE", "SMART_DEMO_ALLOW_SCORER_SETUP", "SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC"):
        monkeypatch.delenv(k, raising=False)
    e = make_engine(tmp_path)
    set_engine(e)
    yield e
    set_engine(None)


@pytest.fixture()
def c(app_module, eng):
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as cl:
        yield cl


def new(c, **over):
    """A bare technical interview (no practical, no follow-ups) with the introduction already answered."""
    body = {"role": "Data Scientist", "size": 5, "practical": False, "max_followups": 0}
    body.update(over)
    r = c.post("/demo/api/sessions", json=body)
    assert r.status_code == 201, r.json
    sid = r.json["session_id"]
    assert c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "Hello, I am a candidate."}).status_code == 200
    return sid


def ans(c, sid, n, text):
    """Answer technical question n (item n + 1: item 1 is the introduction)."""
    return c.post(f"/demo/api/sessions/{sid}/answer", json={"n": n + 1, "answer": text})


def restart(tmp_path, **kw):
    """A fresh engine over the same session folder = a server restart."""
    e = make_engine(tmp_path, **kw)
    set_engine(e)
    return e


# ------------------------------------------------------------------ new interview + five-question completion + results
def test_five_question_interview_start_to_finish_with_results_display(c, eng):
    assert c.get("/demo/").status_code == 200 and b"Dashboard" in c.get("/demo/").data
    assert b"Evaluation methods" in c.get("/demo/settings").data and b"Similarity score" in c.get("/demo/settings").data
    sid = new(c)
    asked = []
    for n in range(1, 6):
        page = c.get(f"/demo/s/{sid}").data.decode()
        assert "Technical question" in page and "Interview stages" in page            # stage + progress
        q = c.get(f"/demo/api/sessions/{sid}").json["question"]
        asked.append(q["question_id"])
        r = ans(c, sid, n, GOOD + f" (answer {n})")
        assert r.status_code == 200 and r.json["pending"] is False
        assert "Similarity score (Sentence-BERT)" in r.json["html"] and "Automatic comment" in r.json["html"] and "Experimental code check" not in r.json["html"]
    assert len(set(asked)) == 5, "no repeated questions"
    assert c.get(f"/demo/s/{sid}", follow_redirects=False).status_code == 302
    html = c.get(f"/demo/s/{sid}/summary").data.decode()
    assert html.count('class="card item"') == 6 and "Similarity" in html          # the introduction + five questions
    export = c.get(f"/demo/s/{sid}/export.json").json
    assert [a["question_id"] for a in export["answers"][1:]] == asked and all(a["legacy"]["status"] == "scored" for a in export["answers"][1:])
    assert export["answers"][0]["legacy"]["status"] == "not_scored", "the introduction is never scored"
    assert all("code_check" not in a for a in export["answers"]), "no code check unless it was requested"
    assert export["summary"]["answered"] == 5 and all(a["experimental"]["mode"] == "off" for a in export["answers"])


def test_about_and_guide_pages_describe_only_what_exists(c):
    about = c.get("/demo/about").data.decode()
    assert "does not run your code" in about or "never runs it by default" in about
    assert "failed its acceptance gate" in about
    assert "<svg" in about and 'role="img"' in about
    for banned in ("production-grade", "secure sandbox", "validated accuracy", "state-of-the-art"):
        assert banned not in about.lower()
    assert c.get("/demo/guide").status_code == 200


# ------------------------------------------------------------------ code answers + static check (never executed)
def code_session(c, monkeypatch):
    """Intro answered, the one core question skipped: the current item is the spec-backed practical exercise, which is technical question 2 (item 3)."""
    monkeypatch.setenv("SMART_DEMO_CODE_EVAL", "1")
    sid = new(c, role="Python Developer", size=1, practical=True, code_eval=True)
    assert c.post(f"/demo/api/sessions/{sid}/skip", json={"n": 2}).status_code == 200
    return sid, c.get(f"/demo/api/sessions/{sid}").json["question"]["question_id"]


def test_code_answer_static_check_results_display_export_and_refresh(c, eng, monkeypatch):
    sid, qid = code_session(c, monkeypatch)
    assert qid == NP_QID
    text = F.NP_GOOD + "\n# The broadcast version builds an (n, m, d) temporary, so it uses far more memory.\n"
    r = ans(c, sid, 2, text)
    assert r.status_code == 200
    h = r.json["html"]
    assert "code NOT run" in h and "Your code was read, not run" in h and "NO SCORE" in h and "EXPERIMENTAL" in h
    assert "SANDBOXED RUN" not in h
    s1 = c.get(f"/demo/s/{sid}/summary").data
    assert c.get(f"/demo/s/{sid}/summary").data == s1, "stable after refresh"
    ck = c.get(f"/demo/s/{sid}/export.json").json["answers"][2]
    assert ck["answer"] == text and ck["code_check"]["executed"] is False and ck["code_check"]["score"] is None
    assert ck["code_check"]["buckets"]["verified_correct"] == []                 # reading code can never verify behaviour
    assert "passed" not in json.dumps(ck["code_check"]["buckets"]) and ck["code_check"]["summary"]["functional"].lower().find("not run") >= 0


def test_a_static_check_never_executes_the_submitted_code(c, eng, monkeypatch, tmp_path):
    sid, _ = code_session(c, monkeypatch)
    marker = tmp_path / "pwned.txt"
    evil = (f"import os\nopen({str(marker)!r}, 'w').write('x')\nos.system('echo hi')\n" + F.NP_GOOD)
    r = ans(c, sid, 2, evil)
    assert r.status_code == 200 and not marker.exists(), "submitted code must never run in the Flask process"
    assert "Not run by policy" in r.json["html"] or "read, not run" in r.json["html"]
    ck = c.get(f"/demo/s/{sid}/export.json").json["answers"][2]["code_check"]
    assert ck["executed"] is False


def test_prose_only_and_unparsable_answers_to_a_code_question_fail_gracefully(c, eng, monkeypatch):
    for text, needle in (("I would use matrix multiplication and broadcasting, and clip at zero.", "No code found"), ("def f(:\n    pass\n", "could not be parsed")):
        sid, _ = code_session(c, monkeypatch)
        r = ans(c, sid, 2, text)
        assert r.status_code == 200 and needle in r.json["html"], needle
        assert c.get(f"/demo/s/{sid}/summary").status_code == 200


def test_unverified_and_advisory_findings_are_never_presented_as_confirmed(c, eng, monkeypatch):
    sid, _ = code_session(c, monkeypatch)
    h = ans(c, sid, 2, F.NP_KEYWORD_STUFFING_WRONG).json["html"]
    assert "Experimental code check" in h
    verified = h.split("Verified correct behaviour")[1].split("</section>")[0]
    assert "None." in verified and "passed" not in verified
    assert "not proof" in h or "NOT verified" in h or "not verified" in h.lower()
    legacy = h.split("panel-code")[0]
    assert "not a check that your answer is correct" in legacy and "accurate response" not in legacy


# ------------------------------------------------------------------ persistence, restart, resume, expiry, deletion
def test_restart_resume_and_expired_sessions(c, eng, tmp_path):
    sid = new(c, size=5)
    ans(c, sid, 1, GOOD); ans(c, sid, 2, GOOD)
    before = c.get(f"/demo/api/sessions/{sid}").json
    e2 = restart(tmp_path)
    after = c.get(f"/demo/api/sessions/{sid}").json
    assert after["current"] == 4 and after["question"] == before["question"] and after["summary"]["answered"] == 2
    page = c.get(f"/demo/s/{sid}").data.decode()
    assert "Technical question" in page
    for n in (3, 4, 5):
        assert ans(c, sid, n, GOOD).status_code == 200
    first = c.get(f"/demo/s/{sid}/export.json").json
    restart(tmp_path)
    assert c.get(f"/demo/s/{sid}/export.json").json["answers"] == first["answers"], "results identical after another restart"
    # expired / unknown / malformed ids: friendly pages, never a stack trace or a disk read
    for bad in ("demo_" + "0" * 20, "../../etc/passwd", "demo_zzz"):
        r = c.get(f"/demo/s/{bad}")
        assert r.status_code in (404, 400) and b"Traceback" not in r.data and b"could not be found" in r.data or r.status_code == 404
        assert c.get(f"/demo/api/sessions/{bad}").status_code == 404


def test_repeated_and_conflicting_submissions(c, eng):
    sid = new(c, size=3)
    a = ans(c, sid, 1, GOOD).json
    again = ans(c, sid, 1, GOOD)
    assert again.status_code == 200 and again.json["n"] == 2
    assert c.get(f"/demo/api/sessions/{sid}").json["summary"]["answered"] == 1
    assert ans(c, sid, 1, "a different answer").status_code == 409
    assert ans(c, sid, 3, GOOD).status_code in (409, 400)
    assert c.get(f"/demo/s/{sid}/export.json").json["answers"][1]["answer"] == GOOD


def test_deletion_removes_every_trace(c, eng, tmp_path, monkeypatch):
    sid, _ = code_session(c, monkeypatch)
    ans(c, sid, 2, F.NP_GOOD)
    f = tmp_path / "sessions" / f"{sid}.json"
    assert f.exists() and F.NP_GOOD.splitlines()[1].strip() in f.read_text(encoding="utf-8")
    assert c.post(f"/demo/api/sessions/{sid}/delete").json["deleted"] is True
    assert not f.exists() and not list((tmp_path / "sessions").glob("*"))
    assert c.get(f"/demo/api/sessions/{sid}").status_code == 404 and c.get(f"/demo/s/{sid}/summary").status_code == 404
    restart(tmp_path)
    assert c.get(f"/demo/s/{sid}/export.json").status_code == 404


# ------------------------------------------------------------------ failing scorer / failing code checker
def test_failing_legacy_scorer_does_not_stop_the_interview(tmp_path, app_module):
    class Boom:
        def score(self, *a): raise RuntimeError("model exploded")
    e = make_engine(tmp_path, scorer_factory=lambda k, c: Boom()); set_engine(e)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        sid = new(c, size=3)
        for n in (1, 2, 3):
            r = ans(c, sid, n, GOOD)
            assert r.status_code == 200 and "Similarity unavailable" in r.json["html"] and "interview continues without it" in r.json["html"]
        s = c.get(f"/demo/s/{sid}/summary").data.decode()
        assert s.count('class="card item"') == 4 and "unavailable" in s
        assert c.get(f"/demo/s/{sid}/export.json").json["summary"]["answered"] == 3
    set_engine(None)


def test_crashing_code_checker_at_every_layer_is_contained(c, eng, monkeypatch):
    import src.demo.codeassess as CA
    boom = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("checker exploded"))
    sid, _ = code_session(c, monkeypatch)
    monkeypatch.setattr(CA, "assess", boom)                                              # the assessment itself crashes
    r = ans(c, sid, 2, F.NP_GOOD)
    assert r.status_code == 200 and "Code check unavailable" in r.json["html"] and "Nothing was verified" in r.json["html"]
    assert "Similarity score (Sentence-BERT)" in r.json["html"], "the similarity result is still shown"
    assert c.get(f"/demo/s/{sid}/summary").status_code == 200 and c.get(f"/demo/s/{sid}/export.json").status_code == 200
    monkeypatch.undo(); monkeypatch.setenv("SMART_DEMO_CODE_EVAL", "1")
    sid, _ = code_session(c, monkeypatch)
    monkeypatch.setattr(CA, "sandboxed_runner", boom)                                    # the execution backend lookup crashes: falls back to read-only
    r = ans(c, sid, 2, F.NP_GOOD)
    assert r.status_code == 200 and "code NOT run" in r.json["html"] and "SANDBOXED RUN" not in r.json["html"]


# ------------------------------------------------------------------ feature isolation
def test_flags_are_genuinely_off_by_default(c, eng):
    cat = c.get("/demo/api/catalog").json
    assert cat["code_eval"]["enabled"] is False and "live" not in cat["modular_modes"]
    assert b"Experimental code check" not in c.get("/demo/").data
    assert c.post("/demo/api/sessions", json={"role": "Data Scientist", "code_eval": True}).status_code == 400
    assert c.post("/demo/api/sessions", json={"role": "Data Scientist", "modular_mode": "live"}).status_code == 400
    sid = new(c, size=3)
    assert c.get(f"/demo/api/sessions/{sid}").json["config"]["modular_mode"] == "off"
    assert c.get(f"/demo/api/sessions/{sid}").json["config"].get("code_eval") in (False, None)


_ATTEMPTS = f'''
import sys
sys.path.insert(0, r"{ROOT / 'tests' / 'helpers'}")
import import_recorder as R
R.install(r"{ROOT}")
ATTEMPTS = R.ATTEMPTS
'''


def test_default_full_journey_never_imports_experimental_or_code_layers(tmp_path):
    code = _ATTEMPTS + f'''
import os, tempfile
os.environ["SMART_DEMO_DATA_DIR"] = r"{tmp_path / 'iso'}"
for k in ("SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC", "SMART_DEMO_LIVE_MODULAR"): os.environ.pop(k, None)
import importlib.util
spec = importlib.util.spec_from_file_location("smart_app", "main/app.py"); m = importlib.util.module_from_spec(spec); sys.modules["smart_app"] = m; spec.loader.exec_module(m)
from src.demo.engine import DemoEngine
from src.demo.routes import set_engine
from src.demo.sim import bm25_search
from src.demo.store import DemoStore
class S:
    def score(self, r, a): return 0.5
# The candidate-question RANKING is its own layer (Stage 9B): it loads Sentence-BERT + FAISS where installed, lazily, at the first session. This test is about the experimental and code layers, so the
# ranking is BM25 here (the same ranker the offline simulator uses); the lazy loading of the ranking layer itself is pinned by the next test.
set_engine(DemoEngine(DemoStore(r"{tmp_path / 'iso'}"), scorer_factory=lambda k, c: S(), feedback_fn=lambda *a: "ok", search_fn=bm25_search))
c = m.app.test_client()
sid = c.post("/demo/api/sessions", json={{"role": "Python Developer", "size": 3, "practical": False, "max_followups": 0}}).json["session_id"]
for n in (1, 2, 3, 4):
    assert c.post(f"/demo/api/sessions/{{sid}}/answer", json={{"n": n, "answer": "def f():\\n    return 1"}}).status_code == 200
for u in (f"/demo/s/{{sid}}/summary", f"/demo/s/{{sid}}/export.json", "/demo/about", "/demo/guide", "/demo/"):
    assert c.get(u).status_code == 200, u
bad = [x for x in sys.modules if x.startswith(("src.codeeval.runner", "src.codeeval.static", "src.codeeval.evaluate", "src.codeeval.harness", "src.codeeval.spec", "src.evaluation.modular", "src.demo.modular_adapter")) or x in ("torch", "faiss", "sentence_transformers")]
assert not bad, bad
assert not ATTEMPTS, ATTEMPTS
print("ISOLATED")
'''
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and "ISOLATED" in r.stdout, r.stderr[-1500:]


def test_the_default_engine_loads_the_semantic_stack_lazily_and_only_through_retrieval(tmp_path):
    """The default engine (no search_fn) ranks candidate questions with the retrieval service. Importing the app, building the engine and opening the static pages must NOT touch Sentence-BERT /
    FAISS / torch; the first session may, and only through src.retrieval (lazy), never through the scorer, the follow-up or the experimental layers."""
    code = _ATTEMPTS + f'''
import os
os.environ["SMART_DEMO_DATA_DIR"] = r"{tmp_path / 'iso'}"
import importlib.util
spec = importlib.util.spec_from_file_location("smart_app", "main/app.py"); m = importlib.util.module_from_spec(spec); sys.modules["smart_app"] = m; spec.loader.exec_module(m)
from src.demo.engine import DemoEngine
from src.demo.routes import set_engine
from src.demo.store import DemoStore
class S:
    def score(self, r, a): return 0.5
set_engine(DemoEngine(DemoStore(r"{tmp_path / 'iso'}"), scorer_factory=lambda k, c: S(), feedback_fn=lambda *a: "ok"))
c = m.app.test_client()
for u in ("/demo/about", "/demo/guide", "/demo/"):
    assert c.get(u).status_code == 200, u
assert not ATTEMPTS, ("before the first session", ATTEMPTS)
c.post("/demo/api/sessions", json={{"role": "Python Developer", "size": 3, "practical": False, "max_followups": 0}})
allowed, outside = R.classify(ATTEMPTS)
assert not outside, [(n, f[-3:]) for n, f in outside]
assert all(any(rel.startswith("src/retrieval/") for rel, _ in f) for _, f in allowed)
print("LAZY")
'''
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and "LAZY" in r.stdout, r.stderr[-1500:]


# ------------------------------------------------------------------ hostile candidate text
HOSTILE = ["</pre><script>window.__x=1</script>", "{{ 7*7 }} {% for i in range(3) %}x{% endfor %} ${7*7} #{7*7}", "<img src=x onerror=alert(1)>", "\x00null\x01ctl", "‮RTL‬ override",
           "'; DROP TABLE sessions; --", "A" * 7999, "```python\nprint('</code></pre><script>1</script>')\n```", "\U0001F600 emoji éè 中文"]


@pytest.mark.parametrize("text", HOSTILE)
def test_hostile_candidate_text_is_inert_everywhere(c, eng, text):
    sid = new(c, size=3)
    r = ans(c, sid, 1, text)
    assert r.status_code == 200, r.data[:200]
    assert c.post(f"/demo/api/sessions/{sid}/finish").status_code == 200
    pages = [r.json["html"], c.get(f"/demo/s/{sid}/summary").data.decode(), c.get(f"/demo/s/{sid}").data.decode()]
    for h in pages:
        assert "<script>window.__x" not in h and "<img src=x" not in h and "<script>1</script>" not in h
        assert "DROP TABLE" not in h or "&#39;; DROP" in h or "'; DROP" in h
    summary_page = c.get(f"/demo/s/{sid}/summary").data.decode()
    if "{{ 7*7 }}" in text:
        assert "{{ 7*7 }}" in summary_page and "{% for i in range(3) %}x{% endfor %}" in summary_page, "template syntax must be shown literally, never evaluated"
    import re as _re
    expected = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)                  # control characters are removed on purpose
    export = c.get(f"/demo/s/{sid}/export.json")
    assert export.status_code == 200 and export.json["answers"][1]["answer"] == expected


def test_hostile_code_is_escaped_in_the_code_panel_and_blocks(c, eng, monkeypatch):
    sid, _ = code_session(c, monkeypatch)
    evil = F.NP_GOOD + "\ndef </code><script>window.__y=1</script>():\n    pass\n# \"><img src=x onerror=alert(1)>\n"
    r = ans(c, sid, 2, evil)
    assert r.status_code == 200
    for h in (r.json["html"], c.get(f"/demo/s/{sid}/summary").data.decode()):
        assert "<script>window.__y" not in h and "<img src=x" not in h


# ------------------------------------------------------------------ readiness never triggers a download
def test_tfidf_readiness_requires_the_grammar_checker_and_its_cache(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "src" / "model"))
    import importlib.util as iu
    import model_registry as MR
    real = iu.find_spec
    monkeypatch.setattr(iu, "find_spec", lambda name, *a, **k: real(name, *a, **k) if name != "language_tool_python" else None)
    r = MR.readiness("tfidf")
    assert r["ready"] is False and "language-tool-python" in r["reason"]
    monkeypatch.setattr(iu, "find_spec", lambda name, *a, **k: object() if name in ("language_tool_python", "sklearn") else real(name, *a, **k))
    monkeypatch.setenv("LTP_PATH", str(tmp_path / "empty"))
    r = MR.readiness("tfidf")
    assert r["ready"] is False and "download" in r["reason"] and "Java" in r["reason"]
    (tmp_path / "ltp").mkdir(); (tmp_path / "ltp" / "LanguageTool-6.x").mkdir()
    monkeypatch.setenv("LTP_PATH", str(tmp_path / "ltp"))
    assert MR.readiness("tfidf")["ready"] is True


def test_summary_uses_compact_score_explanations_but_the_full_text_is_one_click_away(c, eng):
    sid = new(c, size=3)
    for n in (1, 2, 3):
        ans(c, sid, n, GOOD)
    s = c.get(f"/demo/s/{sid}/summary").data.decode()
    assert s.count('<details class="explain">') == 3 and "What does this number mean?" in s and "resemblance, <strong>not correctness</strong>" in s
    frag = c.get(f"/demo/api/sessions/{sid}/answers/2?compact=1").json["html"]
    assert 'details class="explain"' in frag and 'details class="explain"' not in c.get(f"/demo/api/sessions/{sid}/answers/2").json["html"]


def test_prose_answer_box_wraps_and_code_box_does_not(c, eng, monkeypatch):
    sid = new(c, size=3)
    page = c.get(f"/demo/s/{sid}").data.decode()
    assert 'wrap="off"' not in page and 'data-code="0"' in page
    sid2, _ = code_session(c, monkeypatch)
    page2 = c.get(f"/demo/s/{sid2}").data.decode()
    assert 'wrap="off"' in page2 and 'data-code="1"' in page2 and "codearea" in page2
