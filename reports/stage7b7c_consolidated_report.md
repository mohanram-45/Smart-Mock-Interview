# Stage 7B + 7C consolidated report: publication safety, DVC/MLflow reproducibility, CI readiness, portfolio audit

Date: 2026-10-17. Scope: make the first public update of the repository and the first GitHub Actions run safe, finish what can be verified without Windows,
and say plainly what cannot. Nothing was committed, pushed, published or uploaded; repository visibility was not changed; no history was rewritten; no tracked file was deleted;
nothing was trained or downloaded; Ollama/Qwen and paid APIs were not used. Frozen datasets and the frozen **DO NOT ADVANCE** result (Stage 3C-2, abstain rate 0.45 > 0.40) are unchanged.
Nothing in this project is validated against human graders.

## 1. Verdict

| Mission | Status |
|---|---|
| A. Windows verification | **Not executed on Windows.** This session's link to your computer is a Linux shell with the project folder mounted (no PowerShell, no Docker, no Windows Python). `validate_windows.ps1` was extended and run under PowerShell 7 on Linux (path separators adapted): 23 PASS, 0 FAIL, 3 SKIP. Nothing here is claimed as Windows-verified. Exact commands in section 3 |
| B. Publication safety audit | **Done; the tree is safe to commit once you decide public/private.** Inventory in section 5. The audit found and fixed six real problems, two of which would have broken the first GitHub run |
| C. DVC and MLflow | `.dvc/` does not exist because `dvc init` was never run; `dvc init` creates one empty file. The pipeline reproduces its declared outputs byte-for-byte (offline stand-in embedder), in a new one-command check. MLflow store and DVC local state are ignored. Real-MiniLM DVC run not done |
| D. CI readiness | Closest local simulation done: the publishable tree committed to a scratch repository, cloned the way Git for Windows does, every CI job's commands run on Python 3.12 from the hash-locked requirements: **0 failures, 896 tests passed**. Never run on GitHub |
| E. Portfolio audit | README corrected in six places (corpus "verified" wording, what "RAG" does and does not mean here, DVC, CI-not-CD, Windows status); public text scanned for unsupported accuracy/security claims: none found |

## 2. Findings and fixes

| # | Finding | Why it mattered | Fix and regression test |
|---|---|---|---|
| 1 | **Stage 7A's `.gitattributes` (`* text=auto eol=lf`) was incomplete.** 13 hash-pinned files are stored with Windows CRLF line endings (e.g. `retrieval_benchmark_minilm.json`); their checksums were computed over CRLF bytes | Committing them would have converted them to LF and `test_originals_are_byte_identical_to_checksums` would have failed on GitHub (it failed in the first simulation) | those 13 files are `-text` (byte-exact on every OS); `test_hash_pinned_files_stored_with_crlf_are_exempt_from_line_ending_conversion` finds any pinned CRLF file missing from the list |
| 2 | `test_provenance_script_records_fingerprints` needed the **git-ignored FAISS index**, which a fresh clone does not have | would have failed the first GitHub run (it passed only in working trees that had built an index) | the test builds the offline stand-in index when none exists and removes exactly what it built |
| 3 | `test_probe_script_is_read_only_and_degrades_without_ollama` **overwrote a committed evidence file** (`ollama_probe.json`) with Linux/failed-probe data on every test run | every `pytest tests/evaluation` silently changed tracked data and dirtied the tree | the probe honours `SMART_PROBE_OUT`; the test redirects it and asserts the committed file is byte-identical afterwards |
| 4 | `.gitignore` did not cover `mlops_venv/`, `app_venv/`, `.dvc/config.local` (can hold remote credentials), `dvc_storage/`, `*.faiss`, `*.pt`, `*.db`, nor the 55 journey screenshots (22 MB) under `data/evaluation/*/screenshots/` | an unguarded `git add -A` would have staged them | rules added; `.dockerignore` extended (recursive patterns); `tests/mlops/test_publication_safety.py` |
| 5 | Your **Windows user name** was recorded in `data/retrieval/model_provenance.json` and `data/evaluation/stage3b/ollama_probe.json` | personal path in a public repository | redacted to `~` (backups in `tmp\backup_7b\`); both producer scripts now redact; test scans all publishable text |
| 6 | A folder named `mlflow/` (the local store) is importable as an empty namespace package, so `tracking.available()` could report MLflow as installed when it is not | confusing failures on a machine without MLflow after the importer has run once | `available()` rejects namespace packages; `test_mlflow_shadowing.py` (fails without the fix) |
| 7 | `docs/REPRODUCIBILITY.md` told you to `dvc add results\siamese_bilstm.pt`; that file is already tracked by Git and DVC refuses it (verified) | a command that cannot work | checkpoint stays in Git (3.8 MB, already in history); optional later move documented |
| 8 | README: corpus described as "verified" (it is AI-authored and AI-checked, human review is blank); retrieval layer could be read as full RAG; no DVC mention; "CI/CD" ambiguity; Windows status | overstated or unclear claims | rewritten: "not human-reviewed", "retrieval half of a RAG design ... no retrieval-augmented grading yet", DVC paragraph, "continuous integration only", Windows/GitHub still unproven |
| 9 | No mechanical guard against a bad commit | "do not `git add .` indiscriminately" relied on care | **new `scripts/check_staged.py`** (read-only: blocked paths, >50 MB, credential shapes, real user paths) with 16 tests; every commit step runs it |
| 10 | No way to prove DVC reproducibility on your machine without touching your repository | Mission A.4 | **new `scripts/verify_dvc.py`** (temporary copy, offline stand-in, 6 checks); `validate_windows.ps1 -Dvc` calls it |

Also noted, not changed: 61 audit files mention `/home/claude/` (AI authoring sandbox paths; harmless provenance); the git history already exposes two author e-mail addresses on the public remote;
`results/reports/` holds 8 legacy interview reports from real sessions (ignored by the original rules, never published).

## 3. Mission A: Windows verification

What was and was not possible:

| Check (your list) | Result |
|---|---|
| 1. Windows Python environment, dependency compatibility | **Not run on Windows.** Linux: Python 3.12.13 from `requirements-ci.lock` (hashes verified) and 3.13 environments pass. PowerShell script checked statically for Windows PowerShell 5.1: parses with 0 errors, no PowerShell-7-only syntax, every cmdlet exists in 5.1, pure ASCII, CRLF |
| 2. Corpus and experiment fingerprints | `check_integrity.py`: INTEGRITY OK in the fresh clone made with `core.autocrlf=true` (Linux). The 13 CRLF-pinned files keep their exact bytes through that clone |
| 3. MLflow historical import and idempotency | Linux (MLflow 3.17.1): 30 runs / 642 metrics created, second import 0 created / 30 present, verification matches. The validator now also re-checks the byte-exact immutable files |
| 4. DVC configuration and index reproducibility | `verify_dvc.py`: 6/6 PASS on Linux (details in section 6). Not run on Windows |
| 5-8. Docker Desktop, official base image, Compose startup, health/readiness | **Not run.** No Docker Desktop reachable. Last real-daemon result (Stage 7A, substitute base image): 29/29. Only `.dockerignore` changed since; verified statically (`docker compose config` valid; 0 files in the Docker `COPY` directories match the new exclusions) |
| 9. Session persistence across container restart | Stage 7A, Linux daemon: passed. Not re-run |
| 10. No unintended training, downloading, code execution | startup check in the validator: no checkpoint changed, 0 files added to the Hugging Face cache; CI env forces offline and an unreachable Ollama address |

**Commands to run on your machine** (nothing trains, downloads, pulls a model, runs candidate code, or listens beyond 127.0.0.1):
```bat
cd /d D:\Projects\SMART-MOCK-INTERVIEW
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Tests
pip install -r requirements-mlops.txt
pip install "dvc>=3,<4"
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Mlflow -Dvc -Docker -Tests
```
`-Docker` builds the real `python:3.13-slim-bookworm` image (needs Docker Desktop running, internet) and starts it on 127.0.0.1:5099 for a few minutes. Send me the output and I will fix what it reports.

## 4. Mission B and C: Docker, MLflow results

* MLflow: see item 3 above. MLflow databases and run artifacts are ignored (`mlflow/`, `mlruns/`, `*.db`, `*.sqlite*`) and a test blocks them from the build context and the working-tree scan.
* Docker: unchanged Dockerfile; compose valid; the model cache volume and offline defaults from Stage 7A remain. Not re-run against a daemon in this stage.

## 5. Publication safety inventory (deliverable 5)

Inspected: the complete diff of the 6 modified tracked files (279 insertions, 231 deletions: application wiring, metrics hooks, a training guard, README), all 951 new files (58.1 MB) and the 36 unchanged tracked files.

| Check | Result |
|---|---|
| Credentials, tokens, private keys | none (10 credential patterns scanned across 993 files: OpenAI, Anthropic, GitHub, AWS, Google, Slack, Hugging Face, bearer tokens, private keys, `password=`/`api_key=` assignments) |
| Private configuration | `.env`, `report_delivery/.env` ignored and untracked; `.env.example` is placeholders only |
| Candidate answers, session data | published answers are synthetic benchmark answers; all 5 human-review sheets are blank; `results/demo_sessions/` (1 MB) and `results/reports/` (legacy session reports) are ignored |
| Personal information | Windows user name found in 2 files: **fixed**. E-mail-shaped strings: test fixtures only (`example.com`, `x.com`) and a `@contextlib` decorator. Author line in the README matches the already-published README |
| Large binaries, checkpoints, embeddings, indexes, caches, archives | none in the publishable set. Excluded: `data/retrieval/index` (4 MB) and `cache` (9 MB), 55 screenshots (22 MB), `mlflow/` (2 MB), `*.zip` (2 audit archives and the hand-off bundles in `tmp/`), `tmp/` (local working files), environments, `node_modules`. Already tracked: `results/siamese_bilstm.pt` (3.8 MB) |
| GitHub limits | largest new file 5.0 MB (`reports/stage2b_final_benchmark.json`); nothing near the 50 MB warning or 100 MB limit. Total new 58.1 MB |
| Generated experiment outputs vs reproducibility manifests | manifests, frozen data, reference results and audit evidence are published (the integrity checks and tests need them); regenerable outputs are not |
| Unsupported claims in public text | swept `README.md`, `docs/`, `reports/` for production-ready, secure, accuracy-percentage, human-level and similar claims: none unhedged |

### Recommended files to commit (deliverable 6)

| Commit | Paths | New / modified files |
|---|---|---|
| 1 hygiene | `.gitignore` (mod) `.gitattributes` `.dockerignore` `.dvcignore` `.env.example` | 5 |
| 2 code and tests | `main` (mod) `src` (mod) `tests` `scripts` `requirements*.txt` `pyproject.toml` `run_demo.bat` `verify_windows.bat` `verify_mlops.bat` | 214 (1.4 MB) |
| 3 data and audit | `data` `audit` `results/stage3c1_comparison.json` | 629 (42.0 MB) |
| 4 CI, Docker, DVC | `.github` `Dockerfile` `docker` `docker-compose.yml` `dvc.yaml` `params.yaml` `requirements-docker*` `requirements-ci*` `requirements-mlops.txt` | 15 (0.3 MB) |
| 5 documentation | `docs` `reports` `README.md` (mod) | 94 (14.3 MB) |

All 957 changed files (951 new, 6 modified) fall in exactly one group (verified by script). **Exclude:** everything git-ignored (listed above), `tmp/`, anything `scripts\check_staged.py` flags. Do not use `git add -A` or `git add .`.

## 6. DVC readiness (deliverable 4)

| Item | Status |
|---|---|
| `dvc.yaml` / `params.yaml` / `.dvcignore` | present, in commit 4 / 1; one stage `build_index` (integrity check, then index + embedding cache); `data/retrieval/index` and `cache` are git-ignored outputs |
| `.dvc/` repository | **does not exist** until you run `dvc init`; verified that it creates exactly one empty file, `.dvc/config`, reads nothing and changes no frozen file |
| Reproduction | `python scripts\verify_dvc.py` (temporary copy): `dvc init`, `dvc repro` (integrity check, then offline `dev-lsa` index), built index matches the hash recorded beside it (`ba1100af...`), `dvc status` up to date, outputs deleted and restored by `dvc checkout` byte-identical: **6/6 PASS on Linux, about 11 s** |
| Default (`minilm`) stage without the model | stops with an error after the integrity check; downloads nothing; writes nothing |
| `dvc.lock` | must **not** be committed from the offline run (it would describe `dev-lsa`, not the committed `minilm` params); commit it after one real MiniLM `dvc repro` on your machine |
| Checkpoint | stays in Git; `dvc add` refuses a tracked file (verified). Optional move needs `git rm --cached` and your approval; nothing duplicated |
| Remote storage | none configured; nothing uploaded. Use a folder outside the repo, or the ignored `dvc_storage/`; credentials belong in the ignored `.dvc/config.local`. A cloud remote needs your approval |
| Not verified | the real MiniLM index through DVC, any remote, Windows |

## 7. Commit commands, first PR and CI (deliverables 7 and 8)

The exact, ordered commands are in **`docs/GITHUB_FIRST_PUSH.md`** (explicit paths, `scripts\check_staged.py` before every commit, branch `ci/mlops-stages-6-7`, then `git push -u origin ...` and
`gh pr create` marked **[PUBLISHES]**). Required check: **`CI gate`**; it can only be selected in branch protection after it has run once, so protect `main` after the first pull-request run.
Pushing the branch does not trigger CI by itself (`push` is limited to `main`); opening the pull request does, with eight checks: Lint and format, Dataset integrity, Tests (3.12), Tests (3.13), MLflow tracking, Windows smoke, Docker image, CI gate.

## 8. CI simulation (Mission D)

The publishable tree (993 files) was committed to a scratch repository and cloned with `core.autocrlf=true`. All 993 files were present. Pinned LF files had no CR; the 13 CRLF-pinned files kept their CR bytes
and their stored blob hash equals the checked-out hash; `.bat`/`.ps1` stayed CRLF.

| Job (commands taken from `ci.yml`) | Result |
|---|---|
| Lint and format | `ruff check` (repo), strict `ruff check --select E,F,I`, `ruff format --check` on 22 files: all clean |
| Dataset and frozen-experiment integrity | INTEGRITY OK |
| Tests, Python 3.12.13 from `requirements-ci-mlops.lock` (hashes enforced) | retrieval 137 passed / 1 skipped; evaluation 428; app 199 / 5 skipped; codeeval 42 / 1 skipped; mlops 90 |
| MLflow tracking tests | 14 passed |
| Windows smoke commands on the lean environment (no MLflow) | integrity OK; retrieval + app + mlops 412 passed / 7 skipped; `verify_mlops.py` 11 PASS, 3 SKIP, nothing failed |
| Publication check on the clone | OK |
| Tree after all jobs | clean (no test writes into a tracked or unignored path) |
| Docker build configuration | `docker compose config` valid; static review only (no image built this stage) |
| Workflow permissions, pinned actions, secrets | asserted by `tests/mlops/test_ci_and_packaging.py` (SHA pins, `contents: read`, no `pull_request_target`, no secrets, no GPU/Ollama/paid key, offline Hugging Face) |

Limits of the simulation: Linux only; Python 3.13 matrix leg verified earlier (Stage 7A), not repeated here; runner images, the real Docker base, GitHub Actions behaviour and `windows-latest` are untested.

## 9. Test results (deliverable 9)

| Suite / check | Result |
|---|---|
| retrieval / evaluation / Flask app / code evaluation | 137 (+1 skip) / 428 / 199 (+5 skips) / 42 (+1 skip) |
| MLOps (observability, privacy, MLflow, startup safety, packaging, CI supply chain, publication safety, staged check, DVC helper, namespace shadowing) | **90** (62 before this stage, +28) |
| Total in the CI environment | **896 passed**, 7 environment skips, 0 failures |
| Lean (Windows-job) environment | 412 passed, 7 skipped |
| `validate_windows.ps1 -Mlflow -Dvc` under PowerShell 7 on Linux | 23 PASS, 0 FAIL, 3 SKIP (DVC repo not initialised in a fresh clone, Docker engine, Ollama) |
| `verify_dvc.py` | 6/6 PASS |
| `check_staged.py --worktree` on the real tree and on the clone | OK, 993 files, 71.6 MB |
| `check_integrity.py` | OK |

Regression tests added this stage fail without their fix: byte-exact pinned files (reproduced in the first simulation), namespace shadowing (shown failing then passing), probe isolation, provenance index fixture, user-name and credential scans, ignore-rule coverage.

## 10. Remaining blockers (deliverable 10)

1. **You must push.** It needs your GitHub credentials and your decision on a publicly readable repository. CI is unproven until it has run once.
2. **Windows is unverified.** Run the commands in section 3 and send me the output. The `windows-latest` job is the independent second check.
3. Docker: official base image, Docker Desktop/WSL2, `INSTALL_ML=1` image and the Ollama profile untested; no vulnerability scanning (`pip-audit`, CodeQL, image scan); Docker lock not hash-checked; base pinned by tag.
4. DVC: `dvc init` not yet run; real-MiniLM `dvc repro` and `dvc.lock` pending; no remote.
5. Commit author identity: the existing history already shows two e-mail addresses publicly; check what the new commits will use (step 0 of the push procedure).
6. Public deployment remains blocked (no authentication/TLS/rate limiting, in-process legacy sessions, plaintext session files, candidate-code execution only in a hardened ordinary container, metrics reset on restart). Nothing was deployed.
7. No score is validated against human graders; the experimental modular evaluator remains DO NOT ADVANCE; retrieval benchmark labels are AI-generated.

## 11. Files added or changed in this stage

New: `scripts/check_staged.py`, `scripts/verify_dvc.py`, `tests/mlops/test_publication_safety.py`, `test_check_staged.py`, `test_verify_dvc.py`, `test_mlflow_shadowing.py`, this report.
Changed: `.gitignore`, `.gitattributes`, `.dockerignore`, `README.md`, `scripts/validate_windows.ps1`, `scripts/stage3b_probe_ollama.py`, `audit/retrieval/model_provenance.py`, `src/mlops/tracking.py`,
`tests/mlops/test_tracking.py`, `tests/evaluation/test_stage3b_assets.py`, `docs/GITHUB_FIRST_PUSH.md`, `docs/REPRODUCIBILITY.md`, `docs/TROUBLESHOOTING.md`, `docs/MLOPS.md`, `docs/ARCHITECTURE.md`.
Redacted in place (backups in `tmp\backup_7b\`): `data/retrieval/model_provenance.json`, `data/evaluation/stage3b/ollama_probe.json`. No frozen data file, manifest or result was edited.
