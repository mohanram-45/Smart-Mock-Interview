# MLOps guide (Stages 6B, 6C and 7A)

This document covers experiment tracking, versioning, CI, Docker, monitoring and local deployment. It describes only what exists in this repository; where something could
not be verified in the development sandbox, the **Verification status** table at the end says so.

Nothing here changes scoring, retrieval or the interview flow, and nothing here makes the evaluator more or less accurate. **No result in this project is validated against
human graders**, and the experimental Qwen evaluation keeps its frozen **DO NOT ADVANCE** decision (3C-2: abstain rate 0.45 > 0.40).

## 1. Required and optional components

| Component | Needed for | Mandatory? | How to get it |
|---|---|---|---|
| Python 3.12 or 3.13, Flask, flask-cors, numpy, scikit-learn, reportlab, pydantic | the web app, `/demo`, static code check, all non-model tests | **yes** | `pip install -r requirements.txt` (full) or `requirements-docker.in` (lean) |
| The repository's data (`data/curated`, `data/expansion`, manifests) | the 666-question corpus | **yes** (in Git) | clone |
| PyTorch + `sentence-transformers` | legacy Sentence-BERT scorer; real MiniLM retrieval (`/api/retrieval/*`) | optional | `pip install -r requirements-rag.txt` |
| `results/siamese_bilstm.pt` | legacy Bi-LSTM scorer (the legacy default) | optional | trained once on a dev machine; never trained at start-up (`SMART_FORBID_MODEL_TRAINING=1` in Docker) |
| `language-tool-python` + Java + LanguageTool cache | legacy TF-IDF + grammar scorer | optional | one-time setup, see TROUBLESHOOTING |
| Ollama + `qwen2.5:7b` | the opt-in live experimental evaluation | optional | `ollama pull qwen2.5:7b` (a download; never done automatically) |
| MLflow (`requirements-mlops.txt`) | experiment tracking and its UI | optional | `pip install -r requirements-mlops.txt` |
| DVC | sharing FAISS indexes / checkpoints between machines | optional | `pip install "dvc>=3,<4"` |
| Docker Desktop | the container image; the optional Docker code-check runner | optional | docker.com |

Without any optional component the app still runs: the demo shows "scorer not set up" with the exact one-time fix, and the experimental features stay off.

## 2. Experiment tracking (MLflow)

Local only: a SQLite database `mlflow/mlflow.db` and artifacts under `mlflow/artifacts/` (both git-ignored; they are rebuilt from files that **are** in Git).

```
pip install -r requirements-mlops.txt
python scripts\mlflow_import_history.py          # import existing results, then verify them against the source files
mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db     # browse at http://127.0.0.1:5000  (use --port 5001 if the app is running)
python scripts\mlflow_log_provenance.py          # one LIVE run: corpus + index fingerprints, strict corpus loader
```

**What was imported (no model was run; values are copied verbatim from the result files, 30 runs):**

| Experiment | Runs | Source (path + sha256 stored on every run) |
|---|---|---|
| `smart-retrieval` | 25 = 5 evaluation sets x 5 systems (dense qka / question / qk / qk_concise, BM25) | `data/retrieval/stage2c/eval_results.json` |
| `smart-evaluation` | 4 Stage 3B runs (llama3.2:3b smoke and confirm, qwen2.5:7b v1 and v2), 5-12 calls each | `data/evaluation/stage3b*/analysis_*.json` |
| `smart-evaluation` | 1 frozen Stage 3C-2 run (qwen2.5:7b, 20 answers, 40 modular rows) with `smart.decision = DO NOT ADVANCE` | `data/evaluation/stage3c2_results/20261015T120208Z/analysis_v2.json`, `freeze_manifest_v2.json` |
| `smart-provenance` | live snapshots you create | corpus manifest, index files |

**Labelling rules enforced in code and tests:** every imported run carries `smart.provenance = imported_historical`, its source path and sha256, a note starting
"IMPORTED HISTORICAL RESULT", and `smart.human_validated = false`. Retrieval runs are tagged `ai_authored_pooled_judgements_not_human_validated`; evaluation runs
`ai_authored_unreviewed` / `ai_provisional_not_human_reviewed`. No accuracy or human-agreement metric is created. Importing is idempotent, and if a source file's hash
changes after import, `ImportDrift` is raised instead of silently overwriting.

**What is tracked, per the brief:** retrieval configuration (system, doc format, eval set) and benchmarks (success@k, MRR, nDCG, recall, no-answer AUROC); embedding model
and library versions (**the Hugging Face model *revision* was not recorded in the Stage 2C file and is stored as "not recorded", not guessed**); FAISS index fingerprints
(recorded and, in live runs, freshly computed `index.faiss` sha256); evaluator implementation versions (pipeline 3c1.0, rubric engine 3c1.0, prompt versions, freeze
manifest sha256); model/provider configuration (model, temperature, seed rule, `num_ctx`, output tokens, timeout); schema-validity rates (`valid_output_rate`,
`schema_valid_first_attempt_pct`); evidence-verification (`gate_downgrade_rate`, verdict states before and after the gate, rejection reasons); abstention
(`abstain_rate`, `modular_rows_abstained`); latency (median/p95/max warm latency, tokens/s, query-encode ms, corpus-embed seconds); the pass/fail of every 3C-2
acceptance criterion.

**Not imported (and why):** the partial 2-answer pilot of 3C-2 (a partial run, not a result); the offline replay diagnostics (derived from recorded outputs, not new
measurements); the Stage 2A/2B retrieval benchmarks (earlier evaluation-set versions; the Stage 2C file is the latest and covers all five sets, and mixing label versions in one
experiment would mislead; their reports remain in `reports/`).

**Future experiments:**

```python
from src.mlops.tracking import live_run
with live_run("smart-retrieval", "minilm qk_concise, new eval set", params={"doc_format": "qk_concise"}) as run:
    run.log_metrics({"success@1": 0.74, "mrr@10": 0.83})     # your measured values
```
The context manager adds the standard tags, the corpus/index/freeze fingerprints and evaluator versions. The frozen 3C-2 runner scripts are **not** modified (their hashes
are frozen); to track a future run post hoc, add an extractor in `src/mlops/historical.py` or call `live_run` from a new script.

Verification: `python scripts\mlflow_import_history.py --verify` re-reads the source files and compares every metric (642 in 30 runs), the provenance tags and the 3C-2
decision tag; it exits 1 on any mismatch.

### Future experiments (Stage 8A)

`python scripts/mlflow_track_retrieval.py --backend minilm --local-files-only` evaluates the served retrieval configuration on the dev set and the frozen challenge set and records a **live** run in experiment `smart-retrieval-live`: embedder configuration (model, dimension, max sequence length, library versions), document format, corpus fingerprint, index file sha256, each evaluation file's sha256, label provenance (AI-pooled, not human ground truth), metrics and latency. `--dry-run` prints it without recording. It refuses to run when `scripts/check_versions.py` finds a mismatch (`--allow-mismatch` records the run tagged `MISMATCH_OVERRIDDEN`). Evaluator experiments use the same `tracking.live_run` helper (see the validation protocol). Imported historical runs keep the tag `imported_historical` and are never overwritten.

## 3. Data and model versioning

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md). Summary: corpus CSVs and manifests stay in Git (small, already fingerprinted by the project's own controls); DVC is used for
one thing: the git-ignored, large, derived FAISS indexes + embedding cache (`dvc.yaml`, one stage; run `dvc init` first, see REPRODUCIBILITY.md). The 3.8 MB Bi-LSTM checkpoint
(`results/siamese_bilstm.pt`) stays in Git because `dvc add` refuses a Git-tracked file; REPRODUCIBILITY.md describes the optional later move.

## 4. Continuous integration (GitHub Actions)

`.github/workflows/ci.yml` (pull requests, pushes to main/master, manual):

| Job | What it does |
|---|---|
| `lint` | `ruff check` (correctness rules: syntax errors, undefined names) on the whole repository; stricter rules + `ruff format --check` on the new MLOps files only. Legacy and frozen files are **not** reformatted because several are pinned by sha256 in the Stage 3C-2 freeze manifest |
| `integrity` | `scripts/check_integrity.py`: strict corpus loader, per-batch fingerprints, corpus manifest hashes, Stage 3C-2 freeze v2, bench_v2 hashes |
| `tests` (3.12 and 3.13) | retrieval, evaluation, Flask integration (legacy routes, demo, end-to-end journeys), static code-evaluation, observability and packaging tests |
| `mlops` | MLflow import / verify / provenance tests against a temp store |
| `windows` | `windows-latest`: integrity check, retrieval + Flask + MLOps tests, `scripts/verify_mlops.py`. This is the first place the Windows path/line-ending behaviour is exercised by an independent machine |
| `docker` | `docker compose config`, `docker build`, start on loopback with read-only rootfs, health + readiness check, non-root and no-secret checks |
| `ci-ok` | one gate job that fails unless every job above succeeded; make *this* the required status check in branch protection |

Normal CI needs **no GPU, no live Ollama (pointed at an unreachable address on purpose), no paid key or secret (none referenced), no private data, no model download
(HF/Transformers forced offline), and never executes candidate code.** Tests that need the real embedding model skip themselves. `heavy.yml` (manual or weekly only)
installs CPU PyTorch + sentence-transformers (downloads the ~90 MB MiniLM), Playwright/Chromium, and builds the image with the ML extras; it never runs a Qwen benchmark.

**Workflow security review (Stage 7A), each point asserted by `tests/mlops/test_ci_and_packaging.py`:**

- `permissions: contents: read` at workflow level, no job widens it; no `secrets.*` and no `GITHUB_TOKEN` reference anywhere; no `pull_request_target` or `workflow_run` (untrusted fork code never runs with privileges).
- Every third-party action is pinned to a **full commit SHA** (the version is kept as a comment); `actions/checkout` uses `persist-credentials: false`.
- Python packages install from **hash-checked lock files** (`pip install --require-hashes -r requirements-ci.lock`, `requirements-ci-mlops.lock`), generated with `uv pip compile --universal`, so a compromised or silently updated release cannot enter CI. PyPI is the only package source in normal CI (the CPU-PyTorch index is used only by `heavy.yml`).
- No `upload-artifact`, no hand-rolled cache: nothing a job produces (screenshots, session files) can carry candidate data out of the runner. The only cache is `setup-python`'s pip cache, keyed by the lock file.
- No `${{ github.event.* }}` / branch names / inputs are interpolated into shell scripts (script-injection pattern); the gate job passes `needs` through an environment variable.
- Candidate code is never run: `SMART_CODEEVAL_EXEC` is empty, no step builds the code-check image, `SMART_DEMO_CODE_EVAL` is unset.
- `.github/dependabot.yml` proposes monthly pull requests for the pinned actions and the base image (it never merges).

Refreshing the locks (do it deliberately, then run the full test matrix):
```
uv pip compile requirements-ci.txt --universal --python-version 3.12 --generate-hashes -o requirements-ci.lock --no-header
uv pip compile requirements-ci.txt requirements-mlops.txt --universal --python-version 3.12 --generate-hashes -o requirements-ci-mlops.lock --no-header
```
Refreshing an action pin: `git ls-remote https://github.com/actions/checkout "refs/tags/v4*"`, take the SHA of the tag you want, and update the comment.

Both workflows pass `actionlint`. **They have not run on GitHub yet**; see [GITHUB_FIRST_PUSH.md](GITHUB_FIRST_PUSH.md) for the exact first-push procedure and the things that could still fail on the first run.

## 5. Docker

```
docker compose up --build                       # app only  -> http://127.0.0.1:5000/demo/
docker compose --profile ollama up --build      # + optional Ollama service
docker compose down                             # keep sessions;   docker compose down -v   deletes the volume (all session files)
```

* **Image** (`Dockerfile`): `python:3.13-slim-bookworm`, dependencies from the fully pinned `requirements-docker.lock` (lean: no torch, no FAISS, no weights), non-root user
  uid 10001, `HEALTHCHECK` (`scripts/healthcheck.py`), waitress (1 process, 8 threads; legacy sessions live in process memory), `SMART_FORBID_MODEL_TRAINING=1`, no credentials,
  no Docker client. Pin the base image by digest for full reproducibility: `SMART_PYTHON_IMAGE=python:3.13-slim-bookworm@sha256:<digest>` in `.env`
  (`docker buildx imagetools inspect python:3.13-slim-bookworm`). `INSTALL_ML=1` adds torch/sentence-transformers/faiss (large; not built here). The embedding model is looked up in the `smart-hf-cache` volume (`/hf-cache`, `HF_HOME`) and `HF_HUB_OFFLINE=1` by default, so nothing is downloaded unless you run the one-time command in `.env.example`.
* **Compose** (`docker-compose.yml`): published on `127.0.0.1` only; read-only root filesystem; `cap_drop: ALL`; `no-new-privileges`; no host bind mounts; named volume
  `smart-results` at `/app/results` (sessions, reports); every experimental flag defaults to off; `SMART_CODEEVAL_EXEC` is **not** passed through, and there is no Docker socket in
  the container, so **arbitrary candidate-code execution cannot happen inside this container**. The static code check (read-only parsing) can be switched on with
  `SMART_DEMO_CODE_EVAL=1`.
* **Ollama** is a separate optional service (profile `ollama`), not published to the host. Models live in the `ollama-models` volume, never in an image. Pull manually:
  `docker compose exec ollama ollama pull qwen2.5:7b` (a multi-GB download: your decision). To use Ollama already running on Windows instead, set
  `SMART_DEMO_OLLAMA_HOST=http://host.docker.internal:11434` and `SMART_DEMO_LIVE_MODULAR=1`.
* **What the lean image can and cannot do:** serves `/demo` (corpus, interview, recorded results, static code check) and `/healthz`, `/readyz`, `/metrics`. The scorers need the
  optional packages, so the demo reports "scorer not set up". The legacy `/api/start-interview` needs torch for its default scorer and returns HTTP 400 "Failed to load
  questions" in the lean image (unchanged legacy behaviour); use `INSTALL_ML=1` plus a checkpoint volume if you want it.
* GPU: no GPU is reserved. For NVIDIA Ollama on Docker Desktop add a `deploy.resources.reservations.devices` block to the `ollama` service (not tested here).

## 6. Monitoring and observability

No monitoring stack is added: in-process counters, a JSON access log and three endpoints.

| Endpoint | Purpose |
|---|---|
| `GET /health` | legacy, unchanged: `{"status":"ok"}` |
| `GET /healthz` | liveness + build identity (app version, git commit, evaluator versions). No I/O: used by the container `HEALTHCHECK` |
| `GET /readyz` | 200 if the corpus manifest is present and the session directory is writable (503 otherwise). Reports scorer readiness and, only with `SMART_OBS_PROBE_OLLAMA=1`, a 1-second Ollama reachability probe; optional models never make the app "not ready" |
| `GET /metrics` | JSON (default) or `?format=prometheus`; `SMART_METRICS_ENABLED=0` returns 404. Contains counts and latency summaries only |

Metrics: request counts and latency by method / **route template** / status class; interviews started / completed (surface `demo` or `legacy`); answers submitted;
scorer failures (stage `load` or `score`) and scorer-unavailable events; retrieval failures (`corpus_unavailable`, `source_unavailable`); experimental evaluations by
outcome and abstentions; code assessments by outcome; sessions deleted; model-availability gauge; `smart_build_info` (app version, commit, pipeline version, freeze version).

**Retrieval fallbacks:** the project deliberately has none (a failing curated source returns HTTP 503 and is never silently replaced by another source, see
`interview_session.py`), so only failures are counted; a fallback counter would be invented.

**Logging:** one JSON line per request on the `smart.access` logger: timestamp, request id, method, route template, status, milliseconds. Never logged: request or response
bodies, answers, reference answers, query strings, session ids, cookies. Metric label values are restricted to short `[a-z0-9_.:/<>-]` tokens chosen by the code, series per
metric are capped, and only registered metric names are accepted. Tests post a hostile answer and assert that neither the log nor `/metrics` nor `/healthz` contains it.
Switches: `SMART_JSON_LOGS`, `SMART_ACCESS_LOG`.

Limits: counters are per process and reset on restart; there is no alerting, persistence or authentication on `/metrics` (it holds no sensitive data, but do not expose it).

## 7. Local deployment

Windows development (no Docker):
```
python -m venv .bot && .bot\Scripts\activate
pip install -r requirements.txt
python main\app.py                               # http://127.0.0.1:5000/demo/
verify_mlops.bat --url http://127.0.0.1:5000     # health + integrity + MLflow checks (read-only)
```
Docker: copy `.env.example` to `.env`, then `docker compose up --build`, then `python scripts\healthcheck.py --ready`.

One-shot validation on a Windows machine (PowerShell; read-only, never trains or downloads anything, binds only to 127.0.0.1):
```
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1                       :: files, versions, integrity, startup side effects (fast)
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Mlflow -Docker -Tests
python scripts\verify_compose.py                                                           :: Docker Desktop: build, start, health, persistence, privacy, clean-up
python scripts\mlops_demo.py                                                               :: 7-step walk-through; labels what was demonstrated and what was not
```
`verify_compose.py` uses its own Compose project (`smartverify`) and port 5099, so it never touches your normal containers or the `smart-results` volume.

## 8. Production and security limitations (blockers for any public deployment)

1. No authentication, authorisation, TLS, rate limiting or CSRF protection; CORS on `/api/*` is `*`. The compose file binds to loopback for this reason.
2. Legacy interview sessions are in process memory (lost on restart, single process only); demo sessions are plain JSON files containing candidate answers, retained 14 days, not encrypted.
3. Candidate-code execution is **not** production-grade: the optional Docker runner is a hardened ordinary container, not a sandbox (shared kernel; see CODE_EXECUTION_SECURITY.md).
4. Scores are not validated against human graders; the experimental evaluator abstains on 45% of rows in its frozen test and is DO NOT ADVANCE.
5. The metrics are in-process only; no alerting; logs go to stderr only.
6. CI dependencies are hash-locked, but the Docker image's `requirements-docker.lock` is version-pinned only (not hash-checked), nothing is vulnerability-scanned (no `pip-audit`/Trivy/CodeQL run), and the base image is pinned by tag, not digest, until you set `SMART_PYTHON_IMAGE`.
7. The workflows have not run on GitHub; Windows (including Docker Desktop) was not available to the development sandbox, so the Windows scripts are verified only as far as PowerShell 7 on Linux can exercise them.
8. The remote repository is publicly readable. Everything committed there is public, including `data/`, `audit/` and `reports/`; review `docs/GITHUB_FIRST_PUSH.md` before the first push.

## 9. Verification status

| Item | Status |
|---|---|
| Observability endpoints, counters, JSON log privacy, flags-off, training guard | automated tests pass (tests/mlops; Linux, Python 3.12 from the hash lock and 3.13) |
| MLflow import / verify / provenance / drift detection | tests pass against a real MLflow 3.17 SQLite store (Linux); `scripts/mlops_demo.py` reproduces 30 runs / 642 metrics in a throwaway store |
| Dockerfile / compose | built and run with a real Docker 29.8 daemon in the sandbox, **on a substitute Python 3.13 base** because Docker Hub is unreachable there. `scripts/verify_compose.py --no-build` passed 29/29 against that daemon: healthy, non-root (uid 10001), published only on 127.0.0.1, training forbidden, no weights, session survived container recreation, no candidate text in metrics or logs. **Not verified:** the real `python:3.13-slim-bookworm` base, Docker Desktop on Windows, `INSTALL_ML=1`, the Ollama profile |
| DVC | `dvc.yaml` executed with DVC 3.67 on the dev-LSA backend (Stage 6B). **Not verified:** the MiniLM backend (model not available offline); `dvc init` has not been run in the real repository |
| GitHub Actions | `actionlint` clean; structure and supply-chain tests pass; the full CI command set was dry-run on Python 3.12 from the hash-checked locks (all suites pass). Never executed on GitHub |
| Windows (Stage 8C) | Run by the project owner on Windows 11, Python 3.12.7, and reported to the assistant (output not stored in the repository): official `python:3.13-slim-bookworm` image and Compose **29/29**; health, readiness, non-root, loopback binding, session persistence; MLflow 3.17.1 with 30 runs / 642 metrics verified and an idempotent import; corpus and frozen-benchmark integrity; publication audit; no unintended training or download. The suite then gave 958 passed / 7 failed; all seven are explained and fixed in `reports/stage8c_consolidated_report.md` and need a re-run to confirm on Windows. **Container health is not a working interview with local models:** the lean image has no torch/FAISS, so legacy BERT/Bi-LSTM scoring and `/api/retrieval` inside the container were not exercised (they need `INSTALL_ML=1` plus a model volume) |
| Version consistency (Stage 8A) | `scripts/check_versions.py` passes on Linux; unit-tested for wrong params, drifted manifest, stale and tampered index. The Windows run and the real-MiniLM index have not been checked |

Run on your machine: `scripts\validate_windows.ps1 -Mlflow -Docker -Tests`.
