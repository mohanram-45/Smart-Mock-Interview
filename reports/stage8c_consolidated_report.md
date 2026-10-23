# Stage 8C consolidated report: Windows regression fixes, DVC and real-index status, Docker/MLflow milestones, CI readiness

Date: 2026-10-17. Nothing was committed, staged, pushed, published or uploaded; repository visibility and Git history are untouched; no model was downloaded, trained or run
(no MiniLM, no Ollama/Qwen); no dataset or checkpoint left your machine; frozen data, frozen benchmark results and grading policy are unchanged.
**Still true: nothing in this project is validated against human graders.**

Evidence rules used below. *Reported by you* = your Windows run (the pytest output itself was not attached to this request, so I could not read the seven tracebacks;
I reproduced the failures instead). *Reproduced here* = Linux, with the Windows conditions emulated (see section 1). *Not verified* = needs your machine.

## 0. Verdict

| Mission | Status |
|---|---|
| A. Seven Windows failures | **Six root causes found, reproduced and fixed; the seventh (a third evaluation test) could not be identified without the full pytest output.** No test was weakened. One real CI defect (ruff import classification) was found on the way and fixed. A Windows re-run is needed to confirm. |
| B. DVC and real MiniLM `qk_concise` index | Everything checkable without the model passes. **The real `qk_concise` index does not exist yet** (only `q`, `qk`, `qka` do). Estimated cost of building it: about 15 s on CPU, no download. Not built by me (no model here). |
| C. Docker and MLflow | Windows Compose 29/29 and the MLflow import are treated as verified (your run). The difference between "container healthy", "interview with local ML models" and "RAG inside the container" is documented; the latter two are **not** verified. |
| D. CI readiness | All CI-job commands pass on a clone of your synced folder. Not yet run on GitHub. First-commit and PR instructions are in `docs/GITHUB_FIRST_PUSH.md` and section 7. |

## 1. Root cause and fix for each failed test

Method: the failures could not be reproduced on plain Linux (the same tree passes 967/967 with 7 environmental skips). I therefore ran the full suite with two emulated Windows conditions:
text files opened with the Windows defaults (cp1252 encoding, `\n` written as `\r\n`) and a slow local Ollama server listening on `127.0.0.1:11434` (as on your machine).
Together they reproduce **five of the six** named failures (two scope tests, the two Flask tests, the `.gitattributes` test); the sixth (`crlf_files` path separators) is a
Windows-only property found by reading the code.

| # | Test | Class | Root cause | Fix |
|---|---|---|---|---|
| 1 | `test_stage3c1_scope::test_heuristic_only_flag_true_in_sidecar_still_cannot_be_eligible` | fixture issue, OS-specific | the `_tampered` fixture wrote the modified sidecar with `Path.write_text`, which on Windows turns `\n` into `\r\n`; the sha256 recorded for the fixture was computed over `\n` bytes, so the loader (correctly) raised `ScopeIntegrityError` before reaching the assertion | the fixture writes exact bytes (`write_bytes`). The loader and its integrity gate are untouched; the test still asserts that a tampered, re-checksummed sidecar cannot unlock penalties |
| 2 | `test_stage3c1_scope::test_human_review_flag_blocks_eligibility` | same | same | same fix |
| 3 | a third evaluation test | **not identified** | the pytest output was not provided and no emulation reproduced a third failure; `tests/evaluation` and `tests/codeeval` pass 516/516 under both emulations with a live Ollama and no offline flags | see "Open item" below. I also made `test_stage3c0_assets::test_validator_detects_tampering` byte-exact for the same reason as #1 (it passed in the emulation, so it is a hardening, not a claimed fix) |
| 4 | `test_curated_integration::test_full_curated_interview_and_report` | environment dependence | `llm_report` reads `OLLAMA_HOST` once at import (default `127.0.0.1:11434`). With Ollama running on your PC the background report job asked the real model (timeout 180 s) while the test polls for 10 s, so the status stayed HTTP 202. Reproduced exactly with a fake slow Ollama | `tests/app/conftest.py` points the report LLM at a refusing port, so the rule-based fallback report is produced exactly as in CI. The tests still assert HTTP 200 and the report content; production code is unchanged |
| 5 | `test_legacy_characterisation::test_end_interview_is_async` | same | same | same fix. New regression tests: `tests/app/test_stage8c_hermetic_reports.py` (a listening server must receive zero requests) |
| 6 | `test_ci_and_packaging::test_gitattributes_forces_lf_for_hash_pinned_files_and_crlf_for_windows_launchers` | working-tree state, not a code defect | `run_all.bat` is tracked with LF in the index and the working tree (committed before `.gitattributes`). `.gitattributes` says `*.bat eol=crlf`, so a fresh checkout would be CRLF but your long-lived checkout kept LF. The test reads the working-tree bytes | I converted that one launcher to CRLF in your folder (backup in `tmp\stage8c_backup\`). It is not hash-pinned, and `git diff` shows no content change because Git normalises it. The assertion message now explains the cause |
| 7 | `test_startup_safety::test_integrity_check_explains_crlf_checkouts` | implementation defect (OS-specific) | `check_integrity.crlf_files()` returned `str(path.relative_to(root))`, i.e. `data\curated\v5\...` on Windows, while the test and the user-facing hint use `data/curated/...` | `as_posix()`. Not a hash-pinned file; no pinned byte was touched |

**Hash-pinned files and line endings:** no pinned file, manifest, corpus CSV or frozen benchmark was modified. The 13 CRLF-stored pinned files remain `-text`; the LF-pinned ones remain LF; `check_integrity.py` still reports `INTEGRITY OK`.

**Open item (failure 3):** run this and send me `tmp\eval_fail.txt`; the fix is then usually a few lines:
```powershell
cd D:\Projects\SMART-MOCK-INTERVIEW
python -m pytest tests\evaluation -q -rf --tb=long -p no:cacheprovider > tmp\eval_fail.txt 2>&1
```

**Additional CI defect found during this work (not in your list):** ruff's isort rule treats the directory `mlflow/` (the local tracking store, created on any machine that ran MLflow) as first-party. The strict lint step therefore **passed on your PC and failed on a fresh checkout** for `tests/mlops/test_stage8_consistency.py`. The CI simulation caught it (the earlier simulation ran in a folder without `mlflow/`). Fixed with `known-third-party = ["mlflow"]` in `pyproject.toml`, the import order corrected, and a regression test. Verified with and without an `mlflow/` directory.

## 2. Windows test results after the fixes

I cannot run Windows. What I can report:

| Run | Result |
|---|---|
| Your run before the fixes (reported) | 958 passed, 7 failed |
| Linux, plain, Python 3.12 from the hash lock | **967 passed, 7 skipped, 0 failed** (963 before this stage plus 4 new regression tests) |
| Linux with Windows text defaults emulated | all passed, including the 5 reproduced failures |
| Linux with a slow local Ollama listening and Windows text defaults | all passed |
| CI simulation on a clone of your synced folder (`core.autocrlf=true`) | see section 6 |

The first three rows of "fixed" rely on emulation. **The authoritative result is your re-run:**
```powershell
cd D:\Projects\SMART-MOCK-INTERVIEW
python -m pytest tests -q -rf -p no:cacheprovider
```
Expected: no failures except possibly the open item above.

## 3. DVC installation and verification status

* DVC is not in any requirements file by design (it is an optional tool; `docs/REPRODUCIBILITY.md`). Safe local install, into the environment you use for the project (no model download, no remote):
  ```powershell
  python -m pip install "dvc>=3,<4"
  python -m dvc --version
  ```
* Verified here (Linux, DVC 3.67): `verify_dvc.py` 6/6 in a temporary copy: `dvc init`, `dvc repro` (integrity check then index build with the offline stand-in), index hash equals the recorded sha256, `dvc status` up to date, delete outputs, `dvc checkout` restores a byte-identical index. Your repository is not touched by that script.
* Pipeline configuration (static checks, `scripts\check_versions.py`, 11 PASS on Linux): `params.yaml` `doc_mode=qk_concise` equals the format the application serves; `model=sentence-transformers/all-MiniLM-L6-v2` equals the application default; the manifest matches the loaded corpus.
* **`dvc init` has not been run in your real repository** (it creates `.dvc/config` only). Nothing in `dvc.yaml` can overwrite the existing indexes: the stage's outputs are `persist: true`, and the CLI writes a new directory per (model config, format).
* Not verified: DVC on Windows; `dvc repro` with the real model.

## 4. Real MiniLM `qk_concise` index status

What exists on your disk (read from the index metadata, nothing was modified):

| Index directory | Format | Built | Embedder config | Corpus fingerprint |
|---|---|---|---|---|
| `minilm_d14b0073_q` | q | 2026-10-14 | MiniLM-L6-v2, 384-d, max 256 word-pieces, sentence-transformers 5.6.0, torch 2.12.1+cpu | `db776e9f...` |
| `minilm_d14b0073_qk` | qk | same | same | same |
| `minilm_d14b0073_qka` | qka | same | same | same |
| `minilm_d14b0073_qk_concise` | **served format** | **does not exist** | | |

* The corpus fingerprint of the current corpus is `db776e9fa135...`, identical to the one recorded in all three real indexes, so those indexes are current with the corpus.
* Model provenance (`data/retrieval/model_provenance.json`): `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, `model.safetensors` sha256 `53aa5117...`, already in your Hugging Face cache. The embedder configuration id computed from the parameters (`d14b0073c4bfe08b`) equals the one in the existing indexes, so the new index will sit beside them as `minilm_d14b0073_qk_concise`.
* **Cost estimate before building:** the three existing builds recorded 10.7 to 16.3 s of embedding for 666 documents on your CPU (about 16 s in total including FAISS), plus model load of a few seconds. No download (`--local-files-only`). The embedding cache holds no MiniLM vectors in its top-level folder, so all 666 documents will be embedded once. Disk: about 1 MB.
* **Which index Flask uses:** with `SMART_RETRIEVAL_ENABLED=1` the service uses the `qk_concise` index and, if it is missing, builds it on the first search (about 15 s cold start, into the same new directory). So the application does not fall back to `q`, `qk` or `qka`, and the frozen ones are not overwritten. `POST /api/retrieval/diagnostics` shows `index_faiss_sha256`, `index_corpus_sha256` and `index_matches_corpus` for the index actually loaded.
* **Not verified (needs you):** the build itself, its hash, and a real retrieval through Flask. Commands in section 7.

## 5. Docker and MLflow verified milestones

Reported by you (Windows 11, Python 3.12.7) and treated as verified, **not re-run**:

* Official `python:3.13-slim-bookworm` image and Compose: 29/29 checks; healthy, ready, non-root, loopback-only binding, session persistence; no unintended training or model download.
* MLflow 3.17.1: 30 historical runs and 642 metrics verified; import idempotent. Imported metrics remain labelled as imported history, not new training.
* Corpus and frozen-benchmark integrity; publication audit.

What those results do and do not prove (documented in `docs/MLOPS.md`):

| Level | Verified? | Why |
|---|---|---|
| Container builds, starts, `/healthz` `/readyz` `/metrics`, non-root, loopback, persistence | **yes (your run)** | the 29 checks |
| A complete interview with local ML models inside the container | **no** | the image is deliberately lean: no PyTorch, no FAISS, no weights. Legacy BERT/Bi-LSTM scoring needs `INSTALL_ML=1` and a model volume; the lean image reports "scorer not set up" |
| Optional RAG retrieval inside the container | **no** | `/api/retrieval` needs `INSTALL_ML=1`, the MiniLM cache volume and `SMART_RETRIEVAL_ENABLED=1` |
| Live Qwen evaluation | **no** | separate optional Ollama service, off by default |

Preserved: privacy-safe monitoring (no answers or reference text in logs/metrics), non-root user, read-only root filesystem, loopback publishing, candidate-code execution disabled (`SMART_CODEEVAL_EXEC` not passed through, no Docker socket). An `INSTALL_ML=1` build downloads torch (large) and is your decision; it is not part of this stage.

## 6. GitHub CI readiness

Simulation: the publish candidate was rebuilt from your folder after syncing the Stage 8C files, committed to a scratch repository and cloned with `core.autocrlf=true` (what Git for Windows does).

| Check | Result |
|---|---|
| Candidate files committed; CRLF-pinned files keep their bytes, LF files stay LF, `.bat`/`.ps1` CRLF | pass |
| Ruff lint (`src main scripts tests report_delivery`), strict lint and format on the MLOps files | pass, with and without an `mlflow/` directory |
| `check_integrity.py` | INTEGRITY OK |
| `check_versions.py` | 11 PASS, 0 FAIL on Linux; run it on Windows to check your real indexes |
| Tests: retrieval, evaluation, app, codeeval, mlops | all passed (counts in the table below) |
| mlops job; lean "windows" job commands (no MLflow) | pass |
| `check_staged.py --worktree` (publication safety) | PUBLICATION CHECK OK: nothing blocked or oversized, no credential-shaped strings, no personal paths |
| `verify_dvc.py` | ALL PASSED |
| `validate_windows.ps1 -Mlflow -Dvc` under PowerShell 7 on Linux | 24 PASS, 0 FAIL, 3 SKIP (no index built, DVC repo not initialised, no Docker engine) |
| Workflow validity | `ci.yml` and `heavy.yml` parse; `permissions: contents: read`; one required `CI gate` job (`ci-ok`); no GPU, Ollama or paid APIs in normal CI |

Local tree safety: tests leave the tree clean; `check_staged.py` passes on the working tree. **Never run on GitHub.**

## 7. Exact PowerShell commands still needed

```powershell
cd D:\Projects\SMART-MOCK-INTERVIEW

# 1. Confirm the seven fixes on Windows (send me the output of any failure)
python -m pytest tests -q -rf -p no:cacheprovider
python -m pytest tests\evaluation -q -rf --tb=long -p no:cacheprovider > tmp\eval_fail.txt 2>&1   # only if step 1 still shows an evaluation failure

# 2. Consistency and publication checks (read-only)
python scripts\check_integrity.py
python scripts\check_versions.py
python scripts\check_staged.py --worktree

# 3. DVC (optional tool; installs one package, downloads no model)
python -m pip install "dvc>=3,<4"
python scripts\verify_dvc.py

# 4. Build the real served-format index (about 15 s, no download; model must already be in the Hugging Face cache)
python -m src.retrieval.cli build --backend minilm --doc-mode qk_concise --model sentence-transformers/all-MiniLM-L6-v2 --local-files-only
python scripts\check_versions.py            # now also checks the new index against the corpus
python scripts\mlflow_track_retrieval.py --backend minilm --local-files-only --dry-run

# 5. Only after step 4 passes: initialise DVC and reproduce through the pipeline (creates .dvc\config and dvc.lock; the existing indexes are kept)
python -m dvc init
python -m dvc repro
python -m dvc status

# 6. Real retrieval through Flask (optional)
$env:SMART_RETRIEVAL_ENABLED="1"; $env:SMART_QUESTION_SOURCE="curated"; $env:HF_HUB_OFFLINE="1"
python main\app.py       # then POST /api/retrieval/diagnostics and read the "versions" block
```

First commit and pull request (**these publish; nothing here has been run or approved**): follow `docs\GITHUB_FIRST_PUSH.md` exactly. In short: step 0 checks (`git status --short`, author identity, `check_integrity`, `check_versions`, `check_staged --worktree`, `validate_windows.ps1 -Tests`); five reviewed commit groups on branch `ci/mlops-stages-6-7` with `check_staged.py` before each; `git push -u origin ci/mlops-stages-6-7` and `gh pr create` marked **[PUBLISHES]**; wait for the `CI gate` check; then require that check in branch protection. Commit messages end with the attribution lines you approved for this session only if you want them.

## 8. Remaining blockers for a portfolio release

1. **Confirm the seven fixes on Windows** (and identify the third evaluation failure if it persists).
2. **First real GitHub Actions run**; nobody has seen the `CI gate` go green remotely. Needs your approval to push.
3. **Build and verify the `qk_concise` MiniLM index**, then a real-model retrieval through Flask; the DVC pipeline on Windows with the real model.
4. **Container with local ML models and RAG** (`INSTALL_ML=1`) is unverified; decide whether the portfolio claim is "lean demo image" (verified) or "full ML image" (not built).
5. **Human-validated evaluator accuracy does not exist**; the real modular evaluator still fails its frozen abstention criterion (45% vs 40%). Next step is the protocol in `docs/EVALUATOR_VALIDATION_PROTOCOL.md` with two independent reviewers.
6. Code assessment covers two shipped question types plus one documentation example; no sandbox suitable for public code execution (a normal Docker container is not one).
7. Housekeeping: git history exposes two author e-mail addresses on the public remote (decision for you); the 31/15 truncated-document records remain a documented retrieval weakness.

Maturity: **implemented and verified on your Windows machine:** Docker lean image, Compose, health/readiness, MLflow import. **Verified on Linux only:** tests, CI commands, DVC with the stand-in embedder. **Not production-ready:** authentication/TLS (none), public deployment, code execution, LLM grading.

## Test counts (clone of your synced folder, Linux, Python 3.12 from the hash lock)

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| retrieval | 149 | 1 | 0 |
| evaluation | 444 | 0 | 0 |
| app (Flask) | 201 | 5 | 0 |
| codeeval | 72 | 1 | 0 |
| mlops | 101 | 0 | 0 |
| **Total** | **967** | **7** | **0** |

Skips are environmental (no Hugging Face model cache for the real-MiniLM tests, no Docker daemon). The lean "windows" job command set (no MLflow) gives 436 passed, 8 skipped. The `mlops` job (`test_tracking.py`) gives 14 passed.
