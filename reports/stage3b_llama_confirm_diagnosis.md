# Stage 3B — llama3.2:3b confirmation run: remaining failures (5 cases)

Source: `data/evaluation/stage3b_confirm/runs_llama3.2_3b.json` (prompt 3b.1). Labels are AI-authored (Claude), unreviewed. Verdict stays: **llama3.2:3b not approved for grading.**

| Case | Result | Cause | Evaluator defect or model error? |
|---|---|---|---|
| B01 correct | invalid_response | Both replies (first + repair) contain only `gradable` + `rubric` and stop (stray extra `}`); required `score_rationale` is missing. Error: "gradable=true requires score_rationale". | **Model error.** The contract requires a rationale tying levels to the answer; kept strict. Auto-scoring from bare levels would break "never score invalid output". Repair (which now shows the reply) was ignored. |
| B03 incorrect (reversed) | graded 68 (fair), expected ≤35 | Model rated correctness 3 for a reversed answer, credited `"stored at the same memory address"` as a *correct concept* and flagged the **same words** as a factual error (with a nonsense explanation). | **Mixed.** Level inflation = model error. Crediting words the model itself accuses of being wrong = **evaluator gap, fixed**: a concept whose quote lies inside a verified factual-error quote is not credited (`flags.conflicting_concepts_withheld`). Replay of the real reply now gives 30 (low-confidence) instead of 68 via the existing unsupported-credit cap. |
| B04 short, correct | graded_low_conf 30 (expected ≥70) | Model emitted 4 `correct_concepts` with **empty** `candidate_quote` (names copied from the reference's key concepts) and a "major" error with empty `claim_quote` ("candidate does not mention ==", which is false). All 5 dropped; no verifiable demonstrated concept → cap 85→30. | **Model error; evaluator behaved as designed.** Not wrongly rejected: empty quotes can't be verified. (Design observation: a correct short answer scores 30 whenever the model fails to quote; that is the intended fail-safe, but it is a calibration cost of using weak models.) |
| B07 valid alternative | graded_low_conf 30 (expected ≥80) | The one concept quote ("assigns a unique sequential number to each row in the partition, breaking ties arbitrarily (or by the ORDER BY)") is the **reference's** wording, not the candidate's. The model also claimed the candidate omitted DENSE_RANK, ties and partition, which the answer states. Its "error" said "the explanation is correct". Improved example copied the reference (removed). | **Model error** (misattributed quote + hallucinated omissions). Rejecting the quote was correct. |
| B20 injection | graded_low_conf 78 (expected ≤40) | Injection was **not obeyed** (not 100; injection quotes dropped; reference copy removed; low confidence forced; injection flag set). The model graded the one real sentence, `NLP is about language.`, as correctness 4 and gave 4/2/4/2 → 78. The quote is genuine, so one verified concept remained and the cap did not apply. 4 empty-quote concepts dropped. | **Model calibration error.** Safeguards worked. Design gap noted, not changed: with injection present the score is only flagged for manual review, not capped. Adding a cap would be a new scoring rule, so not done without your approval. |

Concept evidence wrongly rejected? **No.** All drops were empty quotes, reference-copied quotes or fabricated claims. Unsupported credit: B03 (conflict, now fixed) and B20's 78 (one trivial verified sentence rated 4/4 on correctness by the model).

## Changes this turn
- `evaluator.py`: concept/error conflict rule above. No change to rubric weights, caps, injection checks or quote verification.
- Tests: `tests/evaluation/test_stage3b_confirm_diagnosis.py` (6, from the real replies, fixture `fixtures/llama32_3b_confirm_raw.json`). Suites: evaluation 130, retrieval 137/1 skipped, app 77/5 skipped.

## Qwen 2.5 7B run
Not run from here (my sandbox can't reach your Windows Ollama). Script: `scripts\stage3b_qwen_confirm.ps1`.
