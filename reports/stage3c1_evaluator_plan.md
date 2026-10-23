# Stage 3C-1 — Modular evaluator: sidecar handoff and implementation plan

Design only. **Nothing in this document is implemented**, and no Qwen/Llama call was made in Stage 3C-0. It follows `reports/stage3c_architecture_review.md` (stages S0–S8).

## 1. Planned flow

Candidate answer → **S0** pre-checks (existing) → **S1** claim segmentation → **S2** question-specific requirements (reads `scope_v1.jsonl`) → **S3** concept-to-claim verification → **S4** evidence consistency checks → **S5** alternative recognition → **S6** error detection → **S7** deterministic rubric calculation (weights 40/30/15/15 unchanged) → **S8** optional feedback (after scoring; never changes the score).

## 2. How the evaluator consumes the sidecar (S2)

For a `question_id`, S2 loads the row and builds the requirement list:

| Sidecar field | S3 receives it as | Can it lower the score? |
|---|---|---|
| `essential_concepts` | required concept | **Yes, completeness only**, when `not_stated` and the row is `completeness_penalty_eligible` |
| `essential_groups` | required group: satisfied when ≥ `min_required` members are `states_correctly`; any valid member counts | Completeness only, same condition |
| `supporting_concepts` | optional concept | No. Can add credit or feedback |
| `background_concepts` | not sent to S3 | No |
| `label_concepts` | not sent; implied by the essentials | No |
| `acceptable_alternative_explanations` | S5 matching hints (`basis` kept so S5 knows which are AI-proposed) | No |
| `ambiguity_flags`, `human_review_required` | confidence inputs and report columns | Lowers **confidence**, not score |
| `completeness_penalty_eligible = false` | essential misses are *reported* ("not demonstrated") but the completeness level is capped as "unscored for this dimension" and status becomes `graded_low_confidence` | No automatic penalty |

Reference helper already in the repo: `audit/evaluation/stage3c_validate.penalty_relevant_concepts(row)` returns the only concepts allowed to penalise completeness.

Code/SQL rows (`code_or_sql_exercise*`): correctness comes from executing the answer where a runnable check exists; concepts only drive feedback. Where no runnable check exists, treat the row as low-confidence.

## 3. The four concept states (never conflated)

| State | Meaning | Credit | Penalty | Confidence |
|---|---|---|---|---|
| **correct** (`states_correctly`) | a verified claim id states the concept consistently with the reference or a recognised alternative | yes | none | raises |
| **incorrect** (`states_incorrectly`) | a verified claim contradicts the reference or matches a documented common mistake, with an explanation | none | **correctness only** | — |
| **missing required information** (`not_stated`) | no claim states it, and the cross-check agrees | none | **completeness only, essential concepts only, eligible rows only** | neutral |
| **unverified** | the model asserted something but claim id/offset/cross-check failed, or it answered unsure/garbage | none | **none** | lowers; if it covers an essential concept, the dimension is "insufficient evidence", not low |

**An unverified concept is never converted to incorrect or to missing.** A quoting failure must never "prove" ignorance. Supporting concepts never produce `not_stated` penalties.

## 4. Implementation plan (offline-first; no real model until gate 3)

| Step | Work | Gate |
|---|---|---|
| 3C-1a | Sidecar loader + schema validation, `RequirementSet` object, penalty-eligibility handling, unit tests (including group semantics and the four-state table) | tests pass; frozen corpus hash unchanged |
| 3C-1b | S1 deterministic claim segmenter (sentences/clauses; code and SQL kept whole; stable claim ids and offsets) | property tests: ids stable, offsets reproduce text |
| 3C-1c | S4/S7 deterministic verification and rubric mapping with a **mock S3**; rule table for correctness/completeness/relevance/reasoning; caps carried over | offline tests incl. injection answers, fabricated claim ids, unverified ≠ incorrect |
| 3C-1d | Baseline harness over `bench_v2` that reads inputs only from `questions.jsonl`/`answers.jsonl` and writes predictions to a separate file | harness cannot open label files; prompts/code hashed before any scoring |
| 3C-1e | Human pilot (26 answers) completed; first human check of scope tiers for the 24 bench questions | human results in hand |
| 3C-1f | Only then: real S3 (enum-constrained, small) with the local model, **run once** on bench_v2, no tuning against it | acceptance criteria below |

Acceptance criteria are the fixed ones in the architecture review §6 (validity ≥ 99%, 0 injection compliances, Spearman ρ ≥ 0.80, MAE ≤ 12, concise/alternative answers never > 20 points under the human lower bound, correct-vs-incorrect AUC ≥ 0.95, stability, abstention ≤ 10%, latency). They are measured against **human** labels; AI labels alone cannot pass them.

## 5. Constraints on the prototype that follow from Stage 3C-0

- Use only the 77 AI-reviewed rows for any prototype; of these only 16 (8 of the 24 bench questions) may apply completeness penalties automatically.
- The other 16 bench questions can still be run, but their completeness result should be reported as a range/low-confidence and compared with human labels, not used for pass/fail on completeness.
- The 589 heuristic rows are for feedback and for building a human review queue only.
- Any change to scope tiers or the rule table after bench_v2 results are seen requires a new fresh set (or a held-out split declared in advance).
- Keep Flask scoring, adaptive difficulty and the frozen datasets untouched until a separate approval.
