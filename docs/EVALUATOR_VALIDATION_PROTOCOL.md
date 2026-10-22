# Validation protocol for the experimental modular evaluator (proposal, Stage 8B)

**Status: a plan, not a result.** Nothing in this document has been run. There are **no human labels** in this repository for the modular evaluator: the 20-answer
benchmark's expectations were written by an AI and are provisional (see `reports/stage3c3_consolidated_report.md`). The recorded real-model run **failed** its frozen
criterion (abstain rate 0.45 against a limit of 0.40), the decision is *do not advance*, and nothing below changes that.

## Why a new protocol, and why not just re-run the old one

The frozen 20-answer set has been looked at repeatedly (two prompt iterations, a diagnosis, a review). Anything tuned or "fixed" against it would be measured on data it was
tuned on. The Stage 8B safeguards (`src/evaluation/modular/safeguards.py`) were therefore written from **input-handling defects found with synthetic probes**, not from
benchmark errors, and are tested with scripted (mock) verifiers only. They make the evaluator safer to run; they say nothing about whether it grades correctly.

## What would be measured

For each *required concept* in an answer: does the evaluator's finding (`states_correctly`, `states_incorrectly`, `not_stated`, `unverified`) agree with independent human
reviewers? Secondary: abstention rate and its causes, false error accusations, latency, provider failures. Not measured: a "score" (numbers come from fixed rules over these findings).

## Design (every number below is a proposal for the project owner to confirm BEFORE data collection)

1. **Fresh sample.** At least 40 answers, none from the frozen 20, spread over at least 8 of the penalty-eligible questions (`src/demo/experimental.py: scorable_ids`, 16 today). Answers should come from
   people (practice answers from consenting volunteers, or answers written by a human on purpose, including concise correct ones, correct-but-different ones, and wrong ones).
   Answers written by an AI may be added only as a separate, clearly labelled *synthetic stress* group that is reported on its own and never pooled into accuracy figures.
2. **Two independent reviewers**, each qualified in the topic, who do not see the evaluator output or each other's labels. They follow one written guideline and label every required
   concept as: states correctly / states incorrectly / not stated / cannot tell, and the answer as on-topic / off-topic.
3. **Agreement first.** Report Cohen's kappa between the reviewers per state. If agreement is poor (the owner sets the floor in advance; 0.6 is a common starting point), the guideline is
   revised and the sample is re-labelled; the evaluator is not compared against labels the humans themselves do not agree on. A third reviewer settles remaining disagreements and the
   number of adjudicated items is reported.
4. **Freeze, then run once.** Record the evaluator code fingerprint, prompt/rubric versions, model name and Ollama version, the sample file's sha256 and the label files' sha256. Run the
   evaluator exactly once. No re-runs after seeing results, no threshold changes, no prompt edits on this sample; any change means a new sample.
5. **Pre-registered criteria** (owner to fix in writing first, with their reasons): maximum abstention rate; maximum rate at which the evaluator says *incorrect* where both reviewers say *correct*;
   minimum agreement on *states correctly*. The existing frozen abstention limit (0.40) stays in force unless the owner explicitly replaces it, and the replacement is dated.
6. **Report.** Confusion matrix of evaluator vs reviewer consensus per state; abstention broken down by cause (the existing taxonomy: model uncertain, evidence gate, off-topic, provider failure,
   plus the Stage 8B reasons *answer truncated* and *possible hidden instruction*); safeguards fired; latency percentiles; provider failures; Wilson 95% intervals; the sample size stated next to every figure.
   Record the run in MLflow with `src.mlops.tracking.live_run` (kind *evaluator validation*, `human_validated` stays `false` until the owner signs off).

## Guardrails that stay regardless of the outcome

- LLM-derived scores do not drive adaptive difficulty. That needs a separate decision after a pass **and** a second independent review.
- Numeric experimental grades stay disabled for questions without penalty-eligible scope, and wherever evidence is insufficient (the evaluator abstains instead).
- A pass would support the words "agreed with two human reviewers on N answers", never "accurate" or "validated for grading".
- No personal data in the sample; volunteers consent in writing; the files are not committed until the owner has reviewed them.

## Effort

A reviewer needs roughly a few minutes per answer; 40 answers by two reviewers is a day or two of calendar time, not weeks. The expensive part (the Qwen run) is about 30-90 s per answer on a local GPU/CPU.
