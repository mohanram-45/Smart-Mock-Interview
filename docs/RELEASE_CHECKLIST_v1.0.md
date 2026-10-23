# v1.0 final verification checklist

Do the steps in order. Every command is run from the project root; a step is done only when its expected result is seen. Nothing here needs a paid service.

## A. Before touching Git (Windows, project root)
1. `git branch --show-current` -> `Update`. `git status --short` shows only the intended Stage 12-15 files (see the Stage 15 report for the list).
2. `.bot\Scripts\python.exe -m pytest tests -q` -> 0 failed (about 4 minutes).
3. `.bot\Scripts\python.exe -m ruff check src main scripts tests report_delivery compare` -> `All checks passed!`
4. `.bot\Scripts\python.exe scripts\check_integrity.py` -> `INTEGRITY OK`; `scripts\check_versions.py` -> 0 failed.
5. `.bot\Scripts\python.exe scripts\check_staged.py --worktree` -> `PUBLICATION CHECK OK`. It must not list `.env`, `report_delivery\.env`, `results\demo_sessions`, `tmp`, `.claude` or any transcript.
6. Untracked files that are NOT part of the release (leave them uncommitted): `data\evaluation\*\memory_samples.csv`, `reports\stage10*_transcripts\`, `docs\MLOPS_DEMO_TRANSCRIPT.md`, `docs\STAGE9B_TRANSCRIPT_DATA_SCIENTIST.md`. Check them first if you want them published. Also the six data/model files that differ only in line endings (`git diff --stat --ignore-space-at-eol` shows nothing) are not part of the release.
7. Rotate the Gmail app password in `report_delivery\.env` if it was ever shared (it is gitignored and was never committed).

## B. Run the app yourself
8. `run_demo.bat` -> browser opens `/demo/`. Start a 15-minute Python Developer interview; answer two questions, skip one, close the tab, reopen the dashboard and Continue; finish. The summary shows *Correctness check*, then **Download PDF report** and **Download my results (JSON)** both download; the PDF has a "CORRECTNESS FEEDBACK" section and no percentage score.
9. Open `http://127.0.0.1:5000/` -> redirected to `/demo/`. `curl http://127.0.0.1:5000/` -> JSON description.

## C. Real-model checks (the two that have never been run)
10. **Correctness with Ollama** (about 10-30 minutes): `ollama pull qwen2.5:7b`, then `verify_ollama_stage12.bat`. Read `tmp\stage12_live\summary.md`: the autoencoder "always needs labelled data" answer should not be *Correct*. Record the three results honestly in the README table if you publish them.
11. **ML Docker, either way:**
    - On GitHub: Actions -> "Heavy checks (manual / weekly)" -> Run workflow on `Update`. The job `docker-ml-image` must pass its step "Real Sentence-BERT scoring inside the ML container" (look for `REAL SENTENCE-BERT SCORING VERIFIED` in the log).
    - Or locally with Docker Desktop: `verify_docker_ml.bat` -> `ML-ENABLED DOCKER VERIFIED`.
    If a threshold in `scripts/verify_ml_scoring.py` fails on the real model, fix the threshold with the printed values; do not delete the check.

## D. GitHub
12. Commit in logical groups (security, Stage 12, Stage 14 product, Stage 15 release). Push to `origin Update` only.
13. Actions -> CI on `Update` is green (lint, security, integrity, tests 3.12 and 3.13, mlops, windows, docker, gate).
14. If you want the dependency audit on the Node front end: `cd frontend && npm audit --omit=dev`.
15. Only when A-D pass: merge through a pull request and tag `v1.0` yourself.
