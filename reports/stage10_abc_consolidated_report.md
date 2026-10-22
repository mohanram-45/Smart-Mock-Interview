# Stage 10 (A + B + C) — consolidated report

**Evidence status, up front:** everything measured below is **scripted / mock** (synthetic candidates, deterministic generators, word-overlap scorer, BM25 retrieval). No real Ollama, Sentence-BERT or Docker run was possible in the build environment, and **no human has rated anything**. Nothing here is a model benchmark or an accuracy claim.

## 1. What was built
| Part | Result | Where |
|---|---|---|
| 10A Interview memory | Rule-based extraction with exact turn, span, quote and confidence; every item a *candidate claim* (never verified fact); dedupe, contradictions (years of experience, tool negation) with a non-accusatory clarification; TF-IDF retrieval (Sentence-BERT optional); restraint rules; persisted with the session, expires at 14 days, deleted with it | `src/demo/memory.py` |
| 10B Behavioural / mixed | Setup choice of technical / behavioural / mixed; 9 versioned competencies, 36 original questions; STAR-inspired evidence with exact quotes; probe policy; memory-driven project prompts; mixed with spoken transition; JD-aware selection; qualitative-only feedback | `src/demo/behavioural.py`, `behavioural_data/` |
| 10C Adaptive policy | Deterministic decisions (deeper, clarify, explore_related, revisit, new_competency, practical, wrapup); vetted-bank next question; verification layer for any model-proposed wording; deterministic fallback; `adaptive:false` keeps the old ladder | `src/demo/policy.py`, `engine.py`, `followup_llm.py` |
| Integration | Minimal UI (three-option radio, behavioural chip, separate feedback block); code-only metrics; export; existing CI extended with one scripted step (no Ollama on hosted runners) | templates, `metrics.py`, `ci.yml` |
| Evidence tooling | Scripted suite (15 gates), transcripts, blind review sheet + separate key, Windows real-stack runner | `scripts/stage10_*.py` |

Design and limits: `docs/STAGE10_MODEL_AND_POLICY.md`.

## 2. Results
| Measure | Result | Type |
|---|---|---|
| Scripted gates | 15 / 15 passed | MOCK (mechanics) |
| Long-range recall | 4 / 4 scenarios | MOCK |
| Unsupported "earlier you…" claims | 0 / 5 references | MOCK |
| Memory spans reproduce their quote | 40 / 40 | MOCK |
| Near-duplicate question pairs | 0 / 168 | MOCK |
| Restraint violations | 0 in 5 interviews | MOCK |
| Prompt-injection text in output or memory | none | MOCK |
| Ollama unavailable / timeout | finished via deterministic fallback; 0.26 s wall at 0.2 s deadline | MOCK (fake provider) |
| Restart persistence, deletion, cross-session isolation | pass | MOCK |
| Engine turn time (no model) | median 6.4 ms, p95 22 ms | container CPU |
| Real-model acceptance, latency, relevance; SBERT retrieval quality | **NOT MEASURED** | needs Windows |
| Human ratings (naturalness, relevance, fairness) | **NONE** | needs two raters |

Test status (sandbox, Python 3.12): full regression 1165 passed / 8 skipped; browser journeys 29 passed (incl. 3 new Stage 10 journeys); `ruff check .` clean; `check_integrity.py` OK (no frozen file drifted); `check_versions.py` 11/11. Not run here: Python 3.13, Windows, Docker.

## 3. Failures and limitations (honest list)
- Exact-word coverage cannot tell a fluent wrong answer from an alternative valid one; the policy therefore only eases or deepens the next question and never says "wrong".
- Topic-link score floors (`BM25_MIN=6.0`, `SEMANTIC_MIN=0.45`) are heuristics, uncalibrated for Sentence-BERT.
- No LLM memory extractor (rules only). Metric contradictions are intentionally not flagged.
- Coherence is a word-overlap proxy only.
- Scripted candidates only exercise mechanics; real candidates will differ.
- The frozen modular evaluator still cannot be promoted; it was not touched.
- Model choice: llama3.2:3b stays the latency baseline (Stage 9D: ~2.4 s warm median). qwen2.5:7b (~11.4 s) is unmeasured for Stage 10 prompts. No superiority claim.
- Not touched: 3D/avatar/webcam, frozen MLflow runs, repository visibility. Nothing committed, staged or pushed.

## 4. Transcripts (all labelled SCRIPTED / MOCK)
`reports/stage10_transcripts/`: `memory_long_range.md`, `behavioural.md`, `mixed.md`, `technical_data_scientist.md`, `technical_python_developer.md`, `candidate_contradicts_earlier_answer.md`. Raw results: `reports/stage10_eval/results.{md,json}`. Human-review pack (unrated, with separate key): `docs/stage10_review/`.

## 5. Blockers and next actions (Windows)
1. `python scripts\stage10_verify_real_stack.py --models llama3.2:3b qwen2.5:7b --runs 3 --mlflow --sbert` — real acceptance, fallback rate, latency, memory citations (MLflow gets counts/timings only, no text).
2. Calibrate the topic-link floors on Sentence-BERT with real transcripts.
3. Two raters fill `docs/stage10_review/review_sheet.csv` blind; report agreement.
4. Only then decide whether a bigger model is worth its latency.

Privacy: candidate text is absent from logs, metrics and reports (covered by `tests/app/test_stage10_eval_and_privacy.py`).
