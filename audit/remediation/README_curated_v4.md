# data/curated/v4 - final consolidated knowledge base for the first RAG prototype

**Core = 447 records** (360 v2 core + 41 audited pilot-01 + 46 batch-02 questions re-verified in this stage). **Batch 03 = 40 records, kept separate** until you approve them (`pilot_batch_03.csv/json`). Quarantine is empty. v1, v2, v3 and all original data are untouched (hash-checked against their manifests).

## Files
* `curated_questions.csv/json` - the 447 core records. Same columns as v3 plus `v4_verification`, `evidence_summary`, `remaining_limitations`.
* `pilot_batch_03.csv/json` - 40 new records (ids `smi-i0001`-`smi-i0040`: ML 10, SQL 10, Python 10, Data Analysis 10). Not part of the core.
* `batch02_verification.json` - evidence for the 26 re-verified batch-02 records (claim, method, evidence, remaining limitations).
* `batch02_corrections.csv` - every field changed in batch 02 between v3 and v4.
* `batch03_review.json` - independent review of every batch-03 record (verdict, issues, difficulty, code and source findings).
* `code_tests.json` (146 executable reference solutions), `cross_version_results.json` (Python 3.10 / 3.11 / 3.13 results).
* `gap_analysis_v4.md`, `rag_readiness.json/.md` (measurements; the verdict is in `reports/stage1b_final_report.md`).
* `lineage.csv`, `removed_duplicates.csv`, `review_queue.csv`, `quarantine.csv`, `manifest.json`.

## Id scheme
`smi-NNNN` seed-derived, `smi-gNNNN` pilot 01, `smi-hNNNN` batch 02, `smi-iNNNN` batch 03. Ids never change between versions.

## `v4_verification`
`reverified_v4_verified` / `reverified_v4_corrected` = independently re-checked in v4 with recorded evidence; `independent_review_v3_only` = batch-02 record not re-verified in v4 (relies on the v3 independent review); empty = the 401 v3 core records (unchanged).

## Honest limits
No record has had human expert review. Verification labels read `ai_generated+ai_reviewed[+code_executed][+source_opened]`. Some literature claims are hedged and unsourced (see `remaining_limitations`). Seed records (360) have no `question_type`.

## Regenerate / validate
`python audit/remediation/build_curated_v4.py --force` (needs the v3 data and `stage1b4/` evidence), `python audit/remediation/validate_curated_v4.py`.
