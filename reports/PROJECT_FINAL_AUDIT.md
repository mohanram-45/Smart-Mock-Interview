# SMART-MOCK-INTERVIEW: Project Audit

**Date:** 22 October 2026
**Scope:** read-only audit of `D:\Projects\SMART-MOCK-INTERVIEW`. No files were changed apart from this report. No installs, commits or pushes. Git was queried with `--no-optional-locks`, so the index was not rewritten.

**Evidence.** Facts come from the files, git and the GitHub remote, read on 22 October 2026. Test results quoted from Windows are the owner's own runs (the latest: 880 passed in `tests/app`). Nothing was executed for this audit.

---

## 0. Headline findings

1. **Almost none of the project is on GitHub.**
   - Git tracks 42 files. The working tree has **1,398 untracked files**: the whole `/demo` application, retrieval, evaluation, code-eval, MLOps, all tests, Docker, CI, DVC and docs. There are also 7 modified tracked files.
   - GitHub (`mohanram-45/Smart-Mock-Interview`) has one branch, `main` at `2639cdd` (19 Sep 2026). That is the same commit as local HEAD.
   - The local branch `ci/mlops-stages-6-8` has no upstream.
   - **A recruiter today sees the September legacy app only.**
2. **The engineering underneath is strong.** About 20k lines of Python in `src/`, 1,268 test functions, hash-locked CI, a hardened Docker image, MLflow, DVC, privacy-aware logging and a carefully honest evaluation trail.
3. **The product is split in two.**
   - The legacy app: `/api/*` plus a Node front end, a compare tool, three scorers, and PDF/e-mail reports.
   - The newer `/demo` app, which holds nearly all the AI work.
   - They share a process but not a user journey. The demo has no PDF report; the legacy app has no memory, follow-ups or retrieval.
4. **Three security issues to fix before any push or demo** (section 7.1): a Werkzeug debugger exposed to the LAN, an unauthenticated cross-origin e-mail endpoint, and a real SMTP app password on disk (gitignored).
5. **No AI component is validated against human judgement.** The project says this itself, honestly. Blind review sheets exist but are unrated.

---

## 1. Structure and architecture

```
main/app.py                 Flask entry point: legacy /api/*, registers /demo, /api/retrieval/*, report delivery, /healthz /readyz /metrics
src/demo/        (8.2k loc) Current interview app: blueprint, engine, policy, memory, follow-ups (LLM), behavioural, insights, store, templates
src/retrieval/   (2.0k)     Corpus loader (fingerprints, manifests, quarantine), MiniLM embeddings, FAISS, BM25, evaluation, CLI, Flask API
src/evaluation/  (3.4k)     Modular LLM evaluator (schema, claims, rubric, verification, providers) - experimental
src/codeeval/    (1.6k)     Static code check, declarative specs, optional Docker runner
src/mlops/       (1.3k)     Observability (metrics, JSON logs, health), MLflow tracking/import, version consistency
src/components/  (2.7k)     Legacy adaptive session, data pipeline, feedback, PDF/LLM report generation
src/model/       (1.0k)     Legacy scorers: Sentence-BERT, Siamese Bi-LSTM, TF-IDF+grammar; model_registry
report_delivery/            PDF + Gmail SMTP delivery for legacy reports
frontend/  compare/         Legacy Node UI (port 3000); model comparison tool (port 5050)
data/                       raw/processed (legacy 4,085 Qs); curated v1-v5 + expansion batches (666 Qs used by /demo); retrieval manifests; evaluation sets
tests/                      app 610, evaluation 350, retrieval 139, mlops 90, codeeval 55, ui 24 (test functions)
scripts/                    57 scripts, 41 of them stage-named one-off diagnostics
docs/ reports/ audit/       18 docs, stage reports, dataset audit trail
Dockerfile, docker-compose.yml, .github/workflows/{ci,heavy}.yml, dvc.yaml, params.yaml, pyproject.toml, 9 requirements/lock files
```

**Runtime flow for `/demo`, the main product.** Setup (role, optional job description, interview type) → plan: core questions ranked from the 666-question bank by retrieval (MiniLM+FAISS, or BM25 fallback) plus job-description terms → for each answer:
- Sentence-BERT similarity score;
- optional modular LLM evaluation;
- optional static code check;
- the policy decides the next move: follow-up, next question, wrap-up or time budget;
- memory extracts the candidate's claims;
- a follow-up comes from the curated bank, a mock, or a local LLM with validation and fallback.

Each session is saved atomically as JSON. The summary page and JSON export follow.

---

## 2. Features and where they live

| Feature | Files |
|---|---|
| Flask app, blueprint registration, legacy API | `main/app.py` |
| Interview journey (setup, interview, summary, history, settings, guide, export, delete) | `src/demo/routes.py`, `templates/`, `static/demo.js` |
| Session engine, locking, scoring dispatch, follow-up integration | `src/demo/engine.py` |
| Interview structure and job-description sanitising (injection and PII stripping) | `src/demo/interview.py` |
| Adaptive policy (time budget, follow-up limits, retrieval for follow-ups) | `src/demo/policy.py` |
| Retrieval-ranked question planning | `src/demo/engine.py` (via `src/retrieval/service.py`) |
| Candidate memory (claims with quotes, turn, confidence; TF-IDF or optional SBERT recall; TTL) | `src/demo/memory.py` |
| LLM follow-ups (Stage 10N default; validation, retry, fallback, deadline) | `src/demo/followup_llm.py`, `ollama_stream.py` |
| Objective follow-up engine (Stage 11, flag `SMART_DEMO_FOLLOWUP_ENGINE=objective`) | `src/demo/intel.py` |
| Grounded deterministic follow-ups | `src/demo/grounded.py` |
| Behavioural interviews (STAR evidence, no scores) | `src/demo/behavioural.py`, `behavioural_data/` |
| Feedback insights and summary | `src/demo/insights.py`, `present.py` |
| Session persistence (atomic JSON, retention, Windows retry) | `src/demo/store.py` |
| Question catalogue and role mapping | `src/demo/catalog.py`, `src/components/config.py` |
| Corpus integrity (fingerprints, manifests, freeze) | `src/retrieval/corpus.py`, `scripts/check_integrity.py`, `scripts/check_versions.py` |
| Embeddings, FAISS, BM25, retrieval evaluation, CLI | `src/retrieval/embeddings.py`, `index.py`, `evaluate.py`, `cli.py` |
| Retrieval API and diagnostics (opt-in) | `src/retrieval/flask_api.py` |
| Modular LLM evaluator (opt-in) | `src/evaluation/modular/*`, `src/demo/experimental.py` |
| Code assessment: static check (opt-in), Docker runner (opt-in) | `src/codeeval/*`, `src/demo/codeassess.py`, `docker/codeeval/` |
| Legacy adaptive interview, scorers and report | `src/components/interview_session.py`, `src/model/*`, `src/components/report_generator.py`, `llm_report.py` |
| PDF and e-mail delivery (legacy reports only) | `report_delivery/*` |
| Model comparison tool | `compare/app.py`, `compare/*.html` |
| Observability: `/healthz`, `/readyz`, `/metrics`, JSON access log | `src/mlops/obs.py`, `metrics.py` |
| MLflow history import, provenance and retrieval tracking | `src/mlops/tracking.py`, `historical.py`, `scripts/mlflow_*.py` |
| DVC index build | `dvc.yaml`, `params.yaml` |
| Benchmarks, replays, validator comparison, blind review sheets | `src/demo/opportunity_eval.py`, `question_pairs_eval.py`, `scripts/stage10*_*.py`, `scripts/stage11*_*.py` |
| Launchers and verifiers | `run_demo.bat`, `run_all.bat`, `verify_windows.bat`, `verify_mlops.bat`, `scripts/validate_windows.ps1` |

---

## 3. Integration status

| Status | Features |
|---|---|
| **Integrated, on by default** in the running Flask app | `/demo` journey; retrieval-ranked planning (BM25 when torch/FAISS are absent); Sentence-BERT scoring (needs the model locally); policy and time budget; memory; deterministic follow-ups; behavioural mode; persistence; export; observability endpoints; legacy `/api/*` journey with PDF/e-mail |
| **Integrated but off by default** (environment flag) | LLM follow-ups (`--live-model`, Stage 10N); objective engine (`SMART_DEMO_FOLLOWUP_ENGINE=objective`); modular evaluator (`SMART_DEMO_LIVE_MODULAR`); static code check (`SMART_DEMO_CODE_EVAL`); Docker code runner (`SMART_CODEEVAL_EXEC=docker`); `/api/retrieval/*` (`SMART_RETRIEVAL_ENABLED`); SBERT memory recall (`SMART_DEMO_MEMORY_SBERT`) |
| **Standalone** (separate process or offline) | `compare/` tool; `frontend/` Node UI; MLflow (offline scripts, the app does not log to it); DVC; benchmark, replay and review scripts; `notebooks/EDA.ipynb` |
| **Legacy, unreachable from `/demo`** | Siamese Bi-LSTM and TF-IDF+LanguageTool scorers; legacy 4,085-question knowledge base; `report_delivery` (the demo has no PDF or e-mail) |
| **Experimental, failed or unvalidated** | modular evaluator (failed its gate: abstain 0.45 > 0.40); objective engine (measured 17/23 automatic acceptance on 11.obj4; 11.obj5 unmeasured); evidence band (uncalibrated) |

---

## 4. AI/ML, RAG, evaluation, follow-ups, memory, reporting, MLOps

- **Models.**
  - Sentence-BERT `all-MiniLM-L6-v2`: scoring, retrieval and optional memory recall.
  - Siamese Bi-LSTM (`results/siamese_bilstm.pt`, tracked binary) and TF-IDF+grammar: legacy only.
  - Ollama `llama3.2:3b`: follow-ups (default, provisional).
  - Ollama `qwen2.5:7b`: modular evaluator and the legacy LLM report (`OLLAMA_MODEL`).
  - No training happens at request time (`SMART_FORBID_MODEL_TRAINING`).
- **RAG.**
  - The retrieval half is real: a corpus with integrity checks, MiniLM embeddings, exact FAISS `IndexFlatIP`, BM25 fallback, diagnostics with provenance, and a DVC-rebuildable index.
  - Retrieval drives question planning and follow-up context in `/demo`.
  - There is **no retrieval-augmented grading**: the similarity scorer compares against one reference answer.
  - Benchmarks use AI-pooled labels: success@1 is 0.71 on dev and 0.63 on the frozen challenge set. There is no human relevance set.
- **Evaluation.**
  - Similarity score: not validated.
  - Modular LLM rubric with claim verification: experimental, failed its gate.
  - Static code check.
  - Follow-up benchmark: 23 scored opportunities, frozen labels and fixture hash, rule audit, old-vs-new validator comparison, blind sheets (unrated).
- **Follow-ups.**
  - Hybrid design: code owns the decision, the LLM only words the question, rule validators gate it, there is one retry, then a curated fallback, under a deadline.
  - The validators are word- and regex-level (`followup_llm.py`, about 1.5k lines; `intel.py`, about 1.3k lines).
- **Memory.** Per-session candidate claims with verbatim quotes, turn and confidence, a "never verified" status, 14-day TTL, provenance owned by code. Isolated per session and deleted with it.
- **Reporting.**
  - `/demo`: summary page (digest, coverage, improvement areas, behavioural feedback) and JSON export.
  - Legacy: JSON report, LLM or rule-based coaching, PDF, Gmail.
- **MLOps.**
  - Prometheus-style `/metrics` and JSON logs with no candidate text.
  - MLflow store (`mlflow/mlflow.db`) with 30 historical runs / 642 metrics imported.
  - DVC `build_index` stage; version-consistency checks; hash-locked CI dependencies; Dependabot.

---

## 5. Tests, Docker, CI/CD, deployment readiness

- **Tests.** 1,268 test functions across six suites.
  - Includes golden characterisation of the legacy app, hermetic report tests, real-browser journeys (Playwright, run by the heavy workflow) and publication-safety tests.
  - Many tests are named by stage (`test_stage10n_*`) rather than by feature.
- **Docker.**
  - Lean, non-root image (uid 10001) on Python 3.13-slim, served by waitress, read-only filesystem, healthcheck.
  - Compose binds to loopback only, has an optional Ollama profile, and drops capabilities.
  - The lean image has **no torch**, so Sentence-BERT scoring and FAISS are unavailable in the container unless built with `INSTALL_ML=1` (unverified). The base image is pinned by tag, and the Docker lock is not hash-checked.
- **CI.**
  - `ci.yml`: lint, integrity, tests on 3.12/3.13, MLflow, a Windows smoke job, Docker build and health, and a single gate job. `heavy.yml` runs weekly (real MiniLM, browser journeys, ML image).
  - Actions are pinned by SHA with least-privilege permissions.
  - **Never run on GitHub, because `.github/` is untracked.** Every path it references exists locally.
  - Stage 11 tests are covered (they're in `tests/app`), but the Stage 11 scripts are not.
- **Deployment readiness: local single-user only**, as documented in `docs/MLOPS.md` §8:
  - no authentication, TLS, rate limiting or CSRF;
  - legacy sessions held in memory;
  - session JSON (candidate answers) unencrypted;
  - no vulnerability scanning.

---

## 6. Git status

| Item | State |
|---|---|
| Current branch | `ci/mlops-stages-6-8` (no upstream). Local `main` tracks `origin/main` |
| HEAD | `2639cdd Add project documentation`; identical to GitHub `main` (checked with `git ls-remote`); last fetch 19 Sep |
| Tracked | 42 files (legacy app, `data/raw`, `data/processed`, `data/interim`, `frontend`, `compare`, `notebooks`, `report_delivery`, `results/siamese_bilstm.pt`) |
| Modified, tracked (7) | `.gitignore`, `README.md`, `main/app.py`, `requirements.txt`, `run_all.bat`, `src/components/interview_session.py`, `src/model/model_registry.py` (+308 / −230 lines) |
| Untracked | 1,398 files. Largest: `data/curated` (11.7 MB), `data/retrieval` (8 MB), `data/expansion` (6.6 MB), `docs/screenshots` (6.2 MB), `reports/stage2b_final_benchmark.json` (4.8 MB), `.claude/skills` (4.1 MB, 172 files), `audit/expansion` (4 MB) |
| Ignored | `.bot/`, venvs, caches, `tmp/`, `Temp/`, `output/`, `results/demo_sessions` (2 sessions on disk), `results/reports` (8), `mlflow/`, `report_delivery/.env`, `dataset_upgrade_prompt.md`, FAISS/model binaries, DVC cache |
| Not ignored but should be | `.claude/` (third-party agent skills; would be committed by `git add .`) |
| Secrets in history | none found: only the placeholder `SMTP_PASSWORD=your-app-password` appears |

---

## 7. Bugs, incomplete work, technical debt, security

### 7.1 Security (fix first)

1. **`compare/app.py:177`** runs `app.run(host="0.0.0.0", port=5050, debug=True)` and is started by `run_all.bat`. The Werkzeug debugger allows remote code execution from anyone on the same network. Bind to `127.0.0.1` and set `debug=False`, or retire the tool.
2. **Legacy `/api/*`** has CORS `origins: "*"` and no authentication.
   - `POST /api/reports/<id>/email` sends a report PDF through the owner's Gmail to **any** address.
   - Interview ids are a timestamp plus 6 hex characters (24 bits), so they are guessable within a time window.
   - Any website open in the same browser could trigger it. Restrict CORS to the local front end, require a same-origin token, and lengthen the ids.
3. **`report_delivery/.env`** holds a real Gmail app password in plain text. It is gitignored and excluded from Docker (`.dockerignore`), but it is a live credential. Rotate it if it was ever shared, and prefer environment variables.
4. Session JSON files hold candidate answers unencrypted (documented). History pages are loopback-only by default (good).
5. Lower-bound unpinned `requirements.txt` for the legacy app; no `pip-audit`/CodeQL/Trivy; Docker lock not hash-checked.

### 7.2 Bugs and incomplete work

- **Docs out of date.**
  - The README and `docs/ARCHITECTURE.md` say the demo "does not use vector search" and "does not adapt", with "3/5/8 questions" and a fixed Easy→Hard pattern.
  - `engine.py`/`policy.py` now rank questions by retrieval, adapt on time budget and answers, and plan intro / 5 core / follow-ups / practical / wrap-up.
- The interview length (`time_budget_min`) is accepted by the API but not offered in the UI; the default is 45 minutes.
- The Docker image cannot run the default scorer (no torch). The container shows "similarity unavailable" unless built with `INSTALL_ML=1` (unverified).
- The objective engine's 11.obj5 is unmeasured on Windows; blind review sheets (Stage 11T/11U) are unrated.
- Stage 8C reported 7 Windows failures as "fixed, needs re-run"; the Windows `tests/app` suite has since passed (880).
- Modular evaluator: failed gate, still shipped behind a flag.
- `results/siamese_bilstm.pt` is a tracked binary for a scorer the current app doesn't use.

### 7.3 Technical debt

- **Two products in one repo** (legacy `/api` + Node front end + compare tool, and `/demo`) with duplicated concepts: sessions, scoring and reports.
- **Very large rule modules.** `followup_llm.py` (1,477 lines) and `intel.py` (1,265) hold hundreds of regexes, with a circular import (`followup_llm` imports `intel` inside functions). Word-level validators can be gamed by rewording, and the "ignores objective" check rejects about half of good scenario questions.
- **Clutter.** 41 stage-named scripts and stage-named tests; nine requirements/lock files; curated v1–v4 superseded by v5; `Temp/`, `output/` and `tmp/` in the working tree.
- **Lint.** Repo-wide ruff runs only correctness rules (`E9,F63,F7,F82`); strict rules apply to MLOps files only.
- **MLflow** is fed by offline import scripts, not by benchmark runs as they happen (except `stage10_verify_real_stack.py`).

---

## 8. Recommendations (existing code first)

### P0: make it visible and safe (one to two days)

1. Fix the three security items in 7.1. Add `.claude/` to `.gitignore`.
2. **Get the work onto GitHub properly.**
   - Follow `docs/GITHUB_FIRST_PUSH.md`.
   - Decide what is public (keep `data/curated/v5`, expansion, manifests and evaluation sets; drop or archive v1–v4, bulky transcripts, `.claude/`).
   - Commit in logical commits on a feature branch, open a PR so CI runs for the first time, fix whatever fails, then merge.
3. Refresh the README and ARCHITECTURE: one accurate diagram of the current flow, an honest results table (retrieval success@1, follow-up acceptance with "automatic, not human-rated", test counts), screenshots, and a CI badge.

### P1: one coherent product (about a week)

4. Make `/demo` the application.
   - Move the legacy `/api` app, `frontend/`, `compare/`, the Bi-LSTM/TF-IDF scorers and the 4,085-question base into `legacy/`, or keep them only on a tagged release.
   - Port the **existing** `report_delivery/pdf_generator.py` into the `/demo` summary (PDF download). Keep e-mail off by default.
5. Expose the existing `time_budget_min` and follow-up mode on the setup page.
6. Consolidate dependencies into `requirements.txt` (app), `requirements-ml.txt` and `requirements-dev.txt`, plus the existing locks. Hash-lock the Docker lock.
7. Archive the one-off `stage*` scripts. Keep a small CLI set: `eval`, `compare`, `review-sheet`, `verify`, `check_integrity`. Rename tests by feature.
8. Split `followup_llm.py` and `intel.py` into `prompting`, `validation_rules`, `attribution` and `engine` modules. Remove the circular import. Extend strict ruff to `src/demo`.

### P2: credibility as a Data Science/AI Engineering project

9. **Human evaluation with what already exists.**
   - Rate the blind sheets (two raters if possible), report agreement and validator precision/recall against the ratings, and publish the confusion matrix.
   - Label about 100 retrieval queries by hand and rerun the existing `src/retrieval/evaluate.py`.
   - This turns every "AI-labelled / not validated" caveat into a measured result.
10. **Use the Sentence-BERT model already in the project** for the follow-up engagement check and for semantic scoring of key concepts. Calibrate thresholds on the existing pair sets. This removes the biggest false-rejection source without new technology.
11. Run the Windows real-model benchmark for 11.obj5, then adopt or retire the objective engine on the evidence. Retire the modular evaluator from the UI if it stays below its gate.
12. Log every benchmark and evaluation run to the existing MLflow store, with params, prompt version and metrics, and include an MLflow comparison screenshot in the README.
13. Verify the `INSTALL_ML=1` image, so the container actually scores answers. Add `pip-audit` to CI (small, existing ecosystem).

### Remove

- `compare/` (or reduce it to a notebook).
- `frontend/` once the legacy app is archived.
- `results/siamese_bilstm.pt` from git.
- `data/curated/v1–v4` (keep v5 plus manifests).
- `Temp/` and `dataset_upgrade_prompt.md`.
- Stage-named diagnostics (archive them).
- The duplicated report paths.

### Add (only where it closes a gap)

- A short "Results and limitations" page with the human-rated numbers.
- A 2-minute demo GIF from the existing screenshots and journeys.
- A tagged release (`v1.0`) once CI is green on GitHub.

---

**Bottom line.** The code is well ahead of what anyone can see. The highest-value next steps are:
1. fix three local security issues;
2. publish the work through a reviewed PR so CI runs;
3. collapse the two apps into one `/demo` product;
4. replace the "not validated" caveats with a small human-rated evaluation, using the review sheets, evaluation harness and Sentence-BERT model the project already has.
