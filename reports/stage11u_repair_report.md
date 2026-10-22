# Stage 11U - Final quality correction

**Status:** implemented and tested in the Linux sandbox copy, then installed into `D:\Projects\SMART-MOCK-INTERVIEW`. The previous versions are backed up in `tmp\stage11u_backup_20261022\`.
- Not executed on Windows. No real model was run, so there is no new real-model score.
- Automatic acceptance is not human-rated quality.
- Stage 10N stays the default. No commits, pushes or deployments.

**Baseline** (your run `tmp/stage10_opps_20261022_194032/results.json`, prompt 11.obj4, llama3.2:3b): 17/23 automatic acceptance, technical 11/12, grounded memory 2/7, strict skips 10/10, 0 detected fabricated references; Windows suite 880 passed.

## 1. Root causes and exact changes

### A. Memory false rejections

**M02, M01.** The memory claim check (`memory:implies_unclaimed_use`) still had an 11T branch that treated *any* word of this turn's question or answer, appearing in the same sentence as "your", as a claim about the candidate's work.
- M01: "How does the evaluation of **a logistic regression model**'s performance, specifically its ROC curve and AUC, relate to the performance of your oral cancer classification model?" mentions logistic regression as another model's evaluation. It claims nothing about theirs.
- M02: "the use of labelled training data in your spam classifier" tripped the grammatical check on the word *data*. They had said they trained it "on labelled emails". The validator confused the established project with an unestablished technique.

**M07.** "How would linear search affect the efficiency of your search feature?" was accepted but not credited as memory use. Its only link to the statement is the handle "your search feature", and "search" also appears in the interview question, so it didn't count as a distinctive word.

Changes in `src/demo/intel.py`:
- `implies_unclaimed_use` now asks `claimed_about_work`, which collects only what the grammar places in their work:
  - "the X in your …" or "the X you rely on" (any modal verb);
  - "X in your …" stated as fact;
  - modifiers in front of the part of the work they named ("your **binary** search");
  - "your X uses Y";
  - a bare process related to their work as fact ("How does halving the sorted list relate to … your search feature?");
  - an outcome stated as fact (", making it efficient").
- Filler and vague words ("use", "role", "data") are not claims.
- A topic given another owner ("of **a** … model") or a would/if possibility is not a claim.

Change in `attribute_memory` and, for the objective profile only, in `src/demo/followup_llm.py` `validate`: the code-built handle counts as a reference to the statement. Every other check (current session, objective progression, no claims, no presupposition) still applies, and Stage 10N's validation is unchanged.

**Still refused** (tested):
- "How does LRU eviction work in your Redis cache?"
- "How do atomicity and isolation in your money transfers ensure …?"
- "your binary search"
- "your logistic regression model" (they built a PyTorch oral cancer model)
- ", making it efficient for large datasets"
- "How does supervised learning apply in your spam classifier?" (no progression)
- "How old is your search feature?" (handle without the objective)

### B. Accepted technical inaccuracies

All six were accepted with no reason, because nothing compared what the question *asserts* with the rubric. The new checks in `intel.py` allow only what the vetted reference (prose only: code samples and URLs removed), the question asked, the concept names and the candidate's answer support:

| case | the question asserted | rule |
|---|---|---|
| T08 | a probability computed "for a specific input feature"; the sources only speak of features together | `narrows_collection` |
| T10 | "closest to the actual positive class probability", a case no source describes | `invented_qualifier` (now covers closest/nearest/earliest …) |
| T11 | hierarchical representations "in a decision tree"; the rubric gives them to deep networks | `misattributed_target` (model and algorithm nouns only) |
| T12 | "when a false negative is detected"; nothing supports a false negative being detected | `unsupported_target_event` |
| M03 | mock settings "affect the behavior of your API"; the rubric says mocks replace a dependency inside a test | `unsupported_effect` |
| N06 | "…meaning the patient doesn't have cancer", an inference stated as fact (and a wrong one) | `asserts_interpretation` |

Each has a retry instruction that tells the model what was wrong. The prompt version is now `11.obj5`; the only model-visible change is that retry wording.

**T09 checked, not relaxed.** Its fallback question ("What is the trade-off in terms of interpretability for clustering as an unsupervised task?") builds on nothing the candidate said, and interpretability is the model's own topic. The rejection stands.

## 2. Positive/negative validator comparison

Offline, same text, no model. The baseline is exactly what was on D: (11T). FR = good refused; FA = bad accepted.

| set | good | FR 11T → 11U | bad | FA 11T → 11U |
|---|---|---|---|---|
| fixture pairs | 12 | 1 → 1 | 13 | 2 → 2 |
| holdout | 10 | 5 → 5 | 12 | 0 → 0 |
| holdout2 | 10 | 5 → 5 | 10 | 0 → 0 |
| holdout3 | 15 | 2 → 2 | 27 | 1 → 1 |
| holdout4 (correctness) | 8 | 0 → 0 | 18 | 3 → 3 |
| holdout5 (memory) | 7 | 1 → 1 | 11 | 0 → 0 |
| reference controls | 10 genuine | 0 → 0 | 22 unsupported | 0 → 0 |

Recorded real questions (146 across four runs):
- **Newly refused (5):** T08, T10, T11, T12 from the 194032 run, and one Stage 10N question that claims "your logistic regression model".
- **Newly accepted (2):** M01 and M02 from the 194032 run.
- Nothing else changed.

M03's and N06's full questions are refused as shown above. They are missing from this count because `results.json` cuts each attempt at 200 characters, and the cut text is refused under both versions.

The new tests include 16 valid paraphrases that must keep passing, for example:
- "How would doubling a single feature's value change the probability the sigmoid function gives?"
- "What would happen if a false negative were made in a cancer screening study?"
- "How would return_value and side_effect change what the mocked dependency returns in a test?"

These were written by the rules' author: a guard against false rejection, not independent evidence.

**Iteration note.** The comparison caught three of my own over-reaches before installation, and each was fixed generally:
- "LRU eviction work in your cache" briefly passed after the broad branch was removed;
- "the number of comparisons needed…" was briefly refused;
- "change what two transfers see" was briefly refused.

**Diagnostic replay of the 194032 text** (no model; retries cannot be simulated): an accepted attempt on 14 of 25 model-called rows, with memory credited for M01, M02, M04 and M07. This is not a score. One environment difference: the sandbox has no bank vocabulary, so T06's "[5, 4, 3, 2, 1]" is refused here as novel numbers, while on Windows it was accepted.

## 3. Tests, lint, integrity (sandbox)

- `tests/app`: **916 passed, 5 skipped**, including 41 new tests in `tests/app/test_stage11u_final_correction.py`.
- The version asserts in two earlier test files were updated to `11.obj5`.
- `ruff check src scripts tests`: clean. `scripts/check_integrity.py`: OK. Frozen fixture sha256 unchanged (59e92f47…).

## 4. Still questionable (needs a human)

Accepted by the rules in your run and still accepted:
- **T02** "How does a transaction ensure that the data remains in a consistent state after a crash, but still respects constraints?" Conflates consistency with durability ("after a crash").
- **N05** "How does bubble sort handle elements that are already in order?" Asks about the best case while O(n²) worst case is open.
- **M04** "How would uncontrolled isolation in your money transfers affect the accuracy of transaction balances?" The idea is right, but "uncontrolled isolation" is odd wording (weak isolation level).
- **M05** "How does maximum likelihood estimation help in finding the optimal weights …?" Generic, and doesn't use the earlier sigmoid explanation. Correctly not credited as memory.
- **T03, T04, N04:** acceptable but shallow.
- **M01** (now accepted): no false claim, but its comparison of another model's ROC with their model's performance is muddled. It's in the blind sheet.

Known rule gaps:
- the four semantic false acceptances from the earlier stages;
- `question:ignores_objective` refuses about half the good scenario questions in holdout/holdout2;
- every 11U check is word-level, so a differently worded version of the same mistake can pass.

The blind sheet is `reports/stage11_eval/stage11u_review/sheet.csv`: 31 unrated items (19 follow-ups your run showed, verbatim, plus 12 author-written), with the source and current rule verdict in `key.json`.

## 5. Windows installation and verification

**Installed:**
- `src/demo/intel.py`, `src/demo/followup_llm.py`
- `scripts/stage11r_validator_compare.py` (new `--baseline stage11t`), `scripts/stage11t_review_sheet.py`
- `tests/app/test_stage11u_final_correction.py` and two updated test files
- both docs and this report
- the comparison JSON, the replay and the blind sheet

Hashes were checked after copying. **Windows verification is pending:**

```bat
.bot\Scripts\python.exe -m pytest tests\app -q
.bot\Scripts\python.exe -m ruff check src scripts tests
.bot\Scripts\python.exe scripts\check_integrity.py
set SMART_DEMO_FOLLOWUP_ENGINE=objective
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --engine objective
```

Gate for the benchmark run:
- 0 fabricated references, 0 duplicated phrases, 0 implied unclaimed implementations, 0 payload inconsistencies;
- strict skips 10/10;
- `prompt_version` 11.obj5.

## 6–7. Real interview and inspection

See `docs/STAGE11_REAL_INTERVIEW_GUIDE.md`: starting the app with the objective engine, creating a 20-minute session (the UI has no length control; the API's `time_budget_min` does), how to answer so memory, gap and misconception handling are all exercised, and where to read memory, follow-ups, fallbacks and the final report.

## Recommendation

**Proceed to human review and an end-to-end interview now, even though automatic acceptance is below 80%,** provided the Windows run shows the safety gate holding:
- no fabricated or unsupported personal references;
- no implied implementations;
- no duplicated phrases or leaked markers;
- strict skips intact.

More rule passes would mostly trade one word pattern for another. What's missing is evidence the rules can't produce: whether real follow-ups in a real conversation are correct and useful. Keep the objective engine experimental and Stage 10N the default until the blind ratings and the live interview say otherwise.
