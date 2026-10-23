"""Stage 5A: the code-assessment prototype's evaluator, specs and static layer. Behaviour tests run through the TRUSTED local runner on fixtures written in this repo only."""
import pytest

from src.codeeval import extract, static
from src.codeeval.evaluate import BUCKETS, assess
from src.codeeval.runner import DisabledRunner
from src.codeeval.spec import get_spec, spec_question_ids
from tests.codeeval import fixtures as F

NP, LR = "smi-h0029", "smi-0462"


def req(r, rid):
    return next(x for x in r["requirements"] if x["id"] == rid)


def status(r, rid):
    return req(r, rid)["status"]


# ------------------------------------------------------------------------------------------------ default: no execution, no verification
def test_default_is_static_only_and_never_claims_verified_behaviour():
    r = assess(NP, F.NP_GOOD)
    assert r["status"] == "assessed" and r["executed"] is False and r["execution"]["status"] == "not_run"
    assert r["buckets"]["verified_correct"] == [] and r["buckets"]["incorrect"] == []
    assert all(status(r, i) == "not_run" for i in ("f_example", "f_values", "f_shapes", "f_nonneg", "f_broadcast"))
    assert {"s_matmul", "s_noloops", "s_nonneg", "s_broadcast"} <= set(r["buckets"]["demonstrated"])
    assert "were not run" in r["summary"]["functional"] and any("nothing was run" in n for n in r["notes"])
    assert "NO SCORE" in r["labels"] and "EXPERIMENTAL" in r["labels"] and not any(k in r for k in ("score", "total", "grade"))


def test_every_requirement_lands_in_exactly_one_bucket():
    for q, code in ((NP, F.NP_GOOD), (LR, F.LR_GD)):
        r = assess(q, code)
        placed = [i for b in BUCKETS for i in r["buckets"][b]]
        assert sorted(placed) == sorted(x["id"] for x in r["requirements"]) and len(placed) == len(set(placed))


def test_unknown_question_not_code_and_syntax_errors_are_reported_not_scored():
    assert assess("smi-0001", "x")["status"] == "no_spec"
    r = assess(NP, "I would use a matrix product and clip the result at zero.")
    assert r["status"] == "no_code" and "requirements" not in r
    r = assess(NP, "def pairwise_sq_dists(A, B:\n    return 1\n")
    assert r["status"] in ("parse_error", "no_code")
    r = assess(NP, "```python\ndef pairwise_sq_dists(A, B:\n    return 1\n```")
    assert r["status"] == "parse_error" and "Nothing was run" in r["message"] and r["answer"]["parse_ok"] is False


def test_a_crash_inside_the_assessment_is_contained(monkeypatch):
    import src.codeeval.evaluate as E
    monkeypatch.setattr(E, "_assess", lambda *a, **k: 1 / 0)
    r = assess(NP, F.NP_GOOD)
    assert r["status"] == "error" and "ZeroDivisionError" in r["message"]


# ------------------------------------------------------------------------------------------------ pairwise distances: behaviour vs structure vs explanation
def test_good_numpy_answer_passes_behaviour_but_explanations_are_missing(trusted):
    r = assess(NP, F.NP_GOOD, trusted)
    assert r["executed"] and r["summary"]["functional"] == "5 of 5 behaviour tests passed in the sandbox"
    assert sorted(r["buckets"]["verified_correct"]) == sorted(["f_example", "f_values", "f_shapes", "f_nonneg", "f_broadcast"])
    assert set(r["buckets"]["missing"]) == {"e_memory", "e_cancel"}, "code-only answer: the requested trade-off explanations are missing, however good the code is"
    assert r["buckets"]["incorrect"] == []


def test_explanation_prose_is_recognised_but_only_ever_unverified(trusted):
    r = assess(NP, F.NP_GOOD + F.NP_EXPLANATION, trusted)
    assert status(r, "e_memory") == "mentioned_unverified" and status(r, "e_cancel") == "mentioned_unverified"
    assert set(r["buckets"]["unverified"]) >= {"e_memory", "e_cancel"} and not {"e_memory", "e_cancel"} & set(r["buckets"]["verified_correct"])
    assert "NOT verified" in req(r, "e_memory")["note"]


def test_missing_clip_fails_the_negative_test_and_static_check(trusted):
    r = assess(NP, F.NP_NO_CLIP, trusted)
    assert status(r, "f_nonneg") == "failed" and status(r, "f_values") == "passed"      # values right, but not non-negative on hard input
    assert status(r, "s_nonneg") == "missing" and "f_nonneg" in r["buckets"]["incorrect"] and "s_nonneg" in r["buckets"]["missing"]


def test_sign_error_is_incorrect_behaviour_even_though_structure_looks_right(trusted):
    r = assess(NP, F.NP_SIGN_BUG, trusted)
    assert {"f_example", "f_values"} <= set(r["buckets"]["incorrect"]) and status(r, "s_matmul") == "demonstrated"


def test_keyword_stuffing_earns_nothing(trusted):
    r = assess(NP, F.NP_KEYWORD_STUFFING_WRONG, trusted)
    assert status(r, "e_memory") == "mentioned_unverified" and status(r, "e_cancel") == "mentioned_unverified"
    assert r["buckets"]["verified_correct"] == [] or "f_example" not in r["buckets"]["verified_correct"]
    assert "f_example" in r["buckets"]["incorrect"]
    assert set(r["buckets"]["unverified"]) >= {"e_memory", "e_cancel"}          # mentioned words are never counted as verified


def test_loops_are_a_contradiction_not_a_failure_of_behaviour(trusted):
    r = assess(NP, F.NP_LOOPS, trusted)
    assert status(r, "s_noloops") == "contradicted" and "s_noloops" in r["buckets"]["incorrect"] and "s_matmul" in r["buckets"]["missing"]
    assert status(r, "f_values") == "passed"                                   # separate questions: it works, but it breaks the stated constraint
    assert "line" in " ".join(req(r, "s_noloops")["evidence"])


def test_exceptions_and_wrong_names_are_reported_distinctly(trusted):
    raises = assess(NP, F.NP_RAISES, trusted)
    assert status(raises, "f_values") == "error" and "ValueError" in req(raises, "f_values")["evidence"][0]
    names = assess(NP, F.NP_WRONG_NAMES, trusted)
    assert status(names, "f_example") == "failed" and "no callable named" in req(names, "f_example")["evidence"][0] and status(names, "s_matmul") == "missing"


# ------------------------------------------------------------------------------------------------ linear regression
@pytest.mark.parametrize("code", [F.LR_GD, F.LR_CLOSED])
def test_gradient_descent_and_closed_form_both_pass(trusted, code):
    r = assess(LR, code, trusted)
    assert r["summary"]["functional"] == "5 of 5 behaviour tests passed in the sandbox" and r["buckets"]["incorrect"] == []
    assert status(r, "s_updates") == "demonstrated"
    assert r["summary"]["explanation"] == "this question does not request an explanation"


def test_closed_form_has_no_gradient_requirement():
    r = assess(LR, F.LR_CLOSED)
    assert status(r, "s_gradient") == "not_applicable" and "closed-form" in req(r, "s_updates")["note"]


def test_wrong_gradient_sign_is_caught_by_behaviour(trusted):
    r = assess(LR, F.LR_SIGN_BUG, trusted)
    assert {"f_positive", "f_negative"} <= set(r["buckets"]["incorrect"])
    assert status(r, "s_updates") == "demonstrated" and status(r, "s_gradient") == "demonstrated", "structure alone cannot see a sign error"


def test_interface_and_input_mutation_problems(trusted):
    assert status(assess(LR, F.LR_NO_PREDICT, trusted), "f_interface") == "failed"
    assert status(assess(LR, F.LR_NO_PREDICT), "s_methods") == "unclear"
    args = assess(LR, F.LR_NEEDS_ARGS, trusted)
    assert status(args, "f_positive") in ("error", "failed")
    mut = assess(LR, F.LR_MUTATES, trusted)
    assert status(mut, "f_untouched") == "failed"
    noupd = assess(LR, F.LR_NO_UPDATE, trusted)
    assert status(noupd, "s_updates") == "missing" and status(noupd, "f_positive") == "failed"


def test_no_hardcoded_answers_a_new_spec_works_without_touching_the_evaluator(trusted):
    from src.codeeval.spec import CodeSpec, Requirement, Finding, register
    register(CodeSpec("toy/1", "toy-q", "Toy", "numpy_pairwise_sq_dists", (Requirement("s_def", "defines f", "structure", check=lambda c: Finding("demonstrated" if "f" in c.report.functions else "missing")),)))
    assert assess("toy-q", "def f():\n    return 1\n")["buckets"]["demonstrated"] == ["s_def"]
    assert assess("toy-q", "def g():\n    return 1\n")["buckets"]["missing"] == ["s_def"]
    from src.codeeval import spec
    spec._REGISTRY.pop("toy-q")


def test_spec_registry_and_validation():
    assert {"smi-h0029", "smi-0462"} <= set(spec_question_ids())
    from src.codeeval.spec import CodeSpec, Requirement, register
    with pytest.raises(ValueError):
        register(CodeSpec("bad", "bad", "bad", "h", (Requirement("a", "a", "functional"),)))
    with pytest.raises(ValueError):
        register(CodeSpec("bad", "bad", "bad", "h", (Requirement("a", "a", "structure"),)))


# ------------------------------------------------------------------------------------------------ static layer + extraction
def test_static_policy_gate_refuses_and_never_calls_the_runner(trusted):
    for evil in ("import os\nos.system('id')", "import subprocess", "open('/etc/passwd').read()", "__import__('os')", "import numpy as np\nnp.load('x.npy')",
                 "x = ().__class__.__bases__", "import socket", "eval('1')", "from . import secrets", "import requests"):
        code = F.NP_GOOD + "\n" + evil + "\n"
        r = assess(NP, code, trusted)
        assert r["execution"]["status"] == "refused" and r["policy_violations"], evil
        assert r["executed"] is False and "f_example" in r["buckets"]["unverified"]
    assert trusted.calls == [], "a refused submission must never reach a runner"


def test_static_analysis_never_executes_the_code():
    marker = []
    code = "import numpy as np\nraise SystemExit(1)\nopen('/tmp/should_not_exist_5a','w')\n"
    rep = static.analyze(code)
    assert rep.parse_ok and rep.forbidden and not __import__("os").path.exists("/tmp/should_not_exist_5a")
    assert not marker


def test_extract_splits_prose_code_and_keeps_indentation():
    text = "My approach:\nuse a matrix product.\n\n```python\ndef f(a):\n    if a:\n        return 1\n    return 0\n```\nThis is O(n) memory."
    segs = extract.split(text)
    assert [s.kind for s in segs] == ["prose", "code", "prose"]
    assert segs[1].text == "def f(a):\n    if a:\n        return 1\n    return 0"
    assert extract.answer_kind(text) == "mixed" and extract.answer_kind("def f():\n    return 1") == "code" and extract.answer_kind("Plain words only.") == "prose"
    assert "matrix product" in extract.prose_of(text) and "def f" not in extract.prose_of(text)
    assert extract.prose_of("x = 1  # explains the step\n# whole line comment") == "explains the step\nwhole line comment"
    assert extract.question_expects_code("Implement a simple linear regression from scratch using NumPy.") and not extract.question_expects_code("What is a random variable?")


def test_answer_with_tabs_and_crlf_round_trips_through_extract():
    text = "def f(x):\r\n\tif x:\r\n\t\treturn 1\r\n\treturn 0\r\n"
    code = extract.code_of(text)
    assert code == "def f(x):\n\tif x:\n\t\treturn 1\n\treturn 0"
