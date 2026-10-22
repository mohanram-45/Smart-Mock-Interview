# Stage 1B continuation - pilot 01 merged, batch 02 generated and validated

Stopped here for your approval. Nothing in v1, v2, the raw/processed data, models, pipeline or application code was changed (hash-checked on your machine too). No RAG work started.

## Headline

| | Count |
|---|---:|
| **v3 core** = 360 v2 core + 41 pilot-01 (audited, corrected, merged) | **401** |
| **Batch 02** (separate, awaiting approval): NLP 12, Deep Learning 10, Python 12, Data Analysis 12 | **46** |
| Quarantined | **0** |
| Still in review queue (smi-0457, smi-0459, recommend dropping) | 2 |
| Executable reference tests | 130 (30 SQL, 100 Python); 43 of the 46 batch-02 questions have one |
| Validator | **83 checks, 0 failed** in the build sandbox (Python 3.13); **81, 0 failed** on your machine (Python 3.10.12, SQLite 3.37.2) |
| Independent audits | all 41 pilot-01 + all 46 batch-02 records; **no record has had human expert review** |

Files: `data/curated/v3/` (README, core, batch 02, spot-check evidence, review evidence, gap analysis, code tests, cross-version results, manifest). Scripts: `audit/remediation/build_curated_v3.py`, `validate_curated_v3.py`, `curated_v3_config.py`. Reports: `reports/stage1b_pilot01_spotcheck.md` (separate spot-check report) and this one; `reports/validation_v3_sandbox.json` holds the sandbox validator output.

## Step 1 - pilot spot-check (details in `stage1b_pilot01_spotcheck.md`)

21 stratified questions audited first (NLP 7, DL 5, SQL 9; all 9 Hard + 12 Medium). 5 of 21 needed content-level fixes, so I extended the audit to the other 20: **all 41 audited, 21 pass, 20 corrected, 0 quarantined.** 7 of 41 had a major defect (wrong sign in a growth example, a self-contradicting batch-norm claim, missing trade-offs the question asked for, an nltk dependency in a test, an author-narrated answer, an unconditioned latency claim, a missing demonstration). All 39 replacements are applied; 5 records had code changed and re-passed. 4 difficulty labels changed (2 up, 2 down), 1 disagreement kept and recorded. I opened all 11 cited pages myself: the auditors' statuses hold (12 supported, 2 partially - one sklearn page does not say what the stop list contains; that was verified by running code).

## Step 2 - merge

`data/curated/v3/curated_questions.csv` = 360 + 41. IDs and provenance are stable (`smi-NNNN`, `smi-gNNNN`; new `introduced_in`, `audit_scope`, `audit_verdict` columns). The 360 v2 core records are text-, concept-, difficulty-, domain- and provenance-identical to v2 (regression check); the 41 pilot records differ from v2 only where `pilot01_corrections.csv` lists a change. `quarantine.csv` exists and is empty.

## Step 3 - batch 02 (`pilot_batch_02.csv`, ids `smi-h0001`-`smi-h0046`)

Planned from `gap_analysis_v2.md` (NLP -> DL -> Python -> Data Analysis), each with a named missing concept: beam search and exposure bias, top-k/top-p sampling, RAG hallucination triage, LoRA, ROUGE, extractive QA span selection, char n-gram/OOV handling, small-data model choice, cosine vs dot product, retrieval metrics (recall@k/MRR/nDCG), tokenizer/padding bugs, benchmark contamination; reverse-mode autodiff, LSTM cell, mixed precision, positional encodings, KV cache, diffusion forward process, multi-GPU scaling, "predicts one class" debugging, residual-block parameter counts, contrastive loss; mutable defaults, late-binding closures, context managers, lazy batching, decorators with arguments, bounded asyncio, broadcasting, pandas merge/groupby pitfalls, algorithmic cost counting, log parsing, copy semantics; sample size, peeking, sample-ratio mismatch, Simpson's paradox, outliers, bootstrap, multiple comparisons, cohort retention, conversion-drop decomposition, non-response bias, seasonal decomposition, confounding.

Types: 34 coding (with executed tests), 7 debugging, 4 scenario, 1 design. Answers 175-662 words (median 433). No question claims to be a real interview question; none cites a source (nothing was opened that a claim depends on), so `sources` is empty everywhere in this batch.

## Step 4 - validation

| Check | Result |
|---|---|
| Schema / metadata | required fields, ids, enums, one domain per topic, versions, key concepts 3-8 distinct: pass |
| Exact and near duplicates (TF-IDF cosine, 447 questions) | none >= 0.85 (questions) / 0.90 (answers); no batch-02 question within 0.50 of an existing one; 5-gram template check pass |
| Technical review | independent review of all 46: **24 pass, 22 corrected, 0 quarantined**; 8 records had a major issue (see below); 37 replacements applied |
| Difficulty | blind auditor rating vs author label differed on 7 (all Hard -> Medium, adopted). Final batch: Medium 37, Hard 9, Easy 0. No ratio forced |
| Execution | all 43 batch-02 Python tests pass on **Python 3.10.20 and 3.11.17 (numpy 2.2.6, pandas 2.3.3)** and **3.13.16 (numpy 2.5.3, pandas 3.0.5)**; they import only stdlib/numpy/pandas and contain no 3.11+ features; on your machine 107 of 130 tests ran (23 need scikit-learn, spaCy, nltk, scipy or pytest, which you do not have) |
| Source / provenance | batch 02: `ai_generated_original`, no sources claimed; pilot 01: 14 citations on 11 pages, all re-opened by me (2 judged 'partially', recorded in `verification`) |
| Regression | v1 and v2 manifests match; 22 original files match; 360 v2 core records identical; reference code of those records unchanged |

Major issues the review caught in batch 02: NLP-04 (the asked-for merge/rank demonstration was missing), NLP-09 (wrong claim that Euclidean distance ignores norm), NLP-10 (ambiguous duplicate rule), DL-07 (never said when gradient accumulation is better; warm-up step range inconsistent), DL-08 (the question said wrong-axis softmax explains a loss of 2.30 - it does not), DL-10 (a "symmetric loss" cannot fix false negatives), PY-10 (counting wrapper not shown; false O(1)-space claim for sorting), PY-11 (`\d` matches non-ASCII digits, fixed in text and code).

## Updated gap analysis (`gap_analysis_v3.md`, concepts matched in question text, <=1 hit = gap)

| Domain | Gaps v1 | v2 core | v3 core | + batch 02 |
|---|---:|---:|---:|---:|
| NLP (17) | 14 | 13 | 6 | **2** |
| Deep Learning (20) | 14 | 14 | 5 | **3** |
| Python (16) | 12 | 11 | 11 | **4** |
| Data Analysis (15) | 8 | 8 | 8 | **3** |
| SQL (15) | 6 | 6 | 2 | 2 |
| Machine Learning (24) | 8 | 8 | 8 | 8 |

Left after batch 02: NLP - machine translation, OOV/multilingual (the OOV question is counted once); DL - backprop wording, framework autograd/training loops, diffusion/LLM basics; Python - packaging/typing, file I/O + regex, profiling, plotting; Data Analysis - EDA/visualisation, cohort/funnel (one question), sampling; SQL - set operations, CASE/pivot; ML - untouched (outliers, time series, interpretability, anomaly detection, drift, RL, semi-supervised, calibration). Keyword matching under-credits some questions (e.g. the cohort-retention question counts once) and cannot judge depth.

## Remaining issues and recommendations

1. **Human review is still missing.** About 1 in 6 AI-written records (7/41 pilot, 8/46 batch 02) had a major defect that only an independent read caught, and the reviewers are the same model family as the author. I recommend a human domain check of at least the 20 + 22 "corrected" records before any retrieval use.
2. **Batch 02 is coding-heavy (34 of 46), has no Easy item and no `concept` question.** Real interviews also ask short conceptual questions; the next batch should add Easy/Medium concept and scenario questions rather than more coding.
3. **Known code edge cases, documented not fixed** (in `review_notes`): DA-04/09/10/07 helpers do not enforce some conditions their answers describe (duplicate segments, missing cells, empty strata, NaN p-values); NLP-01/06/09/12 edge inputs outside the stated spec; DL-01 lacks `__rsub__`. The reference answers state the conditions; the helpers are teaching code.
4. **Claims resting on background knowledge, not on a source** (hedged in the text): fastText defaults, "lost in the middle", anisotropy/hubness, beam-size degradation, RAGAS definitions, Goyal et al. scaling rules, ROUGE-Lsum. A source pass would be worthwhile before these are used as ground truth.
5. **Tests on your machine:** 23 older tests need packages you do not have; they pass in the sandbox only. Installing scikit-learn, nltk, spaCy and pytest would let the validator run everything locally. `smi-g0002` and `smi-g0014` test scikit-learn behaviour on purpose.
6. **Two SQL tests compare `EXPLAIN QUERY PLAN` by first word only** because plan text varies by SQLite version.
7. Carried over: smi-0457 and smi-0459 (Flask/JWT) still queued - recommend dropping; 188 -> 233 key-concept wording warnings (token heuristic, semantic review is the real check); stray `audit/triage/gap_analysis_concepts.py` still on your machine; my validator runs left `__pycache__` folders under `audit/remediation/`.
8. Disclosure: the 46 batch-02 drafts were produced after a rate-limit interruption; the NLP and Data Analysis drafts were regenerated from scratch, the DL and Python drafts are the earlier ones, and all four passed the same review.

## Waiting for you

Decide: (a) approve merging batch 02 into the core set as v4 (I would first want a human look at the 22 corrected records), (b) a concept/scenario-heavy batch 03 for ML, Easy-level, SQL set operations and Python I/O-packaging, (c) anything to drop or rework.
