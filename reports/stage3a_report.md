# Stage 3A - LLM Evaluation Foundation: Report

**Status: foundation built and contract-tested offline. No real LLM has been called, no provider is configured, the live app is unchanged and still scores with the legacy scorers.**

## 1. What was implemented
New package `src/evaluation/` (≈1,100 lines), 95 offline tests, two docs, one inspection script, `requirements-llm.txt`. Nothing under `main/`, `src/components/`, `src/model/` or the datasets was modified.

| deliverable | where |
|---|---|
| 1 Evaluator architecture | `src/evaluation/README.md`, `evaluator.py` |
| 2 Pydantic schema | `schema.py` (`EvaluationRequest`, `LLMEvaluation` = model contract, `EvaluationResult`) |
| 3 Provider abstraction | `providers/base.py`, `providers/mock.py`, `providers/http.py` (Ollama, Anthropic, OpenAI-compatible), `config.py`, `errors.py` |
| 4 Grounded prompt | `prompt.py` (`PROMPT_VERSION 3a.1`), inspect with `scripts/stage3a_show_prompt.py` (calls nothing) |
| 5 Offline test suite | `tests/evaluation/` (5 files, 95 tests) |
| 6 Rubric | `src/evaluation/RUBRIC.md`, `rubric.py` |
| 7 Integration plan | section 6 below |
| 8 Report | this file |
| 9 Human decisions / credentials | section 8 below |

## 2. Phase 1 - existing architecture and integration points
| piece | fact found | consequence |
|---|---|---|
| `POST /api/submit-answer` (`main/app.py`) | takes `{session_id, answer}`, calls `session.submit_answer`, then adds `round_complete`, `round_action`, `next_round`, `round_average`. Response keys: `similarity_score` (0-100), `feedback`, `question_completed`, `next_action` | an LLM result must be **additive** (new `evaluation` object); `similarity_score` has to keep existing |
| `AdaptiveInterviewSession.submit_answer` | `neural_scorer.score(reference_answer, answer)` → float 0-1 → ×100; tiered template feedback; stores `similarity_score` in `round_answers` and `ReportGenerator.append_answer` | the only place a per-answer score is produced; the integration seam |
| adaptive logic | gating uses the **average of `similarity_score`** against `ADAPTIVE_EASY_THRESHOLD=70` and `ADAPTIVE_MEDIUM_THRESHOLD=50` | LLM scores have a different scale/distribution; thresholds must **not** consume them until calibrated |
| scorers (`model_registry.py`) | cached adapters `bilstm`, `bert`, `tfidf`, all `.score(ref, ans) -> [0,1]`; a similarity, not a correctness judgement | unchanged; stays the default |
| question dicts | legacy: `{id:int, question, reference_answer, domain, difficulty}` (no key concepts/verification); curated: string ids `smi-…` with the same keys | evaluator accepts both; legacy references are labelled unverified |
| retrieval interface | `RetrievalService.get(id)`, `.search(query,k,domain)`; HTTP layer redacts reference answers | reference comes from `get(id)`; `search` only feeds optional support |
| existing LLM use | `llm_report.py` (Ollama, `OLLAMA_HOST`, default model `qwen2.5:7b`, optional, post-interview narrative only) | the only LLM integration; I reuse the `OLLAMA_HOST` convention |
| tests | 137 retrieval + 77 app tests (+ the golden legacy baseline) | re-run after this stage, unchanged |

Regression guards added: the evaluation package imports no torch/flask/sentence-transformers/faiss/requests/LLM SDK (subprocess-tested); live app/session/scorer/report files are asserted not to reference it; default config is `legacy`; no module makes a network call at import.

## 3. Design (Phases 2-5)
* **Inputs:** exact question id/text, domain, topic, difficulty, candidate answer, canonical reference **looked up by id** (never accepted from the client, never replaced by a neighbour; a request containing the selected question as "support" is rejected), key concepts, alternatives, common mistakes, optional FAISS support (self excluded, truncated, labelled "other questions"), and reference verification: `verification`, `human_reviewed`, `source_opened`, `code_executed`, `time_sensitive`, `remaining_limitations`, provenance.
* **Facts about the data that the design is built around:** 666 curated records, **0 human-reviewed**, 17 time-sensitive, 123 with alternative answers, 306 with common mistakes, 36 with rubric points. The reference is AI-written and AI-reviewed only, so the prompt calls it fallible and results always say `human_validated: false`.
* **Output:** model returns rubric levels + findings; **code** computes the 0-100 score (see RUBRIC.md), applies caps, verifies quotes, sets status/confidence. Statuses: `graded`, `graded_low_confidence`, `insufficient_evidence`, `not_gradable`, `provider_error`, `invalid_response`, `provider_not_configured`. A number appears only with the first two.
* **Prompt (Phase 5 checklist):** (1) judges the answer to the actual question; (2) reference = supporting evidence, fallible; (3) demonstrated vs missing concepts; (4) factual errors separated from omissions; (5) constructive suggestions + follow-up; (6) alternative correct explanations must not be penalised; (7) instructions inside candidate/retrieved text are data - nonce-fenced, fence forgery neutralised, explicit security rule; (8) reference limitations (not human-reviewed, time-sensitive, legacy, missing) are injected into the prompt and echoed in `verification_limitations`.
* **Prompt-injection handling is layered, and only partly proven:** structural fencing; heuristic flag (never a grade by itself); injection-shaped quotes can't count as evidence; unquoted credit capped at 30; flagged answers are forced `graded_low_confidence` with a manual-review note. The tests cover scripted *compromised* output; they do not show a real model resists injection.
* **Providers:** one blocking `generate(system, user)`; error taxonomy with `retryable`; transient errors (timeout, 429, 5xx, connection) retried with capped exponential backoff, honouring `Retry-After` up to a cap; auth/4xx/bad envelope never retried; invalid JSON gets exactly one repair re-ask; on exhaustion a non-scored status is returned - **never fabricated text**. Hosted providers are refused unless `SMART_LLM_ALLOW_PAID=1`; no model name, key or endpoint is assumed; keys never appear in `repr`; no secrets in source (tested).

## 4. What passed
| suite | result |
|---|---|
| `tests/evaluation` (new) | **95 passed** (sandbox, Linux, Python 3.13, pydantic 2.14) |
| `tests/retrieval` | 137 passed, 1 skipped |
| `tests/app` | 77 passed, 5 skipped (live real-MiniLM tests; they passed on your Windows machine in Stage 2) |

What the 95 tests cover: correct / partially correct / incorrect / valid-alternative / short-sufficient / verbose-inaccurate / off-topic / hallucinated-claims / prompt-injection (compromised model output, injection inside a legitimate answer, fence forgery in candidate and support text) / missing reference / key-concepts-only / time-sensitive reference / model declines / empty and non-answers / reference copied into the improved example / candidate view hides reference and internals; provider timeouts (retry counts and sleeps), rate limits, auth errors not retried, invalid JSON (repair then success, repair then failure), schema violations, extra keys ignored and a self-declared "100" ignored; score monotonicity and caps over all 625 level combinations; adapter request shapes, headers, error mapping, timeout and connection refusal against a **local fake server**; config gating.

**What these tests are:** manually specified expectations for a **scripted mock model**. They verify the pipeline's handling of each case type. They are **not** an accuracy measurement and nothing here may be quoted as real LLM performance. Note one deliberate behaviour the tests pin down: a wrong answer with nothing verifiable scores ≤30 even if the model's levels would give 36.

## 5. What remains unverified
* **Any real LLM's grading quality** - agreement with humans, calibration, bias, variance across runs. Not measured; no model was called.
* Real-model **prompt-injection robustness** and whether real models follow the JSON contract (the repair path is only tested with a mock).
* The Ollama / Anthropic / OpenAI-compatible adapters against **real** services (tested only against a fake local server).
* Whether Ollama or any model is installed on your machine (not checked; the sandbox cannot see it).
* Quote verification proves a quote exists, not that the claim is true; it can drop a legitimate paraphrase-quote mismatch (normalisation is whitespace/case/punctuation only).
* The rubric weights, caps (10 / 60 / 30) and bands are design choices, never compared with human graders; the 30-point cap may under-score a correct answer the model forgot to quote.
* Cost, latency and token usage; cross-run determinism (temperature 0 does not guarantee identical outputs).
* Privacy: enabling a hosted provider sends candidate answers and reference text to a third party.
* The new tests have not yet been run on your Windows machine (pydantic must be installed: `pip install -r requirements-llm.txt`).
* Lexical key-concept hits are a diagnostic only.

## 6. Integration plan (design only; nothing implemented)
1. **Flag:** `SMART_EVALUATION_BACKEND=legacy|llm` (parsed by `config.py`, default legacy, invalid → startup error). `legacy` = exactly today's behaviour, byte-for-byte API.
2. **Stage 3B - shadow mode (recommended first):** with `llm`, `submit_answer` still returns the legacy `similarity_score`/`feedback`; the LLM evaluation runs **after** the legacy result is computed, never blocks it, and is stored beside it (report JSON + log) for offline comparison. A provider failure only records an error status.
3. **Contract:** add an optional `evaluation` object to the `submit-answer` response and report entries (`to_candidate_view()` already strips reference/internal fields). Existing keys, types and meanings stay. Clients ignoring `evaluation` keep working.
4. **Latency:** an LLM call is seconds, the current route is synchronous. Use the existing background-job pattern (as `report_jobs`) with a pollable result, or return legacy immediately and fill `evaluation` later.
5. **Adaptive difficulty:** keep gating on legacy `similarity_score` until LLM scores are calibrated against a human-labelled set (the 70/50 thresholds are tuned for similarity percentages). Only then consider a mapped score, behind a second flag.
6. **Failure policy:** any non-scored status → fall back to the legacy score and tell the client the evaluation status; never invent a score.
7. **Reports:** add provisional LLM scores/rationales as clearly labelled "AI-generated, not human-validated"; do not mix into `average_score` until step 5.
8. **Before any real run:** a human-graded gold set (≥ a few hundred answers across domains, including injection and alternative-explanation cases) to measure agreement; budget cap and logging of token usage.

## 7. Risks to keep in view
Same-family bias if the same model both writes references and grades; verbosity/position bias in graders; stale answers for the 17 time-sensitive records; the reference corpus is unreviewed by humans; LLM scores will not be comparable with similarity scores.

## 8. Human decisions and credentials needed to test a real LLM
1. **Choose the provider path:** local Ollama (no cost; which model? the project's report writer defaults to `qwen2.5:7b`, unverified here) or a hosted API.
2. **Hosted API only:** an API key (set `SMART_LLM_API_KEY`, never commit it), an explicit `SMART_LLM_ALLOW_PAID=1`, a model name (`SMART_LLM_MODEL`), a spending cap, and an OK to send candidate answers + reference text to that vendor.
3. **Local only:** confirm Ollama is running (`ollama list`), which model to pull, and your machine's tolerance for latency.
4. **A human-graded gold set** (or approval to have a few hundred answers hand-scored) - without it only "does it run and follow the contract" can be tested, not accuracy.
5. **Decisions on rubric:** accept or change the weights (40/30/15/15), caps (10 / 60 / 30) and what a non-answer should map to (`not_gradable` now; the legacy app would score it).
6. **Approval of the integration plan** in section 6 (shadow mode first), and whether LLM output should ever influence adaptive difficulty.
7. Confirm whether a first real run should be a small **dry run on ≤20 answers** with the prompt printed beforehand (`scripts/stage3a_show_prompt.py`).

## 9. Run it yourself
```
pip install -r requirements-llm.txt
python -m pytest tests/evaluation tests/retrieval tests/app -q
python scripts/stage3a_show_prompt.py --qid smi-0453 --answer "Bubble sort swaps neighbours until sorted, O(n^2)."
```

**Stopped after Stage 3A. Awaiting approval for Stage 3B.**
