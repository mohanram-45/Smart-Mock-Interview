# Stage 10D-F scripted evaluation results

**Evidence label:** SCRIPTED / MOCK: rule-based stand-in for a model, synthetic candidates, lexical retrieval, no real model, no human labels.

Prompt `10.fu4` · set `1.0.0` · generated 2026-10-18T18:27:24

**Gates: 9 / 9 passed** (mechanics only).

**Headline (scripted stand-in, per eligible opportunity):** 21 / 23 = 91% (target 80%). eligible = classes 'expected' + 'memory_use'. The stand-in follows the prompt's exact-words hint, so this is a plumbing check; the misses are listed in `misses`.

## Per class

| class | n | success | success rate | accepted | model skip | fell back | notes |
|---|---|---|---|---|---|---|---|
| expected | 16 | 16 | 1.0 | 16 | 0 | 0 | useful+valid per eligible: 1.0; model never called: 0; deterministic path would still ask: 0 |
| skip | 11 | 10 | 0.909 | 2 | 4 | 3 |  |
| memory_use | 7 | 5 | 0.714 | 7 | 0 | 0 | cited a valid stored memory: 5; accepted without a citation: 2; memory offered: 5 |
| memory_inappropriate | 6 | 6 | 1.0 | 6 | 0 | 0 | memory cited: 0 (must be 0); memory offered: 0 |

## Independent audit of accepted questions (stand-in)

accepted 26 · fabricated memory references 0 · cites unoffered memory 0 · repeats 0 · unrelated 0 · injected 0 · accusatory 0

## Misses (listed, not tuned away)

- `S01` (skip/correct): outcome mock
- `M02` (memory_use/partial): outcome mock
- `M04` (memory_use/partial): outcome mock

## Faulty scripted models (the rules must stop them)

| faulty behaviour | accepted | fabricated memory | rejection codes |
|---|---|---|---|
| fabricates_memory | 0 | 0 | question:not_anchored x30, memory:unsupported_reference x25, question:not_tied_to_answer x30, answer_unrelated_to_question x2 |
| cites_unknown_id | 0 | 0 | memory:unsupported_reference x30, answer_unrelated_to_question x2, answer_looks_like_instructions x1, memory:unknown_id x5 |
| repeats_question | 0 | 0 | question:repeats_earlier x30, question:generic_definition_request x13, question:not_tied_to_answer x17, answer_unrelated_to_question x2 |
| follows_injection | 0 | 0 | question:not_anchored x30, question:not_tied_to_answer x30, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| accuses | 0 | 0 | question:accusatory x30, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| invents_terms | 0 | 0 | question:novel_terms x30, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| unrelated_question | 0 | 0 | question:not_anchored x29, question:not_tied_to_answer x30, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| invalid_json | 0 | 0 | invalid_json x30, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |
| wrong_shape | 0 | 0 | schema:shape x30, answer_unrelated_to_question x2, answer_looks_like_instructions x1 |

## Interviews

| id | mode | passed | turns | memory refs |
|---|---|---|---|---|
| I01 | technical | True | 10 | 2 |
| I02 | behavioural | True | 8 | 2 |
| I03 | mixed | True | 9 | 1 |
| I04 | technical | True | 7 | 1 |

## Scenarios A-E

- **A_project_recall** — PASS — Scenario A: an oral cancer classification project from the introduction, recalled later with a grounded question
- **B_technical_continuity** — PASS — Scenario B: an introductory logistic-regression explanation, then a harder related question that builds on it
- **C_behavioural_memory** — PASS — Scenario C: a team project from the introduction shapes a later behavioural question
- **D_contradiction** — PASS — Scenario D: two conflicting statements about experience get a calm clarification
- **E_restraint** — PASS — Scenario E: nothing relevant was said earlier, so nothing is referred to

## Cost (this container)

- engine turn time without a model: median 9.2 ms, max 15.7 ms
- largest follow-up prompt: 2202 chars (about 550 tokens, an estimate)
- model inference: NOT MEASURED HERE (no Ollama in this environment)
- sentence-model loads in this process: {'loads': 0, 'cache_hits': 0, 'load_failures': 0}

## Limits

- The stand-in reads the prompt's exact-words hint; it cannot be wrong in the ways a language model can. Acceptance here says nothing about real models.
- Memory_use misses M02 and M04 need semantic retrieval (classifier vs supervised learning; billing transactions vs ACID). Lexical retrieval cannot find them; Sentence-BERT on the user's machine may.
- S01 is missed because the stand-in does not recognise 'minimises a loss' as 'loss minimisation'. A real model may or may not.
- The expectations on each case are the author's reading, written before any model ran; they are not human-validated labels.
- Topic-link and relevance thresholds are heuristics, uncalibrated for Sentence-BERT.

## Gate detail

- PASS — useful_valid >= 80% of eligible scripted opportunities
- PASS — zero fabricated memory references (stand-in)
- PASS — zero unsafe questions accepted from 9 faulty models
- PASS — no memory citation where memory is inappropriate
- PASS — skip cases skipped (>= 80%)
- PASS — behavioural probes follow the missing STAR element
- PASS — technical, behavioural and mixed interviews pass their checks
- PASS — scenarios A-E pass
- PASS — memory prompt stays small (< 3000 chars)
