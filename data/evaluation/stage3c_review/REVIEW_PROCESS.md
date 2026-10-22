# Human-review process

**No human has reviewed anything yet. No reviewer is named here. AI agreement is never counted as human validation.**

## A. Initial pilot (26 answers, single reviewer, ≈ 1 hour)
Files: `pilot_review_sheet_v2.csv` / `.md` (with AI columns) and `pilot_review_sheet_v2_blind.csv` (no AI columns).
1. Prefer the **blind** sheet first. For each row fill `reviewer_score_0_100`, `reviewer_factual_correctness` (correct / partly_correct / incorrect / not_applicable) and comments.
2. Use comments to say whether the listed essential requirements are right (missing, wrong, over-demanding).
3. Only afterwards compare with `proposed_score_range_AI_PROVISIONAL`. Record the share inside the range as a calibration note, labelled **single-reviewer** and **not validation**.
4. Anything with a code/SQL answer: run it if unsure.
The 26 rows: 24 questions × 1 answer rotating through answer styles, plus the ambiguous-reference item and the injection-wrapped correct answer.

## B. Scope tiers
Order of review: the 24 bench questions → the other 53 AI-reviewed rows → a random 10% sample of flagged heuristic rows. Reviewer marks essential tiers agree / disagree. A row becomes `human_verified` only after sign-off by a named reviewer; until then it stays AI-only. Gate carried over from the architecture review: ≥ 90% human agreement on essential tiers in the sample, otherwise rework.

## C. Full benchmark (120 answers) — later
1. **Two independent reviewers**, blind to AI labels, model scores and each other. Same scale and instructions as the pilot, plus per-requirement checklist: stated correctly / incorrect / not stated.
2. Both review at least 60 answers fully, covering every stratum; the rest get AI label plus ≥ 25% human spot-check.
3. **Disagreements:** |difference| ≤ 10 → average; 11–20 → average and flag; **> 20 points, or different factual-correctness verdict → discussion, outcome and reasoning recorded**; no agreement → a third reviewer decides; still none → item marked `contested` and excluded from accuracy metrics (reported separately). Original scores are always kept; nothing is averaged away silently.
4. Report weighted kappa between reviewers. If reviewers cannot agree on a stratum, the rubric for that stratum is revised first.
5. If only one reviewer is available, every result is labelled "single-reviewer" and claims are weakened accordingly.
6. AI labels are read only after human scoring; human labels go in a separate `human_labels.jsonl`.
