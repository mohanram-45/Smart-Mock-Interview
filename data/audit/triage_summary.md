# Dataset triage summary

Scope: all 4,085 records in `data/processed/questions.csv` (processed IDs preserved). Nothing in the original datasets, pipeline code or models was modified; every status below is a *proposal* awaiting approval.

## 1. Counts by domain (all records, current domain labels)

| Domain | KEEP | FIX | EXCLUDE | EXCLUDE_TEMPLATE | Total |
|---|---:|---:|---:|---:|---:|
| Machine Learning | 103 | 93 | 43 | 612 | 851 |
| Deep Learning | 31 | 35 | 42 | 602 | 710 |
| NLP | 7 | 20 | 10 | 612 | 649 |
| Python | 9 | 16 | 3 | 600 | 628 |
| SQL | 27 | 2 | 1 | 612 | 642 |
| Data Analysis | 16 | 8 | 1 | 580 | 605 |
| **All** | 193 | 174 | 100 | 3618 | 4085 |

* **EXCLUDE_TEMPLATE (3,618)**: every record produced by `scripts/expand_interview_dataset.py` (processed IDs 1-3618).
* **Seed records (467)**: KEEP 193, FIX 174, EXCLUDE 100.

### Seed records only

| Domain | KEEP | FIX | EXCLUDE | EXCLUDE_TEMPLATE | Total |
|---|---:|---:|---:|---:|---:|
| Machine Learning | 103 | 93 | 43 | 0 | 239 |
| Deep Learning | 31 | 35 | 42 | 0 | 108 |
| NLP | 7 | 20 | 10 | 0 | 37 |
| Python | 9 | 16 | 3 | 0 | 28 |
| SQL | 27 | 2 | 1 | 0 | 30 |
| Data Analysis | 16 | 8 | 1 | 0 | 25 |
| **All** | 193 | 174 | 100 | 0 | 467 |

### Seed records if proposed domain moves were applied (15 records)

| Domain | KEEP | FIX | EXCLUDE | EXCLUDE_TEMPLATE | Total |
|---|---:|---:|---:|---:|---:|
| Machine Learning | 103 | 86 | 43 | 0 | 232 |
| Deep Learning | 31 | 36 | 42 | 0 | 109 |
| NLP | 7 | 20 | 10 | 0 | 37 |
| Python | 9 | 16 | 3 | 0 | 28 |
| SQL | 27 | 2 | 1 | 0 | 30 |
| Data Analysis | 16 | 14 | 1 | 0 | 31 |
| **All** | 193 | 174 | 100 | 0 | 467 |

Domain moves are all *proposals* (Predictive-modelling product-metric cases to Data Analysis; one ML-labelled deep-learning definition to Deep Learning). Statistics questions (Central Limit Theorem, confidence intervals, hypothesis tests) currently sit in ML and could move to Data Analysis if you want that domain to cover statistics; see `gap_analysis.md`.

## 2. FIX records (174) by review state

| review_state | Count | Meaning |
|---|---:|---|
| ready_for_approval | 139 | Mechanical fix (trim of leaked text, typo) or rewrite that uses only well-established facts; still needs your sign-off |
| needs_review | 30 | Proposal depends on judgement (domain move, premise change, contested claim, missing table reconstructed from general knowledge) |
| needs_code_test | 4 | Needs executable verification that could not be completed here |
| needs_source | 1 | Technically uncertain; no proposal made (3834, temporal-difference learning) |

Proposal confidence (reviewer judgement): high 137, medium 31, low 6. 6 FIX records have **no proposed text** because I could not responsibly invent one (IDs: 3636, 3834, 3967, 4075, 4077, 4081).

## 3. What was found in the 467 seed records

| Flag | Records |
|---|---:|
| THIN_ANSWER | 106 |
| IMPRECISE | 67 |
| DUPLICATE | 56 |
| OPEN_ENDED | 41 |
| COSMETIC_PREFIX | 40 |
| FACTUAL_ERROR | 36 |
| CORRUPTED | 27 |
| LOW_RELEVANCE | 26 |
| DOES_NOT_ADDRESS | 21 |
| LOW_VALUE | 20 |
| MISSING_FORMULA | 20 |
| ANSWER_BLEED | 18 |
| REQUIRES_CODE | 18 |
| DOMAIN_MISMATCH | 16 |
| MISLEADING | 15 |
| QUESTION_FORMAT | 11 |
| OUTDATED | 9 |
| EDITORIAL | 9 |
| ILL_POSED_QUESTION | 8 |
| TYPO | 7 |
| QUESTION_TYPO | 7 |
| REQUIRES_DATA | 6 |
| TIME_SENSITIVE | 6 |
| UNVERIFIED_CLAIM | 6 |

(A record can carry several flags. THIN_ANSWER on a KEEP record means the answer is correct but brief.)

Requested categories:

* **Corrupted answers**: 29 flagged CORRUPTED, plus 18 with next-question text leaked into the answer and 36 with a factual error.
* **Missing formulas**: 20; **missing tables**: 3 (3973, 3974, 3990); **outdated content**: 9.
* **Questions requiring executable code**: 18 (REQUIRES_CODE) and 6 requiring an external dataset (REQUIRES_DATA).
* **Duplicates**: 59 seed records are marked as duplicates of another seed record (`duplicate_of`); 4 of those point at a record that is itself excluded (the whole cluster is excluded as low value: 3657->3725, 3658->3726, 3686->3723, 3708->3675).
* **Difficulty**: reviewer rubric (Easy = single-concept recall, Medium = comparison/mechanism/application, Hard = multi-step reasoning/design/edge cases) was applied to the 367 KEEP/FIX records. The proposed label differs from the current processed label in 253 cases (69%) and from the *raw* seed label in 87 (24%). Difficulty changes are recorded in `proposed_difficulty` only; they do not by themselves make a record FIX.
* **Cosmetic prefixes** ("Ans.", "Solution:") remain on 15 KEEP records; they are stripped in proposed answers of FIX records only. Recommended as a pipeline normalisation step.

### Executable-code verification

Snippets proposed for answers were run in the audit sandbox (Python 3, NumPy, matplotlib, NLTK 3 installed into a scratch directory): **14 passed**, 1 could not be run (3963: NLTK tokenizer data cannot be downloaded in the sandbox). 4 records that need code (4075 Flask REST, 4077 JWT, 4081 pytest mocking, 3967 spaCy similarity) have **no proposed answer** because pytest/spaCy are not installed and the Flask/JWT items are security- and scope-sensitive. Passing tests mean the snippet behaves as described; they do not remove the need for human approval.

## 4. How the generated records were handled

All 3,618 generated rows are EXCLUDE_TEMPLATE without individual review. They come from 304 (domain, topic) pairs x 12 question templates; once the topic is masked the answers collapse to 15 distinct texts, difficulty labels are produced by a keyword-count rebalance, and the answers describe what a good answer should contain rather than giving one (see `reports/dataset_audit.md`). Their `note` column carries this reason.

## 5. Usable pool for RAG

KEEP + ready_for_approval FIX = **332** seed questions; KEEP + all FIX = 367. Many KEEP answers are one-line definitions, so even the best case is a small, thin reference set (see `gap_analysis.md`).

## 6. Files

* `data/audit/triage.csv`: one row per record (4,085), original question and answer plus proposed fields.
* `data/audit/triage_summary.md` (this file), `proposed_corrections.md`, `gap_analysis.md`, `unresolved_issues.md`.
* `audit/triage/`: decision files (`dec_*.py`), builders and test runner.
