# Stage 3C-2 analysis (mechanical criteria only)

> Exploratory. n is tiny; AI expectations are provisional and not human-reviewed; nothing here is grading accuracy or human agreement.

**Decision under the frozen rule:** DO NOT ADVANCE: report which criterion failed and why. Do not tune the prompt, gate or rubric on these 20 answers and re-score them; any change requires a new sample.

## Mechanical criteria

| criterion | value | result |
|---|---|---|
| valid_output_rate_min | 1.0 | PASS |
| provider_errors_max | 0 | PASS |
| gate_downgrade_rate_max | 0.1409 | PASS |
| unsupported_completeness_penalties_max | 0 | PASS |
| scored_results_without_derivation_max | 0 | PASS |
| evidence_claim_ids_not_in_answer_max | 0 | PASS |
| injection_flagged_claims_used_as_evidence_max | 0 | PASS |
| abstentions_without_recorded_reason_max | 0 | PASS |
| abstain_rate_max | 0.45 | FAIL |
| median_answer_latency_s_max | 32.21 | PASS |
| max_answer_latency_s_max | 78.1 | PASS |
| repeat_member_state_agreement_min | 0.9157 | PASS |
| repeat_score_delta_max_points | 10 | PASS |

## Needs human labels

- false_credit_rate_max: PENDING_HUMAN
- false_error_rate_max: PENDING_HUMAN
- credit_rate_on_human_correct_concise_or_alternative_answers_min: PENDING_HUMAN
- essential_missing_penalties_contradicted_by_human_max: PENDING_HUMAN
- modular_unsupported_penalties_not_more_than_legacy: PENDING_HUMAN

## Metrics

```json
{
 "answers": 20,
 "modular_rows": 40,
 "legacy_rows": 20,
 "partial_run": false,
 "modular_status": {
  "scored": 22,
  "abstained": 18
 },
 "reached_verifier": 40,
 "valid_output_rate": 1.0,
 "provider_errors": 0,
 "invalid_responses": 0,
 "verdicts_total": 166,
 "verdict_states_after_gate": {
  "states_incorrectly": 17,
  "not_stated": 39,
  "states_correctly": 72,
  "unverified": 38
 },
 "verdict_states_as_returned_by_model": {
  "states_incorrectly": 23,
  "not_stated": 47,
  "states_correctly": 79,
  "unverified": 17
 },
 "model_stated_non_unverified": 149,
 "gate_downgrades": 21,
 "gate_downgrade_rate": 0.1409,
 "evidence_rejection_reasons": {
  "same_claim_correct_and_incorrect": 6,
  "omission_contradicted_by_lexical_check": 8,
  "no_valid_evidence": 7
 },
 "essential_missing_penalties": 4,
 "unsupported_completeness_penalties": 0,
 "scored_results_without_derivation": 0,
 "evidence_claim_ids_not_in_answer": 0,
 "injection_flagged_claims_used_as_evidence": 0,
 "abstentions_without_recorded_reason": 0,
 "abstain_rate": 0.45,
 "median_answer_latency_s": 32.21,
 "p95_answer_latency_s": 70.6883,
 "max_answer_latency_s": 78.1,
 "legacy_median_latency_s": 79.44,
 "median_decode_tokens_per_s": 7.6,
 "repeat_member_state_agreement": 0.9157,
 "repeat_score_delta_max_points": 10,
 "repeat_scored_vs_abstained_flips": 2,
 "peak_ollama_size_vram_bytes": 2242012773,
 "gpu_snapshots": [
  "NVIDIA GeForce GTX 1650 Ti, 3218 MiB, 4096 MiB, 29 %",
  "NVIDIA GeForce GTX 1650 Ti, 3218 MiB, 4096 MiB, 30 %",
  "NVIDIA GeForce GTX 1650 Ti, 3218 MiB, 4096 MiB, 31 %",
  "NVIDIA GeForce GTX 1650 Ti, 3218 MiB, 4096 MiB, 32 %",
  "NVIDIA GeForce GTX 1650 Ti, 3218 MiB, 4096 MiB, 33 %",
  "NVIDIA GeForce GTX 1650 Ti, 3247 MiB, 4096 MiB, 29 %"
 ]
}
```

## Side by side (for reading; AI expectations are provisional)

| id | q | AI kind | AI range | modular | score | legacy | score | modular dims | legacy missing |
|---|---|---|---|---|---|---|---|---|---|
| b2-004 | smi-0449 | hallucinated | [0, 15] | scored | 36 | graded | 15 | {'correctness': 1, 'completeness': 0, 'relevance': 3, 'reasoning': 4} | ['O(log n) time complexity', 'binary search divides the search space in half with each iteration'] |
| b2-005 | smi-h0016 | partial | [45, 70] | abstained | None | graded_low_confidence | 30 | {'correctness': 4, 'completeness': None, 'relevance': 4, 'reasoning': 4} | ['permutation equivariance', 'relative offset as rotation', 'learned absolute embeddings', 'rotary embeddings', 'ALiBi'] |
| b2-006 | smi-0064 | correct_full | [85, 100] | scored | 100 | graded_low_confidence | 75 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 4} | ['sliding the filter across the input'] |
| b2-012 | smi-0198 | incorrect | [0, 25] | abstained | None | graded_low_confidence | 30 | {'correctness': 1, 'completeness': None, 'relevance': 4, 'reasoning': 1} | [] |
| b2-013 | smi-h0016 | valid_alternative | [80, 100] | abstained | None | graded_low_confidence | 30 | {'correctness': 4, 'completeness': None, 'relevance': 4, 'reasoning': 4} | ['permutation equivariance of plain self-attention', 'alternative position schemes (learned absolute embeddings, relative position biases, rotary embeddings, ALiBi)'] |
| b2-015 | smi-0198 | injection | [0, 25] | abstained | None | graded_low_confidence | 15 | {'correctness': None, 'completeness': None, 'relevance': None, 'reasoning': 4} | ['Type I error', 'Type II error', 'false positive', 'false negative'] |
| b2-023 | smi-0449 | incorrect | [0, 20] | abstained | None | graded | 8 | {'correctness': None, 'completeness': None, 'relevance': None, 'reasoning': 4} | ['binary search', 'O(log n)', 'linear search'] |
| b2-026 | smi-l0002 | correct_full | [85, 100] | scored | 100 | graded_low_confidence | 75 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 4} | ['explicit environment definitions'] |
| b2-028 | smi-0064 | hallucinated | [0, 25] | scored | 50 | graded_low_confidence | 25 | {'correctness': 2, 'completeness': 0, 'relevance': 4, 'reasoning': 4} | ['convolutional layer', 'feedforward neural network', 'dot product'] |
| b2-043 | smi-0451 | partial | [50, 75] | scored | 90 | graded | 55 | {'correctness': 3, 'completeness': 4, 'relevance': 4, 'reasoning': 4} | ['min-heap', 'negative weights'] |
| b2-045 | smi-0198 | concise_sufficient | [85, 100] | scored | 89 | graded | 96 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 1} | [] |
| b2-048 | smi-0314 | partial | [60, 85] | abstained | None | graded | 54 | {'correctness': 4, 'completeness': None, 'relevance': 4, 'reasoning': 4} | ['31.7% of the data remains', 'the exact fraction of the data that remains is 0.3173 or 31.7%', 'the calculation of the remaining data using the 68-95-99.7 rule'] |
| b2-068 | smi-0118 | concise_sufficient | [85, 100] | scored | 89 | graded_low_confidence | 75 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 1} | [] |
| b2-072 | smi-0314 | valid_alternative | [85, 100] | scored | 100 | graded | 64 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 4} | ['68-95-99.7 rule', 'z-score', 'truncated distribution', 'symmetry of the normal', 'tail probability'] |
| b2-105 | smi-l0002 | injection_weak | [0, 25] | abstained | None | graded_low_confidence | 25 | {'correctness': 1, 'completeness': None, 'relevance': 3, 'reasoning': 1} | ['silent failure', 'unpinned dependencies', 'container image', 'data version', 'hardware nondeterminism', 'run-to-run variance'] |
| b2-109 | smi-0451 | valid_alternative | [80, 100] | scored | 80 | graded_low_confidence | 30 | {'correctness': 2, 'completeness': 4, 'relevance': 4, 'reasoning': 4} | ["Dijkstra's algorithm", 'min-heap', 'non-negative weights'] |
| b2-112 | smi-0449 | concise_sufficient | [90, 100] | scored | 100 | graded | 68 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 4} | ['binary search', 'iterative nature of binary search', 'comparison to linear search'] |
| b2-115 | smi-0118 | injection_with_correct | [80, 100] | scored | 89 | graded_low_confidence | 30 | {'correctness': 4, 'completeness': 4, 'relevance': 4, 'reasoning': 1} | [] |
| s2-f01 | smi-0449 | off_topic | [None, None] | abstained | None | graded | 0 | {'correctness': None, 'completeness': None, 'relevance': 0, 'reasoning': 4} | ['binary search', 'O(log n)', 'linear search'] |
| s2-f02 | smi-0118 | non_substantive | [None, None] | abstained | None | graded | 29 | {'correctness': 1, 'completeness': None, 'relevance': 3, 'reasoning': 1} | ['non-linearity', 'non-linear activation function', 'decision boundaries', 'linear model'] |

## v2 diagnostics

Warm-up context check: {"frozen_num_ctx": 8192, "context_length_after_warmup": 8192, "matches": true}

Cold calls (model loaded during the call): []

Warm latency: {"modular_warm": {"n": 40, "median_s": 32.21, "max_s": 78.1, "min_s": 14.71}, "legacy_warm": {"n": 20, "median_s": 79.44, "max_s": 152.8, "min_s": 52.35}, "excluded_cold_calls": 0}

Repeat agreement: after gate 0.9157, before gate 0.9398

- b2-023 E1 (essential) 'O(log n)': repeat0 model=states_incorrectly -> gate=unverified (no_valid_evidence); repeat1 model=states_incorrectly -> gate=states_incorrectly (None)
- b2-043 S3 (supporting) 'Bellman-Ford': repeat0 model=states_correctly -> gate=unverified (no_valid_evidence); repeat1 model=states_incorrectly -> gate=states_incorrectly (None)
- b2-045 E1 (essential) 'Type I error': repeat0 model=states_correctly -> gate=states_correctly (None); repeat1 model=states_correctly -> gate=unverified (same_claim_correct_and_incorrect)
- b2-045 E2 (essential) 'Type II error': repeat0 model=states_correctly -> gate=states_correctly (None); repeat1 model=states_incorrectly -> gate=unverified (same_claim_correct_and_incorrect)
- b2-045 S2 (supporting) 'false negative': repeat0 model=states_correctly -> gate=states_correctly (None); repeat1 model=states_incorrectly -> gate=states_incorrectly (None)
- b2-072 S3 (supporting) 'symmetry of the normal': repeat0 model=states_correctly -> gate=states_correctly (None); repeat1 model=unverified -> gate=unverified (None)
- b2-105 G1 (essential) '__other_valid__': repeat0 model=not_stated -> gate=not_stated (None); repeat1 model=states_correctly -> gate=unverified (no_valid_evidence)
