# Curated interview knowledge base - v3

Built by `audit/remediation/build_curated_v3.py` from v1 and v2 (both left byte-for-byte unchanged) plus the independent audits stored in `audit/remediation/stage1b3/`. Checked by `audit/remediation/validate_curated_v3.py`.

## What is in v3

| File | Content |
|---|---|
| `curated_questions.csv/json` | **Core set, 401 records** = the 360 v2 core records (text identical to v2) + the 41 pilot-01 questions after the independent audit and its corrections. |
| `pilot_batch_02.csv/json` | **Batch 02, 46 new questions** (NLP 12, Deep Learning 10, Python 12, Data Analysis 12). Separate on purpose: not merged until approved. |
| `quarantine.csv` | Audited records that could not be fixed locally. Empty in this build (header only). |
| `code_tests.json` | 130 executable reference solutions/tests (30 SQL, 100 Python), keyed by record id. |
| `cross_version_results.json` | Result of every Python test on Python 3.10 / 3.11 (numpy 2.2.6, pandas 2.3.3) and 3.13 (numpy 2.5.3, pandas 3.0.5). `SKIP:<pkg>` = optional package not installed there. |
| `pilot01_spotcheck.json/.csv` | Independent audit of all 41 pilot-01 questions: sampled ids, scope, verdict, every issue with its replacement, blind difficulty rating, code and source findings. |
| `pilot01_corrections.csv` | Every field of a pilot-01 record that differs between v2 and v3. |
| `batch02_review.json` | Independent review of every batch-02 record (same structure). |
| `gap_analysis_v3.md` | Concept-coverage gap analysis (v1 / v2 core / v3 core / + batch 02). |
| `review_queue.csv`, `lineage.csv`, `removed_duplicates.csv` | Carried over from v2 (2 queued records, 4,085-record lineage, 5 removed duplicates). |
| `manifest.json` | SHA-256 of every file above and the record counts. |

## Identifiers and provenance

* `smi-NNNN` - seed-derived record; `NNNN` is the raw seed id (`introduced_in` = `v1` or `v2`). Provenance columns trace to `data/raw/questions_seed.csv`.
* `smi-gNNNN` - pilot-01 question (`introduced_in` = `v3-pilot01`, plan id `P-XXX-NN` in `plan_id`). Stable since v2; the id never changed when the text was corrected.
* `smi-hNNNN` - batch-02 question (`introduced_in` = `v3-batch02`, plan id `P2-XXX-NN`). Numbered in plan order (NLP, Deep Learning, Python, Data Analysis).
* Every generated record has `source_type = ai_generated_original`. None is claimed to be a real interview question.
* New columns in v3: `introduced_in`, `audit_scope` (`stratified_sample_21`, `extension_audit_20` or `batch02_independent_review`), `audit_verdict` (`pass` / `corrected`), `interview_style_note`.

## How records were checked

1. Authoring agent writes question, answer, tests (tests are executed, not just written).
2. A separate agent that did not write the record, and had not seen earlier reviews, audits it blind to the difficulty label: parts-answered checklist, claim-by-claim accuracy, re-running all code and trying to break it, near-duplicate search, source checking.
3. Exact-substring corrections from the audit are applied by script (`apply_audit`), explicit patches live in `curated_v3_config.py`; anything that could not be applied would stop the build.
4. Validator: schema, provenance, duplicates, key concepts, sources, code execution, portability, regression against v1/v2, audit evidence.

**No record has been reviewed by a human subject-matter expert.** The audits are by AI agents. Corrections from the audits were applied by script and were not re-audited by a third reviewer; code changes were re-executed.

## Difficulty

Easy = single-concept recall. Medium = comparison, mechanism, short code or simple application. Hard = multi-step reasoning, design with trade-offs, subtle debugging or non-trivial implementation. No target ratio is imposed. Where the blind auditor disagreed with the author, the auditor's rating was adopted except where `curated_v3_config.DIFFICULTY_KEPT` records a reason.

## Environment notes

Reference code in batch 02 and in pilot-01 (except `smi-g0002`, `smi-g0014`, which demonstrate scikit-learn behaviour and are skipped where scikit-learn is missing) uses only the standard library, numpy and pandas and is tested on Python 3.10, 3.11 and 3.13. SQL tests run on whatever SQLite the machine has (auditors also ran them on SQLite 3.37.2 and 3.45.1). `EXPLAIN QUERY PLAN` rows are compared by their first word only.
