# First GitHub push and first CI run (Stages 7A-7B)

Nothing in this repository has been pushed, published or changed on GitHub by any automated step. This page is what **you** run, in order, when you decide to. Every command that
touches the remote is marked **[PUBLISHES]**. Run them in a Windows `cmd` prompt in the project folder.

## What the audit found (Stage 7B, 2026-10-17, read-only inspection of your working tree)

| Finding | Detail and what was done |
|---|---|
| Remote | `origin` = `https://github.com/mohanram-45/Smart-Mock-Interview.git`, one branch `main` at `2639cdd`; local `main` is level with it. **The remote is publicly readable**, so everything pushed there is public. Decide public/private before pushing (next section) |
| Work not yet in Git | 6 modified tracked files and about 950 new files (about 58 MB, largest 5.0 MB). The whole publishable tree is about 990 files / 72 MB. No file is near GitHub's 50 MB warning or 100 MB limit |
| Credentials | pattern scan of every file that would be published (OpenAI, Anthropic, GitHub, AWS, Google, Slack, Hugging Face, private-key shapes, bearer tokens, `password=`/`api_key=` assignments): **none**. `.env` and `report_delivery/.env` are git-ignored. The only "secret" string is the deliberately fake candidate answer in `scripts/mlops_demo.py` |
| Candidate / personal data | every candidate answer in the published data is a synthetic benchmark answer (`bench_v2/answers.jsonl` is AI-authored); all five human-review sheets are **blank** (no reviewer input exists). `results/demo_sessions/` (real session answers) is ignored. **Fixed:** your Windows user name was recorded in `data/retrieval/model_provenance.json` and `data/evaluation/stage3b/ollama_probe.json` (now `~`; backups in `tmp\backup_7b\`; the two producer scripts now redact it) |
| `.gitignore` gaps (fixed) | `mlops_venv/`, `app_venv/`, `.dvc/config.local` (can hold remote credentials), `dvc_storage/`, `*.faiss`, `*.pt`, `*.db` and the 28 MB of journey-script screenshots under `data/evaluation/*/screenshots/` were not ignored. All are now; a test guards them |
| Line endings (7A fix was incomplete, now fixed) | 13 hash-pinned files are stored with Windows CRLF line endings (for example `retrieval_benchmark_minilm.json`). The Stage 7A rule `* text=auto eol=lf` would have converted them on commit and broken their checksums in the published repository. They are now exempt (`-text` in `.gitattributes`); a test finds any pinned CRLF file that is missing from that list |
| Tests that failed in a fresh clone (fixed) | (1) the provenance test needed the git-ignored FAISS index (it now builds the offline stand-in and removes it); (2) the "read-only" Ollama probe test overwrote a committed evidence file on every run (it now writes to a temp file) |
| Commit author identity | the existing history already shows two author e-mail addresses on the public remote (`git log --format="%an <%ae>"`). Check what your next commits will use (step 0) |
| Archives and large binaries | `*.zip` is ignored (the `stage*.zip` hand-off bundles and `audit/retrieval/labelling_and_authoring_archive.zip` stay local). `results/siamese_bilstm.pt` (3.8 MB) is already tracked since the first commit and stays in history; moving it to DVC is optional and not done |
| Paths in `audit/` | 61 audit briefs and outputs mention `/home/claude/` (the AI authoring sandbox). Harmless, left as provenance |
| Fresh-clone simulation | the exact publishable tree was committed to a scratch repository and cloned with `core.autocrlf=true` (what Git for Windows does): every file present, pinned bytes identical, `ruff` clean, integrity OK, 876 tests passed in that simulation (Stage 8 adds tests: 969 collected locally, re-simulate before relying on the number) from the hash-locked requirements (see the Stage 7B report). **This is a simulation on Linux, not a GitHub run** |

## Public or private (your decision)

The corpus, AI-authored labels, audit material and reports would all become public. They contain no credentials, no personal data beyond your name in the README author line, and no
real candidate answers, but they are working material. To make the repository private first: GitHub > Settings > General > Danger Zone > *Change visibility*, or
`gh repo edit mohanram-45/Smart-Mock-Interview --visibility private --accept-visibility-change-consequences` **[PUBLISHES a setting change]**. Private repositories use your Actions minutes quota.

## 0. Before committing (local, nothing is changed)

```bat
cd /d D:\Projects\SMART-MOCK-INTERVIEW
git status --short
git config user.name
git config user.email
python scripts\check_integrity.py                  :: must print INTEGRITY OK
python scripts\check_versions.py                   :: data/index/params/model consistency: must print no FAIL (Stage 8)
python scripts\verify_real_index.py                :: read-only: corpus, model cache, existing indexes; no model load, no download (Stage 8D)
python scripts\check_staged.py --worktree          :: what `git add -A` WOULD add: must print PUBLICATION CHECK OK
powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Tests
```
* If `git status` lists `.bot\`, `mlops_venv\`, `app_venv\`, `node_modules\`, `__pycache__\` or `tmp\`, stop: `.gitignore` is not the Stage 7B one.
* If you do not want your personal e-mail address in new commits, set the GitHub no-reply address first (GitHub > Settings > Emails shows it) with
  `git config user.email "<id>+mohanram-45@users.noreply.github.com"` and tick *Block command line pushes that expose my email*. Existing commits are not rewritten.
* Optional DVC repository (a local, empty config; uploads nothing): `pip install "dvc>=3,<4"`, then `dvc init`, then include `.dvc/config` in commit 4 below. See `docs/REPRODUCIBILITY.md`.

## 1. Commit on a branch (local)

Use a branch, never `main`, so the first CI run happens in a pull request. Run the safety check before **each** commit; every command below names explicit paths (no `git add .`).

```bat
git switch -c ci/mlops-stages-6-8

git add .gitignore .gitattributes .dockerignore .dvcignore .env.example
python scripts\check_staged.py
git commit -m "Repo hygiene: ignore rules, byte-exact pinned files, docker context"

git add main src tests scripts requirements.txt requirements-llm.txt requirements-rag.txt pyproject.toml run_all.bat run_demo.bat verify_windows.bat verify_mlops.bat
python scripts\check_staged.py
git commit -m "Application, retrieval, evaluation, demo, code check, MLOps modules and tests"

git add data audit results/stage3c1_comparison.json
python scripts\check_staged.py
git commit -m "Corpus, manifests, frozen evaluation data and audit evidence"

git add .github Dockerfile docker docker-compose.yml dvc.yaml params.yaml requirements-docker.in requirements-docker.lock requirements-docker-ml.txt requirements-ci.txt requirements-ci.lock requirements-ci-mlops.lock requirements-mlops.txt
python scripts\check_staged.py
git commit -m "CI, Docker, DVC pipeline and hash-locked requirements"

git add docs reports README.md
python scripts\check_staged.py
git commit -m "Documentation and stage reports"

git status --short                                  :: must now be empty (run_all.bat is listed in commit 2 only to refresh its status: it was converted to CRLF in the working tree, Git stores it as LF and sees no change)
git log --oneline origin/main..HEAD                 :: your 5 commits, nothing else
```
If `check_staged.py` prints `FAIL`, do not commit: `git restore --staged .` un-stages everything (it changes nothing in your files), fix the cause, and stage again. To throw away
all five local commits before pushing (nothing has left your machine): `git switch main` then `git branch -D ci/mlops-stages-6-8`.

## 2. Push the branch and open the pull request  **[PUBLISHES]**

```bat
git push -u origin ci/mlops-stages-6-8
gh pr create --base main --head ci/mlops-stages-6-8 --title "MLOps stages 6-8: MLflow, DVC, Docker, CI, retrieval evidence" --body "First CI run. See docs/GITHUB_FIRST_PUSH.md."
```
No GitHub CLI? Open the link `git push` prints. Pushing a branch does not start CI by itself (`push` triggers only on `main`); the pull request does (`pull_request`). Watch it on the
pull request page, or `gh run watch`. Expect eight checks: *Lint and format*, *Dataset and frozen-experiment integrity*, *Tests (Python 3.12)*, *Tests (Python 3.13)*, *MLflow tracking tests*,
*Windows smoke (lean)*, *Docker image*, and finally **CI gate**.

## 3. What the first run can still get wrong

None of these has been executed on GitHub. In order of likelihood:

| Job | Possible failure | What it means / fix |
|---|---|---|
| `windows` | a path, quoting or console-encoding issue the Linux simulation could not see | open the failing step; for the integrity step, `git ls-files --eol data/curated data/raw` should show `w/lf` for the curated CSVs and `w/crlf` for `data/raw` |
| `docker` | the real `python:3.13-slim-bookworm` base differs from the substitute used in the sandbox | the build log names the failing `RUN` line; the Dockerfile only uses `useradd`, `groupadd` and `pip` |
| `docker` | the health check starts before the app is ready | the loop retries for 60 s; raise it in `ci.yml` if the runner is slow |
| `tests` 3.13 | a pinned wheel missing for the runner platform | the 3.13 lock install was verified on Linux only |
| `lint` | a ruff rule newer than the pinned 0.17.1 | the lock pins it; nothing floats |
| any | an action commit SHA GitHub cannot resolve | re-resolve it with `git ls-remote https://github.com/actions/<name> refs/tags/<tag>` (docs/MLOPS.md) |

`heavy.yml` never runs on a pull request. Run it once by hand (Actions > *Heavy checks* > Run workflow) after the normal CI is green; it downloads about 90 MB of MiniLM and CPU PyTorch.

## 4. After it is green

1. Settings > Branches (or Rules > Rulesets) > protect `main`: require a pull request and require the status check **`CI gate`** (the one job that fails unless every other job passed). The check
   only appears in GitHub's picker after it has run once, which is why this step comes after the first run. Also disallow force pushes.
2. Merge the pull request (GitHub UI, or `gh pr merge --squash`) **[PUBLISHES]**. Squashing keeps `main` to one commit per pull request; the five commits above remain on the branch.
3. `git switch main` and `git pull`.
4. Settings > Code security: enable Dependabot alerts if you want vulnerability notices (`.github/dependabot.yml` only proposes action and base-image bumps).

## What stops this from being "production CI"

No vulnerability scanning (add `pip-audit` and CodeQL), the Docker lock is version-pinned but not hash-checked, the image base is pinned by tag not digest, no image is published
anywhere, and nothing is deployed (continuous integration only). All intentional for a local portfolio project.
