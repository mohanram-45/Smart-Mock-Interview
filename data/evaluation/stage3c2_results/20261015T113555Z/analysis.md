# Stage 3C-2 analysis (mechanical criteria only)

> Exploratory. n is tiny; AI expectations are provisional and not human-reviewed; nothing here is grading accuracy or human agreement.

**Decision under the frozen rule:** PARTIAL RUN: not the frozen experiment; no decision.

## Mechanical criteria

| criterion | value | result |
|---|---|---|
| valid_output_rate_min | 1.0 | PASS |
| provider_errors_max | 0 | PASS |
| gate_downgrade_rate_max | 0.0833 | PASS |
| unsupported_completeness_penalties_max | 0 | PASS |
| scored_results_without_derivation_max | 0 | PASS |
| evidence_claim_ids_not_in_answer_max | 0 | PASS |
| injection_flagged_claims_used_as_evidence_max | 0 | PASS |
| abstentions_without_recorded_reason_max | 0 | PASS |
| abstain_rate_max | 0.5 | FAIL |
| median_answer_latency_s_max | 23.1 | PASS |
| max_answer_latency_s_max | 103.19 | PASS |
| repeat_member_state_agreement_min | 0.8333 | FAIL |
| repeat_score_delta_max_points | 0 | PASS |

## Needs human labels

- false_credit_rate_max: PENDING_HUMAN
- false_error_rate_max: PENDING_HUMAN
- credit_rate_on_human_correct_concise_or_alternative_answers_min: PENDING_HUMAN
- essential_missing_penalties_contradicted_by_human_max: PENDING_HUMAN
- modular_unsupported_penalties_not_more_than_legacy: PENDING_HUMAN

## Metrics

```json
{
 "answers": 2,
 "modular_rows": 4,
 "legacy_rows": 2,
 "partial_run": true,
 "modular_status": {
  "scored": 2,
  "abstained": 2
 },
 "reached_verifier": 4,
 "valid_output_rate": 1.0,
 "provider_errors": 0,
 "invalid_responses": 0,
 "verdicts_total": 12,
 "verdict_states_after_gate": {
  "states_correctly": 8,
  "unverified": 1,
  "not_stated": 3
 },
 "verdict_states_as_returned_by_model": {
  "states_correctly": 8,
  "states_incorrectly": 1,
  "not_stated": 3
 },
 "model_stated_non_unverified": 12,
 "gate_downgrades": 1,
 "gate_downgrade_rate": 0.0833,
 "evidence_rejection_reasons": {
  "no_valid_evidence": 1
 },
 "essential_missing_penalties": 1,
 "unsupported_completeness_penalties": 0,
 "scored_results_without_derivation": 0,
 "evidence_claim_ids_not_in_answer": 0,
 "injection_flagged_claims_used_as_evidence": 0,
 "abstentions_without_recorded_reason": 0,
 "abstain_rate": 0.5,
 "median_answer_latency_s": 23.1,
 "p95_answer_latency_s": 103.195,
 "max_answer_latency_s": 103.19,
 "legacy_median_latency_s": 75.6,
 "median_decode_tokens_per_s": 7.9,
 "repeat_member_state_agreement": 0.8333,
 "repeat_score_delta_max_points": 0,
 "repeat_scored_vs_abstained_flips": 0,
 "peak_ollama_size_vram_bytes": 2242012773,
 "gpu_snapshots": [
  "NVIDIA GeForce GTX 1650 Ti, 3178 MiB, 4096 MiB, 28 %",
  "NVIDIA GeForce GTX 1650 Ti, 3287 MiB, 4096 MiB, 24 %",
  "NVIDIA GeForce GTX 1650 Ti, 3346 MiB, 4096 MiB, 31 %",
  "NVIDIA GeForce GTX 1650 Ti, 3352 MiB, 4096 MiB, 13 %"
 ]
}
```

## Side by side (for reading; AI expectations are provisional)

| id | q | AI kind | AI range | modular | score | legacy | score | modular dims | legacy missing |
|---|---|---|---|---|---|---|---|---|---|
| b2-006 | smi-0064 | correct_full | [85, 100] | scored | 100 | graded_low_confidence | 75 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 4} | [] |
| s2-f01 | smi-0449 | off_topic | [None, None] | abstained | None | graded | 0 | {'correctness': None, 'completeness': None, 'relevance': 0, 'reasoning': 4} | ['binary search', 'O(log n)'] |
