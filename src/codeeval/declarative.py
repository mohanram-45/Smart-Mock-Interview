"""Declarative code-assessment specs (Stage 8B): a question's requirements as validated DATA instead of Python callables.

Why: the two hand-written specs (specs_builtin.py) use Python functions for their structure and explanation checks, and a hard-coded harness function per question.
That is fine for two questions and does not scale to a third. A declarative spec is a JSON document that a person can review without reading Python:

    {"schema": 1, "spec_id": "example_add/1", "question_id": "example-add", "title": "...", "limitations": ["..."],
     "requirements": [
        {"id": "f_basic", "kind": "functional",  "label": "add(2, 3) is 5", "case": {"function": "add", "args": [2, 3], "expect": {"equals": 5}}},
        {"id": "s_def",   "kind": "structure",   "label": "Defines add", "rule": {"type": "defines_function", "name": "add"}},
        {"id": "e_why",   "kind": "explanation", "label": "Mentions integer overflow", "topic": [["overflow", "wrap"], ["integer", "int"]]}]}

The three kinds stay separate, exactly as in the hand-written specs (see spec.py): functional cases run ONLY in the sandbox (never in Flask, never at load time), structure
rules read the code text with `ast` (never run it), explanation topics match wording only and can never verify an explanation. Nothing here evaluates anything:
cases hold JSON literals that the sandbox harness passes to the candidate's function, rules come from a fixed whitelist, and unknown keys are rejected.
Loading a spec registers it for its question id; nothing is auto-loaded, and no spec for a real corpus question ships with this module.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List

from .spec import CodeSpec, Context, Finding, Requirement, explanation_check, register

SCHEMA = 1
MAX_REQUIREMENTS, MAX_CASE_BYTES, MAX_PATTERN = 40, 4000, 120
EXPECT_KEYS = {"equals", "approx", "raises", "returns_type"}
RAISES = {"ValueError", "TypeError", "ZeroDivisionError", "IndexError", "KeyError"}
RETURN_TYPES = {"list", "tuple", "dict", "str", "int", "float", "bool", "NoneType"}
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_DOTTED = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,3}$")
_ID = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_NESTED_QUANT = re.compile(r"(\)|\])[*+{]\s*[*+{]|\([^)]*[*+][^)]*\)[*+{]")     # (a+)+ style: catastrophic backtracking


class SpecError(ValueError):
    """The spec document is invalid. The message names the offending requirement and field."""


def _only(d: Any, allowed: set, where: str) -> Dict[str, Any]:
    if not isinstance(d, dict):
        raise SpecError(f"{where}: must be an object")
    extra = set(d) - allowed
    if extra:
        raise SpecError(f"{where}: unknown key(s) {sorted(extra)}")
    return d


def _literal(x: Any, where: str, depth: int = 0) -> None:
    if depth > 6:
        raise SpecError(f"{where}: nested too deeply")
    if x is None or isinstance(x, (bool, int, str)):
        return
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            raise SpecError(f"{where}: NaN/inf are not allowed")
        return
    if isinstance(x, list):
        for i in x:
            _literal(i, where, depth + 1)
        return
    if isinstance(x, dict):
        for k, v in x.items():
            if not isinstance(k, str):
                raise SpecError(f"{where}: object keys must be strings")
            _literal(v, where, depth + 1)
        return
    raise SpecError(f"{where}: only JSON literals are allowed, got {type(x).__name__}")


def _case(req_id: str, c: Any) -> Dict[str, Any]:
    where = f"requirement {req_id!r} case"
    c = _only(c, {"function", "args", "kwargs", "expect", "args_unchanged"}, where)
    if not isinstance(c.get("function"), str) or not _IDENT.match(c["function"]):
        raise SpecError(f"{where}: 'function' must be a plain identifier")
    for key, typ in (("args", list), ("kwargs", dict)):
        if key in c:
            if not isinstance(c[key], typ):
                raise SpecError(f"{where}: '{key}' must be a {typ.__name__}")
            _literal(c[key], f"{where}.{key}")
    if "args_unchanged" in c and not isinstance(c["args_unchanged"], bool):
        raise SpecError(f"{where}: 'args_unchanged' must be true or false")
    e = c.get("expect")
    e = _only(e, EXPECT_KEYS | {"rtol", "atol"}, f"{where}.expect")
    kinds = EXPECT_KEYS & set(e)
    if len(kinds) != 1:
        raise SpecError(f"{where}.expect: give exactly one of {sorted(EXPECT_KEYS)}")
    k = next(iter(kinds))
    if k in ("equals", "approx"):
        _literal(e[k], f"{where}.expect.{k}")
    if k == "raises" and e["raises"] not in RAISES:
        raise SpecError(f"{where}.expect.raises: must be one of {sorted(RAISES)}")
    if k == "returns_type" and e["returns_type"] not in RETURN_TYPES:
        raise SpecError(f"{where}.expect.returns_type: must be one of {sorted(RETURN_TYPES)}")
    if ({"rtol", "atol"} & set(e)) and k != "approx":
        raise SpecError(f"{where}.expect: rtol/atol only apply to 'approx'")
    for t in ("rtol", "atol"):
        if t in e and (isinstance(e[t], bool) or not isinstance(e[t], (int, float)) or e[t] < 0):
            raise SpecError(f"{where}.expect.{t}: must be a non-negative number")
    if len(json.dumps(c)) > MAX_CASE_BYTES:
        raise SpecError(f"{where}: larger than {MAX_CASE_BYTES} bytes")
    return c


# ------------------------------------------------------------------------------------------------ structure rules: a fixed vocabulary, each reads the AST report only
def _fn(ctx: Context, name: str):
    return ctx.report.functions.get(name)


def _r_defines_function(r: Dict[str, Any]) -> Callable[[Context], Finding]:
    def check(ctx: Context) -> Finding:
        if _fn(ctx, r["name"]) is not None:
            return Finding("demonstrated", [f"defines {r['name']}()"], f"A function named {r['name']} is defined. Text evidence only.")
        return Finding("missing", note=f"No function named {r['name']} was found.")
    return check


def _r_calls_any(r: Dict[str, Any]) -> Callable[[Context], Finding]:
    wanted = set(r["names"])

    def check(ctx: Context) -> Finding:
        f = _fn(ctx, r["function"])
        if f is None:
            return Finding("missing", note=f"No function named {r['function']} was found.")
        used = sorted(f.calls & wanted)
        if used:
            return Finding("demonstrated", [f"calls {u}" for u in used], f"{r['function']} calls one of the expected operations. Text evidence only: it does not show the result is right.")
        if r.get("allow_matmul_operator") and f.matmul_ops:
            return Finding("demonstrated", [ctx.snippet(n) for n in f.matmul_ops[:2]], f"{r['function']} uses the @ operator. Text evidence only.")
        return Finding("missing", note=f"None of {sorted(wanted)} is called inside {r['function']}.")
    return check


def _r_no_loops(r: Dict[str, Any]) -> Callable[[Context], Finding]:
    def check(ctx: Context) -> Finding:
        f = _fn(ctx, r["function"])
        if f is None:
            return Finding("unclear", note=f"{r['function']} was not found, so loops could not be checked.")
        if f.loops == 0 and f.comprehensions == 0:
            return Finding("demonstrated", [f"no for/while statement or comprehension in {r['function']}"], "Helper functions it calls are not inspected.")
        return Finding("contradicted", [f"{f.loops} loop(s), {f.comprehensions} comprehension(s)"], f"{r['function']} contains a loop or comprehension.")
    return check


def _r_class_methods(r: Dict[str, Any]) -> Callable[[Context], Finding]:
    need = set(r["methods"])

    def check(ctx: Context) -> Finding:
        best = None
        for cname, ms in ctx.report.classes.items():
            have = need & set(ms)
            if have == need:
                return Finding("demonstrated", [f"class {cname} defines {', '.join(sorted(need))}"], "The required methods are defined. Text evidence only.")
            if have and (best is None or len(have) > len(best[1])):
                best = (cname, have)
        if best:
            return Finding("unclear", [f"class {best[0]} defines only {', '.join(sorted(best[1]))}"], f"Missing: {', '.join(sorted(need - best[1]))}.")
        return Finding("missing", note=f"No class defining {', '.join(sorted(need))} was found.")
    return check


def _r_imports(r: Dict[str, Any]) -> Callable[[Context], Finding]:
    def check(ctx: Context) -> Finding:
        if r["module"] in ctx.report.imports:
            return Finding("demonstrated", [f"imports {r['module']}"], "The module is imported. Text evidence only.")
        return Finding("missing", note=f"{r['module']} is not imported.")
    return check


def _need_names(r: Dict[str, Any], where: str, key: str = "names") -> None:
    v = r.get(key)
    if not isinstance(v, list) or not v or len(v) > 20 or not all(isinstance(x, str) and _DOTTED.match(x) for x in v):
        raise SpecError(f"{where}: '{key}' must be a non-empty list of dotted names")


def _need_ident(r: Dict[str, Any], key: str, where: str) -> None:
    if not isinstance(r.get(key), str) or not _IDENT.match(r[key]):
        raise SpecError(f"{where}: '{key}' must be a plain identifier")


RULES: Dict[str, Dict[str, Any]] = {
    "defines_function": {"keys": {"name"}, "build": _r_defines_function, "check": lambda r, w: _need_ident(r, "name", w)},
    "function_calls_any": {"keys": {"function", "names", "allow_matmul_operator"}, "build": _r_calls_any, "check": lambda r, w: (_need_ident(r, "function", w), _need_names(r, w))},
    "function_has_no_loops": {"keys": {"function"}, "build": _r_no_loops, "check": lambda r, w: _need_ident(r, "function", w)},
    "class_defines_methods": {"keys": {"methods"}, "build": _r_class_methods, "check": lambda r, w: _need_names(r, w, "methods")},
    "imports_module": {"keys": {"module"}, "build": _r_imports, "check": lambda r, w: _need_ident(r, "module", w)},
}


def _rule(req_id: str, rule: Any) -> Callable[[Context], Finding]:
    where = f"requirement {req_id!r} rule"
    if not isinstance(rule, dict) or rule.get("type") not in RULES:
        raise SpecError(f"{where}: 'type' must be one of {sorted(RULES)}")
    spec = RULES[rule["type"]]
    r = _only(rule, spec["keys"] | {"type"}, where)
    spec["check"](r, where)
    if "allow_matmul_operator" in r and not isinstance(r["allow_matmul_operator"], bool):
        raise SpecError(f"{where}: 'allow_matmul_operator' must be true or false")
    return spec["build"](r)


def _topic(req_id: str, label: str, groups: Any) -> Callable[[Context], Finding]:
    where = f"requirement {req_id!r} topic"
    if not isinstance(groups, list) or not groups or len(groups) > 6:
        raise SpecError(f"{where}: must be 1-6 groups of alternative phrases")
    out: List[List[str]] = []
    for g in groups:
        if not isinstance(g, list) or not g or len(g) > 12 or not all(isinstance(p, str) and p.strip() for p in g):
            raise SpecError(f"{where}: each group must be a non-empty list of phrases")
        pats = []
        for p in g:
            if len(p) > MAX_PATTERN:
                raise SpecError(f"{where}: phrase longer than {MAX_PATTERN} characters")
            if _NESTED_QUANT.search(p):
                raise SpecError(f"{where}: phrase {p!r} looks like a catastrophic-backtracking pattern")
            try:
                re.compile(p)
            except re.error as e:
                raise SpecError(f"{where}: phrase {p!r} is not a valid pattern ({e})") from e
            pats.append(p)
        out.append(pats)
    return explanation_check(out, label)


def spec_from_dict(d: Any, *, register_it: bool = False) -> CodeSpec:
    """Validate `d` and build a CodeSpec. Raises SpecError with a precise message; never executes anything."""
    d = _only(d, {"schema", "spec_id", "question_id", "title", "limitations", "requirements"}, "spec")
    if d.get("schema") != SCHEMA:
        raise SpecError(f"spec: unsupported schema {d.get('schema')!r} (this loader reads schema {SCHEMA})")
    for k in ("spec_id", "question_id", "title"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            raise SpecError(f"spec: '{k}' must be a non-empty string")
    lim = d.get("limitations", [])
    if not isinstance(lim, list) or not all(isinstance(x, str) for x in lim):
        raise SpecError("spec: 'limitations' must be a list of strings")
    reqs_in = d.get("requirements")
    if not isinstance(reqs_in, list) or not reqs_in or len(reqs_in) > MAX_REQUIREMENTS:
        raise SpecError(f"spec: 'requirements' must be a list of 1-{MAX_REQUIREMENTS} items")
    reqs: List[Requirement] = []
    cases: List[Dict[str, Any]] = []
    seen = set()
    for i, r in enumerate(reqs_in):
        r = _only(r, {"id", "kind", "label", "help", "case", "rule", "topic"}, f"requirements[{i}]")
        rid = r.get("id")
        if not isinstance(rid, str) or not _ID.match(rid) or rid in seen:
            raise SpecError(f"requirements[{i}]: 'id' must be unique lowercase letters, digits and underscores")
        seen.add(rid)
        kind, label = r.get("kind"), r.get("label")
        if kind not in ("functional", "structure", "explanation") or not isinstance(label, str) or not label.strip():
            raise SpecError(f"requirement {rid!r}: needs a 'kind' (functional|structure|explanation) and a non-empty 'label'")
        needs = {"functional": "case", "structure": "rule", "explanation": "topic"}[kind]
        if needs not in r or (set(r) & {"case", "rule", "topic"}) != {needs}:
            raise SpecError(f"requirement {rid!r}: a {kind} requirement takes exactly one '{needs}' and no other of case/rule/topic")
        help_ = r.get("help", "")
        if not isinstance(help_, str):
            raise SpecError(f"requirement {rid!r}: 'help' must be a string")
        if kind == "functional":
            cases.append({"id": rid, **_case(rid, r["case"])})
            reqs.append(Requirement(rid, label, "functional", test_id=rid, help=help_))
        elif kind == "structure":
            reqs.append(Requirement(rid, label, "structure", check=_rule(rid, r["rule"]), help=help_))
        else:
            reqs.append(Requirement(rid, label, "explanation", check=_topic(rid, label, r["topic"]), help=help_))
    if sum(len(json.dumps(c)) for c in cases) > 10 * MAX_CASE_BYTES:
        raise SpecError("spec: the functional cases are too large in total")
    spec = CodeSpec(d["spec_id"], d["question_id"], d["title"], "declarative_cases" if cases else "none", tuple(reqs),
                    tuple(lim) + ("Declarative cases test only the inputs listed in the spec; passing them does not prove the code is correct for all inputs.",) * bool(cases),
                    tuple(cases))
    return register(spec) if register_it else spec


def load_spec_file(path: Path | str, *, register_it: bool = False) -> CodeSpec:
    p = Path(path)
    if p.stat().st_size > 200_000:
        raise SpecError(f"{p.name}: larger than 200 kB")
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SpecError(f"{p.name}: not valid JSON ({e})") from e
    return spec_from_dict(doc, register_it=register_it)
