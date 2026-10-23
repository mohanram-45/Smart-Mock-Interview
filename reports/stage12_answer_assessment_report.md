# Stage 12: Technical Answer Assessment

**Status:** implemented and tested in the Linux sandbox copy, then installed into `D:\Projects\SMART-MOCK-INTERVIEW`. Backup: `tmp\stage12_backup_20261023\`.
- **No real-model run.** Ollama on the Windows host is not reachable from the sandbox or the linked shell (connection refused / blocked by the network allowlist).
- No new dependencies. No git operations.
- Follow-up intelligence, memory and question selection are untouched.

## The problem, from your own 22 October interview

| Question | Your answer | Shown before |
|---|---|---|
| Autoencoder | "…compresses data and then reconstructs it. It **always needs labelled training data** to learn the correct output." | **90.7 %** — "Excellent work — this answer is clear, accurate, and complete." |
| Unsupervised learning | one correct sentence | 65.7 % — "You're showing good understanding of the topic here." |
| Fourier transform | "I'm not sure about this concept. Could we move on…?" | 0.0 % — "There's a gap in understanding here." |

The comment was chosen from the similarity band alone (`src/components/feedback_generator.py`, 85/50/35 thresholds). A high resemblance to the reference was presented as "accurate and complete".

## What changed

1. **Similarity is shown on a 0–1 scale, never as a percentage, and never with a band comment.** This applies to the answer card, the summary table and averages, history, the trend chart axis and the improvement areas. Stored values stay 0–100, so older sessions load unchanged. The legacy `/api` app is unchanged.
2. **A new correctness check** (`src/demo/assessment.py`). It returns Correct / Partially correct / Incorrect / Uncertain, plus Not assessed or Checking…, with:
   - correct concepts;
   - missing concepts;
   - misconceptions (each with the candidate's claim and the reference text it conflicts with);
   - up to three lines of feedback.

   It is built only from the existing modular evaluator's requirement outcomes and verified factual errors, and **never from similarity** (a test proves the verdict is identical at similarity 0, 49, 91 and 100).
3. **A contradiction pass** (`src/evaluation/modular/contradictions.py`, new, outside the frozen set). It makes one extra call to the same local model and asks which of the answer's claims the reference contradicts. Code accepts a finding only if:
   - the claim id exists;
   - the quote occurs word for word in the reference prose (code samples and URLs removed);
   - the claim and the quote share a content word;
   - the explanation is short.

   It exists because the concept verifier judges one requirement at a time, so a false statement that isn't a requirement ("always needs labelled data") was never judged.
4. **Fail-safe rules.**
   - Evaluator off, failed, timed out or interrupted: **Not assessed**.
   - Evidence incomplete or suspect: **Uncertain**.
   - **Correct** requires every essential concept demonstrated **and** a contradiction pass that actually ran.
   - A verified misconception caps the verdict at Partially correct, or Incorrect when misconceptions ≥ essentials demonstrated.
   - The mock verifier can never produce Correct.
   - An empty or "I don't know, can we move on" answer is Incorrect (no attempt), decided by rule.
5. **Integration.**
   - The panel sits above the similarity card in the per-answer fragment (live and summary).
   - The summary gains a "Correctness check" section (counts, per-question verdicts, statements to correct) and a column in the per-question table.
   - `assessment` appears in the answer API, the fragment API and `export.json`.
   - The older "Written feedback" panel now lists contradiction findings too, so the two panels cannot disagree. This was seen on the rendered page and fixed.

## Changed files

| File | Change |
|---|---|
| `src/demo/assessment.py` | **new**: verdict, schema `smi.assessment/1`, fail-safe rules, session overview |
| `src/evaluation/modular/contradictions.py` | **new**: evidence-checked contradiction pass |
| `src/demo/experimental.py` | runs the pass after the concept check (live: same provider; mock: not checked); never raises |
| `src/demo/routes.py` | `assess`/`similarity_view` globals, `sim` filter, assessment in the answer/fragment APIs, export and summary |
| `src/demo/grounded.py` | contradiction findings shown in the Written feedback errors box |
| `src/demo/insights.py` | similarity labels 0–1 (trend axis, lowest-similarity list) |
| `src/demo/templates/_macros.html` | `assessment_panel`; similarity card shows 0–1; band comment removed |
| `src/demo/templates/_answer_eval.html`, `summary.html`, `history.html`, `_lists.html` | panel, summary section and column, 0–1 displays |
| `src/demo/static/demo.css` | panel and badge styles |
| `scripts/stage12_assess_answers.py` | **new**: bounded before/after evaluation (`--live` on Windows, `--scripted` anywhere) |
| `tests/app/test_stage12_answer_assessment.py` | **new**, 43 tests |
| `tests/app/test_stage4a_demo.py`, `test_stage4d_code.py`, `test_stage5b_e2e.py`, `test_stage9a_product_ui.py` | 6 assertions changed. They checked the removed presentation (`bigscore` percentage, band comment, 0–100 axis labels); each now asserts the new presentation, with a comment saying why |

Frozen files are untouched: `check_integrity.py` and `check_versions.py` pass.

## Tests (sandbox)

- `tests/app`, `evaluation`, `mlops`, `codeeval`, `retrieval`: **1,738 passed, 7 skipped, 0 failed**. 43 of these are new; the six changed assertions are listed above.
- The CI scripted gates `stage10_eval_suite --quick` and `stage10f_eval --quick` pass, so follow-up and memory behaviour are unchanged.
- `ruff`: clean.

## Before / after (10 representative answers)

**Evidence: scripted stand-in.** The concept verdicts and contradiction replies are written by the author, so these rows prove the code path and the decision rules, **not model quality**. They still pass the real frozen evidence gate. "Expected" is the author's judgement, not a human-rated label. The "before" values are recorded from the 22 October interview where the answer is real. The others need Sentence-BERT, which isn't in the sandbox.

| Case | Before | After | Expected |
|---|---|---|---|
| Autoencoder + "always needs labelled data" (real) | 90.7 % "Excellent… accurate, and complete" | **Partially correct**; misconception quoted against "learn representation… without any supervision"; similarity 0.91 | partially ✓ |
| Autoencoder, correct paraphrase | — | **Uncertain**: the frozen gate would not credit "autoencoder" from a sentence that doesn't contain the word | correct ✗ |
| Unsupervised, one sentence (real) | 65.7 % "good understanding" | **Partially correct**; missing: an unsupervised task | partially ✓ |
| Unsupervised, complete, own words | — | **Correct** | correct ✓ |
| Fourier "I'm not sure… move on" (real) | 0.0 % "gap in understanding" | **Incorrect** (no attempt); key terms listed | incorrect ✓ |
| Hypothesis testing, brief (real) | 72.3 % "clear, well-formed" | **Correct** | correct ✓ |
| Hypothesis testing, "proves H0 true" (reference vocabulary) | — | **Incorrect**; caught only by the contradiction pass (the frozen gate rejected the verifier's own error findings) | incorrect ✓ |
| Unrelated (cooking, hiking) | — | **Incorrect** (off topic) | incorrect ✓ |
| Empty answer | — | **Incorrect** (no attempt) | incorrect ✓ |
| Mocking, right idea, no pytest mechanism (real) | 49.7 % "solid foundation" | **Partially correct**; missing: a mocking mechanism in pytest | partially ✓ |

Full table: `reports/stage12_eval/scripted/summary.md`.

## Real-model run: PENDING (Windows)

```bat
set SMART_DEMO_LIVE_MODULAR=1
.bot\Scripts\python.exe scripts\stage12_assess_answers.py --live --out tmp\stage12_live
```

This is ten answers, one concept check plus one contradiction call each, roughly 20–40 minutes on qwen2.5:7b. The live run also computes the real "before" similarity for the six new answers.

## Known limitations

- **Verdict quality is unmeasured.** Every result above is scripted. Whether qwen2.5:7b finds the right concepts and contradictions is exactly what the pending live run, and then a human rating, must show. In its frozen 3C-2 run the evaluator abstained on 45 % of answers, so expect many **Uncertain** verdicts.
- **Correct paraphrases often come out Uncertain, not Correct.** The frozen evidence gate requires the concept's wording in the cited sentence. That meets "not marked incorrect", but it is not a confirmation.
- **By default the concept check is off**, so every answer shows "Not assessed". Correctness needs `--live-model` and Ollama.
- **Live checking takes longer:** the contradiction pass adds one model call (it reuses the 300 s timeout).
- **Rubrics and references are AI-written and not human-reviewed.** For example, the autoencoder question's essentials are just "autoencoder" and "artificial neural network". A wrong reference makes a wrong finding.
- **The contradiction rules are word-level.** The claim/quote overlap check is weak: a quote that merely shares a word with the claim passes. A model that contradicts a correct claim with a real but irrelevant quote could still produce a false misconception.
- The "no attempt" rule is English-phrase based.

## Verdict

**READY WITH LIMITATIONS.**

Ready now:
- the misleading presentation is gone;
- correctness and similarity are separated and tested;
- failures and timeouts show as Not assessed or Uncertain, never invented.

Not yet shown: that the local model's verdicts are accurate. That needs the Windows `--live` run above, and then a human check of its ten rows, before the verdicts are trusted.
