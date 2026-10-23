# The interview application (Stage 9A)

A server-rendered Flask application (Jinja templates, one small vanilla-JS file, no build step, no external requests) on top of the existing `/demo` backend. No framework migration: the
backend already handled sessions, persistence, scoring and the three evaluation layers; what was missing was the product around it.

Launch (Windows): `run_demo.bat` — or `python main\app.py` — then open **http://127.0.0.1:5000/demo/**.

## Screens

| Screen | Route | What it shows and where the data comes from |
|---|---|---|
| Dashboard | `/demo/` | Totals, a similarity line chart and a per-topic breakdown, all computed from the saved interviews (`src/demo/insights.py`). "Continue" for an unfinished interview. Empty states instead of charts when there is no data; the line chart needs at least two finished interviews with scored answers. |
| New interview | `/demo/new` | Role (and an optional job description). Nothing else; length, difficulty and scorer are internal (Stage 9B). A live summary panel states exactly how answers will be evaluated and why *Start* is disabled when it is. Saved defaults (browser only) never include experimental options. |
| Interview workspace | `/demo/s/<id>` | Question set as a paper on the left, answer editor on the right (stacked on mobile). Progress, count-up timer (hide-able), keyboard submit, skip, finish. Python questions get a code editor with line numbers, Tab indent and auto-indent. A draft survives a refresh (browser tab storage), the timer is restored from server time, and feedback on the previous question can be reopened after a refresh. |
| Feedback | inside the workspace and the summary | **Legacy similarity score** in its own panel (what the number is and is not). **Experimental** concept check and code check in separate, dashed panels with their own labels; concept findings (stated / not found / flagged wrong / undecided) appear only when the evaluator produced verdicts. With experimental evaluation off the page says plainly that no strengths or missing concepts can be listed. |
| Summary | `/demo/s/<id>/summary` | Questions answered, skipped, average similarity, time spent and per answer, "Areas to review" derived from this interview only (lowest similarity, skipped, and — separately and labelled — experimental findings), question-by-question table, and each answer with its feedback. JSON export and delete. |
| History | `/demo/history` | Every interview saved on this computer. |
| Settings | `/demo/settings` | Plain explanation and live status of each evaluation method, how to turn the experimental ones on, browser-only preferences (defaults, timer), where data is stored, delete all. |

The older pages (About, label guide, recorded real-model run) are unchanged and linked from the side navigation.

## Rules the screens follow

* The only score that is aggregated or charted is the legacy similarity score, always called *similarity*, never a grade. The chart axis is fixed at 0–100.
* Experimental output is never merged into a number, never charted, never used to pick questions, and always carries its labels (`MOCK VERIFIER`, `NOT human-validated`, `ADVISORY ONLY`, `STATIC READ: code NOT run`).
* Experimental features are opt-in per interview and off by default. The browser cannot switch on a server-side feature: *live model* and *code check* appear only when the server was started with them (`run_demo.bat --live-model`, `--code-check`).
* No candidate code is executed in the Flask process. Sandboxed behaviour tests remain a separate, off-by-default Docker path.
* The history list is served only to this computer (see `SMART_DEMO_HISTORY`). It contains numbers and topic names only; no question text or answer text.
* Time per question is wall-clock between showing a question and submitting it, counted at most 30 minutes per question in totals. It is shown as recorded, not as a measure of skill.

## APIs added in Stage 9A

| Route | Purpose |
|---|---|
| `GET /demo/api/history` | Digests (numbers only) of saved interviews plus aggregates. 403 unless served to this computer. |
| `POST /demo/api/sessions/delete-all` | Erase every saved interview. Same access rule. |
| session JSON | `q_started` (time the current question was shown) and `elapsed_s` per answer, written by the engine. Sessions saved before Stage 9A still load. |

Nothing under the legacy `/api/*` routes changed.

## Tests

* `tests/app/test_stage9a_product_ui.py` — insights, timing, history access rule, pages, honesty of the legacy-only and experimental panels, no inline styles (the page CSP blocks them).
* `tests/ui/test_browser_journeys.py` — 12 real-browser journeys (Playwright + Chromium) against the running app: dashboard empty state, setup validation, timer / draft / refresh recovery / previous feedback, experimental opt-in and mock evaluation, code indentation end to end, finish and summary, history, trend only with real data, no candidate text in logs / metrics / history, preferences, mobile layout without horizontal scroll, keyboard reachability, delete all, live model unavailable.
  Skipped automatically when Playwright or Chromium is missing. To run: `python -m pip install playwright pytest` then `python -m playwright install chromium`, then `python -m pytest tests\ui -q`.
  The server for these tests is `tests/ui/browser_server.py`: the real app with one substitution, a word-overlap scorer labelled "Test scorer (word overlap, not a real model)".

## Known limitations

* Similarity scores measure resemblance to a reference answer. They are not validated against human marking and are not a grade.
* The real similarity scorers (Bi-LSTM, Sentence-BERT) need torch and a checkpoint or cached model. Without them the interview runs and shows "scorer unavailable" with the exact one-time fix.
* Strengths and missing concepts exist only for the experimental concept check, and only for the small share of questions with a numeric-eligible scope; elsewhere findings are advisory.
* The concept check with the real local model is slow (30–90 s) and its reliability is not established (see `reports/stage8ab_consolidated_report.md`: the frozen abstention criterion is not met).
* Topic averages over a few answers are noisy; the dashboard says so when there are fewer than three.
* Saved interviews expire after 14 days by default, so trends cover that window unless `SMART_DEMO_RETENTION_DAYS` is raised.
* Sessions are stored as local files; there are no user accounts. Anyone using the same computer and browser can open the dashboard.
* Dark mode follows the operating system setting; it has had less visual review than light mode.

## Stage 9B plan: finishing the experimental assessments

1. **Real scorer baseline on Windows.** Confirm Bi-LSTM / Sentence-BERT run on the target machine; rerun `tests\ui` there with the real scorer. Exit: browser journeys pass with a real scorer.
2. **Concept check (Qwen) readiness.** Run the recorded 3C-2 protocol again through the UI path on 20 answers with the local model; measure abstention rate, latency per answer and provider failures. Exit: abstention under the frozen 40% criterion, or the UI keeps showing findings without a number.
3. **Human-labelled comparison.** Have a person grade a fixed set of answers (at least 60 across the scorable questions) before looking at model output; report agreement per question type. Only then decide whether any number may be shown without the experimental label. Exit: written decision with the numbers.
4. **Python assessment.** Enable the Docker sandbox path on the target machine (`run_demo.bat --docker`), run its self-test and the declarative specs for the questions that have them, and extend the specs to the remaining Python questions (a spec is a JSON test plan, not model output). Exit: every Python question that asks for code has a spec or says it has none.
5. **Feedback quality.** Replace the score-band comment in the legacy panel with the concept findings once step 2 or 3 supports it; until then it stays labelled as automatic.
6. **Promotion rule.** An experimental result moves out of its dashed panel only when steps 2–3 (concept check) or step 4 (code) have a written pass, never by configuration alone.

## Stage 9A.3 — new layout and identity (supersedes 9A.2's layout)

The 9A.2 dashboard (left rail, welcome hero, stat cards, similarity chart) was rejected and replaced. Presentation only: routes, store, evaluation and the interview API are unchanged (the dashboard route also passes the role list from the existing catalog).

- **Process:** the project's UI/UX Pro Max skill (`.claude/skills/ui-ux-pro-max`) was run for the design system; the synthesis is in `design-system/smart-mock-interview/MASTER.md`.
- **Navigation:** floating glass top bar with a sliding indicator (desktop), bottom tab bar (below 820px), footer links for About / label guide / recorded run. The interview page hides primary navigation.
- **Dashboard:** animated hero with a live "interview preview" window (types a sample answer once, tilts with the pointer, labels the three kinds of feedback), a continue strip, **quick-start cards** (one click starts an interview with the chosen difficulty and length; they are real links to `/demo/new?role=...` without JavaScript), practice counts (interviews, answers, time, topics), recent interviews as cards with answered/skipped segments, practice-by-topic *counts*, and how-it-works. **No similarity percentages appear on the dashboard.** Average similarity, the trend and per-topic similarity are unchanged and live on **History**, with their "not a technical grade" labels. The `/demo/api/history` data is unchanged.
- **Workspace:** sticky progress and timer bar, large question card with answering tips, step dots, tall text or Python editor, sticky submit bar, sticky "Next question" after feedback. Draft recovery, timers and keyboard shortcuts are unchanged.
- **Animation:** CSS only plus ~60 lines of vanilla JS (nav indicator, quick start, hero preview). No library, no CDN, CSP unchanged. All motion is disabled under `prefers-reduced-motion`.

## Stage 9A.4: responsive width correction

Root cause: the content column was capped per page (`[data-page=setup|settings|history|summary] .stage-in{max-width:1180px}`, home 1320px, workspace 1440px), the floating nav was a fixed 1320px, and the setup grid kept a fixed 25rem plan column. At about 1760px this left the setup form near 750px wide in the middle of large empty margins.

Fix (CSS only, no backend change): two shared tokens in `app.css`, `--maxw:1600px` and `--gutter:clamp(16px,calc(7vw - 12px),160px)`. `.stage`, `.topbar` and `.site-foot` use the gutter, and `.stage-in` uses `--maxw`, so the nav and the content always share one width. The per-page caps are removed. Role cards are 3 columns (4 from 1280px, with the custom card filling the rest of the row), the setup plan column is `clamp(22rem,24vw,29rem)`, and coding questions use a 4fr/8fr workspace. Paragraph text keeps a 84-100ch measure so wide screens do not produce very long lines.

Measured content width (`.stage-in`): 1920 → 1600px (83%), 1760 → 1538 (87%), 1440 → 1262 (88%), 1024 → 905 (88%), 768 → 685 (89%), 390 → 358 (92%). No horizontal overflow at any of these. Covered by `test_content_width_is_fluid_and_nav_is_aligned`.

## Stage 9B: a structured interview replaces the quiz flow

Product behaviour, not just styling. `src/demo/interview.py` holds the pure planning and conversation logic; `engine.py` only orchestrates it.

- **Setup:** pick a role (only roles the curated bank can support: at least 12 questions in the role's domains), optionally paste a job description, press Start. The form is a `POST` so the job description never appears in a URL.
- **State machine:** `introduction -> core -> (follow_up) -> core ... -> practical -> wrap-up`. `interview.TRANSITIONS` lists the legal moves and `check_sequence` validates every plan and every inserted follow-up (an invalid follow-up is dropped). Interviews end when the plan is exhausted, after 3 skipped technical questions in a row, or when the candidate ends it. The reason is stored in `plan.ended_reason`.
- **Question selection:** the 5 core slots round-robin over the role's domains. Candidates are ranked by near-duplicate (token Jaccard >= 0.55), distance from the slot's fixed difficulty (Easy, Medium, Medium, Medium, Hard, which never adapts to answers), topic already used, then relevance. Relevance = job-description match against the bank's own topics and key concepts + a retrieval hint (MiniLM + FAISS when installed, otherwise BM25, recorded as `retrieval_mode`) + a small seeded random term. Retrieval similarity only orders candidates; it is never a grade. Code-writing questions are kept out of the core slots; one practical question is chosen per role.
- **Follow-ups:** deterministic and bank-backed, no LLM. A very short answer gets "could you expand?"; otherwise the first curated key concept of that question that the answer does not state becomes the prompt ("Where does X fit into your answer?"). At most 2 per interview, spaced out, never after the introduction or the practical. They are not scored and each carries `provenance.llm = false`.
- **Job description:** at most 4000 characters, control characters removed, e-mail/phone/links redacted, instruction-like text flagged and ignored. It is only matched against the bank's vocabulary, so it cannot change rules, scoring or prompts, and the raw text is never stored (only matched terms and counts).
- **Scoring:** Sentence-BERT only. Any other `legacy_model` is rejected with a 400; if SBERT is unavailable the similarity is reported unavailable (no fallback). The introduction and follow-ups are not scored. The similarity number sits inside "Technical details" on the feedback report. "Terms found / not found as written" compares the answer with the curated key concepts by exact words; it says found or missing, never right or wrong.
- **Workspace:** one conversation thread (interviewer messages left, candidate replies right), a stage tracker, a timer, a composer that becomes a code editor for the practical exercise, save-and-leave, and a two-step End interview. "Thinking" appears only while a request is in flight (no streaming, voice or speaking avatar is simulated). Pause means save and leave: the timer is not paused on the server.
- **Report:** questions asked, answers given, topics covered, observations read from the candidate's own words, practice areas, verified code-test results when the opt-in code check ran, and a turn-by-turn transcript with provenance for each question. No overall grade is produced.
- **Not changed:** the experimental concept check and code check stay opt-in (Settings), off by default, and their results stay inside labelled panels. Code is never executed in the web process.
- **Tests:** `tests/app/test_stage9b_interview.py` (planner, state machine, follow-ups, job description, SBERT-only, persistence, stop rules, no grade), `tests/ui/test_browser_journeys.py` (Data Scientist and Python Developer journeys in Chromium). The older suites were migrated to the new flow; tests of the retired quiz controls (difficulty, size, scorer choice) were removed or rewritten.

## Stage 9C: experimental follow-ups and written feedback (opt-in, unvalidated)

- **Settings → Follow-up questions** (stored in this browser only): *Standard* (default), *Mock*, or *Local model* (only offered when the server was started with `run_demo.bat --live-model`). New interviews send `followup_mode`; the API rejects unknown or unavailable modes.
- **How a model follow-up appears:** the same conversation bubble as any follow-up, with the origin label "Experimental follow-up written by the local model (rule-checked, not human-reviewed)". If the model is slow (30 s default, `SMART_DEMO_FOLLOWUP_TIMEOUT_S`), offline, or its question fails a rule, the standard bank-backed follow-up is used and the interview continues; the attempt is recorded (reason codes only) in the session plan.
- **Written feedback panel** (summary and answer cards, only when the experimental concept check actually returned a result): *Covered in your answer* (with your own words), *Not found in your answer* (worded as a prompt, not a mistake), *Possible technical errors with evidence* (only when the question is penalty-eligible and the curated reference contradicts your quoted words), *Could not be decided*. No grade. When the evaluator abstains the panel says so. Sentence-BERT similarity stays in the technical details.
- Verified code-test results and advisory code observations remain separate buckets (see `docs/CODE_EXECUTION_SECURITY.md` §6).
- Evaluation of all of this: `docs/STAGE9C_EVALUATION_PROTOCOL.md`. No human has reviewed any model-written follow-up or feedback.

## Stage 9D: loading state for model follow-ups
With an experimental follow-up mode on, the "thinking" bubble after a technical answer reads "Preparing a follow-up…" (after 7 s: a standard follow-up is used if it takes too long). Live follow-ups use a background-warmed model with a bounded, cancellable request (`docs/STAGE9D_PERFORMANCE.md`); on any failure the standard follow-up arrives instead and the interview never waits past the deadline.
