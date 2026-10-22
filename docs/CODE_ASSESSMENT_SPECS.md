# Declarative code-assessment specs (Stage 8B)

The code check (`src/codeeval`) has two hand-written question specs (NumPy pairwise squared distances; linear regression from scratch). Their structure and explanation checks are
Python functions and each has its own hard-coded behaviour-test function. That does not scale to a third question, so Stage 8B adds a **data format** and a generic test runner.
No spec for a real interview question ships in this format yet, and no new question bank was generated: only a documentation example (`src/codeeval/examples/example_clamp.json`).

## The layers (unchanged, kept apart)

| Layer | File | Runs candidate code? | Produces |
|---|---|---|---|
| Extraction | `extract.py` | no | code vs prose |
| Static analysis | `static.py` | no (`ast` parse only) | structure facts, policy violations |
| Functional test specification | spec file / `spec.py` | no (data) | which behaviours should hold |
| Execution result | `runner.py` + `harness.py` | **only inside an isolated container, only if enabled** | passed / failed / error per case |
| Explanation requirements | `topic` entries | no | "mentioned (wording only)", never "verified" |
| Unverified findings | `evaluate.py` | no | everything that could not be established |

There is **no score** and the legacy similarity score is never an input. A requirement lands in exactly one of five buckets: verified correct / demonstrated in the code text / missing / incorrect / unverified.

## Format (schema 1)

```json
{"schema": 1, "spec_id": "example_clamp/1", "question_id": "example-clamp", "title": "...", "limitations": ["..."],
 "requirements": [
   {"id": "f_below", "kind": "functional", "label": "clamp(-3, 0, 10) returns 0",
    "case": {"function": "clamp", "args": [-3, 0, 10], "expect": {"equals": 0}}},
   {"id": "s_noloops", "kind": "structure", "label": "No loops in clamp()", "rule": {"type": "function_has_no_loops", "function": "clamp"}},
   {"id": "e_edge", "kind": "explanation", "label": "Explains low > high", "topic": [["low\\s*>\\s*high", "reversed"], ["error", "raise"]]}]}
```

- **functional** `case`: `function`, optional `args`/`kwargs` (JSON literals only), optional `args_unchanged`, and exactly one `expect`: `equals`, `approx` (with `rtol`/`atol`), `raises` (ValueError, TypeError, ZeroDivisionError, IndexError, KeyError) or `returns_type`.
- **structure** `rule.type`: `defines_function`, `function_calls_any`, `function_has_no_loops`, `class_defines_methods`, `imports_module`. A fixed whitelist; each reads the `ast` report only.
- **explanation** `topic`: 1-6 groups of alternative phrases; all groups must match for "mentioned". Patterns are length-capped and nested-quantifier patterns are rejected.
- Unknown keys, non-literal values, NaN/inf, duplicate ids and oversized cases are rejected with a message naming the requirement.

Load with `src.codeeval.declarative.load_spec_file(path, register_it=True)`. Nothing is loaded automatically.

## Safety (unchanged rules)

- The loader parses JSON and builds closures over the whitelist. It never evaluates anything (a test checks it imports neither the runner nor the harness and calls no `exec`/`eval`/`compile`/`open`).
- Cases reach candidate code only through the existing sandbox path: `DockerRunner` sends the harness, the candidate source and the cases on **stdin**; the command line carries none of them (tested).
- Static-only remains the default. The static policy gate still refuses forbidden imports/constructs before any backend sees the code. Flask never executes candidate code.
- A normal Docker container is **not** a production-grade sandbox (`CODE_EXECUTION_SECURITY.md`). Do not enable execution for code from strangers.
- The generic harness shares one interpreter with the candidate (as the existing harnesses do): hostile code could tamper with its own results. Passing cases proves only those inputs.

## Adding a question

1. Write the JSON (3-8 functional cases including an edge case, 2-4 structure rules, 1-3 explanation topics) and a `limitations` list that says what the cases do *not* cover.
2. Have someone else read it: the cases are the definition of "correct" for that question.
3. `spec_from_dict` / `load_spec_file` must accept it; add one known-good and one known-bad fixture to the tests and run them through the test-only `TrustedLocalRunner`.
4. Behaviour verification in the real container still needs Docker on your machine (`verify_windows.bat --docker-sample`); until then the findings say *not run*.
