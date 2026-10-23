# Stage 3C-2 preparation report — controlled modular LLM validation

**State: prepared, tested offline, frozen. The real model has NOT been run. Waiting for your approval to run the Windows experiment.**
Nothing in this stage touched Flask scoring, shadow mode, the corpus, or the scope sidecar. No model was downloaded, no paid API was used, no Ollama call was made from the sandbox.

## What was built
| Deliverable | Where |
|---|---|
| Qwen/Ollama verifier adapter (one structured call per answer, per-request schema with closed enums, claim-id enums, all fields required, truncation = invalid, full call trace) | `src/evaluation/modular/qwen_verifier.py` (prompt `3c2.v1`) |
| Frozen sample: 20 answers, 8 eligible questions | `data/evaluation/stage3c2/sample.jsonl` |
| Blind human-review sheet (CSV + Markdown, review fields blank, no AI expectations, shuffled ids; key kept separately) | `data/evaluation/stage3c2/review/` |
| Provisional AI expectations (separate file, never shown to evaluator or reviewer) | `provisional_ai_expectations.jsonl` |
| Fingerprints / freeze | `freeze_manifest.json`, `scripts/stage3c2_freeze.py` |
| Protocol and acceptance criteria (written before any result) | `reports/stage3c2_protocol.md`, `acceptance_criteria.json` |
| Windows runner (one command) + analyzer | `scripts/stage3c2_run.ps1`, `scripts/stage3c2_run.py`, `audit/evaluation/stage3c2_analyze.py` |

## The sample (frozen)
20 answers: correct 2, concise-sufficient 3, valid-alternative 3, partial 3, incorrect 2, hallucinated/contradicting 2, prompt-injection 3, off-topic 1, non-substantive 1. Eighteen come from the fresh Stage 3C benchmark (bench_v2); two were written for this stage because bench_v2 has no off-topic answer on an eligible question. The old B01–B43 cases are not used. Questions: smi-0064, 0118, 0198, 0314, 0449, 0451, h0016, l0002 — the only eligible questions bench_v2 covers, so the other 8 eligible questions are untested here.

Fingerprints recorded for: sample, 8 corpus records, scope sidecar (sha 7332f65c…) and manifest, verifier prompt text, modular code (rubric/gates/pipeline/adapter), legacy code, model configuration, protocol/criteria/runner/analyzer. The runner recomputes them and refuses to run on any drift.

## Model configuration (frozen)
qwen2.5:7b via local Ollama; temperature 0; seed 7 + repeat (modular runs twice: seeds 7, 8); num_ctx 8192; 1800 output tokens; 300 s timeout; modular max 1 retry for retryable provider errors only; legacy single-call evaluator once, schema-constrained, same reference material, no retrieved snippets (so only the architecture differs). Offline dry run: the largest prompt is about 2,200 tokens, comfortably inside the context window.

## How the model is kept from deciding scores
It only labels each listed requirement member (`states_correctly / states_incorrectly / not_stated / unverified`) citing claim ids. The schema has no score field. Existing gates then apply: cited claim ids must exist (the schema also forbids unknown ids); an error accusation needs a real reference quote; `not_stated` is downgraded if the candidate's words are visibly there; instruction-bearing claims never reach the model and are never evidence; unverified stays "no credit, no penalty". The 40/30/15/15 engine computes the score and records its derivation; if a dimension cannot be determined the result abstains. Failures (timeout, down, malformed, truncated) become `provider_error` / `invalid_response` with no score.

## Tests (all offline)
| Suite | Result | Before this stage |
|---|---|---|
| `tests/evaluation` (sandbox) | **344 passed** | 289 |
| retrieval + evaluation (`rag_venv`) | **479 passed, 3 skipped** | 425 / 2 |
| app (`app_venv`) | **77 passed, 5 skipped** | 77 / 5 |

55 new tests: adapter contract (34: schema/prompt, unsupported credit, fabricated ids, contradictions with/without reference quote, uncertainty not penalised, non-eligible stays advisory, alternatives, injection, instruction-only, off-topic, code flagged, malformed/truncated/timeouts/retry, determinism, real HTTP path against a fake local server), freeze + sample + blind sheet (10), runner and analyzer end-to-end against a fake local Ollama (11, including refusals: missing model, unreachable, wrong model, freeze drift, no overwrite, never calls pull). The one new skip is the JSON-schema validity test in `rag_venv`, which lacks the optional `jsonschema` package (same convention as the Stage 3B schema test). No failures.

## Run it (after you approve), from the project root in PowerShell
```
powershell -ExecutionPolicy Bypass -File scripts\stage3c2_run.ps1
```
It verifies the freeze, builds all prompts offline, unloads other models, samples RAM/GPU every 10 s, runs 40 modular + 20 legacy evaluations (about 60 model calls; duration not yet measured on your machine), then runs the analyzer. Output: `data\evaluation\stage3c2_results\<timestamp>\` (`results.json`, `analysis.md`, `analysis.json`) plus a `_monitor_*` folder. Optional first look at two answers (marked partial, no decision): add `-Ids s2-f01,b2-006`.

## Acceptance criteria and decision rule (fixed now)
Mechanical (evaluated automatically): valid-output rate ≥ 90%; 0 provider errors; gate-downgrade rate ≤ 25%; 0 unsupported completeness penalties; every scored dimension has a derivation; 0 evidence ids outside the answer; 0 injection claims used as evidence; every abstention has a reason; abstain rate ≤ 40%; median latency ≤ 60 s and max ≤ 180 s per answer; repeat member-state agreement ≥ 85% and repeat score delta ≤ 10 points.
Human-label criteria (`PENDING_HUMAN` until you or a reviewer fill the sheet): false-credit ≤ 10%, false-error ≤ 5%, credit on human-correct concise/alternative answers ≥ 70%, no missing-concept penalty contradicted by the human, modular unsupported penalties ≤ legacy.
Decision: any failed criterion = do not advance (and no tuning on these 20); all mechanical pass without human labels = "exploratory behavioural readiness" only; advancing needs human labels as well.

## Honest caveats before you approve
1. **No human labels exist.** The blind sheet is ready (20 rows). Without it, the run can show behaviour (valid output, evidence handling, abstention, speed) but not whether credits or errors are right.
2. **Coarse scope labels.** Several essential requirements are single terms ("Dijkstra's algorithm", "shortest path", "O(log n)", "68-95-99.7 rule"). A model may credit an answer that merely names the term; I cannot detect that offline. The reviewer is asked to flag it.
3. **Not fully unseen.** The injection patterns were extended in 3C-1 after the contract test showed bench_v2 answer b2-032 slipped through. That answer is not on an eligible question and is not in this sample, but the code has seen the benchmark's style.
4. **Small and single-model.** 20 answers, 8 questions, one 7B model, two seeds: no statistical claims.
5. **Unmeasured behaviour of constrained decoding.** Ollama's grammar handling of `minItems` and enums has not been exercised here (the fake server cannot tell). If the first call is rejected the runner reports the error rather than silently loosening the schema; I would then stop and report, not retune.
6. **Legacy comparison is like-for-like only on model, answers and reference.** It runs without retrieved snippets, which production legacy would normally include.
7. **Code/SQL is not executed** by either evaluator.
8. Latency/RAM/VRAM on your hardware are unknown until the run; the criteria use generous ceilings.

## Remaining quality risks (unchanged from 3C-1, plus)
Verifier quality is unproven; abstention may be too conservative; only 16/666 records are scorable; tiers are AI-reviewed, not human-verified; new: a 7B model may give many `unverified` verdicts, which would show up as a high abstain rate rather than as wrong scores.

## Approval needed
Please say "run it" (and, ideally, have the sheet filled in first or in parallel). I will not execute anything against Ollama until you do.
