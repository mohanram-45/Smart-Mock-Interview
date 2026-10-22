# Stage 9C evaluation protocol: experimental follow-ups and grounded feedback

**Status: a plan plus tooling. No human labels exist.** Nothing here supports a claim about follow-up quality or feedback accuracy. The recorded real-model run of the modular
evaluator (Stage 3C) **failed** its frozen criterion (abstention 0.45 against a 0.40 limit) and that result stands; it is historical evidence only. Do not tune prompts, thresholds
or the validator against the frozen 20-answer benchmark and then report on it.

## What is being evaluated (and what is not)
| Thing | Question for human reviewers | Not claimed until labelled |
|---|---|---|
| Answer-aware follow-up (`followup_llm`) | Is it relevant to what the candidate said? Does it ask about something the answer already showed? Does it assume a fact that is not in the question, the answer or the curated material? | relevance, usefulness |
| Grounded feedback (`grounded`) | Is each "covered" concept really covered? Is any "possible technical error" really an error? | false-credit rate, false-accusation rate |
| Safety rules (validator, injection guard, deadline, fallback) | Automated tests, deterministic | already covered by `tests/app/test_stage9c_*.py` |

## Scenario coverage (each needs at least 8 human-written answers before any rate is reported)
correct concise · correct but differently worded / alternative approach · partially correct · confidently incorrect · missing evidence (vague) · prompt injection · off-topic ·
follow-up relevance · false concept credit · false accusation of a technical mistake. Seed cases (AI-written, `origin: synthetic`) live in `docs/stage9c_eval/cases_seed.json`; they exercise
the safety paths and are **never pooled with human cases**. Three slots (`H01`-`H03`) are waiting for human-written answers.

## Workflow (blind)
1. People write the answers (volunteers, at least 2 different people, none of whom tuned the system). Put them in a copy of `cases_seed.json` (`origin: "human"`).
2. `python scripts/stage9c_review_pack.py build --cases <file> --out reviews/round1 --mode live` (use `--mode mock` to rehearse the process). Output: `reviewer_sheet.csv` (no category, origin, mode or model name) and `key.json` (keep private).
3. Two reviewers, qualified in the topic, each get their **own copy** of `reviewer_sheet.csv` and fill `y / n / unclear` in the label columns. They do not see each other's labels or `key.json`.
4. `python scripts/stage9c_review_pack.py score --key reviews/round1/key.json --labels a.csv --labels b.csv`. The scorer prints agreement (Cohen's kappa) and counts per origin. With fewer than two reviewers it says so; it never prints "accuracy".
5. Decide thresholds **before** looking at results (e.g. kappa floor, maximum false-accusation rate). Disagreements are adjudicated by a third person and kept as a separate column.
6. Any change made after seeing results needs a **fresh** set of answers for the next round.

## Where human judgement is missing today
- Relevance and usefulness of every model-written follow-up: **no human has rated any**.
- Correctness of the AI-written concept lists and reference answers (the scope sidecar is "AI-reviewed, not human-verified").
- Whether "covered" / "possible error" findings agree with experts.
- Whether the validator rejects too many good questions (fallback rate with a real model is unmeasured in CI; the smoke test reports it for a handful of samples).
