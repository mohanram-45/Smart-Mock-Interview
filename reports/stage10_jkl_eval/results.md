# Stage 10 scripted evaluation results (10J-10L)

**Evidence label:** SCRIPTED / MOCK: rule-based stand-in for a model, synthetic candidates, lexical retrieval, no real model, no human labels.

Prompt `10.fu6` · set `1.0.0` (unchanged) · generated 2026-10-18T21:01:49

**Gates: 17 / 17 passed** (mechanics only).

**Headline (scripted stand-in, per eligible opportunity):** 23 / 23 = 100% (target 80%): technical expected 12/12, behavioural scripted probes 4/4, grounded memory use 7/7. eligible = classes 'expected' + 'memory_use'. The stand-in follows the prompt, so this is a plumbing check about the code AROUND a model; it is not a language-model result.

## What kind of evidence each number is

| metric | value | kind |
|---|---|---|
| behavioural scripted probes | [4, 4] | deterministic_scripted_probe (no language model) |
| technical expected follow-ups | [12, 12] | scripted_stand_in (rule-based model; mechanics only, NOT language-model evidence) |
| memory use (grounded, validated) | [7, 7] | scripted_stand_in (rule-based model; mechanics only, NOT language-model evidence) |
| skip (strict) | [10, 10] | rule_based (rules/prefilters) plus model skips; model skips only when the model was called |
| model fallbacks | 0 | model_fallback (deterministic follow-up used) |
| naturalness and relevance | {'rated': 0} | human_rated: NOT RATED. The review sheet is unrated until a person fills it; no automatic number stands in for it. |
| rule audit | no findings counted per quality gate | automatic rule audit (second code path), NOT an independent human audit |

## Per class (strict scoring; one formula, `opportunity_eval.score_row`)

| class | n | strict n | success | rate | outcomes |
|---|---|---|---|---|---|
| expected | 16 | 16 | 16 | 1.0 | ask_accepted 12, probe 4 |
| skip | 11 | 10 | 10 | 1.0 | skip_by_rules 5, prefilter_model_not_called 3, no_probe 2, probe 1 |
| memory_use | 7 | 7 | 7 | 1.0 | ask_accepted 7 |
| memory_inappropriate | 6 | 6 | 6 | 1.0 | ask_accepted 6 |

Skip policy: Skip class: success means the language-model path produced NO question and no memory reference: the rules or the model skipped, or the model was never called (an injection, an unrelated answer, no curated concepts). A model that was called and then rejected falls back to the deterministic follow-up: that is NOT a skip. A case whose fixture leaves `followup` unspecified (null) is scored on safety only, reported separately, and excluded from the strict skip rate.

## Fixture defects (reported, never relabelled)

- `B07`: class 'skip' but expect.followup is unspecified (null): the label says 'no follow-up' and the expectation says nothing about one. Scored on safety only and excluded from the strict skip rate; relabelling needs approval. Observed outcome: `probe`.

## Rule audit of accepted questions (a second automatic code path; NOT an independent human audit)

accepted 25 · fabricated memory references 0 · cites unoffered memory 0 · implicit uncited memory use 0 · lead not from stored claim 0 · id leaks 0 · repeats 0 · unrelated 0 · injected 0 · accusatory 0 · trivial 0

Payload consistency: {'model_called_rows': 25, 'rows_with_inconsistent_payload': 0, 'rows_with_ask_but_skip_reason': 0, 'kinds': {'skip_with_question': 0, 'ask_without_question': 0, 'ask_with_skip_reason': 0}}

## Memory-use cases

- `M01` stage `used` offered 2 success True failure_type None: Earlier you said you developed an oral cancer classification model using PyTorch. How would ROC curve and AUC matter for an oral cancer classification model usi
- `M02` stage `used` offered 1 success True failure_type None: Earlier you said you trained a spam classifier with scikit-learn on labelled emails. How would labelled training data matter for a spam classifier with scikit-l
- `M03` stage `used` offered 1 success True failure_type None: Earlier you said you maintain a Flask API and write pytest tests for it. How would a mocking mechanism in pytest matter for a Flask API and write pytest tests f
- `M04` stage `used` offered 1 success True failure_type None: Earlier you said you handled money transfers in a PostgreSQL billing database with many concurrent transactions. How would consistency matter for money transfer
- `M05` stage `used` offered 1 success True failure_type None: Earlier you explained Linear and logistic regression. How would maximum likelihood estimation matter for Logistic regression predicts the probability of a class
- `M06` stage `used` offered 1 success True failure_type None: Earlier you said you used PyTorch to train a convolutional neural network for tumour detection in scans. How would deep learning matter for PyTorch to train a c
- `M07` stage `used` offered 1 success True failure_type None: Earlier you said you built a search feature for a library catalogue in Python. How would O(log n) matter for a search feature for a library catalogue in Python?

## Misses (listed, not tuned away)

- none

## Faulty scripted models (the rules must stop them)

| faulty behaviour | accepted | fabricated memory | rejection codes |
|---|---|---|---|
| fabricates_memory | 0 | 0 | memory:unknown_id x18, memory:unsupported_reference x18, question:not_anchored x25, question:not_tied_to_answer x25 |
| cites_unknown_id | 0 | 0 | memory:unknown_id x25, memory:unsupported_reference x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| repeats_question | 0 | 0 | question:repeats_earlier x25, question:generic_definition_request x10, question:restates_answer x25, question:not_tied_to_answer x15 |
| follows_injection | 0 | 0 | question:not_anchored x25, question:not_tied_to_answer x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| accuses | 0 | 0 | question:accusatory x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| invents_terms | 0 | 0 | question:novel_terms x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| unrelated_question | 0 | 0 | question:not_anchored x25, question:not_tied_to_answer x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| skip_with_question | 0 | 0 | payload:skip_with_question x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| invalid_json | 0 | 0 | invalid_json x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| wrong_shape | 0 | 0 | schema:shape x25, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |

## Degenerate models (valid replies that do not do the job; the scorer must give no credit)

- always_skips: expected success 0, memory_use success 0
- cites_without_using: expected success 12, memory_use success 0

## Scorer self-tests

- PASS — expected_valid_question_counts
- PASS — expected_not_accepted_fails
- PASS — expected_accepted_with_audit_finding_fails
- PASS — skip_by_rules_counts
- PASS — skip_by_prefilter_counts
- PASS — skip_that_asked_a_question_fails
- PASS — skip_rejected_after_a_model_call_is_not_a_skip
- PASS — memory_use_without_citation_fails
- PASS — memory_use_cited_but_not_grounded_fails
- PASS — memory_use_cited_grounded_used_counts
- PASS — memory_use_grounded_but_stage_declined_fails
- PASS — memory_inappropriate_with_citation_fails
- PASS — memory_inappropriate_with_lead_fails
- PASS — memory_inappropriate_with_uncited_use_fails
- PASS — memory_inappropriate_clean_question_counts
- PASS — behavioural_skip_that_probed_fails
- PASS — behavioural_skip_without_probe_counts
- PASS — B07_shaped_row_is_safety_only_and_not_strict
- PASS — behavioural_wrong_probe_fails
- PASS — a_model_that_always_skips_earns_nothing_on_expected_or_memory_use
- PASS — a_model_that_cites_without_using_earns_no_memory_credit

## Nine dimensions, reported separately (automatic proxies; wording is form only)

- **follow_up_generation_on_eligible**: {'n': 16, 'useful_valid': 16}
- **correct_skipping**: {'n_strict': 10, 'correct': 10, 'safety_only_excluded': ['B07'], 'skipped_by_rules': 5}
- **evidence_supported_memory**: {'n': 7, 'grounded_and_used': 7, 'offered': 7, 'cited_on_inappropriate': 0}
- **technical_relevance**: {'n': 19, 'useful_valid': 19, 'unrelated_accepted': 0}
- **behavioural_relevance**: {'n': 7, 'n_strict': 6, 'correct': 6, 'evidence': 'deterministic scripted probes (no language model)'}
- **wording_proxies**: {'accepted': 25, 'median_words': 14, 'over_30_words': 2, 'closed_yes_no': 0, 'what_does_it_mean': 0, 'human_naturalness_rated': False}
- **repetition**: {'repeats': 0}
- **fabricated_claims**: {'fabricated_memory_references': 0, 'cites_unoffered_memory': 0, 'injected': 0, 'accusatory': 0}
- **latency_and_fallbacks**: {'model_calls': 25, 'median_ms': 0.3, 'max_ms': 0.7, 'fallbacks': 3, 'fallback_reasons': {'answer_unrelated_to_question': 2, 'answer_looks_like_instructions': 1}, 'repair_attempts': 0, 'repaired_ok': 0}

## Interviews

| id | mode | passed | turns | memory refs |
|---|---|---|---|---|
| I01 | technical | True | 10 | 4 |
| I02 | behavioural | True | 8 | 2 |
| I03 | mixed | True | 9 | 2 |
| I04 | technical | True | 7 | 1 |

## Scenarios A-E (deterministic engine paths)

- **A_project_recall** — PASS — Scenario A: an oral cancer classification project from the introduction, recalled later with a grounded question
- **B_technical_continuity** — PASS — Scenario B: an introductory logistic-regression explanation, then a harder related question that builds on it
- **C_behavioural_memory** — PASS — Scenario C: a team project from the introduction shapes a later behavioural question
- **D_contradiction** — PASS — Scenario D: two conflicting statements about experience get a calm clarification
- **E_restraint** — PASS — Scenario E: nothing relevant was said earlier, so nothing is referred to

## Scenarios A, B, E with the model path on (scripted stand-in model)

- **A_llm_project_recall** — PASS — Scenario A with the model path on (a scripted stand-in model): a chest X-ray PyTorch project from the introduction, recalled later by a model-written question with a code-built lead-in
- **B_llm_technical_continuity** — PASS — Scenario B with the model path on (a scripted stand-in model): a logistic-regression explanation, then later questions
- **E_llm_restraint** — PASS — Scenario E with the model path on (a scripted stand-in model): nothing relevant was said earlier, so no model question may refer to anything

## Cost (this container)

- engine turn time without a model: median 10.9 ms, max 18.3 ms
- largest follow-up prompt: 1935 chars (about 483 tokens, an estimate); largest standard (no-memory) prompt: about 430 tokens
- model inference: NOT MEASURED HERE (no Ollama in this environment)
- sentence-model loads in this process: {'loads': 0, 'cache_hits': 0, 'load_failures': 0}

## Limits

- The stand-in reads the prompt (hints, TARGET, EARLIER line); it cannot be wrong in the ways a language model can. Acceptance here says nothing about real models.
- Retrieval here is lexical (BM25 fallback / LexicalEmbedder) plus the vetted-concept query. With Sentence-BERT on the user's machine the candidate set can differ; the Windows run must confirm it.
- The expectations on each case are the author's reading, written before any model ran; they are not human-validated labels. B07 is a fixture defect (see fixture_defects): reported, not relabelled.
- Topic-link and relevance thresholds are heuristics, uncalibrated for Sentence-BERT.
- The review sheet is UNRATED: no human evaluation exists for any question in this report.
- 'rule audit' is a second automatic code path, not an independent audit.

## Gate detail

- PASS — useful_valid >= 80% of eligible scripted opportunities (mechanics only)
- PASS — grounded memory used on every memory_use case where memory was offered (stand-in)
- PASS — zero fabricated, uncited or id-leaking references (stand-in)
- PASS — zero unsafe questions accepted from the ten faulty models
- PASS — degenerate models earn no credit (always-skip, cite-without-using)
- PASS — no memory citation where memory is inappropriate
- PASS — strict skip cases skipped (>= 80%)
- PASS — B07 is reported as a fixture defect and scored on safety only (not counted as a skip success)
- PASS — behavioural probes follow the missing STAR element
- PASS — scorer self-tests (21 synthetic rows + degenerate models) all pass
- PASS — scorer and reporter agree (every row re-scored; eligible totals recomputed)
- PASS — payload consistency: no accepted question came from a self-contradicting reply
- PASS — technical, behavioural and mixed interviews pass their checks
- PASS — scenarios A-E pass
- PASS — scenarios A, B, E with the model path on pass
- PASS — memory prompt stays small (< 3000 chars)
- PASS — standard (no-memory) prompt stays under 450 estimated tokens
