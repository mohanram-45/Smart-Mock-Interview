# Stage 8A + 8B consolidated report: MLOps verification, retrieval evidence, evaluator safeguards, code-assessment specs

Date: 2026-10-17. Nothing was committed, staged, pushed, published or uploaded; repository visibility and Git history are untouched; no dataset or checkpoint left the machine.
Nothing was trained or downloaded; Ollama/Qwen was not run; no paid API was used. Frozen datasets and the frozen **DO NOT ADVANCE** evaluator result (abstain rate 0.45 > 0.40)
are unchanged. **Nothing in this project is validated against human graders.**

## 0. Verdict

| Mission | Status |
|---|---|
| A. Windows / Docker verification | **Not executed on Windows.** This session reaches your computer only through a Linux shell on the mounted project folder (no PowerShell, Docker Desktop or Windows Python). Exact commands are in section 9. |
| A. CI readiness | **Ready, simulated only.** Every CI job's commands pass on a fresh clone made with `core.autocrlf=true` (Linux, Python 3.12, hash-locked deps). GitHub Actions has never run. |
| A. MLflow / DVC | **Extended and verified on Linux**: version-mismatch checker, live retrieval tracker, DVC/served-format defect fixed. Real MiniLM through DVC or the tracker is not verified (no model in the sandbox). |
| B. Retrieval | Audit done; **evidence band, provenance, truncation coverage and a diagnostics endpoint implemented**; a reranker was tested offline and **rejected**. |
| B. Evaluator | Two input-handling safeguards and a provider circuit breaker added; a validation protocol written. **No accuracy claim; real evaluator still fails its frozen criterion.** |
| B. Code assessment | Declarative spec format and generic test runner added; layers kept apart; static-only stays the default. One documentation example, no new question bank. |
| C. Application | Flask app unchanged in behaviour by default; browser run 16/16 on the sandbox. |
| D. Tests | 963 passed, 7 skipped, 0 failed in the sandbox (details in section 7). |

## 1. Windows MLOps verification status

Not run on Windows, so none of the ten checks in the request is claimed there. What exists:

* `scripts/validate_windows.ps1` (ASCII, CRLF) gained section 3c, which runs `scripts/check_versions.py`. Under PowerShell 7 on Linux (paths adapted) the script's `-Mlflow -Dvc` sections were exercised in the earlier stage; they were not re-run on the final tree here (see section 7).
* Linux evidence only: dependency set, MLflow 3.17.1 import/idempotency, DVC `repro`/`status`/`checkout` (6/6), fingerprints (`INTEGRITY OK`).
* Unverified until you run it: Windows Python/dependency resolution, Docker Desktop, the official `python:3.13-slim-bookworm` build, Compose start, health/readiness/metrics in a container, session persistence across a container restart, real-MiniLM behaviour.

## 2. GitHub CI readiness

Simulation: the publish candidate was rebuilt **from your device** after syncing the Stage 8 files (1008 files, 42 tracked), committed to a scratch repository and cloned with `core.autocrlf=true`.

| CI step | Result in the simulation |
|---|---|
| Candidate files all committed; CRLF-pinned files keep their bytes; LF files stay LF; `.bat`/`.ps1` stay CRLF | pass |
| Ruff lint (`src main scripts tests report_delivery`) and format check on the strict lists | pass after one import-order fix in a new test (the simulation caught it) |
| `check_integrity.py` | INTEGRITY OK |
| Tests: retrieval 149 passed / 1 skipped; evaluation 443; app 199 / 5 skipped; codeeval 72 / 1 skipped; mlops 99 passed + 1 failed | the one failure was `test_documentation_links_and_referenced_commands_exist`: README links this report, which did not exist yet. It exists now (see section 7) |
| mlops job (`test_tracking.py`) | 14 passed |
| Lean "windows" job (no MLflow): integrity, tests, `verify_mlops.py` | same single README-link failure; `verify_mlops`: 12 PASS, 3 SKIP, nothing failed |
| `check_staged.py --worktree` | PUBLICATION CHECK OK |
| `verify_dvc.py` | ALL PASSED (6 checks, now with the served `qk_concise` format) |
| Compose file valid; no zip/db/faiss in Docker COPY dirs; tests left the tree clean | pass |

Workflow: one required **`CI gate`** job, minimal permissions, locked deps, no GPU/Ollama/paid APIs. Stage 8 added `check_versions.py` to the integrity job and two new scripts to the strict lint lists.
First-PR procedure: `docs/GITHUB_FIRST_PUSH.md` (step 0 now includes `check_versions.py`; five commit groups; push and PR steps are marked **[PUBLISHES]** and need your approval).
**Not verified: any real Actions run**, the official Docker base build, branch-protection settings.

## 3. MLflow / DVC reproducibility

* **Defect found and fixed:** `params.yaml` declared `doc_mode: qka`, but the served retrieval format is `qk_concise`. `dvc repro` would have built an index the app does not serve, and the CLI had no way to build the served format. Fixed (`params.yaml`, `cli.py --doc-mode` incl. `qk_concise`), guarded by tests.
* **Mismatch detection:** `src/mlops/consistency.py` + `scripts/check_versions.py` (read-only, exit 1 on any FAIL). Checks: manifest vs loaded corpus; DVC `doc_mode` and model vs the served ones; each built index vs the current corpus and its recorded file hash; frozen challenge queries unchanged; stored Stage 2C rankings vs the corpus. Skips are listed, not hidden.
* **Tracking future runs:** `scripts/mlflow_track_retrieval.py` computes retrieval metrics live on the existing eval sets and logs the model/doc-mode/params, corpus and index fingerprints and the code version. It refuses to log on a version mismatch unless `--allow-mismatch`, and supports `--dry-run`. Runs are tagged as live runs, separate from imported history.
* **History:** the historical import (30 runs / 642 metrics, idempotent) is unchanged and remains labelled as imported, not as new training.
* **Not verified:** the tracker and `dvc repro` with the real MiniLM model (offline `dev-lsa` stand-in only); remote storage is deliberately absent.

## 4. Retrieval improvements implemented

Audit (evidence = stored Stage 2C MiniLM rankings; labels are AI-pooled, not human):

| Finding | Status |
|---|---|
| MiniLM reads only 256 word-pieces. 31 records have a head (question + key concepts) that alone exceeds that, and 15 have a first answer sentence that is cut | **Documented, not changed.** Changing the document format alters index fingerprints and cannot be verified offline; needs your MiniLM experiment (section 9) |
| Hybrid/BM25 fusion showed no consistent gain | Not adopted; BM25 stays a fallback and an informational agreement signal |
| Key-concept reranker | **Tested and rejected**: success@1 0.712 to 0.699 on the dev set, no weight helped (`reports/stage8_retrieval_probe.json`) |
| `params.yaml` / served-format mismatch | Fixed (section 3) |

Implemented (`src/retrieval/evidence.py`, `service.diagnose`, `POST /api/retrieval/diagnostics`): a descriptive **evidence band** (insufficient < 0.40, weak < 0.45, adequate), explicitly uncalibrated and never used to hide results (it caught 19/20 dev and 10/18 challenge no-answer queries but also 4/146 and 1/40 answerable ones, so it is a hint only); per-hit **provenance** (question id, origin, corpus fingerprint, indexed format); **embedding coverage** per record; semantic-vs-BM25 **agreement**; and a `versions` block (corpus, embedder, doc mode, index hashes, FAISS). Diagnostics rows contain identifiers and scores only, never question text, reference answers or key concepts. The stable `search()` API is unchanged.

## 5. LLM evaluation safeguards

`src/evaluation/modular/safeguards.py` (wrapper; frozen pipeline untouched; version `8b.1`), found by probing with synthetic inputs, not by tuning on the 20-answer benchmark:

1. **Hidden instructions** (soft hyphens, Cyrillic look-alikes, line breaks inside the phrase) previously evaded the injection detector; such answers now abstain with `possible_hidden_instruction`.
2. **Truncated answers** (> 20,000 chars) previously still produced a number; the score is now withheld (`answer_truncated_not_fully_assessed`).
3. **Provider failures:** `ProviderCircuitBreaker` in `src/demo/experimental.py` stops a dead local model server from holding every queued answer for its full timeout; failures show as "unavailable", never interrupt the session.

Audit conclusions without code change: unverified evidence is already kept separate from incorrect; numeric grades remain disabled where eligibility or evidence is insufficient; LLM scores do not feed adaptive difficulty. Not a complete injection defence (letter-by-letter spacing is not detected). Tested with scripted mock verifiers only. `docs/EVALUATOR_VALIDATION_PROTOCOL.md` is a plan (fresh sample, two independent reviewers, agreement first, freeze then run once, pre-registered criteria); it contains no invented labels.

## 6. Code-assessment engineering

* `src/codeeval/declarative.py`: JSON specs (schema 1) for functional cases plus structure rules (`defines_function`, `function_calls_any`, `function_has_no_loops`, `class_defines_methods`, `imports_module`) and explanation topics. Strict validation: unknown keys rejected, literal-only case values, length/count limits, an allowlist for expected exceptions, regexes length-capped with nested quantifiers refused.
* A generic harness id `declarative_cases` runs the cases; the existing NumPy-distance and linear-regression specs and their hard-coded harnesses keep working (tests unchanged and passing).
* Layers stay separate (static, spec, execution result, explanation, unverified; similarity is never an input). Output buckets: verified correct / demonstrated in code text / missing / incorrect / unverified.
* Safety: static-only remains the default; nothing runs candidate code in the Flask process; execution needs the explicit opt-in and the isolated container. **A normal Docker container is not a production sandbox**, and the generic harness shares an interpreter with candidate code as the existing harnesses do. No public arbitrary-code execution; no correctness claim without verified execution.
* One documentation example (`example-clamp`); no question bank. `docs/CODE_ASSESSMENT_SPECS.md` explains the format.
* Not verified: the generic harness inside the real Docker runner.

## 7. Tests: passed, failed, skipped

| Run | Result |
|---|---|
| Sandbox, Python 3.12 from `requirements-ci-mlops.lock`, full suite | **963 passed, 7 skipped, 0 failed** |
| Device-derived clone simulation (section 2) before this report existed | retrieval 149/1 skipped, evaluation 443, app 199/5 skipped, codeeval 72/1 skipped, mlops 99 + 1 failed (README link to this report), mlops job 14 |
| Skips | 7, all environmental (no Hugging Face model cache, no Docker daemon, and similar) |
| Browser (Playwright/Chromium, sandbox) | 16/16 checks |

New tests: `test_stage8_evidence.py`, `test_stage8_safeguards.py`, `test_stage8_declarative.py`, `test_stage8_consistency.py`. After the last fix (a test import order and this report) the full simulation has **not** been re-run end to end; re-run it or the commands in section 9 before relying on the numbers.

## 8. Docker and application verification

* Static only: compose file valid; `.dockerignore` keeps zip/db/faiss/sqlite out of the build context; tests leave the tree clean.
* Flask app: legacy scoring default, experimental evaluation opt-in, code formatting preserved, failed evaluations do not stop sessions; browser run 16/16 on the sandbox. Monitoring endpoints expose no answers or reference material (covered by the existing privacy tests).
* **Not run:** a real Docker build on the official base image, Compose start, `/healthz` `/readyz` `/metrics` in a container, restart persistence. No Docker daemon exists here.

## 9. Exact PowerShell commands requiring your action

```powershell
cd D:\Projects\SMART-MOCK-INTERVIEW
# 1. Fast checks (no Docker, nothing downloaded)
python scripts\check_integrity.py
python scripts\check_versions.py
python scripts\check_staged.py --worktree
python scripts\stage8_retrieval_probe.py --check
# 2. Dependencies for MLflow/DVC
pip install -r requirements-mlops.txt
pip install "dvc>=3,<4"
python scripts\verify_dvc.py
# 3. Full Windows validation (builds the real python:3.13-slim-bookworm image; Docker Desktop must be running; binds 127.0.0.1:5099)
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Mlflow -Dvc -Docker -Tests
python scripts\verify_compose.py
# 4. Real MiniLM run tracked in MLflow (needs the model already in your Hugging Face cache; no download)
python scripts\mlflow_track_retrieval.py --backend minilm --local-files-only --dry-run
python scripts\mlflow_track_retrieval.py --backend minilm --local-files-only
# 5. Only after approving it yourself: the first-PR procedure in docs\GITHUB_FIRST_PUSH.md (steps marked [PUBLISHES] publish)
```
Send me the output of steps 1 to 4 and I will fix what they report. The 8A files were synced to your folder; backups of the 20 overwritten files are in `tmp\stage8_backup\`.

## 10. Remaining blockers and next milestone

Blockers: Windows/Docker Desktop verification; a first real GitHub Actions run (needs your approval to push); real-MiniLM verification of DVC and the tracker; the 31/15 truncated-document records (needs a MiniLM re-index experiment, which changes index fingerprints); human-validated evaluator accuracy (needs two independent reviewers); code assessment still covers only two shipped question types plus one example.

Maturity: **implemented** (all items above); **experimentally verified** (retrieval evidence on stored rankings, CI jobs on a Linux clone, DVC reproducibility with the stand-in embedder); **production-ready**: none of the evaluator, code-assessment execution or Docker deployment.

Next milestone: run section 9 on Windows, fix findings, then approve the first push/PR and confirm the `CI gate` is green on GitHub; after that, collect the human-labelled evaluator sample per the protocol.
