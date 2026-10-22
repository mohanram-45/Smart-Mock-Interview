# Stage 11R - Quality and Safety Repair: report

Status: implemented and tested in a Linux sandbox copy. **Not run on Windows. No real-model (Ollama) run of the repaired engine was performed, so no acceptance rate is claimed for it and the 80% target is NOT shown to be met.** No git commits, pushes or deployments.

## Evidence kinds (kept separate)
- Real model, measured by you: Stage 10N 13/23, objective 11.obj1 18/23 (fabricated refs 1). Unchanged, quoted only.
- Offline replay of those recorded real replies through repaired code: a diagnostic of decision/validation code, not of a model.
- Author-written pair sets and reference controls: sanity checks, same author as the rules, not independent.
- Human-rated: none.

## Root causes
1. T09: two divergent reference detectors (live `_MEM_CUE` vs audit `_EARLIER_CUE`); live path had no check for "the one you mentioned".
2. T02/T08/N02: concept ids shown in the prompt; `sanitise_ids` substituted the label next to the model's own copy of it.
3. T11: compound parts not stem-matched against the candidate's words.
4. M02/M03/M04: target concept could restate the original question or ignore the stored work; the prompt's word list invited word strings (M05); presupposed use ("how does your experience ... inform") was credited as memory use (M07).
5. T06/T02/M06: no rule for probing a stated wrong value, premise restating the answer, or lead restated inside the question.

## Files changed
src/demo/followup_llm.py, src/demo/intel.py, src/demo/engine.py, src/demo/opportunity_eval.py (audit only; fixture/labels/scoring untouched); new: scripts/stage11r_validator_compare.py, src/demo/eval_data/stage11r_question_pairs_v1.json, src/demo/eval_data/stage11r_reference_pairs_v1.json, tests/app/test_stage11r_quality_safety.py, reports/stage11_eval/{stage11r_validator_compare.json, stage11r_human_review_sheet.csv, replay_11r/, stage11_objective_real_llama3.2_3b_20261021_221628.json}; docs/STAGE11_INTELLIGENCE_ARCHITECTURE.md (new 11R section). `.github/workflows/ci.yml` is not writable from here (unchanged).

## Test outcomes (sandbox)
- New file: 70 passed. Full `tests/app`: 778 passed, 5 skipped. ruff: clean. check_integrity: OK. Frozen fixture sha256 unchanged (59e92f47...0737).

## Old vs repaired validator (objective profile; FR = good questions refused, FA = bad accepted)
| set | FR legacy -> repaired | FA legacy -> repaired |
|---|---|---|
| fixture pairs | 1 -> 1 | 2 -> 2 |
| holdout | 5 -> 5 | 0 -> 0 |
| holdout2 | 5 -> 5 | 0 -> 0 |
| holdout3 (new) | 2 -> 2 | 6 -> 1 |
- Recorded rejected pool (40 questions): 34 still refused; nothing newly accepted.
- Recorded accepted pool (37): accepted by legacy 30 -> repaired 24 (the six dropped are the weak ones listed in D).
- Unsupported-reference controls: 22/22 flagged (legacy 0/22); 10 genuine references: 0 refused.
- Acceptance/audit contradiction: tested as a property over the control and recorded pools; none.

## Replay of the 221628 run (diagnostic)
T09 refused; T02, T06, M05 (word list), M06, M07 refused/uncredited; T08/N02 accepted with a single term; T11 accepted. M02, M03, M04 are refused for the recorded questions, so the replay shows the old model questions would no longer be shown; whether the new prompt makes the model write a valid memory question is unmeasured.

## Remaining weak or uncertain
- `question:ignores_objective` (pre-existing) refuses ~12 of ~47 good scenario questions; a semantic gate needs Windows calibration and was not built.
- "statelessness stateless" style stem doubling passes (1 FA in holdout3).
- Accepted but questionable (see review sheet, 11 of 15 flagged): N02 is tautological ("consistency ... consistent state"); T03 attempt 2 and M01 are long; T10 generic; T01 and N04 vague; N01 convoluted.
- Likely fallback rate stays high; fallbacks are safe standard follow-ups, not failures of safety.

## Integration
Setup -> retrieval -> answer -> objective -> memory selection -> generation -> validation -> `final_gate` -> persistence -> evaluation -> report all run through the existing `engine._llm_followup`; engine test with an unsafe generator confirms an unsafe question is never persisted. Technical/behavioural modes, budgets, provenance, session isolation, retrieval and MLflow paths covered by the unchanged regression tests (all pass).

## Windows verification: NOT PERFORMED. Please run
```
.bot\Scripts\python.exe -m pytest tests\app -q
.bot\Scripts\python.exe -m ruff check src scripts tests
.bot\Scripts\python.exe scripts\check_integrity.py
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --engine objective
.bot\Scripts\python.exe scripts\stage11_compare.py
```
Release gate for the measured run: zero `fabricated_memory_reference` / `duplicated_phrases` findings; then rate the review sheet blind.
