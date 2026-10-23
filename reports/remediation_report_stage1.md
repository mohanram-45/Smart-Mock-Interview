# Stage 1 dataset remediation report

Output: `data/curated/v1/` (new). Originals, pipeline and models untouched. No new questions generated, no RAG work.

## Result

| Source group (original count) | Included | Review queue | Removed duplicate | Excluded |
|---|---:|---:|---:|---:|
| KEEP (193) | 181 | 8 | 4 | - |
| FIX ready_for_approval (139) | 135 | 3 | 1 | - |
| FIX not ready (35) | 0 | 35 | - | - |
| EXCLUDE (100) | - | - | - | 100 |
| Templates (3,618) | - | - | - | 3,618 |
| **Total 4,085** | **316** | **46** | **5** | **3,718** |

Why the counts differ from the brief's 193 + 139 = 332: 16 of those records were not approved. 5 were duplicates of stronger records; 11 were moved to the review queue after a second factual pass found imprecise statements (nothing was silently edited to make them pass). Every moved record is in `review_queue.csv` with its reason.

## Final domain counts and difficulty

| Domain | Easy | Medium | Hard | Total |
|---|---:|---:|---:|---:|
| Machine Learning | 39 | 96 | 16 | 151 |
| Deep Learning | 23 | 33 | 0 | 56 |
| Data Analysis | 12 | 23 | 4 | 39 |
| SQL | 17 | 11 | 1 | 29 |
| Python | 12 | 6 | 4 | 22 |
| NLP | 6 | 13 | 0 | 19 |
| **All** | **109 (34.5%)** | **182 (57.6%)** | **25 (7.9%)** | **316** |

Difficulty was assigned from content (rubric: Easy = single-concept recall; Medium = comparison, mechanism, short code or simple application; Hard = multi-step reasoning, design with trade-offs, or non-trivial implementation). No target ratio was applied. Hard is scarce because the seed pool has few genuinely hard questions that survived review; this is a content gap, not a labelling choice (see `data/audit/gap_analysis.md`). 53 topics.

General statistics and A/B testing sit under Data Analysis (21 records moved there); MLE, likelihood, Bayes, VIF, bias-variance and similar remain under Machine Learning.

## Changes applied to included records

158 unchanged; 23 formatting only (answer prefix or bullet marker removed, sentence case); 106 answers corrected; 22 answer and question corrected; 5 question corrected; 2 metadata only. Each record carries `modification` and `correction_basis`.

## Exclusions and duplicates

- 3,618 template records (processed IDs 1-3618) and 100 EXCLUDE records: listed in `lineage.csv`.
- 5 duplicates removed (`removed_duplicates.csv`), each with the stronger version kept: smi-0026 and smi-0070 (kept smi-0200), smi-0027 (kept smi-0304), smi-0136 (kept smi-0060), smi-0175 (kept smi-0264).
- Post-build check: no exact duplicate question or answer; no pair with question TF-IDF cosine >= 0.85. Six related pairs at 0.60-0.76 were looked at and have distinct intents.

## Review queue (46, not approved)

41 needs_review, 4 needs_code_test, 1 needs_source. 35 came from triage, 11 from the factual pass. Resolve or drop each before v2.

## Validation (`audit/remediation/validate_curated_v1.py`): 45 checks, 0 failed

Schema and enums, stable unique IDs, lineage to raw seed and processed records, unmodified text equals source, exclusions absent, text hygiene, duplicates, key_concepts, review-queue integrity, manifest hashes, original-file hashes. Python: 13 records' snippets (12 fenced blocks) executed and passed. SQL: no approved answer contains a SQL statement, so the sqlite syntax check ran on 0 snippets; nothing was invented to test.

## Remaining issues (honest list)

1. Factual review was AI-only (independent subagents plus code execution). No human subject-matter review; `verification` says so.
2. 18 key_concepts items are only weakly grounded in their record text (mostly acronyms or concept names implied by the answer); flagged WARN, not edited.
3. Known limitations carried by included KEEP records (`known_limitations`): THIN_ANSWER 80, OPEN_ENDED 23, IMPRECISE 19, QUESTION_FORMAT 5, TIME_SENSITIVE 4, OVERSTATED 1. Many SQL answers are short prose definitions with no query examples.
4. Hard is under-represented; Deep Learning and NLP have no Hard items; NLP has only 19 records. Coverage gaps remain large and are documented in `gap_analysis.md`. Filling them needs new questions, deliberately not done.
5. No NLTK-dependent example is in the approved set (smi-0345, 0347, 0367 are in the queue); 4 queue items await code tests.
6. The device has a stray duplicate `audit/triage/gap_analysis_concepts.py` from turn 3; harmless, left in place.
7. Original-file hash check on the sandbox covered the files mirrored there; the final comparison against the device is recorded below.
