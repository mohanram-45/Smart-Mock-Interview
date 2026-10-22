"""Combine extraction, static analysis, the spec and (when a real sandbox is enabled) behaviour tests into ONE report with separated findings.

The report deliberately has NO overall score. Findings are placed in five buckets that are never added together:
  verified_correct  a behaviour test PASSED in the sandbox (only possible when execution is enabled and the sandbox ran)
  demonstrated      structure present in the code text (static evidence; not proof the code works)
  missing           required structure or explanation not found in the text
  incorrect         a behaviour test FAILED/errored in the sandbox, or the code text contradicts an explicit instruction
  unverified        could not be established: tests not run, timed out, unclear static evidence, or an explanation that was only matched by wording
Similarity scores from the legacy scorers are not inputs here and are never treated as evidence of code correctness. Keyword matches never reach `verified_correct`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import ENGINE, VERSION, extract, static
from .runner import DisabledRunner, ExecResult, Runner, shared_runner
from .spec import CodeSpec, Context, Finding, get_spec

BUCKETS = ("verified_correct", "demonstrated", "missing", "incorrect", "unverified")
BUCKET_LABELS = {"verified_correct": "Verified correct behaviour", "demonstrated": "Requirements demonstrated in the code text",
                 "missing": "Requirements missing", "incorrect": "Incorrect behaviour", "unverified": "Unverified or uncertain"}
LABELS = ["EXPERIMENTAL", "NOT human-validated", "NO SCORE"]


def _functional(req, ex: Optional[ExecResult], by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    base = {"id": req.id, "kind": "functional", "label": req.label, "evidence": [], "note": ""}
    if ex is None or ex.status == "not_run" or ex.status == "refused":
        return {**base, "status": "not_run", "bucket": "unverified", "note": (ex.reason if ex else "Execution was not requested.") or "Behaviour tests were not run."}
    if ex.status in ("timeout", "sandbox_error"):
        return {**base, "status": "not_run", "bucket": "unverified", "note": ex.reason}
    if ex.load_error:
        return {**base, "status": "error", "bucket": "incorrect", "note": ex.load_error}
    t = by_id.get(req.test_id)
    if t is None:
        return {**base, "status": "not_run", "bucket": "unverified", "note": "This test produced no result."}
    st = t["status"]
    return {**base, "status": st, "bucket": "verified_correct" if st == "passed" else "incorrect", "evidence": [str(t.get("detail", ""))], "note": ""}


def _bucket_for(kind: str, f: Finding) -> str:
    if kind == "explanation":
        return {"mentioned_unverified": "unverified", "partial_unverified": "unverified", "missing": "missing"}[f.status]
    return {"demonstrated": "demonstrated", "missing": "missing", "contradicted": "incorrect", "unclear": "unverified", "not_applicable": "demonstrated"}[f.status]


def assess(question_id: str, answer_text: str, runner: Optional[Runner] = None, *, execute: bool = True) -> Dict[str, Any]:
    """Assess one answer against the registered spec for `question_id`. Never raises. `runner=None` uses the configured runner (disabled unless explicitly enabled)."""
    base: Dict[str, Any] = {"engine": ENGINE, "version": VERSION, "labels": list(LABELS), "question_id": question_id}
    spec = get_spec(question_id)
    if spec is None:
        return {**base, "status": "no_spec", "message": "No code assessment is defined for this question."}
    try:
        return _assess(spec, base, answer_text, runner, execute)
    except Exception as e:                                         # a bug here must never break the interview
        return {**base, "status": "error", "message": f"The code assessment failed unexpectedly ({type(e).__name__}).", "spec": spec.spec_id}


def _assess(spec: CodeSpec, base: Dict[str, Any], answer_text: str, runner: Optional[Runner], execute: bool) -> Dict[str, Any]:
    kind = extract.answer_kind(answer_text)
    code = extract.code_of(answer_text)
    if not code.strip():
        return {**base, "status": "no_code", "spec": spec.spec_id, "title": spec.title, "answer": {"kind": kind, "code_lines": 0, "parse_ok": False, "parse_error": None},
                "message": "No Python code was found in this answer, so the code requirements could not be assessed."}
    report = static.analyze(code)
    ans = {"kind": kind, "code_lines": len([l for l in code.split("\n") if l.strip()]), "parse_ok": report.parse_ok, "parse_error": report.error, "parse_error_line": report.error_line}
    if not report.parse_ok:
        return {**base, "status": "parse_error", "spec": spec.spec_id, "title": spec.title, "answer": ans,
                "message": f"The code could not be parsed (line {report.error_line}: {report.error}), so nothing could be assessed. Nothing was run."}
    prose = "\n".join(p for p in (extract.prose_of(answer_text), "\n".join(report.docstrings)) if p)
    ctx = Context(report, code, prose)
    violations = static.policy_violations(report)

    ex: Optional[ExecResult] = None
    runner = runner if runner is not None else (shared_runner() if execute else DisabledRunner("Execution was not requested."))
    if violations:
        ex = ExecResult("refused", "Not run: the code uses constructs that are never sent to an execution backend ("
                        + "; ".join(f"line {v['line']}: {v['what']}" for v in violations[:4]) + ").", backend=runner.name)
    elif execute:
        ex = runner.run(spec.harness_id, code, cases=[dict(c) for c in spec.cases]) if spec.cases else runner.run(spec.harness_id, code)
    by_id = {t["id"]: t for t in (ex.tests if ex else [])}

    reqs: List[Dict[str, Any]] = []
    for r in spec.requirements:
        if r.kind == "functional":
            reqs.append(_functional(r, ex, by_id))
        else:
            f = r.check(ctx)
            reqs.append({"id": r.id, "kind": r.kind, "label": r.label, "status": f.status, "bucket": _bucket_for(r.kind, f), "evidence": f.evidence, "note": f.note})
    buckets = {b: [x["id"] for x in reqs if x["bucket"] == b] for b in BUCKETS}
    ran = ex is not None and ex.status == "ok" and not ex.load_error
    func = [x for x in reqs if x["kind"] == "functional"]
    summary = {
        "functional": (f"{sum(1 for x in func if x['status'] == 'passed')} of {len(func)} behaviour tests passed in the sandbox" if ran else "behaviour tests were not run"),
        "structure": f"{sum(1 for x in reqs if x['kind'] == 'structure' and x['bucket'] == 'demonstrated')} of {sum(1 for x in reqs if x['kind'] == 'structure')} structural requirements found in the code text",
        "explanation": f"{sum(1 for x in reqs if x['kind'] == 'explanation' and x['status'] != 'missing')} of {sum(1 for x in reqs if x['kind'] == 'explanation')} requested explanation topics mentioned (wording only, not verified)"
        if any(x["kind"] == "explanation" for x in reqs) else "this question does not request an explanation",
    }
    notes = list(spec.limitations)
    if not ran:
        notes.append("Because nothing was run, no behaviour has been verified: the code may or may not work.")
    if violations:
        notes.append("Static policy gate: the code was not sent to any execution backend.")
    return {**base, "status": "assessed", "spec": spec.spec_id, "title": spec.title, "answer": ans, "execution": ({**ex.to_dict()} if ex else None),
            "executed": bool(ran), "policy_violations": violations, "requirements": reqs, "buckets": buckets, "bucket_labels": BUCKET_LABELS, "summary": summary, "notes": notes,
            "explanation_text_chars": len(prose)}
