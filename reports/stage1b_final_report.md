# Stage 1B - final dataset consolidation (v4)

Stopped here for your approval. v1, v2, v3, the raw/processed data, models and application code are unchanged (hash-checked against their manifests, in the sandbox and on your machine). No RAG work started.

## Verdict: RAG readiness = PASS WITH LIMITATIONS

Good enough for a **first prototype** that is used to test retrieval and prompting, **not** to serve answers as ground truth. Why it is not a clean PASS: no record has had human expert review; the older 360 seed-derived records are the weakest part (no question type, 32 answers under 40 words, 233 key-concept wording warnings overall); ML still has real topic holes; and some literature claims rest on background knowledge.

## Headline

| | Count |
|---|---:|
| **v4 core** = 401 (v3) + 46 batch-02 (re-verified / corrected) | **447** |
| **Batch 03** (separate, awaiting review): ML 10, SQL 10, Python 10, Data Analysis 10 | **40** |
| Quarantined | **0** |
| Executable reference tests | 146 (Python/SQL); all pass on Python 3.10.20, 3.11.17 and 3.13.16 |
| Validator `validate_curated_v4.py` | **89 checks, 0 failed** (sandbox, Python 3.13) |
| Human expert review of any record | **none** |

Files: `data/curated/v4/` (README, core, batch 03, evidence, gap analysis, readiness metrics, manifest); scripts `audit/remediation/build_curated_v4.py`, `validate_curated_v4.py`, `rag_readiness_v4.py`, `make_gap_analysis_v4.py`; evidence in `audit/remediation/stage1b4/` (including `lead_source_checks.md`); `reports/validation_v4_sandbox.json`.

## Phase 1 - batch 02 re-verification (26 records: the 22 corrected + 4 Data Analysis edge-case records)

Each was re-checked by a separate verifier that had to supply evidence per claim (executed code, derivation, doc, paper, or `background_only`). Evidence: `batch02_verification.json` (claim, method, evidence); every changed field is listed in `batch02_corrections.csv`.

* **10 verified unchanged**, **16 fixed**, **0 quarantined**. All 8 originally major-defect records were re-examined; the ones still needing work are in the list below.
* **Text fixes:** h0007 (fastText defaults do not apply in supervised mode), h0009 (float64 copies, empty-matrix IndexError), h0011 (padding claim), h0012 (10% overlap is impossible on an 8-token item), h0029, h0040.
* **Code fixes (re-run on 3.10 / 3.11 / 3.13):** h0013 adds `__rsub__`; h0020 and h0022 validation; h0033 had a real bug (`int()` fails for strings over 4,300 digits); h0037 SRM wording and NaN/zero-total now raise; h0042 had a **real bug** (an event before signup day counted as week-0 retention; cohort filter is now day-level).
* **Data Analysis edge cases you flagged** (h0038, h0041, h0043, h0044): helpers now raise `ValueError` for the conditions the answers describe, with tests.
* **Difficulty:** h0008 stays Medium although a second verifier said Hard (recorded in `review_notes`). Final batch 02: Medium 37, Hard 9.
* **Not re-verified:** the other 20 batch-02 records rely on the v3 independent review only (`v4_verification = independent_review_v3_only`).
* **Sources I opened myself** (`lead_source_checks.md`): LoRA paper section 4.1 (alpha/r "helps reduce the need to retune"), GPT-3 (13-gram overlap), CPython `listsort.txt` (up to N/2 temp slots), SQLite compound-SELECT rules, scikit-learn calibration page. All support the records. The Python docs pages (os.replace, csv, try/finally) I could **not** open (permission prompt went unanswered); those claims are backed by executed tests only. 19 batch-02 claims remain `background_only` and hedged in the text (Lost in the Middle, Goyal sqrt scaling, BH/BY/Holm theorems, bootstrap inconsistency, SRM threshold).

## Phase 2 - v4 build

`curated_questions.csv` = 447. All 401 v3 core records are identical in v4 (every column except `version`), their reference code is unchanged, ids are stable, and the new columns `v4_verification`, `evidence_summary`, `remaining_limitations` are filled only for batch 02 (25 records carry a stated limitation). No difficulty ratio was forced: Easy 118, Medium 284, Hard 45.

## Phase 3 - batch 03 (`pilot_batch_03.csv`, ids `smi-i0001`-`smi-i0040`, separate)

* **Mix:** 13 scenario, 12 concept, 9 SQL exercise, 3 design, 3 debugging. Only 16 have code (all executed). Difficulty after blind audit: Easy 3, Medium 29, Hard 8.
* **Topics:** ML - leakage, calibration, drift, evaluation metrics, validation, production; SQL - UNION/INTERSECT/EXCEPT (NULL handling, ordering, evaluation order), window functions, count(*) vs count(col), pivoting; Python - file handling, modules/packaging, exceptions; Data Analysis - EDA, A/B power and sample size, confidence intervals, MCAR vs MAR, business interpretation.
* **Independent review:** 21 pass, 19 corrected, 0 quarantined; 38 corrections applied. Major defects caught in 9 records (e.g. ML-03 simulation numbers did not reproduce, ML-09 contradictory wording, PY-09 lacked a file-error class, DA-04 sample sizes wrong, DA-03 overstated "rule out MCAR"). 6 difficulty labels changed to the blind rating.
* **Nearest existing question:** cosine 0.32 at most; no pair above 0.50.
* **Sources:** 17 records cite sklearn or SQLite pages. Reviewers marked all supported; I personally opened the calibration and SQLite compound-select pages (supported), not the other cited pages.

## Phase 4 - RAG readiness measurements (v4 core, 447; `rag_readiness.md/.json`)

| Check | Result | Assessment |
|---|---|---|
| Domain coverage | ML 164, DL 86, DA 65, NLP 53, SQL 44, Python 35; 79 topics | Adequate, unbalanced toward ML |
| Checklist coverage (concept in >= 2 questions) | ML 16/24, DL 17/20, NLP 15/17, SQL 13/15, Python 12/16, DA 12/15 | ML weakest |
| Topics with fewer than 3 records | DL 10 of 18, NLP 8 of 16, SQL 5 of 13 | Thin tails; retrieval will miss these |
| Answer completeness | median 83 words (ML) to 193 (NLP); 32 answers under 40 words, all seed-derived | Seed answers are short; new ones are full |
| Retrieval metadata | domain, topic, difficulty, key concepts, provenance, verification 100%; `question_type` 19.5% (the 360 seed records have none); `sources` 3.6% | **Gap: question_type and sources** |
| Chunk size (question + answer + concepts) | median 232 tokens, p90 564, 58 records over 512, 5 over 1,024 | Fits one chunk each for most embedders |
| Key concepts | all 3-8 and distinct; 1,861 distinct (1,527 used once); 90.7% pass the token-grounding heuristic | Usable; long tail of one-off phrases will not help filtering |
| Duplication | 0 exact; 0 question pairs >= 0.85; 0 answer pairs >= 0.90; 4 related pairs at 0.60-0.85 (distinct intents) | Clean |
| Question diversity | 221 of 447 open with a definitional pattern ("What is/are", "How do you"); topic entropy 5.86 bits | Fine for recall; thin on scenario style (about 10 seed-style scenario openers) |
| Lexical self-retrieval baseline (question -> own record) | top-1 66%, top-5 85.7% (SQL 100%, NLP 98%, Python 97%, ML 75%) | A plain TF-IDF baseline already works; ML is the weak domain because its topics overlap |
| Verification | code executed on 131 records; source opened on 16; human review 0 | **Main risk** |

## Updated gap analysis (`gap_analysis_v4.md`; question-text keyword match, <= 1 hit = gap)

| Domain | gaps v1 | v3 core | v4 core | + batch 03 |
|---|---:|---:|---:|---:|
| ML (24 concepts) | 8 | 8 | 8 | **6** |
| Deep Learning (20) | 14 | 5 | 3 | 3 |
| NLP (17) | 14 | 6 | 2 | 2 |
| Python (16) | 12 | 11 | 4 | **2** |
| SQL (15) | 6 | 2 | 2 | **1** |
| Data Analysis (15) | 8 | 8 | 3 | **2** |

Still open after batch 03: ML - missing data and outliers, time-series forecasting, interpretability, anomaly detection, RL basics, semi/self-supervised; DL - backprop wording, framework autograd, diffusion/LLM basics; NLP - machine translation, OOV/multilingual; Python - profiling, plotting; SQL - CASE/conditional aggregation; DA - EDA/visualisation choices, cohort/funnel analysis. Keyword matching under-credits some questions and cannot judge depth.

## Remaining verification risks

1. **No human expert review anywhere.** Reviewers share a model family with the authors. In batch 03 roughly half the records still needed corrections, and 9 of 40 had a major defect; expect similar rates in anything not independently re-verified.
2. 20 batch-02 records, and all 401 v3 core records, were **not** re-verified in this stage.
3. 19 literature claims remain `background_only` (hedged); Python-docs-based claims in batch 03 are test-backed but not source-backed.
4. The 360 seed records are the oldest and shortest; 165 were rewritten by AI in Stage 1B, 195 are close to the raw seed.
5. 23 older tests need scikit-learn/spaCy/nltk/scipy/pytest, so on your machine they skip (the validator still reports them).
6. Carried over: smi-0457 and smi-0459 (Flask/JWT) still in the review queue - I recommend dropping them; stray `audit/triage/gap_analysis_concepts.py` and `__pycache__` folders are still on your machine.

## Recommendations before / during the RAG prototype

* Merge batch 03 as a **tagged** subset (it is separate until you approve it) and keep `verification` and `v4_verification` as retrieval-time metadata so the prototype can label or down-weight unverified answers.
* Back-fill `question_type` for the 360 seed records (cheap, mostly automatable) and add `topic` filters; consider dropping singleton key concepts from any concept-filter index.
* Spend human review on the 16 batch-02 and 19 batch-03 "corrected" records plus the 8 originally major batch-02 ones first.
* Next content batch, if you want one: ML (outliers/missing data, time series, interpretability, anomaly detection), CASE/conditional aggregation, cohort/funnel analysis, profiling/plotting.

## Waiting for you

Decide: (a) approve merging batch 03 into the core as v5 (or keep it separate), (b) whether to start a RAG prototype with the limits above, (c) whether to drop smi-0457 and smi-0459, and (d) whether you can get a human to review the priority records.
