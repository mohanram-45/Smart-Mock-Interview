# Stage 10J + 10K + 10L: consolidated report

**Evidence status, up front.** Everything measured in this cycle ran in a sandbox with a **rule-based stand-in model** (no Ollama, no torch, no Sentence-BERT; lexical retrieval). Those numbers test the code *around* a model. They are **not** language-model results. The **80% target on a real model for the current code (prompt 10.fu6) is NOT MEASURED; Windows verification is outstanding.** No human has rated anything. The only real-model numbers below are the user's recorded Windows runs (llama3.2:3b), quoted as recorded.

Fixture: 40 cases, hash `59e92f47…0737` unchanged and pinned by a test. No labels edited. No Git commit, staging, push or deployment.

## 1. Root causes by case ID (from the recorded Windows run 2)

| case | what happened | cause | fix |
|---|---|---|---|
| T02, T03 | rejected as `concept_already_in_answer` / `not_tied_to_answer` | the validator trusted the declared concept id instead of checking the concept's depth in the answer | depth states absent / mentioned / explained; only explained concepts count as covered |
| T07 | model chose `skip` and wrote a question; old code dropped the question silently | decision/payload inconsistency | `payload:skip_with_question` is a rejection with a targeted repair; if it repeats, fallback class `payload_inconsistent` |
| T09 | restated the answer twice; repair failed twice | the repair said only "ask about the TARGET"; a 3B model did not change its output | repair quotes the rejected question and asks for an example, reason, limit or trade-off about the named target |
| T10 | repeated an earlier question, ignored the open concepts | model ignored the TARGET | `question:ignores_target` (for `probe_concept`, standard mode) |
| M01, M03, M05 | relevant question, `memory_id=none` | generation: the model could decline the citation | memory mode: one statement, code-built lead-in, `memory_id` in {id, none} |
| M02, M04 | no memory offered | **retrieval**: the query lacked the question's vetted concepts, and the overlap test ignored the stored quote (the matching words "concurrent transactions" sat in the quote); M04 also leaked "E1" | expanded query; quote-aware overlap; ids replaced and audited (`id_leak`) |
| M06 | "your convolutional neural network" with no citation | **citation metadata**: the phrase exists only in a stored turn-1 statement, not in the current answer. It is an implicit, real, uncited reference, not invented and not current-answer context | uncited use of statement-only words is rejected; in memory mode code adds the lead-in and validates the id |
| M07 | repeated the binary-search explanation | generation | memory mode links the claim to the open target |
| B07 | class skip, outcome probe, success true | **fixture inconsistency** (`followup: null`) plus a scorer shortcut | safety-only, excluded from strict rates, reported; label unchanged |

## 2. Code changes (files)

- `src/demo/followup_llm.py` (prompt `10.fu6`): memory mode, sentence-level depth, `ignores_target`, `targets_covered_concept`, `payload:skip_with_question`, `memory:uncited_reference`, `memory:double_reference`, fallback classes, new repair texts. At most two bounded model calls per follow-up.
- `src/demo/memory.py`: `recall_lead`, wider generic-word list, extraction verbs ran/conducted/performed.
- `src/demo/policy.py`, `src/demo/engine.py`, `src/mlops/metrics.py`: `followup_query`, `retrieve_for_followup`, per-stage telemetry (`smart_followup_memory_stage_total`), `citation_invalid` handling.
- `src/demo/opportunity_eval.py`: one `score_row` formula, `fixture_defects`, payload checks, `failure_type`, review pack v2, `review_summary`, scenarios A–E, scorer self-tests.
- Scripts: `stage10f_eval.py`, `stage10_eval_suite.py`, `stage10_verify_real_stack.py`, new `stage10l_compare.py`, `stage10l_review_summary.py`. CI gained a comparison step.
- New tests: `test_stage10j_memory_contract.py`, `test_stage10k_technical_questioning.py`, `test_stage10l_evaluation_integrity.py`.

## 3. Memory: extraction, retrieval, generation, citation

- **Extraction** keeps type, source turn, exact quote, topic and confidence. A gap was found and fixed: "I ran A/B tests…" was never stored (verbs ran/conducted/performed now covered, with a test).
- **Retrieval** is tested on four unseen topics (Spark skew, REST security, A/B test sizing, recommender autoscaling) and two unrelated statements that must not be offered. The lead-in is built from the stored claim; no scenario-specific text is in the code.
- **Telemetry** separates `retrieval`, `generation` and `citation_metadata` failures per case.
- **Lifecycle tests:** recall several questions later, refresh/restart, concurrent sessions, contradiction, deletion (no leftover files).

## 4. Evaluator logic and the B07 regression

One formula, `score_row`, is used by the harness, aggregator, re-scorer and self-test. Skip success needs *no question and no memory reference* (a rule skip, a model skip, or a prefilter where the model was never called); a fallback after a model call is not a skip. memory_use needs `useful_valid` + cited + grounded + stage `used`. memory_inappropriate fails on any cite, lead or reference audit. B07 is now `safety_only`, non-strict, listed under `fixture_defects`; strict skip is 10/10, with B07 reported separately. **Approval needed** to relabel B07 or change its expectation. 21 scorer self-tests pass, including degenerate models (always-skip, cite-without-using) earning nothing, and a test that a stale stored `success` is never trusted.

## 5. Before / after (labels unchanged)

| | Windows run 2 (real llama3.2:3b, prompt 10.fu5) | scripted stand-in, current code |
|---|---|---|
| eligible useful+valid | 11/23 = 47.8% | 23/23 (**mechanics only**) |
| technical expected | 7/12 | 12/12 |
| behavioural scripted probes | 4/4 | 4/4 |
| grounded memory use | 0/7 (offered 5/7) | 7/7 (offered 7/7) |
| strict skip | reported 11/11; re-scored 10/10 + B07 safety-only | 10/10 |
| memory_inappropriate | 6/6 | 6/6 |
| fabricated references | 0 | 0 |
| fallbacks / repairs | 14 / 0 of 2 | 0 |

The scripted 100% is expected: the stand-in follows the prompt. Do not read it as model quality. The stand-in's memory questions are also stiff ("How would deep learning matter for …"); only a real model or a human can judge naturalness.

Question-level replay of the Windows replies (`windows_comparison.md`, labelled *not a model run*): T07, T09, T10, M06 and M07 are still rejected by the current rules for the intended reasons. **T02 and T03 are now accepted by the replay.** That follows from the depth change (the concept was mentioned, not explained), but it loosens a rejection. A person should review those two before it is accepted as correct.

## 6. Tests

- Full suite: **1327 passed, 8 skipped**, 0 failed. `tests/app`: 515+ passed. Ruff (CI scope): clean. `check_integrity.py`: OK. `check_versions.py`: 11 passed. `verify_mlops.py`: nothing failed.
- Browser journeys: **skipped here** (Playwright is not installed in this sandbox). Not run, so not claimed.
- Eval gates: 17/17 pass (scripted, mechanics only). All 10 faulty models rejected; standard prompt ≈ 430 estimated tokens (< 450).
- Windows run 1 and 2 evidence files untouched.

## 7. Transcripts (actual engine, labelled)

`reports/stage10_jkl_transcripts/`: A (PyTorch/X-ray project recalled later), B (logistic regression → harder question), C (behavioural example linked to an earlier project), D (contradiction clarified), E (no relevant memory, nothing fabricated). Each is labelled **SCRIPTED / MOCK**; the `*_llm` versions use the stand-in model path with the real validators and say so per turn. None is real-model evidence.

## 8. Evidence kinds

| metric | kind |
|---|---|
| behavioural probes | deterministic scripted probe |
| technical / memory counts | scripted stand-in (this report) or real model (Windows run 2 only) |
| acceptance | rule-based |
| naturalness / relevance | **human-rated: 0 rated.** Review pack: `docs/stage10_review_jkl/` (blind, random ids, separate key, UNRATED) |
| rule audit | second automatic code path, **not** an independent audit |

## 9. Limitations

- Target not measured on a real model. Windows verification outstanding.
- Retrieval here is lexical. A purely semantic link (Spark pipeline ↔ "distributed job") is not found lexically; Sentence-BERT behaviour is untested here.
- Depth is a lexical proxy, not correctness. No technical correctness score exists.
- Fixture expectations are the author's reading, not human-validated. B07 defect awaits approval.
- T02/T03 loosening (above) needs human review.
- Whether a 3B model obeys the memory contract is unknown; the code only guarantees a bad reply cannot reach the user and the memory test is then marked failed.
- Browser tests not run here.

## 10. Windows verification

1. `.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --models llama3.2:3b --mlflow --sbert`
2. `.bot\Scripts\python.exe scripts\stage10l_compare.py` against the new results folder.
3. Check: eligible ≥ 80% (≥ 19/23), memory_use cited+grounded > 0, fabricated references 0, SBERT loads 1, memory stages in the rows (declined vs used), M02/M04 now offered.
4. Fill `review_sheet.csv` blind with two raters, then `python scripts\stage10l_review_summary.py <dir>`.
5. Run `python -m pytest tests -q` and the Playwright journeys (`tests/ui`).
