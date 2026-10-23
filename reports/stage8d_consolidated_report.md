# Stage 8D consolidated report: legacy-isolation fix, real MiniLM index verification, DVC reproducibility, GitHub readiness

Date: 2026-10-17. Nothing was committed, staged, pushed, published or uploaded; repository visibility and Git history are untouched; no model was downloaded, loaded or trained
(the real MiniLM model is not available to this session); no remote storage exists or was configured; frozen data and historical results are unchanged.
**Still true: nothing in this project is validated against human graders.**

Evidence labels: *Reported by you* (your Windows runs), *Verified here* (Linux; or read-only against your real files through the linked folder), *Not verified* (needs your machine).

## 0. Verdict

| Mission | Status |
|---|---|
| 1. Legacy-isolation test | **Fixed permanently** and covered by a regression test. |
| 2. Real MiniLM `qk_concise` index | **Not built (no model here).** A verifier/builder script was written and tested offline; the three existing real indexes (`q`, `qk`, `qka`) were verified against the current corpus on your real files. Windows commands below. |
| 3. DVC reproducibility | Strengthened and **verified on Linux** (15 checks, including pre-existing frozen indexes surviving repro). Not run in your repository or on Windows. |
| 4. GitHub readiness | All local checks pass; the five commit groups were checked to cover every publishable file. **Never run on GitHub.** |
| 5. Final verification | 980 passed, 7 skipped, 0 failed (Linux, hash-locked Python 3.12). |

## 1. Final regression results

* Reported by you before this stage: 968 passed, 1 failed, 8 skipped (the failure: backup files inside `tmp/`).
* **Root cause:** `test_no_application_code_imports_the_modular_package` walked the whole repository (`ROOT.rglob("*.py")`) and only excluded a few path prefixes, so a backup copy of an old `main/app.py` under `tmp/` (which legitimately contained an old import) was treated as application code. Classification: outdated assertion / test-scope defect (not an implementation defect).
* **Fix** (`tests/evaluation/test_stage3c1_legacy_untouched.py`): the scan now walks only active application source and prunes, at any depth, `tmp`, `Temp`, anything named `*backup*` or `*venv*`, `results`, `output`, `mlflow`, `mlruns`, `node_modules`, `__pycache__`, `.git`, `.dvc`, `dvc_storage`, build output, `audit`, `tests`, `scripts`, and the modular package itself (the same exclusions as before, now by directory name instead of prefix). It also asserts that the scan really covers `main/app.py` and `src/components/interview_session.py`, so it cannot silently scan nothing.
* **Regression test** `test_backup_and_scratch_copies_do_not_cause_false_failures_but_real_modules_are_still_caught`: plants forbidden imports in `tmp/backup_7b/...`, `backups/`, `*_venv/`, `results/`, `scripts/`, `tests/` and the modular package (must be ignored), then plants them in `src/components/leak.py` in three import spellings and in `main/app.py` (must be detected), and keeps the one allowed bridge (`src/demo/experimental.py`) exempt.
* Final run (clone of your synced folder, `core.autocrlf=true`, Python 3.12 from the hash-locked requirements):

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| retrieval | 161 | 1 | 0 |
| evaluation | 445 | 0 | 0 |
| app (Flask) | 201 | 5 | 0 |
| codeeval | 72 | 1 | 0 |
| mlops | 101 | 0 | 0 |
| **Total** | **980** | **7** | **0** |

Also: `mlops` job (`test_tracking.py`) 14 passed; lean "windows" command set (no MLflow) 448 passed / 8 skipped; `INTEGRITY OK`; Ruff lint, strict lint and format all clean (with and without an `mlflow/` folder); `PUBLICATION CHECK OK`; tests leave the working tree clean. Skips are environmental (no model cache, no Docker daemon). Your Windows machine will skip fewer. **Authoritative Windows result:** `python -m pytest tests -q -rf -p no:cacheprovider`.

## 2. Real MiniLM index verification

**Built here: no.** The model is not in this session's environment and nothing may be downloaded. What was done instead:

* New `scripts/verify_real_index.py` (read-only by default; `--retrieval` and `--build` opt in). It forces `HF_HUB_OFFLINE=1`, never overwrites an existing index directory, and hashes every other index plus the recorded Stage 2C results before and after.
* Checks it performs: corpus fingerprint (loaded corpus = manifest = recorded Stage 2C rankings); model revision and the sha256 of every cached model file against `data/retrieval/model_provenance.json`; index metadata (corpus fingerprint, `doc_mode == qk_concise`, embedder model/dim/256 word-pieces/normalised, row order equals corpus order); `index.faiss` sha256 against the manifest recorded beside it; FAISS vector count and dimension; with `--retrieval`/`--build`: the service loads the existing index **without rebuilding it**, semantic mode (not BM25 fallback), top-1 agreement and score difference against the recorded Stage 2C `dense_qk_concise` rankings for all 224 dev and challenge queries (pass: at least 99% top-1 agreement and at most 0.002 score difference), self-retrieval of 40 sampled corpus questions (at least 38 first); the model-cache listing is unchanged (no download); frozen artifacts byte-identical.
* **Verified here against your real files** (read through the linked folder, no model loaded): corpus fingerprint `db776e9fa135...` equals the manifest, the recorded rankings and the fingerprint inside all three existing real indexes. For each of `minilm_d14b0073_q`, `_qk`, `_qka` the corpus fingerprint, document format, embedder configuration (MiniLM-L6-v2, 384-d, 256 word-pieces, normalised), row order and the `index.faiss` checksum against its manifest **all pass** (FAISS vector count skipped: FAISS is not installed in the shell I can reach). Those directories were not modified.
* The expected name of the missing index is `minilm_d14b0073_qk_concise` (embedder configuration id `d14b0073c4bfe08b`, the same as the three existing ones). The recorded model revision is `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
* Cost: the three earlier real builds took 10.7 to 16.3 s of embedding for 666 documents on your CPU, so expect about 15 s plus model load. No download. About 1 MB on disk.
* Tests: 12 offline tests (`tests/retrieval/test_stage8d_real_index_verifier.py`) build hand-made index directories and prove that each kind of mismatch (corpus fingerprint, format, embedder, row order, manifest checksum, tampered file, missing files) is detected, that the comparison with recorded rankings flags disagreement, and that the read-only run neither fails without the model nor creates the index.

**Not verified:** the actual build, its checksum, and real retrieval from it. Run on Windows (section 6, step 3).

## 3. DVC reproducibility

Verified here (Linux, DVC 3.67.1, in a temporary copy of the files Git would publish; your repository, `dvc.lock` and `params.yaml` are untouched; the offline stand-in embedder replaces MiniLM for the run). `scripts/verify_dvc.py` now performs 15 checks, all passing:

| Check | Result |
|---|---|
| `dvc init` creates only `.dvc/config` | pass |
| `params.yaml` declares the served format (`qk_concise`) | pass |
| `dvc repro` runs the integrity check then the index build | pass |
| the pipeline **built the declared document format** (index metadata equals params) | pass |
| index checksum equals the one recorded beside it | pass |
| `dvc status` up to date; a second `dvc repro` leaves `dvc.lock` identical | pass |
| `dvc status` **reports a real change** to a dependency, and is quiet again when undone | pass |
| `dvc repro --force` rebuilds a **byte-identical** `index.faiss` | pass |
| a **pre-existing frozen index directory** (stand-in for your real `q`/`qk`/`qka`) survives `repro`, `repro --force` and `checkout` byte-identical | pass |
| dataset and source dependencies (16 files) byte-identical after every run | pass |
| outputs deleted, `dvc checkout` restores a byte-identical index | pass |

Environment: DVC is **not installed** on your Windows machine (reported). Install into the environment you use for the project, from a normal PowerShell; it adds one package and downloads no model: `python -m pip install "dvc>=3,<4"`. `dvc init` has not been run in your real repository; it creates `.dvc/config` and a `.dvc/.gitignore` only, uploads nothing, and no remote is configured. Params match: `params.yaml` `backend=minilm`, `doc_mode=qk_concise`, `model=sentence-transformers/all-MiniLM-L6-v2`, equal to what the application serves (`check_versions.py`: 11 PASS).
**Not verified:** DVC on Windows; `dvc repro` with the real model; DVC adding your real `data/retrieval/index` (about 5 MB) to its local cache the first time.

## 4. GitHub publication inventory

* **Candidate:** 1013 files built from your folder (git's own rules), 42 already tracked. Committed to a scratch repository and cloned with `core.autocrlf=true`: every file present; CRLF-pinned files keep their bytes; LF-pinned files stay LF; `.bat`/`.ps1` stay CRLF.
* **Publication safety** (`check_staged.py --worktree`): nothing blocked or oversized, no credential-shaped strings, no personal paths. Earlier audit unchanged: no model weights, databases or FAISS files published (`.gitignore`/`.dockerignore` rules are enforced by tests), the only binary is the 3.8 MB checkpoint committed in the first commit, no virtual environments, no `tmp/`, no `results/demo_sessions/`, no real interview reports, no `.dvc/config.local`.
* **Frozen data integrity:** `INTEGRITY OK`; `check_versions.py` 11 PASS; the 13 CRLF-pinned files are protected by `.gitattributes` `-text`; no pinned byte was changed in Stages 8A to 8D.
* **Dependency locks:** `requirements-ci.lock` (39 packages, 1003 hashes) and `requirements-ci-mlops.lock` (102 packages, 2545 hashes) are installed with `--require-hashes`. `requirements-docker.lock` (23 packages) is **version-pinned but not hash-pinned** (known and accepted; installing the image is the only consumer).
* **CI workflow:** `permissions: contents: read` at the top of `ci.yml` and `heavy.yml`; actions pinned to commit SHAs; one required **CI gate** job (`ci-ok`); Python 3.12 on `ubuntu-latest` and `windows-latest` (plus a 3.13 test leg); no GPU, Ollama or paid API in normal CI. `verify_real_index.py` joins the strict lint/format lists.
* **Defects found and fixed in this recheck:** (a) the lint/`mlflow/` folder classification (Stage 8C); (b) the five commit groups left `run_all.bat` reported as modified, because it was converted to CRLF in your working tree while Git stores LF. It is now listed in commit 2 so `git status` is empty at the end; (c) the branch name now says stages 6-8.
* **Commit-group coverage check:** staged the five groups of `docs/GITHUB_FIRST_PUSH.md` in a scratch repository built from the candidate: group 1: 5 files, group 2: 243, group 3: 634, group 4: 15, group 5: 99. The only files outside them are the 15 that your repository **already tracks** (for example `LICENSE`, `frontend/`, `compare/`, `notebooks/EDA.ipynb`, `report_delivery/.gitignore`). On your real folder, the only status entry not covered by any group was `run_all.bat`, now covered.

## 5. CI readiness

Simulated end to end on the clone (section 1): lint, strict lint/format, integrity, five test suites, the `mlops` job, the lean Windows job commands, publication check, DVC verification, static Docker/Compose checks (`compose file valid`, no zip/db/faiss in Docker COPY directories), and `validate_windows.ps1 -Mlflow -Dvc` under PowerShell 7 (24 PASS, 0 FAIL, 3 SKIP: no index built, DVC repo not initialised, no Docker engine here).
Remaining first-run risks are listed in `docs/GITHUB_FIRST_PUSH.md` section 3 (Windows runner quoting, the real Docker base build, pinned wheels for the runner platform, action SHAs). **No remote run has happened.**

## 6. Exact commands requiring your action

```powershell
cd D:\Projects\SMART-MOCK-INTERVIEW

# 1. Confirm the regression suite on Windows (backups outside the repository are no longer required, but harmless)
python -m pytest tests -q -rf -p no:cacheprovider

# 2. Read-only checks (no model load, no download)
python scripts\check_integrity.py
python scripts\check_versions.py
python scripts\verify_real_index.py
python scripts\check_staged.py --worktree

# 3. Build and verify the missing served-format index (about 15 s; offline; refuses to overwrite; model must already be cached)
python scripts\verify_real_index.py --build
#    (if the index already exists, or after a manual build)
python scripts\verify_real_index.py --retrieval
python scripts\mlflow_track_retrieval.py --backend minilm --local-files-only

# 4. DVC (installs one package; uploads nothing)
python -m pip install "dvc>=3,<4"
python scripts\verify_dvc.py                 # temporary copy; does not touch your repository
python -m dvc init                           # only after step 3 passes
python -m dvc repro                          # keeps your existing indexes; caches them locally
python -m dvc status                         # expect: Data and pipelines are up to date.

# 5. Final local gate before any commit
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Mlflow -Dvc -Tests
```
Send me the output of any step that does not end in a pass.

**Publishing (nothing below has been run or approved; it needs your explicit decision):** follow `docs\GITHUB_FIRST_PUSH.md`:
1. step 0 checks; 2. `git switch -c ci/mlops-stages-6-8`; 3. five commits, each preceded by `python scripts\check_staged.py` (commit 4 also takes `.dvc/config`, `.dvc/.gitignore` and `dvc.lock` if you ran `dvc init`/`dvc repro`; run `check_staged.py` again); 4. **[PUBLISHES]** `git push -u origin ci/mlops-stages-6-8` and `gh pr create ...`; 5. wait for the **CI gate** check, then require it in branch protection. Decide first whether the repository should be public or private.

## 7. Remaining blockers

1. **Build and verify the `qk_concise` index with the real model** (step 3). Until then the application builds it on its first search (about 15 s cold start) and no checksum for the served index is on record.
2. **DVC has not run on Windows or with the real model**; `dvc init` is pending.
3. **First real GitHub Actions run**: needs your approval to push.
4. Container with local ML models and RAG (`INSTALL_ML=1`) remains unverified; the lean image is the verified one.
5. No human-validated evaluator accuracy; the real modular evaluator still fails its frozen abstention criterion (45% vs 40%); code assessment covers two question types.
6. Decisions for you: public or private repository; the two author e-mail addresses already visible in the public history; whether to keep Windows backups outside the repository (the test no longer cares).

Maturity: **verified on your Windows machine (reported):** lean Docker image and Compose (29/29), MLflow import and verification, integrity, publication audit. **Verified on Linux, with a stand-in embedder or a clone:** full regression suite, CI commands, DVC pipeline behaviour. **Verified read-only on your real files:** corpus fingerprint and the three existing real indexes. **Not verified:** the served-format real index, Windows DVC, GitHub Actions, full-ML container. **Not production-ready:** authentication/TLS, public deployment, code execution, LLM grading.
