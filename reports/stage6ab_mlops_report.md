# Stage 6A + 6B consolidated report: MLOps packaging, tracking, CI, Docker, monitoring

Date: Thu 2026-10-15. Scope: MLflow tracking, data/model versioning, GitHub Actions CI, Docker packaging, monitoring, reproducible local deployment, validation.
Not done (by instruction): no new questions generated, no Qwen/Ollama run, no model download, no paid API, no frozen file modified, no experimental score used for adaptive difficulty,
no public deployment, no candidate code executed.

## 1. Verdict

All seven missions are implemented and verified **as far as the sandbox allows** (Linux, Python 3.13, a real Docker 29.8 daemon without Docker Hub access, DVC 3.67, MLflow 3.17).
Nothing was run on Windows, on GitHub, on Docker Desktop, or with the real MiniLM / Ollama. Those items have exact commands in section 9. The frozen Stage 3C-2 result
(**DO NOT ADVANCE**, abstain rate 0.45 > 0.40) is preserved byte for byte and carried into MLflow as a tag. No accuracy, benchmark improvement or security guarantee is claimed.

## 2. What was built

| Mission | Deliverable | Where |
|---|---|---|
| 1 MLflow | tracker, importer, verifier, live-run helper; 30 imported runs; provenance snapshot | `src/mlops/{tracking,historical,verify,version}.py`, `scripts/mlflow_import_history.py`, `scripts/mlflow_log_provenance.py`, `requirements-mlops.txt` |
| 2 Versioning | integrity gate reusing the project's controls; one DVC stage; checkpoint tracking recipe; reproduction guide | `scripts/check_integrity.py`, `dvc.yaml`, `params.yaml`, `docs/REPRODUCIBILITY.md` |
| 3 CI | normal PR workflow (lint, integrity, tests 3.12/3.13, MLflow, Docker) + separate manual/weekly heavy workflow | `.github/workflows/ci.yml`, `heavy.yml`, `requirements-ci.txt`, `pyproject.toml` |
| 4 Docker | lean non-root image, pinned lock, healthcheck, Compose with optional Ollama profile, env example | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example`, `requirements-docker.{in,lock}`, `requirements-docker-ml.txt` |
| 5 Monitoring | privacy-safe counters, JSON access log, `/healthz` `/readyz` `/metrics`, build identification | `src/mlops/{metrics,obs}.py`, hooks in `src/demo/engine.py`, `main/app.py`, `src/retrieval/flask_api.py` |
| 6 Deployment | Windows verify script and launcher, health probe, docs | `scripts/verify_mlops.py`, `verify_mlops.bat`, `scripts/healthcheck.py`, `docs/MLOPS.md`, README, CONFIGURATION, TROUBLESHOOTING, ARCHITECTURE section 9 |
| 7 Validation | 50 new tests, browser smoke script, this report | `tests/mlops/`, `scripts/stage6b_browser_smoke.py` |

One behavioural addition to existing code, opt-in and off by default: `SMART_FORBID_MODEL_TRAINING=1` makes the legacy Bi-LSTM adapter raise instead of training when no checkpoint
exists (`src/model/model_registry.py`). Unset, legacy behaviour is unchanged (a test asserts both). The Docker image and compose file set it.

## 3. MLflow (Mission 1)

* **30 runs imported, no model run:** 25 Stage 2C retrieval runs (5 evaluation sets x 5 systems), 4 Stage 3B evaluation runs (llama3.2:3b x2, qwen2.5:7b x2, n = 5-12 calls each), 1 frozen Stage 3C-2 run (qwen2.5:7b, 20 answers).
* **Reproduction check:** `scripts/mlflow_import_history.py --verify` re-reads every source file and compares **642 metrics** exactly: all match. A second run creates nothing (idempotent).
  A tampered metric and a changed source hash are both detected (tests).
* **Labelling:** every imported run has `smart.provenance=imported_historical`, source path + sha256, a note beginning "IMPORTED HISTORICAL RESULT", `smart.human_validated=false`; retrieval labels are tagged AI-authored / not human-validated.
  The 3C-2 run carries `smart.decision=DO NOT ADVANCE` and the failed criterion (`criterion_abstain_rate_max_pass = 0`). No accuracy or human-agreement metric exists in the store (test).
* **Tracked per the brief:** retrieval configuration and benchmarks; embedding model and library versions; FAISS index fingerprints (recorded and freshly computed); evaluator implementation versions; provider/model configuration; schema-validity, evidence-verification (gate downgrades) and abstention rates; latency; every acceptance-criterion result.
* **Stored outside Git:** `mlflow/` (SQLite + artifacts) is git-ignored and rebuilt by the importer; only small result files (<= 5 MB) are attached as artifacts.
* **Gaps stated, not filled in:** the Hugging Face model *revision* was never recorded in the Stage 2C file, so it is stored as "not recorded". Observation: the 3C-2 `results.json` records the **v1** freeze-manifest hash (`c54546b6...`) although the run used the v2 tooling; the v2 manifest says it supersedes v1 and both hashes are stored side by side as parameters. Nothing was edited.

## 4. Data and model versioning (Mission 2)

* Audit result: the existing controls (hard-coded frozen v5 fingerprint, per-batch fingerprints, corpus manifest sha256 values, freeze manifest v2, bench_v2 manifest, index metadata) are sufficient and were **reused**; `scripts/check_integrity.py` runs them together: **INTEGRITY OK, no drift**. 666 unique question ids.
* Scope decision: corpus, manifests and frozen evaluation data stay in Git (small, already fingerprinted). DVC is used only for the git-ignored derived binaries (FAISS indexes + embedding cache, one stage) and model checkpoints (`dvc add`).
* DVC evidence (3.67): the stage ran (integrity check then build), `dvc status` was clean, deleted outputs were restored by `dvc checkout`, and the rebuilt `index.faiss` hash equals the repository's recorded hash (dev-LSA backend). A 1 MB stand-in checkpoint round-tripped through `dvc add/push/pull` with identical hash. **Not run:** the stage with real MiniLM (model not available offline); bit-for-bit equality across machines is not claimed for MiniLM.

## 5. CI (Mission 3)

`ci.yml`: lint (correctness rules repo-wide; strict rules + `ruff format --check` on new files only, because legacy/frozen files must not be reformatted), integrity, tests on Python 3.12 and 3.13 (retrieval, evaluation, Flask integration, static code-evaluation, MLOps), MLflow tests, Docker (compose validation, image build, start on loopback, health, non-root and no-secret checks).
No GPU, no live Ollama (pointed at an unreachable address), no secrets referenced, no model download (HF offline), candidate code never executed. `heavy.yml` (manual/weekly only) holds the torch/sentence-transformers/Playwright/ML-image work. Tests assert these properties from the YAML. `actionlint` is clean (it caught one real YAML error in my first draft). **The workflows have never run on GitHub.**

## 6. Docker (Mission 4)

Verified with a real daemon, on a **substitute Python 3.13 base** I assembled locally because Docker Hub, GCR and ECR were blocked in the sandbox (so the exact `python:3.13-slim-bookworm` tag was not built):
the Dockerfile builds (lock installed, 456 MB image); the container runs as uid 10001 with a read-only root filesystem, `--cap-drop ALL`, `no-new-privileges`; HEALTHCHECK reports `healthy`; `/demo` returns 200; `/readyz` ready; no secret-like environment variables; `/app/src` is read-only and `/app/results` writable; a session survives `docker rm` + a new container on the same volume; `docker compose config` and `docker compose up --no-build` work (healthy, `127.0.0.1:5000->5000`, read-only, caps dropped, every experimental flag off, `SMART_CODEEVAL_EXEC` absent).
Safe by construction: no Docker client or socket in the container, no host mounts, no credentials, no weights, `SMART_FORBID_MODEL_TRAINING=1`, loopback-only publishing, Ollama optional (profile, unpublished). **Not verified:** the real base tag, Docker Desktop on Windows, `INSTALL_ML=1`, the Ollama profile, reachability through the published port (the sandbox kernel disables IP forwarding).

## 7. Monitoring (Mission 5)

Counters: requests and latency by route template; interviews started/completed (demo and legacy); answers submitted; scorer failures (load/score) and unavailable events; retrieval failures; experimental evaluations by outcome and abstentions; code assessments by outcome; sessions deleted; model-availability gauge; build-info (version, commit, pipeline, freeze). Endpoints `/healthz`, `/readyz`, `/metrics` (JSON or Prometheus text); legacy `/health` unchanged.
**Retrieval fallbacks are not counted because the project has none by design** (a failing curated source returns 503). Privacy: tests post a hostile answer and assert that logs, `/metrics` and `/healthz` contain neither it nor any session id or query string; label values are sanitised and capped; only registered metric names are accepted. Real-browser check against the container: one five-question interview moved `interviews_started` +1, `interviews_completed` +1, `answers_submitted` +5, exactly.
Limits: per-process, no alerting, no persistence.

## 8. Test results (reproducible)

| Check | Command | Result |
|---|---|---|
| Evaluation tests | `python -m pytest tests/evaluation -q` | 426 passed, 2 skipped (jsonschema not installed in this venv; installed in CI) |
| Retrieval tests | `python -m pytest tests/retrieval -q` | 137 passed, 1 skipped (needs sentence-transformers; heavy workflow) |
| Flask integration (legacy routes golden tests, demo, E2E journeys) | `python -m pytest tests/app -q` | 199 passed, 5 skipped (real MiniLM not available offline) |
| Static code-evaluation | `python -m pytest tests/codeeval -q` | 42 passed, 1 skipped (needs a Docker daemon plus the code-check image; deliberately not run) |
| New MLOps tests (observability, privacy, startup safety, packaging, CI structure) | `python -m pytest tests/mlops -q (no MLflow installed)` | 36 passed, 1 module skipped (MLflow tracking) |
| New MLOps tests incl. MLflow tracking (50 tests) | `python -m pytest tests/mlops -q (full mlflow 3.17)` | 50 passed |
| Dataset / frozen-experiment integrity | `python scripts/check_integrity.py` | INTEGRITY OK, no drift (corpus 666 records, freeze v2, bench_v2) |
| MLflow vs source files | `python scripts/mlflow_import_history.py --verify` | 30 runs, 642 metrics: all match |
| Lint | `ruff check (whole repo, correctness rules); ruff check + ruff format --check (new files)` | clean |
| CI workflows | `actionlint .github/workflows/*.yml` | clean (never executed on GitHub) |
| Compose file | `docker compose config; docker compose --profile ollama config` | valid |
| Docker image (substitute py3.13 base) | `docker build; docker run (read-only, cap-drop ALL, non-root); docker compose up --no-build` | built; healthy; /demo 200; sessions persist across container recreation |
| DVC | `dvc repro / status / checkout (dev-LSA backend); dvc add/push/pull (stand-in checkpoint)` | stage runs; outputs restored from cache; rebuilt index.faiss sha256 equals recorded; checkpoint hash identical |
| Browser: stage 6A journey (stand-in scorer) | `scripts/stage6a_browser_journey.py` | 47/47 |
| Browser: stage 4B journey | `scripts/stage4b_browser_journey.py` | 31/31 |
| Browser: stage 4D journey | `scripts/stage4d_browser_journey.py` | 25/25 |
| Browser smoke against the Docker container (real app, no scorers installed) | `scripts/stage6b_browser_smoke.py` | 16/16: honest 'scorer unavailable' state, interview completes, metrics +1/+1/+5, no answer text in metrics |
| Stage 3C-2 freeze v2 | `python scripts/stage3c2_freeze_v2.py verify` | freeze v2 verified: no drift |

Total in this environment: 426 + 137 + 199 + 42 + 50 = **854 passed** (7 environment-dependent skips listed above are not failures). Linux, Python 3.13.16. Not run: Windows, GitHub Actions, real MiniLM, Ollama/Qwen (by instruction), the Docker code-execution runner (by instruction).

## 9. Run these on your machine (Windows)

```
pip install -r requirements.txt
pip install -r requirements-mlops.txt
verify_mlops.bat                                    :: integrity, health endpoints, flags, MLflow import + verify in a temp store (read-only)
python scripts\mlflow_import_history.py             :: real local store; then:  mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db
python main\app.py                                  :: then in another window:  verify_mlops.bat --url http://127.0.0.1:5000
:: Docker Desktop running (WSL2):
verify_mlops.bat --check-docker
verify_mlops.bat --docker-build --docker-run        :: builds the image, runs it on 127.0.0.1:5099, checks health, user and readiness, removes it
copy .env.example .env  &&  docker compose up --build
:: optional
verify_mlops.bat --check-dvc --check-ollama
python -m pytest tests\mlops -q
```
If anything prints FAIL, send me the output; SKIP lines carry the exact fix.

## 10. Findings during this stage

| # | Finding | Status |
|---|---|---|
| 1 | `mlflow-skinny` (no SQLAlchemy) looked "available" and then failed on the SQLite backend | fixed: availability check requires SQLAlchemy; tests skip cleanly; `requirements-mlops.txt` pins the full package |
| 2 | First metric-label sanitiser flattened route templates (`/health` -> `_health`) | fixed: `/`, `<`, `>` allowed; test added |
| 3 | `actionlint` found an invalid YAML step name (a colon) in the draft CI file | fixed |
| 4 | `# syntax=docker/dockerfile:1` forces a registry pull and breaks offline builds; it was not needed | removed |
| 5 | Legacy `/api/start-interview` in the lean image returns HTTP 400 "Failed to load questions" (PyTorch missing); the message is misleading | **legacy behaviour left unchanged**; documented in MLOPS.md and TROUBLESHOOTING |
| 6 | The legacy Bi-LSTM scorer trains on first use if no checkpoint exists (a request can start a multi-minute job) | opt-in guard `SMART_FORBID_MODEL_TRAINING`, on in Docker |
| 7 | Several existing evaluation tests rewrite nine frozen-data files (`data/evaluation/bench_v2/*`, `stage3b/ollama_probe.json`, `stage3c_review/pilot_review_sheet_v2*`) byte-identically, which touches their mtimes. Content hashes before and after are identical and the integrity check passes | pre-existing; not changed (frozen data); suggest pointing those tests at temp copies |
| 8 | Test fixtures in the sandbox cannot show a CI run, a Windows run or the exact base image | listed under "not verified" |

## 11. Remaining production and security limitations (public-deployment blockers)

1. No authentication, TLS, rate limiting or CSRF protection; CORS `*` on `/api/*`.
2. Legacy sessions in process memory; demo sessions are unencrypted JSON files with candidate answers (14-day retention).
3. Docker code execution is a hardened ordinary container, not a production sandbox; it is not enabled in the image and is never enabled automatically.
4. No scorer is validated against human graders; the experimental evaluator abstains on 45% of rows and is DO NOT ADVANCE.
5. Metrics are in-process only; no alerting; no central log store.
6. Dependencies pinned but not hash-pinned or vulnerability-scanned; base image pinned by tag until you set a digest.
7. Workflows never executed on GitHub; nothing here was run on Windows.

## 12. Recommended next milestone

1. **Push to GitHub and get `ci.yml` green** (hours, not days): it will surface anything the sandbox could not (the exact base image, Python 3.12 pins, Windows line endings in scripts).
2. **Then the human-validation study** already recommended after Stage 5B: about 40 answers graded by you (or a reviewer) against a rubric, including the two code questions, logged to MLflow as a *live* run with `human_validated=true` only for the human-derived labels. Until that exists, no accuracy claim is possible and the experimental evaluator stays off.
Public deployment should wait for both, plus items 1-3 above.
