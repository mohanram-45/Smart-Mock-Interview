# Stage 3B — Final grading-reliability diagnosis (Qwen 2.5 7B, second confirmation)

Inputs: `data/evaluation/stage3b_qwen_v2/runs_qwen2.5_7b.json` (prompt 3b.2, plain JSON mode), earlier Qwen/llama runs. No model calls were made for this report. Expected bands are AI-authored (Claude), unreviewed, and not treated as ground truth.

## 1. B04 — exact failure
| Question | Finding |
|---|---|
| Failed requirement | `LLMEvaluation`: "gradable=true requires score_rationale". |
| What the reply contained | Only `gradable`, `not_gradable_reason` and `rubric` (levels 3/2/4/1 with justifications), then the object closed (`done_reason=stop`, 165 tokens). **Missing: score_rationale, correct_concepts, missing_concepts, factual_errors, strengths, improvement_suggestions, improved_example_answer, follow_up_question, supporting_evidence, confidence, verification_limitations.** |
| Substantively correct? | The levels are plausible-ish but unusable alone: scoring them would bypass the evidence checks (no concepts → the unsupported-credit cap would give 30 anyway). Justifications again demand "memory addresses / value equality" wording the question doesn't require. |
| Did repair introduce defects? | No new defects: the repair returned **byte-identical** output (second call, 165 tokens, same text). The repair prompt only quoted the validator message and the model copied its previous reply. |
| Cause | **Model behaviour (early close) at the provider's plain `format:"json"` mode**, which guarantees syntactically valid JSON but not required keys. Validator and provider adapter behaved correctly. Same pattern: B03's first reply (147 tokens) and llama3.2:3b B01. |
| Prompt link (unproven) | Qwen v1 (prompt 3b.1): 0 of 5 first replies closed early. Qwen v2 (prompt 3b.2): 3 of 8 calls. The prompt grew between the runs, but with n=5 and other confounds I can't claim causation. The schema constraint below removes the failure class either way. |
Required scoring fields were **not** weakened and nothing was defaulted: the reply stays `invalid_response`, unscored, and the partial levels are not used (tested).

## 2. B07 — grading diagnosis
- **Question:** "Difference between ROW_NUMBER and RANK?" Candidate: leaderboard tie example for ROW_NUMBER and RANK, plus DENSE_RANK, plus "all three restart per PARTITION BY group".
- **Reference / key concepts:** reference text covers ROW_NUMBER, RANK **and DENSE_RANK**; key concepts `ROW_NUMBER, RANK, DENSE_RANK, ties, partition`.
- **Model (both Qwen runs):** levels 3/2/4/2 → 68. Justifications: "did not mention DENSE_RANK, which is a key concept". Missing: `["DENSE_RANK"]`. Verified concepts: 2 in v1, 1 in v2.
- **Is a concept the question never required being penalised?** Yes: the question names two functions; DENSE_RANK was not asked. **And** the claim is factually false: the answer states "DENSE_RANK would put the next player 3rd". Two distinct problems: (a) *reference ambiguity* (the reference/key concepts are broader than the question, inviting a checklist reading), and (b) a *model error* (it missed text that is in the answer, in both runs, despite prompt 3b.2 rules about meaning, question scope and checking before calling something missing).
- **Evaluator behaviour:** correct. The false missing claim is removed from feedback and confidence is lowered (`contradicted_missing_concepts`). It cannot repair the levels.
- **Does B07 deserve 80–100?** On my reading, yes: both asked functions are described correctly with a concrete tie example and the extras are accurate. The expectation's `expected_demonstrated_concepts` (`ties`, `partition`) is partly questionable because partition wasn't asked. I'm flagging this, not deciding it: see the human-review sheet.

## 3. Remaining cases in v2
- B01 96 (correct); B03 30 (first reply early-closed, repaired reply complete, major error verified, concept credit correctly absent); B13 11 (verified major error). The flag `contradicted_missing_concepts: ["bubble sort"]` on B13 is a **false positive class**: the answer names the topic but describes it wrongly, so "missing: bubble sort" is sloppy yet not strictly contradicted by a mere mention. Effect is limited to low confidence and removing that feedback line (no score change). Left as is; noted in §6.
- Latency median 71.5 s is inflated by B03's two calls (92 s) and B01's cold load (121 s, 51 s load).

## 4. Architecture review
Question: does LLM levels + LLM concept lists + exact evidence validation + unsupported-credit cap + deterministic scoring systematically penalise correct, concise answers?

| Case (correct/valid) | Real outcome across runs | Cause |
|---|---|---|
| B04 short correct | v1 capped to 30 (placeholder quotes); v2 invalid (early close). **0 of 2 scored properly.** | model quoting + format |
| B07 valid alternative | 68 in both runs (expected ≥80) | checklist reading of key concepts + missed text |
| llama B04 / B07 | 30 / 30 (empty or reference-copied quotes) | model quoting |
| B01 full correct | 96 | fine |

Findings:
1. **Yes, there is a systematic loss for concise/alternative answers, but its cause is mostly upstream of the cap:** small models (a) treat the key-concept list as a required-wording checklist, (b) fail to produce usable quotes, (c) sometimes emit incomplete JSON. The cap then converts "no verified evidence" into a score of 30 and a "weak" band even when the model's own levels were high. The cap itself is behaving safely (it never hands out credit without evidence) but it conflates "answer is weak" with "model couldn't ground it".
2. Demonstrated correctness *can* be lost purely because quotes are missing (B04 v1: levels 3/2/4/2 → 68 → 30). I am **not** recommending auto-restoring the score.
3. Verification is not what is failing: in v2 no legitimate evidence was rejected (0 drops).

### Recommended general improvements (ranked; only the first is implemented)
1. **Schema-constrained structured output on Ollama (implemented, opt-in, untested on the real model).** `OUTPUT_JSON_SCHEMA` makes every key required, constrains levels to 0–4, severity/confidence/source to enums and lists to arrays of strings, so an early close or a bare-string list cannot be generated. Default stays plain JSON; enable with `scripts\stage3b_run.py --schema`. Caveat: grammar-constrained decoding can change output quality/speed and may behave differently across Ollama versions; hence it is opt-in and must be A/B-tested.
2. **Repair names the missing keys (implemented).** The old repair let the model copy its truncated reply (B04). The repair now lists the absent keys and says "your reply stopped early". Unproven on the real model.
3. *(proposal)* **Question-requirements field**: ask the model to first list in 1–3 short items what *this question* requires, then judge completeness against that list. Targets the B07/B04 checklist reading without editing the dataset. Adds ~20–30 tokens.
4. *(proposal)* **Evidence-based consistency re-ask**, only when code finds a missing-concept claim contradicted by the candidate text: re-prompt once with the verified candidate sentence ("you said X is missing; the candidate wrote: '…'") and accept the re-assessed levels only if the new reply validates. Rejected for now: it is a second ~60 s call, can't be validated without more real runs, and invites keyword-stuffing games.
5. *(proposal)* **Honest presentation of capped scores**: a result whose score came from the unsupported-credit cap should be shown as "unverified" rather than as "30/weak" in any future UI/shadow comparison (`flags.low_confidence_reasons` already identifies it). No code change now.
6. **Dataset-level:** distinguish "required" from "background" key concepts in the reference data (changes the dataset; needs your approval, not done).

## 5. Human-review sheet
`data/evaluation/stage3b_review/human_review_sheet_v1.{csv,md}`: B01, B03, B04, B07, B13, B20, with question, candidate answer, concepts actually requested, valid alternatives, a **proposed range drafted by Claude (AI, unreviewed, not human review)**, reasoning, and blank `REVIEWER_*` columns. No model scores appear. Expectations I flag as technically questionable: **B07** (reference broader than question; `partition` not asked), **B04** (upper bound arguable; "memory addresses" not requested), and over-lenient upper bounds on **B03 (35), B13 (30), B20 (40)**. Please fill the reviewer columns before these bands are used as ground truth.

## 6. Code changes this turn (no benchmark-ID logic; rubric weights, caps, injection and evidence checks untouched)
- `schema.OUTPUT_JSON_SCHEMA`; `OllamaProvider(response_schema=...)` (None = unchanged `format:"json"`); `stage3b_run.py --schema` (recorded as `structured_schema` in the run meta).
- `evaluator`: missing-keys diagnosis appended to the validation error; repair prompt names them.
- Known limitation kept: `contradicted_missing_concepts` can fire when a candidate merely *names* a topic it describes wrongly (B13), lowering confidence only.

## 7. Tests
New `tests/evaluation/test_stage3b_qwen_v2_diagnosis.py` (10 tests, real saved replies): B04 stays invalid/unscored and partial levels are unused; repair prompt names keys; B03 repair yields a verified major error; B13 low; B07 flagged but not boosted; schema requires every key and rejects the real early-close reply; compliant real reply passes the JSON schema (skipped if `jsonschema` is absent); Ollama sends the schema only when configured; missing scoring fields never defaulted; fabricated evidence + injection quote still blocked.
Results: evaluation 153 passed; combined retrieval+evaluation in the RAG venv 289 passed / 2 skipped (137/1 retrieval baseline intact, the extra skip is the optional `jsonschema` test); Flask app suite 77 passed / 5 skipped.

## 8. Performance (measured, v1+v2)
- Decode ≈ 6.5–7.4 tokens/s on a 58 %/42 % CPU/GPU split; generation is ≈ 95 % of a warm call. Complete replies average ≈ 421 output tokens ≈ 60 s. Early-closed replies cost ≈ 22 s but are unusable.
- Where the tokens go (estimated from character share × eval_count over 9 complete replies; approximate): rubric justifications 16.5 %, `improved_example_answer` 15.9 %, rubric levels/keys 10.8 %, `score_rationale` 9.9 %, suggestions 6.1 %, concepts 5.8 %, factual errors 5.6 %, `follow_up_question` 4.5 %, rest < 5 %.
- Shortening justifications to ≤ 15 words and dropping `improved_example_answer` + `follow_up_question` from the scoring call would remove ≈ 35 % of tokens (≈ 20 s) *if* quality is unaffected. **Not applied**: unmeasured. Test it only as a separate A/B after the structured-output question is settled. Note constrained decoding adds its own unknown cost.
- RAM stayed at 0.5–0.9 GB free during the run (pressure, no failures).

## 9. Recommendation
**Further local Qwen testing is worthwhile only as one bounded experiment, then decide.** Qwen 2.5 7B is reliable on clearly correct (B01), clearly incorrect (B03, B13) and injection (B20) cases, but in two runs it has not produced a usable grading for the short correct answer (B04) and mis-grades the valid alternative (B07) the same way both times. At ≈ 60–70 s per answer, a 43-answer pass is ≈ 50 minutes per configuration.
Run once (5 calls, ≈ 6–8 min) to test the structured-output fix:
```
powershell -ExecutionPolicy Bypass -File scripts\stage3b_qwen_confirm3.ps1
```
(B04, B03, B07 with `--schema`, plus B01/B13 controls; writes `data\evaluation\stage3b_qwen_v3\` and compares against v2.)
Decision rule: if B04 now returns a full valid reply **and** B04/B07 are no longer penalised for non-required concepts → continue with a small expansion (≈ 10 items) and fill the human-review sheet first. If B04 is valid but still scores ≈ 30, or B07 stays ≈ 68, stop prompt tuning for 7B local models and reassess the provider strategy (larger local model, or a hosted model, which needs your explicit approval). Do not use Qwen for live candidate scoring or shadow mode in any case yet.
