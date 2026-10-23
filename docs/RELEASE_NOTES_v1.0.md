# SMART Mock Interview v1.0 - release notes

**Status: a working local demonstration, ready with limitations.** Nothing in it has been validated against human markers. Tag it only after the checklist in [RELEASE_CHECKLIST_v1.0.md](RELEASE_CHECKLIST_v1.0.md) has been completed.

## What v1.0 is
A local, single-user mock-interview application. `/demo` is the product; the original adaptive Flask API (`/api/*`), the Node front end and the comparison tool are kept unchanged in behaviour (now local-only).

- **Interview:** role, type (technical / behavioural / mixed), length (15, 30, 45 or 60 minutes) and an optional job description. Introduction, five core questions ranked by retrieval (BM25 fallback), follow-ups that use what the candidate said, a practical exercise, a wrap-up. Skip, refresh and resume work; sessions are stored locally and deleted after 14 days.
- **Similarity:** Sentence-BERT (`all-MiniLM-L6-v2`), shown on a 0-1 scale and labelled as not a grade.
- **Correctness check (opt-in):** Correct / Partially correct / Incorrect / Uncertain with correct and missing concepts, misconceptions quoted against the reference, and feedback. Built from the modular evaluator plus one evidence-checked contradiction call; never from similarity. Off by default (*Not assessed*). Needs a local Ollama with `qwen2.5:7b`.
- **Outputs:** summary page, JSON export, PDF report (existing report generator) with the correctness feedback.
- **Packaging:** Docker (lean image, loopback-only publish, non-root, read-only) and an optional `INSTALL_ML=1` image; GitHub Actions CI on the `Update` branch.

## Changes since the audit (Stages 12-15)
- Stage 12: similarity separated from correctness; misleading "Excellent work" band comment and percentages removed from /demo.
- Stage 13: compare tool bound to 127.0.0.1 with the debugger off; report download/e-mail endpoints restricted to local pages, one plain recipient, rate-limited; CORS allow-list; CI runs on `Update` with a dependency and publication safety job.
- Stage 14: /demo is the front door (`/` redirects browsers); PDF report from the summary; interview length in the setup UI; ML Docker verification tooling.
- Stage 15: the Docker peer rule narrowed to one trusted address; GitHub-hosted verification of real Sentence-BERT scoring in the ML image (`heavy.yml`, manual); Pillow and certifi pins updated; documentation and screenshots brought up to date.

## Verified vs not verified
| Item | Status |
|---|---|
| Automated tests, lint, integrity, version checks | pass (Linux sandbox; CI on GitHub reported green for the Stage 13 commit) |
| Full /demo journey (setup, answer, skip, resume, history, export, PDF) | tested with a stand-in scorer and in a real Chromium run |
| Dependency audit of the three hashed/pinned locks (`pip-audit`, 23 Oct 2026) | no known vulnerabilities |
| ML Docker image builds and scores with real Sentence-BERT | **PASSED locally, 23 Oct 2026**: `verify_docker_ml.bat`, six real Sentence-BERT checks and application readiness; semantic retrieval fell back to BM25 due to a read-only FAISS cache path |
| Correctness check with the real local model | **two live runs (23 Oct 2026): initial 0/3 matches; corrected 1/3 matches, one Uncertain and one wrong; six independent cases not run**: `verify_ollama_stage12.bat` (9 answers). **NOT READY to be enabled by default; stays opt-in and labelled advisory** |
| Accuracy of any verdict or similarity against human judgement | **never measured** |

## Known limitations
- Question bank, references and rubrics are AI-written and not human-reviewed.
- The correctness check abstains often (the underlying evaluator abstained on 45 % of answers in its recorded run); a correct paraphrase without a concept's own wording is usually *Uncertain*.
- Follow-up quality is automatically checked only (17/23 accepted on the last real run, before the final repairs; no human rating).
- Without the ML extras the Docker image reports similarity as unavailable.
- Unpinned and un-audited: `requirements.txt` (legacy, lower bounds), `requirements-docker-ml.txt` (torch, sentence-transformers, faiss), and the Node front-end dependencies (`cd frontend && npm audit --omit=dev`).
- Local tool: no accounts, no TLS, in-memory legacy sessions, not for public deployment. If you publish the port beyond 127.0.0.1, set `SMART_REPORT_TOKEN`.
- Windows launchers are covered by a CI smoke job only.
