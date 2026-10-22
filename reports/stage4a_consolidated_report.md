# Stage 3C-4 + Stage 4A: consolidated report

Status of the frozen experiment is unchanged: **the 3C-2 run failed its acceptance gate (abstain rate 0.45 > 0.40, DO NOT ADVANCE).** Nothing below re-scores, re-labels or re-classifies it. No human has reviewed any answer, so every accuracy-type criterion is still PENDING_HUMAN. No model was called, downloaded or paid for in this stage.

## 1. Evaluator fixes (variant 3c4.0, opt-in; frozen 3c1.0 untouched)

`src/evaluation/modular/variant_3c4.py`. Frozen modules are patched only inside `use_3c4()` (lock-serialised, restored on exit, stamped `engine_variant=3c4.0` + gates fired in provenance). The freeze manifest still verifies "no drift"; `results.json` is byte-identical.

| # | Fix | What it does | Cannot do |
|---|---|---|---|
| 1 | Type I / Type II veto (from 3c1.1) | the contradiction rule no longer treats siblings that differ in a numeral/symbol token as one concept | n/a |
| 2 | Normalisation | -ise/-ize, British forms, technical plurals (matrices/matrix), possessive stripping (the stray `s` of "Dijkstra's" was becoming a discriminator), compound joins (tf-idf/tfidf) for the omission guard | word match is only used to REFUSE "never mentioned"; it never grants credit |
| 3 | G1/G2 support gate | a credit (or a penalty) whose cited claims contain **none** of the concept's words becomes UNVERIFIED (`credit_without_concept_in_cited_claim`, `credit_cites_wrong_claim`, `error_without_concept_in_cited_claim`); code claims exempt | never re-points evidence, never creates credit |
| 4 | G3 omission gate | an "incorrect" finding whose own explanation describes an omission ("does not specify X") or negates the concept ("not a heap") becomes UNVERIFIED (`error_alleges_omission`), never "missing" | no new penalty |
| 5 | Finding classes | `review/findings.py`: correct_supported / weakly_supported / unsupported / unchecked, incorrect, omitted, unsupported_credit, unsupported_penalty, omission_labelled_as_error, unverified_by_model, unverified_by_gate | reporting only |
| 6 | Visibility | `reliability_summary`: model-uncertain, gate rejections and legitimate abstentions (off-topic, not-scored-by-design) are separate numbers, shown in the app and review views | |

Considered and **rejected**: a "blamed claim matches a sanctioned alternative" gate. Word overlap cannot tell an equivalent formulation from a contradictory one; it would have hidden the genuine Type I/II and O(n)/O(log n) errors.

Invariant (property test, 400 random verdict sets): every gate output is either unchanged or UNVERIFIED with a reason and no evidence. Injection safeguards (instruction claims withheld, echo downgrade, `injection_detected`) are tested in the variant.

### Diagnostic replay of the recorded REAL Qwen text (no model call; NOT a result)

| configuration | scored | abstained | rate |
|---|---|---|---|
| recorded 3c1.0 | 22 | 18 | 0.450 |
| 3c4.0, normalisation + Type I/II only | 25 | 15 | 0.375 |
| + omission gate | 25 | 15 | 0.375 (b2-109 min-heap false error removed: 80 to 100; b2-043 80 to 90) |
| + support gate only | 21 | 19 | 0.475 |
| 3c4.0 all gates | 21 | 19 | **0.475** |

**The variant does not fix the abstain criterion and must not be presented as improvement.** The support gate removes the clear false credit (b2-028 "feedforward neural network": score 50 to 36), the mis-cited b2-026 credit and two supporting credits in b2-048, but it also turns two plausibly correct answers into abstentions (b2-072 "68-95-99.7 rule" credited from a sentence about |z|>1 tails; b2-109 "Dijkstra's algorithm" credited from a prose sentence that does not name it): paraphrase with no shared word is now uncertainty. Whether that trade is right depends on human labels. Each gate can be switched off (`use_3c4(gates=...)`) so its effect is measurable. A test pins this honesty (`replayed abstain rate > 0.40`).

Fixtures b2-028 (false credit) and b2-109 (false error) are asserted by WHICH verdict is refused and why, never by a target score. b2-109's remaining dependence: the min-heap false error is only caught because the model's explanation said "not a heap"; had it phrased it differently the gate would not fire. That is a model reasoning failure the code only partly contains.

## 2. Working interview demonstration (`/demo`, Flask blueprint, no new infrastructure)

Setup (role or own topics, Easy/Medium/Hard/Mixed, 3/5/8 questions, legacy scorer, experimental mode) -> question per page with progress bar -> answer (Ctrl+Enter, skip, finish) -> immediate feedback card -> summary with per-question review. Server-rendered Jinja + a little vanilla JS; responsive and dark-mode aware; no external requests; CSP header.

- Questions: the existing curated corpus (666 records) via the retrieval service; roles map through the curated-source aliases. Shortages are reported, never padded. "Mixed" is a fixed Easy-Medium-Hard pattern: **no adaptivity** (selection takes no score; tested by signature).
- Five situations kept visibly apart: operational flow; **LEGACY** score (default; existing scorer + feedback); **experimental modular** (opt-in; chips `REAL MODEL` / `MOCK VERIFIER`, engine+variant, `NOT human-validated`); **ADVISORY ONLY** (650 of 666 questions: findings, no number); **abstained / unavailable** (a reason, optional informational range, never a number).
- Experimental detail on every evaluated answer: your answer with evidence highlighted, concept decisions (model said vs evidence-check outcome, finding class, your words), rubric breakdown with the rule behind each level, feedback from verified findings.
- Modes: off (default) / mock (always available) / live (`SMART_DEMO_LIVE_MODULAR=1`, local Ollama qwen2.5:7b, same adapter and frozen settings as the recorded run; single background worker, result polled into the page).
- `/demo/recorded`: the 20 recorded real-Qwen answers read-only, with the failed-gate banner; AI-drafted expectations are not loaded.
- Reference answers hidden unless `SMART_RETRIEVAL_EXPOSE_REFERENCE=1` (existing redaction policy).
- Reliability: scorer failure, evaluator crash, provider failure and unwritable disk never stop the interview; duplicate/out-of-order submissions rejected without state change; finished sessions persist to `results/demo_sessions/` and survive restarts; unfinished sessions are memory-only like the existing `/api` sessions.
- `main/app.py` gained two lines (import + `init_demo(app)`). All `/api/*` routes, `AdaptiveInterviewSession`, scorers and feedback are untouched; the existing "app code must not import modular" guard now exempts exactly one file (`src/demo/experimental.py`) and the default flow is proven not to import the package (subprocess test).

## 3. Launch (Windows)

```
cd D:\Projects\SMART-MOCK-INTERVIEW
python main\app.py
```
Open **http://127.0.0.1:5000/demo/**

Optional, in the same console before launching: `set SMART_DEMO_LIVE_MODULAR=1` (adds the real local model option; needs Ollama running with qwen2.5:7b; about 30 to 90 s per answer), `set SMART_RETRIEVAL_EXPOSE_REFERENCE=1` (show reference answers in the review), `set SMART_DEMO_LEGACY_MODEL=bert` (default legacy scorer in the dropdown).

First session note: the legacy scorer loads at session start. The default (Siamese Bi-LSTM) trains itself on first use if no checkpoint exists (existing behaviour, can take minutes); Sentence-BERT needs the cached MiniLM model. If a scorer cannot load, the interview runs without a legacy score and says why.

Without torch/Ollama (reproducible anywhere): `python scripts\stage4a_demo_server.py --port 5055 [--live-fake ok|fail] [--fail-legacy]` uses a word-overlap stand-in scorer and a slow/failing fake live model. It is a test harness, not the app.

## 4. Tests

| suite | result |
|---|---|
| tests/evaluation | 426 passed, 2 skipped (40 new in `test_stage3c4_variant.py`, incl. 29 from 3C-3) |
| tests/retrieval | 137 passed, 1 skipped |
| tests/app (Flask) | 129 passed, 5 skipped (52 new in `test_stage4a_demo.py`; 77 legacy unchanged) |
| freeze v2 verify | no drift |

New coverage: setup, retrieval, answer/skip/finish, ordering, validation, persistence, scorer/provider/evaluator failure, missing corpus and recorded data, advisory/abstention/scored displays, MOCK labelling, async live jobs, flag isolation (subprocess), prompt-injection text (escaped everywhere, cannot buy a score), CSP headers, legacy route regression, no adaptivity.

## 5. UI verification

Real Chromium (Playwright) drove the whole flow against the real Flask app and real corpus (stand-in legacy scorer): setup, 3 questions with answer + injection text + skip, summary, mobile (390 px, no horizontal overflow after one fix), recorded run, live-pending to done, live-provider-failure. No console or page errors; an injected `<script>` did not execute. Screenshots: `data/evaluation/stage4a/screenshots/` (13 files; 01 setup, 03 feedback, 04 summary, 09 recorded b2-028, 10/11 live states).
**Not verified here:** the real Bi-LSTM/BERT/TF-IDF scorers and a real Ollama call (the sandbox cannot reach them). First launch on your machine is the real test.

## 6. Legacy vs experimental evaluation

| | Legacy (default) | Experimental modular |
|---|---|---|
| Measures | similarity to a reference answer | which required concepts the answer states, with its own words as evidence; fixed 40/30/15/15 rubric |
| Coverage | all 666 questions | 16 scorable; 650 advisory-only |
| Output | number + tiered wording | number only if eligible and evidence is sufficient; else findings and a stated reason |
| Drives adaptive rounds | yes (main app) | never |
| Validated | not against humans either | no; recorded run failed its gate |

## 7. Remaining grading risks (ranked)

1. No human labels exist: nothing is validated. 2. Abstain rate 0.45 (frozen), and 3c4.0 measures 0.475 on the same text; the gate trade-off needs human labels to judge. 3. Model reasoning failures persist (false credits/errors, off-topic flag on wrong answers, omissions as errors); gates only turn some into uncertainty. 4. 650 of 666 questions can never get an experimental number. 5. The 16 eligible scopes are AI-drafted, not human-verified. 6. Legacy similarity rewards resemblance, not correctness, and the Bi-LSTM under-scores rewording. 7. Pending policy decisions (not changed): off-topic numeric policy, free reasoning marks, supporting-tier penalty weight, requiring claim ids in the schema.

## 8. Human-validation hand-off (unchanged, not blocking)

```
python scripts\stage3c3_review.py blind --set sample20
```
fill `data\evaluation\stage3c3\review_sample20\blind_review.html`, press Download CSV, then
```
python scripts\stage3c3_review.py compare --results data\evaluation\stage3c2_results\20261015T120208Z\results.json --human completed.csv
```
Reviewer fields were not filled by any AI. To see what a 3c4.0 replay would change: `python scripts\stage3c3_review.py replay --results ...\results.json --variant 3c4.0` (diagnostic only).

## 9. Next steps toward a portfolio-ready application

1. Run the demo on your machine and fix whatever the real scorers expose. 2. Complete the 20-answer human review, then decide the 3c4.0 gate trade-off and the pending policies from data. 3. Add a README with the launch steps and the label legend, a screenshot gallery, and a sample session export. 4. Persist unfinished sessions and add a "download my session" JSON/PDF. 5. Only after human validation passes: consider showing modular results by default, still never in adaptive difficulty without a separate decision. 6. Optional polish: charts per level, accessibility audit, deploy notes.
