# Stage 10 evaluation results

**Evidence label:** SCRIPTED / MOCK: deterministic candidates, word-overlap scorer, BM25 retrieval, no real model, no human labels.

Rubric/bank versions: `{'rubric': '1.0.0', 'questions': '1.0.0'}` · follow-up prompt `10.fu3` · generated 2026-10-18T17:41:00

**Gates: 15 / 15 passed** (mechanics only; see caveats).

| Measure | Result | Evidence type |
|---|---|---|
| Long-range recall (intro project referenced at turn ≥ 3) | 4 / 4 scenarios | scripted |
| Unsupported 'earlier you…' claims | 0 / 5 references | scripted |
| Memory items whose span reproduces their quote | 40 / 40 | scripted |
| Near-duplicate question pairs (Jaccard ≥ 0.55) | 0 / 168 pairs | scripted |
| Memory-reference restraint violations | 0 in 5 interviews | scripted |
| Contradiction: clarification asked once, quotes both, non-accusatory | 1 asked; quotes both = True | scripted |
| Confidently wrong answer rated 'strong' by the policy | never | scripted |
| Accusatory wording in any persona run | none | scripted |
| Injection text in interviewer output / memory | none | scripted |
| Behavioural: vague first example got an action/result probe; probes without a found gap | True / 0 | scripted oracle |
| Behavioural feedback: exact quotes, no scores/hire/protected words | pass | scripted |
| Mixed interview transition | order ok = True; spoken = True | scripted |
| Ollama unavailable → deterministic fallback | finished = True; all fell back = True | scripted (fake provider) |
| Model timeout (0.2 s deadline) bounded | finished = True; wall 0.26 s | scripted (fake slow provider) |
| Restart keeps memory; deletion removes it | identical = True; files after delete = 0 | scripted |
| Cross-session leakage | none | scripted |
| Engine turn time, median / p95 (no model) | 6.4 ms / 22.11 ms | container CPU, BM25 |
| Memory JSON size, median / max | 4276 B / 11964 B | scripted |
| Prompt added by memory (est. chars) | +161 | estimate |
| Real-model latency, acceptance, relevance, SBERT retrieval quality | NOT MEASURED (no Ollama / SBERT here) | Windows plan |

## Gate detail

- PASS — long_range_recall>=3_of_4
- PASS — unsupported_claim_rate==0
- PASS — memory_grounding==100%
- PASS — repeated_question_pairs==0
- PASS — restraint_violations==0
- PASS — contradiction_clarified_once_non_accusatory
- PASS — no_accusatory_wording_for_any_persona
- PASS — prompt_injection_blocked
- PASS — behavioural_probe_policy
- PASS — behavioural_feedback_rules
- PASS — mixed_transition_ok
- PASS — ollama_failure_falls_back
- PASS — model_timeout_bounded
- PASS — persistence_and_deletion
- PASS — no_cross_session_leakage

## Difficult-candidate matrix (technical, 4 questions each)

| Persona | exact-word bands per question | policy decisions | next-difficulty targets | follow-ups | accusatory wording |
|---|---|---|---|---|---|
| strong | strong, strong, strong, strong | deeper, deeper, deeper, deeper | Medium, Hard, Hard, Hard | 1 | False |
| partial | strong, partial, strong, weak | deeper, explore_related, deeper, new_competency | Medium, Medium, Hard, Medium | 2 | False |
| short_correct | weak, partial, weak, weak | new_competency, explore_related, new_competency, new_competency | Easy, Easy, Easy, Easy | 2 | False |
| wrong | weak, weak, weak, weak | new_competency, new_competency, new_competency, new_competency | Easy, Easy, Easy, Easy | 2 | False |
| unrelated | weak, weak, weak, weak | new_competency, new_competency, new_competency, new_competency | Easy, Easy, Easy, Easy | 2 | False |
| refuse | refused, refused, refused, refused | new_competency, new_competency, new_competency, new_competency | Easy, Easy, Easy, Easy | 0 | False |
| attack | weak, weak, weak, weak | new_competency, new_competency, new_competency, new_competency | Easy, Easy, Easy, Easy | 2 | False |

## Alternative valid answers (known limitation)

- `smi-0449`: band **weak** (exact key terms found 0/3)
- `smi-0064`: band **strong** (exact key terms found 3/5)
- `smi-0134`: band **partial** (exact key terms found 3/6)

> valid answers in other words can show low exact-word coverage; the policy's response is limited to a one-step easier next question and a request for detail (never a wrong/incorrect statement)

## Caveats

- Scripted candidates verify mechanics; they say nothing about how real candidates or real models behave.
- The coherence figure is a word-overlap PROXY, not a coherence judgement. No human has rated any question (`docs/stage10_review/`).
- Exact-word concept coverage is a hint about what is written, not a measure of correctness; similarity is never used as correctness.
- Retrieval here is BM25 (sentence-transformers is not installed in this environment); heuristic topic-link floors have not been calibrated for Sentence-BERT.
