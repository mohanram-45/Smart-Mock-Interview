# Stage 10N: Grounded technical questioning: consolidated report

**Read this first.** No real-model run exists for this code. The build sandbox has no Ollama, torch or Sentence-BERT. Every number below is from the scripted stand-in model or from hand-written question pairs judged by the validator. **The 80% target is not claimed.** The Windows baseline (llama3.2:3b, prompt 10.fu7: 11/23 = 47.8%, ordinary technical 2/12) is still the last real measurement.

**The Windows results file did not arrive.** `tmp/stage10_opps_20261021_172940/results.json` was named in the brief but only the prompt text reached the sandbox. So the per-case statements about T01-T12 are from code inspection plus the case descriptions in the brief, not from replaying the raw model replies. Where I say "likely" it is inference. When the file is available, `scripts/stage10m_trace.py --results <file>` produces the exact per-case trace.

## 1. Confirmed root cause of `evidence:none_verified`
Confirmed from the code path (prompt, schema, parser, validator, repair):
- `answer_quote` was a **required** schema field. The prompt asked the 3B model to paste a verbatim span of the answer. `validate` demanded it be a verbatim 3-240 character, at most 40 word substring of the answer (or of the offered earlier statement). A paraphrase, a near-copy, an empty string or a non-string was rejected (`evidence:none_verified`, or `schema:shape` when absent).
- The quote also counted toward the "tied to the answer" check, so a model-written quote was **both** a hard requirement and a source of proof. That is the contract the brief asked to remove.
- Verdict on each hypothesis: the validator **did require a model-authored field Llama is bad at**; it **rejected reasonable paraphrase**; it did **not** fail to find legitimate source evidence (the answer text was always available to code); the open vs covered confusion is a separate rule (`targets_covered_concept`) and not the cause. Not all nine rejections are claimed to be false: the same validator also (correctly) caught repeats, given-away answers and false premises, which is why the quote requirement was removed but the content checks were kept and extended.

## 2. False-rejection and false-acceptance findings
Method: `src/demo/question_pairs_eval.py` feeds hand-written good and bad questions to the production validator (no model). Items: the 12 frozen T cases (read only) plus 20 new holdout answers across databases, algorithms, Python and ML (H01-H10 were run once for diagnosis; **H11-H20 were written before any change and form the untouched confirmation set**). These are author judgements, **not human validation**. Rerun with `python scripts/stage10n_pairs_eval.py`.

| set | false rejections (good refused) | false acceptances (bad let through) |
|---|---|---|
| T01-T12 fixture | 1 / 12 | 2 / 13 (1 detectable, 1 known gap) |
| holdout H01-H10 | 7 / 10 | 0 / 12 |
| holdout H11-H20 (untouched) | 8 / 10 (10 / 10 before the fixes) | 0 / 10 |

Real bugs found and fixed (not by loosening):
1. **"wrong" was always accusatory.** "What could go wrong if the graph had a cycle?" and "which wrong prediction would worry you more" were refused. Now only an accusation ("you're wrong", "that is incorrect", "you got it wrong", "is wrong") is refused.
2. **"earlier results" counted as a memory reference** (`memory:unsupported_reference`). Now it needs "earlier you ...", "you said ... earlier", or the existing cues.
3. **Open-concept engagement was exact-word only.** "equal contents" did not match "value equality". It now accepts a word stem, or two words from the curated reference sentences about the open concept (evidence chosen by code, from vetted material).
4. The coverage rule (question is 75% the candidate's own words) now exempts a question that adds a word from those reference sentences.

**Remaining false rejections (measured, kept on purpose).** Scenario-style questions that probe an open concept without ever naming it ("what happens when two keys land in the same bucket?" for "collision handling") are still refused as `ignores_target`. The prompt tells the model to name the TARGET, so a well-behaved model passes, and a refused question falls back to the deterministic follow-up, which names the concept. Accepting scenario questions safely needs an embedding relevance check; its threshold cannot be calibrated here (no Sentence-BERT), so I did not guess one. A second source: `novel_terms` refuses "in-place" (no vetted source for it).

**Remaining false acceptances.**
- T01 "what happens when the loss function is undefined for an unusual input?": invents an edge case. Accepted (detectable in principle, not caught).
- T05 "why does `is` compare values while `==` compares memory addresses?": affirms the reversed claim. Accepted. The validator has no technical-truth oracle, and I did not build one.
- T02 "how does a rollback keep committed data safe?": rejected, but because it repeats an explained concept, not because the confusion was understood.

## 3. Changed code and regression tests
Changed: `src/demo/followup_llm.py` (prompt `10.fu8`; code-chosen `code_evidence`; model quote is telemetry; checks `reveals_reference_value`, `presupposes_claim`, `repeats_answer_content`, `memory_link_without_gap`; neutral value labels; `BUILD ON` and `USE` prompt lines; `open_support_stems`; narrower accusation and memory cues; repair text for the new codes; dead `nearest_evidence` removed), `src/demo/memory.py` (faithful lead-in), small changes to `engine.py`, `sim.py`, `opportunity_eval.py`.
New: `src/demo/question_pairs_eval.py`, `src/demo/eval_data/stage10n_question_pairs_v1.json`, `scripts/stage10n_pairs_eval.py`, CI step, `docs/STAGE10_MODEL_AND_POLICY.md` section 14.
Tests: `tests/app/test_stage10n_grounded_questioning.py` (45 tests): the old reason is unreachable; a missing, empty or invented quote neither voids nor vouches; per-case good and bad pairs for T01-T12; value-like gaps never stated (T06); T12 false premise still rejected; accusation and memory-cue false rejections; holdouts have no detectable false acceptance; documented gaps pinned; fixture hash pinned; no case ids in production code; memory links. Existing tests were updated only for deliberate contract changes (no `answer_quote` in the schema, evidence by code, memory questions must name an open concept).

## 4. Do the questions target unanswered gaps?
By construction: the target is the first open concept (absent or only mentioned) chosen by code from curated material, and a `probe_concept` question must engage an open concept (name, stem, or reference words) and may not repeat the answer. Evidence per case (scripted/offline; **not a model result**): T04, T07, T11 repeats are rejected; T09, T12 target the unexplained concept; T06 targets the unstated complexity without giving it. A `deepen` question about the candidate's own claim is still allowed and can be valid but not a new gap. Gap progression has not been measured on a real model.

## 5. Windows memory regression coverage
The memory retrieval subsystem was not rebuilt. Kept: zero fabricated references, session isolation, citation dropped when the memory is not used, the three Windows memory tests (they pass here, and the 10M platform-independence and self-diagnosing tests are unchanged). New: a memory lead is only attached when the question also engages an open concept (M07: a project lead that ignores what is still open is refused), and the repair keeps the memory id. M05 and M07 pass in scripted form, but **whether Llama connects the memory meaningfully is unverified**.

## 6. Test results and limitations
- `pytest tests`: **1417 passed, 8 skipped, 0 failed** (about 160 s). `ruff check`: clean. `check_integrity.py`: OK. `check_versions.py`: 11 passed. `verify_mlops.py`: 16 PASS, 3 INFO.
- Scripted benchmark: 17/17 gates, 23/23 eligible, 25 accepted questions, zero audit findings, standard prompt under 450 tokens. This says nothing about a language model.
- Not run: Playwright browser tests (not installed here, skipped), real Ollama, Sentence-BERT, the 4th real results file.
- B07 stays a fixture defect scored on safety only. The frozen fixture hash `59e92f47...0737` is unchanged (pinned by tests).
- Human review sheets in `docs/stage10_review_n` are **unrated**; the automated rules are not human validation.
- Premise correctness is checked only by: the concept-equivalence table, novel-term vocabulary, and the reference-value reveal rule. The system cannot tell that a candidate's answer is wrong.

## 7. Remaining technical-quality risks
1. Real-model acceptance is unknown; the prompt is smaller and the contract simpler, but a 3B model may still write scenario questions that the engagement rule refuses (high false rejection on the holdouts is the best predictor).
2. T01/T05-type false acceptances.
3. `deepen` questions may be valid but off-gap.
4. Memory lead-ins may be present but generic.
5. If the real run stays near 50% after this change, the bottleneck is the model's wording ability, not the evidence contract. Per the brief, the next step is then a **controlled model comparison** on the same frozen fixture (for example llama3.2:3b against a 7-8B model, same prompt 10.fu8, same validator), not more prompt edits.

## 8. Delivery
`stage10n.zip` holds the changed and new files with project-relative paths. Unzip over `D:\Projects\SMART-MOCK-INTERVIEW`. No git operations were performed.

## 9. Real-model Windows verification procedure
1. Unzip over the project; activate `.bot`; start Ollama with `llama3.2:3b`.
2. `python -m pytest tests -q` (expect all pass; if a memory test fails run `python scripts/stage10m_windows_test_diag.py`).
3. `python scripts/stage10_verify_real_stack.py --opportunities --models llama3.2:3b --mlflow --sbert`
4. `python scripts/stage10m_trace.py --results tmp\<new run>\results.json` for the per-case trace (rejection reasons, replay of the model reply through the new rules).
5. `python scripts/stage10n_pairs_eval.py` for validator rates on your machine.
6. Rate `docs/stage10_review_n` (naturalness, gap relevance, repetition), then `python scripts/stage10l_review_summary.py`.
7. Report: technical acceptance, premise correctness, gap progression, repetition, memory relevance and citation validity, appropriate skips, false acceptances and rejections, repairs and latency. Compare against 11/23 (47.8%), 2/12 ordinary technical, 5/7 memory. Only a real run at or above 80% on the unchanged eligible set supports a success claim.
