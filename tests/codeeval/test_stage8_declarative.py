"""Stage 8B: declarative code-assessment specs. Behaviour cases run only through the test-only TrustedLocalRunner, on fixtures written in this file."""
import copy
import json
from pathlib import Path

import pytest

from src.codeeval import runner as R, spec as SP
from src.codeeval.declarative import SpecError, load_spec_file, spec_from_dict
from src.codeeval.evaluate import BUCKETS, assess
from src.codeeval.runner import DisabledRunner

EXAMPLE = Path(__file__).resolve().parents[2] / "src" / "codeeval" / "examples" / "example_clamp.json"
Q = "example-clamp"

GOOD = '''
def clamp(x, low, high):
    """Return x limited to [low, high]. A reversed range (low > high) is an error: raise ValueError."""
    if low > high:
        raise ValueError("low > high")
    return max(low, min(x, high))
'''
WRONG_UPPER = GOOD.replace("min(x, high)", "min(x, high + 1)")
LOOPY = '''
def clamp(x, low, high):
    if low > high:
        raise ValueError("reversed")
    for _ in range(1):
        x = max(low, min(x, high))
    return x
'''
NO_RAISE = GOOD.replace('        raise ValueError("low > high")\n', "        return low\n")


@pytest.fixture()
def registered(monkeypatch):
    monkeypatch.setattr(SP, "_REGISTRY", dict(SP._REGISTRY))
    SP._load_builtin()
    load_spec_file(EXAMPLE, register_it=True)
    return Q


def doc():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def req(r, rid):
    return next(x for x in r["requirements"] if x["id"] == rid)


# ---- the format ----
def test_example_spec_loads_and_is_pure_data():
    s = load_spec_file(EXAMPLE)
    assert s.harness_id == "declarative_cases" and [c["id"] for c in s.cases] == ["f_inside", "f_below", "f_above", "f_bad_range"]
    assert {r.kind for r in s.requirements} == {"functional", "structure", "explanation"}
    assert any("only the inputs listed" in l for l in s.limitations)
    assert Q not in SP.spec_question_ids()                 # loading a file does not register anything unless asked


@pytest.mark.parametrize("mutate,needle", [
    (lambda d: d.update(schema=2), "unsupported schema"),
    (lambda d: d.update(surprise=1), "unknown key"),
    (lambda d: d["requirements"][0].update(rule={"type": "defines_function", "name": "x"}), "exactly one 'case'"),
    (lambda d: d["requirements"][0]["case"].update(function="a b"), "plain identifier"),
    (lambda d: d["requirements"][0]["case"].update(args=[{1: 2}]), "keys must be strings"),
    (lambda d: d["requirements"][0]["case"].update(args=[float("nan")]), "NaN"),
    (lambda d: d["requirements"][0]["case"]["expect"].update(raises="ValueError"), "exactly one of"),
    (lambda d: d["requirements"][3]["case"]["expect"].update(raises="SystemExit"), "must be one of"),
    (lambda d: d["requirements"][0]["case"].update(extra=1), "unknown key"),
    (lambda d: d["requirements"][4].update(rule={"type": "eval_this", "name": "x"}), "'type' must be one of"),
    (lambda d: d["requirements"][4]["rule"].update(name="os.system('x')"), "plain identifier"),
    (lambda d: d["requirements"][1].update(id=d["requirements"][0]["id"]), "unique"),
    (lambda d: d["requirements"][6].update(topic=[["(a+)+$"]]), "catastrophic"),
    (lambda d: d["requirements"][6].update(topic=[["(unclosed"]]), "not a valid pattern"),
    (lambda d: d.update(requirements=[]), "requirements"),
])
def test_invalid_specs_are_rejected_with_a_precise_message(mutate, needle):
    d = copy.deepcopy(doc())
    mutate(d)
    with pytest.raises(SpecError, match=needle):
        spec_from_dict(d)


def test_non_json_literals_cannot_smuggle_code_into_a_case():
    d = doc()
    d["requirements"][0]["case"]["args"] = [{"__import__": "os"}, "__import__('os').system('x')"]
    s = spec_from_dict(d)                                   # allowed: they are only DATA (a dict and a string) handed to the candidate's function
    assert s.cases[0]["args"][1].startswith("__import__")
    d["requirements"][0]["case"]["args"] = [object()]
    with pytest.raises(SpecError, match="only JSON literals"):
        spec_from_dict(d)


# ---- default behaviour: nothing runs ----
def test_default_is_static_only_for_declarative_specs_too(registered):
    r = assess(Q, GOOD, DisabledRunner(), execute=False)
    assert r["status"] == "assessed" and r["executed"] is False
    assert r["buckets"]["verified_correct"] == [] and all(req(r, c)["status"] == "not_run" for c in ("f_inside", "f_below", "f_above", "f_bad_range"))
    assert "s_defines" in r["buckets"]["demonstrated"] and "s_noloops" in r["buckets"]["demonstrated"]
    assert req(r, "e_edge")["status"] == "mentioned_unverified" and "e_edge" in r["buckets"]["unverified"]      # wording only: never "verified"
    assert not any(k in r for k in ("score", "total", "grade"))


def test_every_declarative_requirement_lands_in_exactly_one_bucket(registered):
    r = assess(Q, GOOD, DisabledRunner(), execute=False)
    placed = [i for b in BUCKETS for i in r["buckets"][b]]
    assert sorted(placed) == sorted(x["id"] for x in r["requirements"]) and len(placed) == len(set(placed))


# ---- behaviour cases, through the trusted test runner only ----
def test_good_solution_passes_every_case_and_is_reported_as_verified(registered, trusted):
    r = assess(Q, GOOD, trusted)
    assert r["executed"] is True and r["buckets"]["verified_correct"] == ["f_inside", "f_below", "f_above", "f_bad_range"]
    assert "4 of 4 behaviour tests passed" in r["summary"]["functional"] and any("only the inputs listed" in n for n in r["notes"])
    assert trusted.calls == ["declarative_cases"]


def test_wrong_solution_fails_the_right_case_and_nothing_else(registered, trusted):
    r = assess(Q, WRONG_UPPER, trusted)
    assert req(r, "f_above")["status"] == "failed" and "expected 10; got 11" in req(r, "f_above")["evidence"][0]
    assert req(r, "f_inside")["status"] == "passed" and "f_above" in r["buckets"]["incorrect"]


def test_missing_expected_exception_is_a_failure_and_a_loop_is_a_structural_contradiction(registered, trusted):
    r = assess(Q, NO_RAISE, trusted)
    assert req(r, "f_bad_range")["status"] == "failed" and "expected ValueError" in req(r, "f_bad_range")["evidence"][0]
    r2 = assess(Q, LOOPY, trusted)
    assert req(r2, "s_noloops")["status"] == "contradicted" and "s_noloops" in r2["buckets"]["incorrect"] and req(r2, "f_inside")["status"] == "passed"


def test_candidate_that_never_defines_the_function_is_an_error_not_a_pass(registered, trusted):
    r = assess(Q, "def other():\n    return 1\n", trusted)
    assert all(req(r, c)["status"] in ("failed", "error") for c in ("f_inside", "f_below", "f_above", "f_bad_range"))
    assert r["buckets"]["verified_correct"] == [] and req(r, "s_defines")["status"] == "missing"


def test_forbidden_constructs_are_refused_before_any_runner_sees_them(registered, trusted):
    r = assess(Q, "import os\ndef clamp(x, low, high):\n    os.system('echo hi')\n    return x\n", trusted)
    assert trusted.calls == [] and r["execution"]["status"] == "refused" and r["buckets"]["verified_correct"] == []


# ---- harness comparison semantics (trusted fixtures) ----
@pytest.fixture()
def harness():
    from src.codeeval import harness as H
    return H


def test_comparison_is_strict_about_bool_vs_int_and_tolerant_only_for_approx(harness):
    s = harness._same
    assert s(1, 1) and not s(True, 1) and not s(1, True) and s(True, True)
    assert not s(0.1 + 0.2, 0.3) and s(0.1 + 0.2, 0.3, 1e-9, 0.0)
    assert s([1, [2, 3]], (1, (2, 3))) and not s([1, 2], [1, 2, 3]) and s({"a": [1]}, {"a": [1]}) and not s({"a": 1}, {"b": 1})
    assert not s("1", 1)


def test_args_unchanged_is_enforced_and_inputs_are_copies(harness):
    src = "def f(xs):\n    xs.append(9)\n    return len(xs)\n"
    out = harness.run("declarative_cases", src, [{"id": "c", "function": "f", "args": [[1, 2]], "args_unchanged": True, "expect": {"equals": 3}},
                                                 {"id": "d", "function": "f", "args": [[1, 2]], "expect": {"equals": 3}}])
    st = {t["id"]: t for t in out["tests"]}
    assert st["c"]["status"] == "failed" and "changed its input" in st["c"]["detail"] and st["d"]["status"] == "passed"


def test_candidate_exception_is_an_error_finding_and_output_detail_is_bounded(harness):
    src = "def f(x):\n    raise RuntimeError('boom')\ndef g(x):\n    return 'y' * 5000\n"
    out = harness.run("declarative_cases", src, [{"id": "e", "function": "f", "args": [1], "expect": {"equals": 1}}, {"id": "l", "function": "g", "args": [1], "expect": {"equals": "n"}}])
    st = {t["id"]: t for t in out["tests"]}
    assert st["e"]["status"] == "error" and "RuntimeError" in st["e"]["detail"] and len(st["l"]["detail"]) < 400


def test_unknown_harness_and_no_cases_are_safe(harness):
    assert harness.run("nope", "x = 1")["load_error"]
    assert harness.run("declarative_cases", "x = 1", None)["tests"] == []
    assert harness.run("numpy_pairwise_sq_dists", "x = 1")["tests"] is not None     # the original harnesses still take (harness_id, source)


# ---- the sandbox path carries the cases as data and never on the command line ----
def test_docker_payload_carries_cases_on_stdin_and_the_command_line_has_no_candidate_code(monkeypatch):
    seen = {}
    d = R.DockerRunner("img")
    d._checked = (True, "ok")

    def fake(cmd, stdin, wall, maxo, kill):
        seen["cmd"], seen["stdin"] = cmd, json.loads(stdin)
        nonce = seen["stdin"]["nonce"]
        return (nonce + json.dumps({"tests": [{"id": "c", "status": "passed", "detail": ""}], "load_error": None})).encode(), "ok"
    monkeypatch.setattr(R, "_bounded_run", fake)
    cases = [{"id": "c", "function": "f", "args": [1], "expect": {"equals": 1}}]
    res = d.run("declarative_cases", "SECRET_CANDIDATE_MARKER = 1", cases)
    assert res.status == "ok" and seen["stdin"]["cases"] == cases and seen["stdin"]["source"] == "SECRET_CANDIDATE_MARKER = 1"
    assert not any("SECRET_CANDIDATE_MARKER" in part for part in seen["cmd"]) and "none" in seen["cmd"]
    d.run("numpy_pairwise_sq_dists", "x = 1")
    assert seen["stdin"]["cases"] is None


def test_the_loader_cannot_execute_anything():
    """declarative.py only parses data: it imports neither the harness, the runner, subprocess, nor os, and has no exec/eval/compile call (the repository-wide guard
    in test_no_exec_in_web_layers.py covers this file too, because it globs src/codeeval/*.py)."""
    import ast
    tree = ast.parse((Path(__file__).resolve().parents[2] / "src/codeeval/declarative.py").read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not mods & {"subprocess", "os", "harness", "runner", "src.codeeval.harness", "src.codeeval.runner"}, mods
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"exec", "eval", "compile", "open", "__import__"} for n in ast.walk(tree))
