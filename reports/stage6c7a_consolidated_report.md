# Stage 6C + 7A consolidated report: Windows validation, GitHub CI readiness, MLOps demonstration, engineering audit

Date: 2026-10-17. Scope: validate the Stage 6A/6B MLOps work against the real project, harden the CI, prepare the first GitHub run, audit the repository.
Nothing was pushed, published, deployed, trained, downloaded, or run against a paid API or Qwen. Frozen datasets and the frozen **DO NOT ADVANCE** result
(Stage 3C-2, abstain rate 0.45 > 0.40) are unchanged. Nothing in this project is validated against human graders.

## 1. Verdict

| Mission | Status |
|---|---|
| 6C Windows validation | **Not executed on Windows.** The linked computer is reachable only as a Linux session with your project folder mounted (no PowerShell, no Docker). I did what could be done there (item 2) and wrote a one-command Windows validator, `scripts/validate_windows.ps1`, for you to run. Nothing below is claimed as Windows-verified |
| 6C Docker | Verified on a **real Docker 29.8.2 daemon** in the development sandbox, on a substitute Python 3.13 base (Docker Hub is blocked there). **29/29** checks of the new `scripts/verify_compose.py`, plus a **16/16** real-browser smoke test against the running container, including host-side reachability of the published port |
| 7A CI | Audited and hardened; **10 problems fixed** (item 5). `actionlint` clean; whole CI command set dry-run on Python 3.12 from the new hash-checked locks: all suites pass. **Never executed on GitHub** |
| 7A repository | **The remote is publicly readable.** First-push procedure written (`docs/GITHUB_FIRST_PUSH.md`). Two real defects found in the repository state and fixed (`.gitignore` lost its secret/cache rules; no `.gitattributes`, which would have failed every hash check on a fresh Windows clone) |
| Demonstration | `scripts/mlops_demo.py`: 7 steps, labels what was demonstrated and what was not (transcript: `docs/MLOPS_DEMO_TRANSCRIPT.md`) |

## 2. Windows validation status (deliverable 2)

What I could and could not do:

| Item | Result |
|---|---|
| Reach Windows / PowerShell / Docker Desktop from here | **No.** `device_bash` is a Linux shell (`uname`: Linux, Ubuntu 22.04, Python 3.10, no `docker`, `pwsh`, `powershell.exe`, `cmd.exe`) with `D:\Projects\SMART-MOCK-INTERVIEW` mounted. I did not drive the desktop with computer use: terminals are restricted apps and clicking through a Docker Desktop build would not be reliable evidence |
| Run `verify_mlops.bat` | Not possible. Its Python program `scripts/verify_mlops.py` passes (15 PASS, 3 INFO) in the sandbox. I fixed one real Windows defect in the `.bat`: it always ended in `pause`, which blocks unattended runs (`SMART_NO_PAUSE=1` now skips it) |
| Frozen data intact on **your** machine | Byte-identical check against the copy that passes `check_integrity.py`: all ten hash-pinned files (curated CSV, corpus manifest, four batch CSVs, bench_v2 files) have the same sha256 prefix on your machine and in the sandbox, and none contains a CRLF. Directory fingerprints of `data/curated`, `data/expansion`, `data/audit`, all `src/*` packages are identical. Differences, all benign: your machine has extra run artifacts the sandbox never had (Stage 3B review sheets, `stage3b_qwen_v3` analysis, `dry_run.json`, a second `_monitor_*` folder, `model_provenance.json`); the sandbox has four label-sensitivity variant files (`*_max/_min.jsonl`) your machine lacks (only an audit script refers to them; no test or manifest does) |
| The PowerShell validator | `scripts/validate_windows.ps1` parses under PowerShell 7.6.7. Its logic was executed under PowerShell 7 **on Linux** with path separators adapted: **23 PASS, 0 FAIL, 4 SKIP** (the skips were Git/Docker/Ollama items that need the real machine). It has never run on Windows PowerShell 5.1 |
| Git / remote state | See `docs/GITHUB_FIRST_PUSH.md`. Local `main` = `origin/main` = `2639cdd`; 6 modified + ~79 new top-level paths are uncommitted |

Run on your machine (nothing here trains, downloads, pulls a model, runs candidate code or leaves 127.0.0.1):
```
cd /d D:\Projects\SMART-MOCK-INTERVIEW
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Mlflow -Docker -Tests
python scripts\mlops_demo.py
```
`-Mlflow` needs `pip install -r requirements-mlops.txt`; `-Docker` needs Docker Desktop running and builds the real `python:3.13-slim-bookworm` image.

## 3. Real Docker build and runtime (deliverable 3)

`python scripts/verify_compose.py --no-build` against the sandbox daemon (own Compose project `smartverify`, loopback port 5099, cleaned up afterwards): **29 PASS, 0 FAIL.**
It checks: compose file valid; `/healthz`, `/readyz`, legacy `/health`, `/demo/`; Docker HEALTHCHECK `healthy`; uid 10001 (non-root); published port bound to `127.0.0.1` only;
`SMART_FORBID_MODEL_TRAINING=1` and no code-execution backend variable; live-Qwen / code-check / retrieval flags off; no `.pt`/`.safetensors`/`.gguf` anywhere in the container; no
training or download text in the startup log; both volumes writable by the non-root user; `HF_HUB_OFFLINE=1`; create a session and submit an answer; `compose down` (volume kept),
`compose up` again, **the session survives**; `/metrics` has request counters and **neither metrics nor logs contain the candidate answer**.
`scripts/stage6b_browser_smoke.py` (Chromium) against the same container: **16/16** (interview of five questions completed, counters +1/+1/+5, no console errors).

Not verified: the real `python:3.13-slim-bookworm` base image, Docker Desktop on Windows/WSL2, an `INSTALL_ML=1` build, the Ollama profile.
The base image used here is a root filesystem assembled from the sandbox's Python 3.13; it exercises the Dockerfile's instructions but is not the official image.

## 4. MLflow and DVC (deliverable 4)

- **MLflow** (full 3.17.1, SQLite): `scripts/mlops_demo.py` in a throwaway store imported **30 runs / 642 metrics**; a second import created 0 and found 30; verification compared every metric with its source file: all match. The Stage 3C-2 run carries `smart.decision = DO NOT ADVANCE`, `smart.provenance = imported_historical`, `smart.human_validated = false`. A live run records the corpus, per-batch, index and freeze fingerprints automatically.
- **DVC:** not installed in this session's environment, so it was not re-run. Stage 6B evidence stands (DVC 3.67, dev-LSA backend: `dvc repro`, `status`, `checkout`, hash of the rebuilt `index.faiss` equal to the recorded one; checkpoint `add/push/pull` round trip). **New finding:** your repository has no `.dvc/` directory, so `dvc repro` will say it is not a DVC repository until you run `dvc init` (documented in `docs/REPRODUCIBILITY.md`; `verify_mlops.py --check-dvc` reports it as SKIP with that command). The real MiniLM backend was never run through DVC.

## 5. GitHub CI readiness (deliverable 5)

Audit of `.github/workflows/ci.yml` and `heavy.yml`, and what changed:

| # | Finding | Fix |
|---|---|---|
| 1 | Actions pinned to movable tags (`@v4`, `@v5`) | pinned to full commit SHAs (checkout v4.4.0, setup-python v5.6.0), resolved with `git ls-remote`; Dependabot proposes monthly bumps |
| 2 | Python dependencies installed from `>=` ranges: each run could differ | hash-checked locks `requirements-ci.lock` and `requirements-ci-mlops.lock` (`uv pip compile --universal --generate-hashes`), installed with `--require-hashes`; verified by installing the CI lock on Python 3.12 and 3.13 |
| 3 | `ruff` floated (`>=0.5`) | pinned to 0.17.1 through the lock |
| 4 | Checkout kept the Git credential in `.git/config` | `persist-credentials: false` |
| 5 | No independent Windows check although the target machine is Windows | new `windows` job (`windows-latest`: integrity, retrieval + Flask + MLOps tests, `verify_mlops.py`) |
| 6 | Seven separate jobs, so branch protection would need seven checks | one `CI gate` job (`needs` all, `if: always()`); `needs` passed through an environment variable, not interpolated into the script |
| 7 | New scripts not linted | `verify_compose.py` and `mlops_demo.py` added to the strict lint/format list |
| 8 | Heavy workflow could pile up runs | `concurrency` group added; its MLflow install uses the lock |
| 9 | Hash-pinned data would fail on any CRLF checkout (Windows runner, your clone) | `.gitattributes` forces LF (see item 8) |
| 10 | Nothing asserted the supply-chain rules | 5 tests: SHA pins, credentials, least privilege per workflow and job, no `pull_request_target`/`workflow_run`/artifacts/secrets/untrusted interpolation, locks hashed and lean, Windows + gate jobs |
| 11 | Normal CI already satisfied | confirmed and asserted: no GPU, no Ollama (unreachable address), no paid key, HF/Transformers offline, no candidate code, no artifact upload |
| 12 | Heavy workflow unpinned PyTorch index | left as is deliberately: it is manual/weekly, uses the CPU index and is not part of the pull-request gate |

Dry run of the CI command set on **Python 3.12.3 installed from the hash-checked lock** (Linux): lint clean, integrity OK, retrieval 137 passed / 1 skipped, evaluation 428, Flask 199 / 5 skipped, static code-eval 42 / 1 skipped, MLOps 62. Python 3.13: MLOps 62 (with MLflow), others as in section 7.
It is a dry run, not a GitHub run: runner images, the real Docker base, Windows behaviour and action versions are untested.

## 6. First push and first CI run (deliverable 6)

Full procedure with findings and failure modes: `docs/GITHUB_FIRST_PUSH.md`. The short form (after you decide public vs private):
```
cd /d D:\Projects\SMART-MOCK-INTERVIEW
git add -n . | find /c "add "                      :: ~1004 files (dry run)
git switch -c ci/mlops-stages-6-7
git add .gitignore .gitattributes && git commit -m "Repo hygiene: restore ignore rules, force LF for hash-pinned data"
(then the four further explicit `git add` + `git commit` groups in the document)
git push -u origin ci/mlops-stages-6-7             :: PUBLISHES
gh pr create --base main --head ci/mlops-stages-6-7 --title "MLOps stages 6-7"     :: PUBLISHES
```
**I stopped here by instruction:** a push needs your credentials and your decision about a publicly readable repository.

## 7. Regression results (deliverable 8)

Linux, Python 3.12.3 installed from `requirements-ci-mlops.lock` (the CI environment), unless stated:

| Check | Command | Result |
|---|---|---|
| Retrieval | `pytest tests/retrieval` | 137 passed, 1 skipped (real MiniLM absent) |
| Evaluation | `pytest tests/evaluation` | 428 passed |
| Flask integration (legacy routes, demo, journeys) | `pytest tests/app` | 199 passed, 5 skipped (real MiniLM) |
| Static code evaluation | `pytest tests/codeeval` | 42 passed, 1 skipped (needs a Docker code-check image; deliberately not run) |
| MLOps (observability, privacy, MLflow, startup safety, packaging, CI supply chain, docs) | `pytest tests/mlops` | **62 passed** (12 new in this stage; 50 before) |
| Same on Python 3.13, full MLflow | `pytest tests/mlops` | 62 passed |
| Python 3.13 without MLflow/torch | retrieval / evaluation / app / codeeval / mlops | 137 / 426 (2 skipped) / 199 / 42 / 48 (1 module skipped) |
| Integrity | `python scripts/check_integrity.py` | INTEGRITY OK (666 records; freeze v2; bench_v2) |
| Lint, format | `ruff check` (whole repo) / strict + `ruff format --check` (new files) | clean / 18 files formatted |
| Workflows | `actionlint .github/workflows/*.yml` | clean |
| Docker + Compose | `scripts/verify_compose.py --no-build` | 29 PASS, 0 FAIL |
| Browser | `scripts/stage6b_browser_smoke.py` against the container | 16/16 |
| Demo | `scripts/mlops_demo.py` | 5 demonstrated, 2 not run here (DVC not installed; Docker build deliberately not repeated), 0 failed |
| Windows validator | `validate_windows.ps1` under PowerShell 7 on Linux (paths adapted) | 23 PASS, 0 FAIL, 4 SKIP |

Total on the CI environment: 137 + 428 + 199 + 42 + 62 = **868 passed**, 7 environment skips, 0 failures. Legacy Flask routes, experimental-scoring opt-in, no candidate code on the host,
and "startup does not train" are covered by tests in those suites (`tests/app` golden routes, `tests/mlops/test_startup_safety.py`, `test_metrics_and_obs.py`).

## 8. Engineering audit (Mission 4): findings and fixes

| Area | Finding | Action |
|---|---|---|
| `.gitignore` | **Defect.** The working-tree file had lost the original rules (`.env`, `.venv/`, `.bot/`, `__pycache__/`, `Temp/`, `tmp/`, `output/`, `frontend/node_modules/`, `.agents/` ...). Before the fix `git status` listed your virtual environment, `node_modules`, `__pycache__` and the internal prompt file as untracked-and-addable | original rules restored + MLflow/DVC/archive rules kept; regression test |
| Line endings | **Defect.** No `.gitattributes`. Evidence (Linux): integrity passes with all text files LF and **fails** with all CRLF (`v5 curated_questions.csv hash differs...`). Git for Windows (`core.autocrlf=true`) would have produced CRLF checkouts | `.gitattributes` (`* text=auto eol=lf`, `.bat`/`.ps1` CRLF, binaries untouched); `check_integrity.py` now prints the cause and fix on failure; two tests |
| Docker volumes | **Gap.** With a read-only root filesystem an `INSTALL_ML=1` build had nowhere to keep the embedding model, and nothing stopped a silent download | `smart-hf-cache` volume at `/hf-cache`, `HF_HOME`, `HF_HUB_OFFLINE=1` default, one documented opt-in command; verified writable by uid 10001 |
| Metrics | `smart_build_info` appeared as two series with different label sets after a Prometheus scrape | one helper, one label set; regression test |
| Windows launcher | `verify_mlops.bat` always paused | `SMART_NO_PAUSE=1` honoured |
| Archives | `stage6ab_bundle.zip`, `stage7a_sync.zip` (delivery archives) in the project root; `audit/retrieval/labelling_and_authoring_archive.zip` (unreferenced, duplicates 63 extracted files) | `*.zip` ignored; the two root zips moved to the ignored `tmp/` (I cannot delete in your folder without a prompt; remove `tmp\*.zip` whenever you like). The audit zip is untouched |
| Large artifacts | `results/siamese_bilstm.pt` (3.8 MB) is tracked since the first commit. Everything else that would be added is text/PNG, largest 4.9 MB; total about 78 MB / 1004 files | left as is (history already contains it; moving it to DVC is your call) |
| Credentials | pattern scan (OpenAI/Anthropic/AWS/GitHub/Slack/Google key shapes, private keys, personal email addresses) over every file `git add .` would add: none. `report_delivery/.env` is ignored | none needed; a test scans `src/`, `scripts/`, workflows, Docker files for credential shapes and machine paths |
| Candidate data | `results/demo_sessions/` is ignored and untracked; CI uploads no artifacts | none |
| Hard-coded paths | none in code, workflows or Docker files; `D:\Projects\...` appears only in user-facing instructions in old reports | test added |
| Documentation | stale statements: "published-port reachability not verified", "CI installs requirements-ci.txt", "dependencies not hash-pinned"; no first-push guide | updated: MLOPS.md (CI, verification table, limitations), REPRODUCIBILITY.md (line endings, locks), TROUBLESHOOTING.md (8 new rows), README, GITHUB_FIRST_PUSH.md, a link/command-existence test |
| Startup / ports | host app default 5000 (`SMART_PORT`), Compose publishes `SMART_PUBLISH_PORT` (5000), `verify_compose.py` uses 5099 and refuses to start if the port is busy | documented in TROUBLESHOOTING |
| Not changed on purpose | the 3C-2 `results.json` records the v1 freeze-manifest hash (the v2 manifest supersedes it; both stored as MLflow params); existing evaluation tests rewrite nine frozen files byte-identically (mtimes change, hashes do not) | pre-existing, no frozen file edited |

## 9. Remaining blockers (deliverable 9)

1. **A human must push.** Needs your GitHub credentials and your decision on the publicly readable repository. Until the first run, CI is unproven.
2. **Windows is unproven.** Run `validate_windows.ps1 -Mlflow -Docker -Tests` and `verify_compose.py`; the `windows` CI job is the independent second check.
3. Docker verified only on a substitute base image; the official base, Docker Desktop/WSL2, `INSTALL_ML=1` and the Ollama profile are untested.
4. `dvc init` has not been run in the real repository; DVC with the real MiniLM backend is untested.
5. No vulnerability scanning (`pip-audit`, Trivy, CodeQL), the Docker lock is version-pinned but not hash-checked, the base is pinned by tag, no image is published.
6. Public deployment remains blocked: no authentication/TLS/rate limiting, in-process legacy sessions, plaintext session files, candidate-code execution only in a hardened ordinary container (not a sandbox), metrics reset on restart. Nothing here was deployed.
7. Scores are not validated against human graders; the experimental evaluator is DO NOT ADVANCE.

## 10. Recommendation for the final portfolio milestone (deliverable 10)

1. Run the Windows validator, fix anything it reports, then do the first push on a branch and get `CI gate` green (the quickest way to turn "linted" into "proven").
2. Then the one piece of evidence that the project cannot produce for itself: a **small human-validation study** of the legacy and experimental scoring (blind review sheets for bench_v2 and the 3C-2 sample already exist in `data/evaluation/stage3c3`). Present results with the abstention/DO NOT ADVANCE history, not around it.
3. Finish with a short README "evidence" section linking CI badge, the MLflow historical runs, the demo transcript, and the limitations above. Do not add features before 1 and 2.

## 11. Files added or changed in this stage

New: `.gitattributes`, `.github/dependabot.yml`, `requirements-ci.lock`, `requirements-ci-mlops.lock`, `scripts/validate_windows.ps1`, `scripts/verify_compose.py`, `scripts/mlops_demo.py`,
`docs/GITHUB_FIRST_PUSH.md`, `docs/MLOPS_DEMO_TRANSCRIPT.md`, this report.
Changed: `.gitignore`, `.github/workflows/ci.yml`, `.github/workflows/heavy.yml`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `requirements-ci.txt`, `scripts/check_integrity.py`,
`src/mlops/obs.py`, `verify_mlops.bat`, `README.md`, `docs/MLOPS.md`, `docs/REPRODUCIBILITY.md`, `docs/TROUBLESHOOTING.md`, `tests/mlops/*`.
No file under `data/`, no frozen manifest and no result file was edited.
