# Stage 3A evaluation rubric (version 3a.1)

The model judges **four dimensions on a 0-4 scale**. It does **not** output an overall score. Code computes
`score = round( Σ weight_d × level_d / 4 )`, applies the caps below, and records every adjustment in `score_adjustments`.

| dimension | weight | what is judged |
|---|---|---|
| correctness | 40 | Are the candidate's claims accurate? Claims are judged, not wording. A correct alternative explanation is correct. Wrong statements become `factual_errors` (minor / major). **Omissions are never factual errors.** |
| completeness | 30 | Does the answer cover what *this question* needs (key concepts/reference are a guide, not a checklist)? A short answer that covers it is complete. Length earns nothing. |
| relevance | 15 | Does it address the question asked? Fluent off-topic text scores 0-1. |
| reasoning | 15 | Does it explain why/how (mechanism, trade-offs), scaled to the question type? |

Levels: 4 fully meets · 3 mostly · 2 partly · 1 barely · 0 does not.

## Deterministic caps (applied by code, in `rubric.apply_caps` and `evaluator._finish`)
1. relevance = 0 → score ≤ 10.
2. any **major** factual error → score ≤ 60, and correctness is re-scored as 1 if the model gave more (contradiction).
3. minor factual error(s) with correctness = 4 → correctness re-scored as 3.
4. key concepts exist but **no demonstrated concept could be verified** against the candidate's own words → score ≤ 30 and status `graded_low_confidence`.
   (A candidate who is right must be quotable. Quotes that match prompt-injection patterns never count.)

Bands: ≥85 excellent · ≥70 good · ≥50 fair · ≥25 weak · else very_weak. The number is always called **provisional**.

## Evidence rules
* `correct_concepts[].candidate_quote` and `factual_errors[].claim_quote` must be exact (whitespace/case/punctuation-normalised) substrings of the candidate answer.
* `supporting_evidence[].quote` must be a substring of the named source (`candidate_answer`, `reference_answer`, `key_concepts`, `supporting_knowledge`).
* Anything unverifiable is **removed and counted** (`flags.dropped_unverifiable`) with a limitation note. An invented factual error therefore cannot penalise a candidate, and an invented concept cannot reward one. Empty evidence lists are allowed.

## Statuses
`graded` · `graded_low_confidence` (scored but treat as provisional) · `insufficient_evidence` (no usable reference/key concepts, or the model declined) ·
`not_gradable` (empty or non-answer) · `provider_error` · `invalid_response` · `provider_not_configured`. Only the first two carry a number.

## Confidence
The model's stated confidence can only be **lowered** by grounding facts: medium if the reference is legacy/time-sensitive/has recorded limitations; low if there is no reference answer or the candidate text looks like an injection attempt.

This rubric is a design decision, not a validated instrument. Its weights have not been compared with human graders.
