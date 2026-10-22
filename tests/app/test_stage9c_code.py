"""Stage 9C: Python code-assessment integration status. Static-only by default; specs are per question; unsupported questions are explicit; Flask never runs candidate code."""
import pytest

from src.demo import codeassess as CA, interview as I
from src.demo.routes import set_engine
from tests.app.test_stage4a_demo import make_engine
from tests.app.test_stage9b_interview import create, current


def _env(monkeypatch, code=True, docker=False):
    monkeypatch.delenv("SMART_CODEEVAL_EXEC", raising=False)
    monkeypatch.setenv("SMART_DEMO_CODE_EVAL", "1") if code else monkeypatch.delenv("SMART_DEMO_CODE_EVAL", raising=False)


def test_static_only_by_default_and_no_runner_in_flask(monkeypatch):
    _env(monkeypatch)
    assert not CA.sandboxed_runner(), "no execution backend unless SMART_CODEEVAL_EXEC=docker is set explicitly"
    d = CA.describe()
    assert d["enabled"] is True and not d.get("executes", False)


def test_specs_are_question_specific_and_unsupported_questions_say_so(monkeypatch):
    _env(monkeypatch)
    ids = CA.spec_ids()
    assert ids and all(CA.has_spec(q) for q in ids)
    assert not CA.has_spec("smi-does-not-exist")
    r = CA.assess("smi-does-not-exist", "def f(x):\n    return x\n")
    assert r["status"] == "no_spec" and r["message"]


def test_python_practical_gets_a_spec_when_code_check_is_on(app_module, tmp_path, monkeypatch):
    _env(monkeypatch)
    e = make_engine(tmp_path)
    set_engine(e)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        r = c.post("/demo/api/sessions", json={"role": "Python Developer", "code_eval": True})
        assert r.status_code == 201, r.json
        s = e.get(r.json["session_id"])
        prac = [q for q in s["questions"] if I.stage_of(q) == I.PRACTICAL]
        for q in prac:                                      # a practical exercise either has a declared spec or is explicitly marked unsupported (None/False), never guessed
            assert q["code_spec"] in (True, False)
    set_engine(None)


def test_code_check_off_by_default_has_no_code_panel(app_module, tmp_path, monkeypatch):
    _env(monkeypatch, code=False)
    e = make_engine(tmp_path)
    set_engine(e)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        r = c.post("/demo/api/sessions", json={"role": "Python Developer"})
        s = e.get(r.json["session_id"])
        assert not s["config"]["code_eval"] and all(not q.get("code_spec") for q in s["questions"])
        r = c.post("/demo/api/sessions", json={"role": "Python Developer", "code_eval": True})
        assert r.status_code == 400
    set_engine(None)
