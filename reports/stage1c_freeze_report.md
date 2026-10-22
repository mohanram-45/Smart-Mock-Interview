# Stage 1C - final dataset freeze (v5)

Stopped here, as asked. No questions were generated, no RAG work was started, and v1-v4, the raw/processed data, models and application code are unchanged (hash-checked in the validator, in the sandbox and on your machine).

## Recommendation: PASS WITH LIMITATIONS - start the first RAG prototype on v5, as an unverified corpus

* Use v5 for retrieval and prompting experiments. Carry `verification`, `v4_verification`, `v5_verification` and the review tier with every retrieved chunk, and show the source/verification status next to any answer the prototype quotes.
* Do **not** let the prototype grade candidates against the reference answers as if they were ground truth until a human has reviewed the tier 1-2 records (65 records, `human_review_queue.csv`). No record has had human expert review.
* Why it holds: 0 exact or near duplicates, 98 validator checks pass, every code claim that has a test passes on three Python versions, and a plain keyword baseline already finds a question's own record in the top 5 for 87% of questions.
* Why it is not a clean PASS: the limits in the last section, above all the missing human review and ML topic coverage.

## Headline

| | |
|---|---:|
| **v5 records** | **487** |
| Domains | ML 174, Deep Learning 86, Data Analysis 75, SQL 54, NLP 53, Python 45 |
| Difficulty (not forced) | Easy 121, Medium 313, Hard 53 |
| Quarantined / review queue | 0 / 0 |
| Archived out of scope (smi-0457, smi-0459) | 2, originals kept in `review_archive.csv` |
| Executable reference tests | 146 (all pass; code unchanged in this freeze) |
| Validator `validate_curated_v5.py` | **98 checks, 0 failed** in the sandbox (Python 3.13) |
| Dataset fingerprint (combined sha256) | `9eb94d8fe8bc83486dd401c5651878ebef0c4d0bd2c359d6e58fe12ba4637123` |

The fingerprint is rebuilt from the data files by the validator, and two separate builds gave the same value. I also changed one answer and one difficulty label in a scratch copy: the validator then failed 8 checks (manifest hashes, fingerprint, regression, json mirror), so the checks do catch edits.

## 1-3. Recheck of the 19 corrected batch-03 records

Three fresh verifiers (not the authors or first reviewers) re-derived or re-ran every non-trivial claim and tried to break the code. The 9 records that had a major defect were marked priority. Evidence per claim is in `batch03_recheck.json`.

| Result | Records |
|---|---|
| Verified unchanged: **13** | i0003 (ML-03), i0004, i0005, i0006 (ML-06), i0009 (ML-09), i0011, i0018, i0020, i0025 (PY-05), i0026, i0027 (PY-07), i0033 (DA-03), i0034 (DA-04) |
| Fixed (text only): **6** | i0013, i0015, i0017 (SQL), i0022 (PY-02), i0028, i0029 (PY) - 7 replacements, listed in `batch03_v5_corrections.csv` |
| Quarantined: **0** | |

What the fixes were: i0013 gave a wrong reason for wrapping each EXCEPT in a subquery and used undefined aliases; i0015 said "no built-in MEDIAN" too absolutely (it exists in SQLite 3.47+ CLI and as an optional extension from 3.51); i0017 contradicted itself about the default window frame; i0022 had a garbled sentence and a `relpath` claim that is only true before Python 3.12; i0028's Python 3.14 SyntaxWarning claim is now attributed to PEP 765; i0029 now lists `UnicodeDecodeError` from a non-UTF-8 file as an exception outside the hierarchy.

Checks that held and are worth knowing: the DA-04 sample sizes (about 39,475 per arm for 4.0 to 4.4%, 154,300 for 4.0 to 4.2%) - I recomputed them myself; the ML-03 simulation numbers (AUC about 0.82 unchanged by tripling the logit, ECE about 0.002 to 0.13) reproduce; the SQL tests ran on a real SQLite 3.37.2, 3.45.1 and 3.53.1; the Python tests passed on 3.10, 3.11 and 3.13.

Difficulty labels and key concepts: all 19 judged correct, none changed. Easy for i0005 is borderline but accepted.

Sources: SQLite pages (`lang_select`, `windowfunctions`, `lang_aggfunc`, `changes`) and the Lipton label-shift paper were opened by the verifiers; I opened `changes.html`, PEP 765, the scikit-learn calibration page and the SQLite compound-select rules myself. Three source entries were added (Lipton for i0005, `changes.html` for i0015, PEP 765 for i0028). The Python docs pages (os, csv, pathlib, packaging, PEP 668) could not be opened because the fetch permission request went unanswered, so those claims are supported by executed tests or by local CPython behaviour, not by a cited page.

The 21 batch-03 records that passed their first review were merged but **not** rechecked (`v5_verification = independent_review_v4_only`); the ML/DA verifier ran no code because those records have none, and checked numbers with its own scripts.

## 4-5. Merge and exclusions

`data/curated/v5/curated_questions.csv` = 447 (v4 core, identical) + 40 batch-03. smi-0457 and smi-0459 are out of the knowledge base (lineage disposition `ARCHIVED_OUT_OF_SCOPE`, no Flask/JWT text in any record); their raw and processed originals plus the proposed rewrites are in `review_archive.csv`.

## 6. Validation (`reports/validation_v5_sandbox.json`)

| Check | Result |
|---|---|
| Schema, ids, enums, one domain per topic | pass |
| Duplicates | 0 exact; 0 question pairs >= 0.85; 0 answer pairs >= 0.90; 4 related pairs at 0.60-0.85 with distinct intents; batch 03's nearest existing question is 0.31 |
| Metadata | domain, topic, difficulty, key concepts, source type, verification: 100%; `question_type` 26% (360 seed records untyped); `sources` 7% |
| Code | 146 tests re-run: SQL in sqlite, Python as subprocess; stdlib/numpy/pandas only; no 3.11+ features; cross-version results retained; every fenced code block in an answer is covered by a tested solution |
| Regression | v4 core identical; code_tests identical; only the 7 logged text changes differ in batch 03; v1-v4 manifests and original files unchanged |
| Provenance | seed records trace to raw and processed rows; no claim of being a real interview question |
| Warnings | 274 key-concept token-heuristic hits (up from 233 because batch 03 was added; the check is wording-based, not semantic); 1 label inconsistency: smi-0063 says `code_executed` (Stage 1A) but has no recorded test - left unchanged to keep the regression identical, disclosed in the manifest |

Run on your machine, see below.

## 8. Manifest (`data/curated/v5/manifest.json`)

Holds version, record count, domain and difficulty counts, question types, verification limitations, review tiers, known label inconsistencies, hashes of the v1-v4 manifests, all file hashes, and the fingerprint with its definition (sha256 over the compact JSON of the nine core fields for all records sorted by id, plus sha256 of `code_tests.json`).

## RAG-readiness measurements (v5, `rag_readiness.md`)

* Coverage: checklist concepts with >= 2 questions - ML 18/24, DL 17/20, NLP 15/17, Python 14/16, SQL 14/15, DA 13/15. Gaps now: ML 6 (missing data/outliers, time series, interpretability, anomaly detection, RL, semi-supervised), DL 3, NLP 2, Python 2 (profiling, plotting), SQL 1 (CASE/pivot), DA 2 (EDA/visualisation, cohort/funnel). Topics with fewer than 3 records: DL 10 of 18, NLP 8 of 16, ML 5, SQL 4.
* Answers: median 108 words (ML) to 202 (SQL); 32 under 40 words, all seed-derived. Chunk estimate (question + answer + concepts): median 243 tokens, p90 590, 74 above 512.
* Diversity: 222 of 487 start with a definitional pattern; 86 topics; 360 seed records have no question type.
* Lexical self-retrieval baseline: top-1 68%, top-5 87% (SQL 100%, NLP 98%, Python 98%, DA 88%, DL 85%, ML 77%).

## 9. Remaining unverified claims and records for human review

* `unverified_claims.csv`: 73 entries - 43 claims supported only by background knowledge (Lost in the Middle, Goyal et al. sqrt scaling, BH/BY/Holm theorems, bootstrap inconsistency, SRM threshold, PSI cut-offs, skew taxonomy, packaging specs, PEP 668 and similar) and the verifiers' remaining limitations. All are hedged in the text.
* `human_review_queue.csv` ranks every record: **tier 1 (24)** every record that ever had a major defect (7 pilot-01, 8 batch-02, 9 batch-03); **tier 2 (41)** corrected records and records with background-only claims; **tier 3 (62)** AI-written records with one AI review; **tier 4 (298)** seed answers rewritten by AI; **tier 5 (62)** seed answers close to the raw source. Start with tiers 1 and 2 (65 records).

## Remaining quality limitations

1. **No human expert review of any record.** Authors and reviewers share a model family; about half of the AI-written batches needed corrections on first review.
2. **Uneven verification depth:** 45 records were re-verified with per-claim evidence (26 batch-02, 19 batch-03); 21 batch-03 and 20 batch-02 records rest on one review; the 401 older records on earlier reviews only.
3. **Few cited sources:** 35 records cite a page (7%); the rest rest on executed code, derivation or background knowledge.
4. **Metadata gaps:** 360 seed records have no `question_type`; key concepts are mostly one-off phrases (1,717 of 2,079 appear once), so concept filters will be sparse.
5. **Topic coverage:** ML has real holes (listed above); 10 of 18 DL and 8 of 16 NLP topics have fewer than 3 records, so queries there will retrieve thin or adjacent answers.
6. **Seed answers are short and older:** 32 under 40 words; 195 seed records are close to the raw source and were never independently re-derived.
7. **Environment:** your machine lacks scikit-learn, spaCy, nltk, scipy and pytest, so 23 older tests skip there and run only in the build sandbox.
8. Housekeeping on your machine: stray `audit/triage/gap_analysis_concepts.py` and several `__pycache__` folders from my validator runs.

## Files

`data/curated/v5/` (dataset, manifest, evidence, review queues, gap analysis, readiness metrics, README); scripts `audit/remediation/build_curated_v5.py`, `validate_curated_v5.py`, `make_gap_analysis_v5.py`, `rag_readiness_v5.py`; recheck briefs and verifier outputs in `audit/remediation/stage1b5/`; this report and `reports/validation_v5_sandbox.json`.

Waiting for your approval before anything else (RAG implementation, human-review plan, or further batches).
