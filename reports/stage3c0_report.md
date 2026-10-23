# Stage 3C-0 — Concept scope and evaluation groundwork: report

**Everything below was authored by Claude (AI). No human has reviewed a tier, an answer or a score range. No Qwen/Llama call, paid API call, Flask change, dataset change, FastAPI/Docker/MLflow work or shadow mode was done.**

## 1. Deliverables

| # | Deliverable | Location |
|---|---|---|
| 1 | 666-record concept-scope sidecar + manifest | `data/evaluation/scope/scope_v1.jsonl`, `scope_v1_manifest.json`, `README.md` |
| 2 | Scope pilot review report | `reports/stage3c0_scope_pilot_report.md` |
| 3 | Fresh 120-answer benchmark | `data/evaluation/bench_v2/` |
| 4 | Human-review pilot sheet (26 answers) + process | `data/evaluation/stage3c_review/` |
| 5 | Validation results | section 3 below; `audit/evaluation/stage3c_validate.py`; `tests/evaluation/test_stage3c0_assets.py` |
| 6 | Remaining ambiguous requirements | `reports/stage3c0_remaining_ambiguities.md` |
| 7 | Stage 3C-1 implementation plan and evaluator handoff | `reports/stage3c1_evaluator_plan.md` |

Builders: `audit/evaluation/build_scope_v1.py`, `build_bench_v2.py` (deterministic). Authoring sources: `scope_heuristic.py`, `scope_manual_zero.py`, `scope_manual_pilot.py`, `bench_v2_source.py`.

## 2. What was built

**Sidecar.** 666 rows, 77 AI-reviewed (`ai_reviewed_pilot`) and 589 rule-based drafts (`ai_heuristic_draft`). Tiers: essential concepts 2,027, essential groups 46, supporting 1,310, background 510. Policy: only essential concepts can lower completeness; supporting is credit/feedback only; background is feedback only; groups need `min_required` members. 400 rows are flagged `human_review_required`; **16 rows are `completeness_penalty_eligible`** (reviewed, no open ambiguity).

**Pilot finding (AI vs AI, not human):** the heuristic agrees with the AI manual review on essential-vs-not for only 63.6% of 247 concepts and fully on 4/40 questions. The heuristic therefore cannot drive grading. All 37 records that had no essential concept got explicit handling (essential groups, definition-level essentials, or flagged ambiguity); none was force-fitted. Details are in the pilot report.

**Benchmark.** 120 answers / 24 questions, all 8 domains (3 each), Easy 8 / Medium 8 / Hard 8, types coding, debugging, sql_exercise (3), scenario, design, evaluation, concept. Kinds: correct 19, concise-sufficient 13, valid-alternative 18, partial 23, incorrect 22, hallucinated 13, off-topic 3, prompt-injection 6, keyword-list 1, non-answer 1, ambiguous-reference 1. 17 earlier tuning/bench IDs excluded. Evaluator inputs (`questions.jsonl`, `answers.jsonl`) hold no labels; labels and rubric are separate files. All 26 answers containing code or SQL were executed in the sandbox against the questions' sample data (the two scikit-learn snippets were only loaded, not fitted) and behave as labelled (e.g. the no-DISTINCT streak query returns 4 instead of 3 for user 1; the INNER JOIN retention query reports 100%).

**Human-review pilot.** 26 rows with the requested columns; reviewer fields blank; AI factual-correctness and ranges are headed `..._AI_PROVISIONAL`; a blind variant without AI columns is included. `REVIEW_PROCESS.md` defines the later two-reviewer process and how disagreements are resolved (>20 points or differing verdict → discussion, third reviewer, otherwise `contested`).

## 3. Validation results

| Check | Result | Detail |
|---|---|---|
| `ids_map_666` | PASS | rows=666 unique=666 missing=0 extra=0 order_matches_corpus=True |
| `question_type_matches` | PASS | question_type copied from corpus |
| `corpus_unchanged` | PASS | problems=0 content_sha_matches_pin=True |
| `frozen_csv_sha` | PASS | csv present=5/5 sha ok=True |
| `tiers_consistent` | PASS | violations=0 [] |
| `optional_never_penalised` | PASS | penalty_eligible_rows=16; supporting/background/label excluded by construction |
| `essential_vs_question_proxy` | PASS | heuristic essentials without question/headline overlap=0; contradiction beyond this proxy needs human review |
| `alternatives_have_basis` | PASS | ai_proposed=21; technical justification by AI only, not human-verified; problems=0 |
| `human_review_identifiable` | PASS | human_review_required=400 human_verified=0 |
| `scope_reproducible` | PASS | sidecar_sha256=7332f65c74a0dd45.. |
| `bench_size_and_ids` | PASS | answers=120 questions=24 |
| `bench_fresh` | PASS | overlap_with_tuning_questions=[] |
| `bench_inputs_label_free` | PASS | evaluator input files carry no kind/score/label fields |
| `bench_coverage` | PASS | domains=8 types=['coding', 'concept', 'debugging', 'design', 'evaluation', 'scenario', 'sql_exercise', 'unspecified'] kinds_missing=[] |
| `bench_labels_provisional` | PASS | all labels AI-provisional, ranges valid |
| `bench_manifest_matches` | PASS | file sha256 equals manifest |
| `bench_reproducible` | PASS | rebuild is byte-identical |
| `review_sheet` | PASS | rows=26 reviewer fields blank=True |

Regression suites after the changes: evaluation 177 passed (153 before plus 24 new); retrieval+evaluation 313 passed, 2 skipped; app 77 passed, 5 skipped. No test was changed except new ones added.

Honest limits of the checks: "essential requirements do not contradict the question" is only checked by a word-overlap proxy for heuristic rows; the 77 reviewed rows were read by AI. "Alternatives technically justified" means AI-justified with a recorded basis, not verified by a human.

## 4. Remaining ambiguous requirements
See `reports/stage3c0_remaining_ambiguities.md` (flag counts, the 77 reviewed rows that still need a decision, cross-cutting questions).

## 5. Is the sidecar reliable enough for a limited modular-evaluator prototype?

**Yes for a deliberately limited prototype; no for general use.**

- **Usable now:** the 77 AI-reviewed rows, with only the 16 penalty-eligible rows (8 of the 24 bench questions) allowed to reduce completeness automatically. That is enough to prototype and test S2–S7 mechanics (group semantics, the four-state table, unverified ≠ incorrect) and to run a baseline on bench_v2.
- **Not reliable:** the 589 heuristic drafts (≈64% essential agreement with the AI review). Use them for feedback and for building a review queue, never for score penalties.
- **No human agreement exists yet.** The architecture gate of ≥ 90% human agreement on essential tiers has not been tested; until it is, every reliability statement here is about internal consistency and AI review, not correctness.
- **Benchmark caveat:** answers and labels came from the same Claude session as the sidecar, so they are not independent of it; ranges are provisional.

## 6. What still requires human review (in priority order)
1. The 26-answer pilot sheet (≈ 1 hour, single reviewer; use the blind CSV first).
2. Essential tiers for the 24 bench questions, then the other 53 reviewed rows (21 were read from truncated references).
3. The 31 zero-essential records whose ambiguity is still open, and the decision on minimum depth for list/open questions.
4. A random sample of the flagged heuristic rows to measure human agreement.
5. The full benchmark by two blind reviewers with the dispute rule in `REVIEW_PROCESS.md`.

Stopped after Stage 3C-0 as instructed.
