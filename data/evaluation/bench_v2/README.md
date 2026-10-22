# bench_v2 — fresh evaluation benchmark (baseline measurement only)

120 candidate answers to 24 corpus questions (3 per domain; Easy 8 / Medium 8 / Hard 8). None of the questions appeared in earlier Qwen/Llama tuning or bench_v1 (17 IDs excluded, listed in `manifest.json`).

**Do not use this set to tune prompts before the baseline has been measured. Do not give label-side files to an evaluator.**

| File | Side | Content |
|---|---|---|
| `questions.jsonl` | evaluator input | question_id, domain, difficulty, question_type, question |
| `answers.jsonl` | evaluator input | answer_id (shuffled, seed 20261014), question_id, answer_text |
| `ai_labels.jsonl` | **labels** | answer_kind, provisional score range, factual_correctness, flags, rationale. `ai_provisional_not_human_reviewed` |
| `scoring_rubric.md` | **labels** | rubric bands and drafting rules |
| `manifest.json` | — | sha256 of each file, counts, seed, exclusions |

Reference answers and key concepts come from the frozen corpus by `question_id`; requirement tiers come from `data/evaluation/scope/scope_v1.jsonl`.

Answer kinds (120): correct_full 19, concise_sufficient 13, valid_alternative 18, partial 22 (+1 explanation-only), incorrect 22, hallucinated 13, off_topic 3, prompt injection 6 (3 pure, 2 weak content, 1 injection wrapped around a correct answer), keyword list 1, non-answer 1, ambiguous-reference 1. Types covered: coding, debugging, sql_exercise, scenario, design, evaluation, concept, unspecified.

**Authorship and limits.** All answers and labels were written by the same Claude session that drafted the scope sidecar, so they are not independent of it. All 26 answers containing code or SQL were executed in the sandbox (the two scikit-learn snippets only loaded); the other labels are judgement. Score ranges are provisional AI expectations. 120 answers give wide confidence intervals; this is a go/no-go gate, not proof of general accuracy.
