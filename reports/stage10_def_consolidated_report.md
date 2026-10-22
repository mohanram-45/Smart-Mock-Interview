# Stage 10D + 10E + 10F: consolidated report

**Read this first.** Everything numeric below was produced in the Linux sandbox with a **scripted rule-based stand-in for the model** (no Ollama, no torch, no Sentence-BERT here; BM25/lexical retrieval). Nothing here is a measurement of llama3.2:3b or qwen2.5:7b. **No real-model numbers are reported** because no real model ran. No human has rated any question.

## 1. Diagnosis: why the Windows run accepted 0

| # | Cause (found by tracing prompt, parse, validate, memory, skip, fallback) | Effect | Fix |
|---|---|---|---|
| 1 | Benchmark answers were `canonical_answer + suffix`, so they covered every concept | Nothing left to probe, so skipping was the *correct* answer. Most of the 12 llama3.2 skips | Skip is still allowed and counted as legitimate; new fixed set has partial / wrong / alternate-valid answers and is scored per eligible opportunity. The Windows script now uses partial answers. |
| 2 | Memory citation required the earlier statement's words to appear in the question (`memory:reference_not_in_question`) | A valid reference to a real earlier statement was rejected | Citation by offered `memory_id`; traceable to a stored candidate statement; unknown ids rejected; unsupported citations dropped, not the whole question |
| 3 | Self-report booleans (`uses_given_facts_only`, `already_in_answer`) had to agree with the validators | `self_report` rejections on sound questions | Removed from the schema; the rules check facts themselves |
| 4 | `num_predict=160` with a 7-field schema | Qwen's JSON was cut (`done_reason=length`, `reply_truncated`, 3/3 of its fallbacks) and a skip cost a full schema | Compact schema, 224 tokens, skip is a few tokens |
| 5 | Memory selection and relevance were loose | Offered memories were often unrelated, so models rightly skipped | `specific_overlap`/theme relevance, role exclusions, displayed-position restraint |

Not done, on purpose: no validator was relaxed across the board. A faulty-model suite (9 behaviours: fabricated memory, unknown id, repeat, injection, accusation, invented terms, unrelated, invalid JSON, wrong shape) must stay at **0 accepted**, and does. Two real bugs found while doing this were fixed the strict way: an unrelated question being accepted (tie rule), and "Earlier you mentioned Kubernetes" being accepted (claimed-clause invented-word check).

Qwen's 19.7 s median is mostly a 4 GB GPU running a 7B model; the token fix cannot change that. **Untested on a real Qwen.** llama3.2:3b stays the preferred model; no other was selected.

## 2. What changed
`followup_llm.py` (prompt `10.fu4`, schema, skip reasons, citation and tie rules, `num_predict()`), `memory.py` (SBERT process cache + counters, relevance), `policy.py` (themes, continuity, relevance), `engine.py` (logging, displayed positions), `behavioural.py`, `mlops/metrics.py`; new `opportunity_eval.py`, eval set `stage10f_opportunities_v1.json`, `scripts/stage10f_eval.py`, per-opportunity mode in `scripts/stage10_verify_real_stack.py`; one step added to the existing CI job. Streaming, deadlines, cancellation, circuit breaker, injection protection and deterministic fallbacks are untouched. See `docs/STAGE10_MODEL_AND_POLICY.md` section 10.

**Sentence-BERT repeated loading:** confirmed real reloads (not duplicated progress text). Fixed with a process-local encoder cache; memory stays per session. Counters: `memory.MODEL_STATS`.

## 3. Results (SCRIPTED / MOCK)
Tests: **1229 passed, 8 skipped** (full regression); **29 passed** (browser journeys); `ruff` clean; integrity OK (no frozen drift); versions 11/11. Scripted gates 9/9.

| class | n | success | note |
|---|---|---|---|
| expected | 16 | 16 | stand-in follows exact-words hint |
| skip | 11 | 10 | S01 missed |
| memory_use | 7 | 5 | M02, M04 need semantic retrieval |
| memory_inappropriate | 6 | 6 | 0 citations |

Per eligible opportunity (expected + memory_use): **21 / 23 = 91%** vs the 80% target, with **0 fabricated memory references**, 0 repeats, 0 unrelated, 0 injected. Eligibility was fixed before running and not changed afterwards. **This 91% is a plumbing check, not a model result**: the stand-in cannot fail the way a language model does. Faulty models: 0 accepted of 9 behaviours. Engine turn time without a model: median about 9 ms. Largest follow-up prompt about 550 tokens (estimate).

Scenarios A-E all pass through the real engine/state machine/evidence store/policy (A project recall, B continuity, C behavioural memory, D contradiction clarification, E restraint with no invented reference). Interviews I01-I04 (technical x2, behavioural, mixed) pass. Transcripts: `reports/stage10_def_transcripts/`. Full tables: `reports/stage10_def_eval/results.{md,json}`.

## 4. Limitations and blockers
- Real inference, real Sentence-BERT retrieval, real latency and the Qwen truncation fix are **unmeasured here**. Run section 5.
- M02/M04 (semantic matches) will only pass with Sentence-BERT; S01 depends on how the real model treats paraphrase.
- Case expectations are the author's reading, not human-validated labels; topic-link floors are uncalibrated for SBERT.
- Exact-word coverage cannot tell a fluent wrong answer from an alternative valid one.
- Blind review pack: `docs/stage10_review_def/` (sheet, key, README), **unrated**.

## 5. Windows PowerShell verification
```powershell
cd D:\Projects\SMART-MOCK-INTERVIEW
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --models llama3.2:3b --mlflow --sbert
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --models llama3.2:3b qwen2.5:7b
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --models llama3.2:3b --runs 2     # interviews with partial answers
.bot\Scripts\python.exe scripts\stage10f_eval.py                                              # scripted gates, no Ollama
.bot\Scripts\python.exe -m pytest -q
```
Expected fields in `summary.md` / `results.json` (`--opportunities`): `model`, `ollama_version`, `num_predict`, `prompt_version`, `cold_load_ms`, `eligible_opportunities`, `useful_valid`, `useful_valid_rate` (target 0.8), `by_class` (expected/skip/memory_use/memory_inappropriate), `quality_gates.fabricated_memory_references` (must be 0), `skip_reasons`, `rejection_reason_codes`, `reply_truncated` (should be 0 at 224 tokens), `first_call_ms`, `warm_latency_ms.median/p95`, `memory_models` (loads should stay at about 1), `misses`, `circuit_breaker_state`. Also `review_sheet.csv` + `key.json` for blind rating. Report whatever comes out, including low rates; a real rate below 80% is a finding, not something to tune around.
