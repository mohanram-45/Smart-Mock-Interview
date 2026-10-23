# data/curated/v5 - frozen knowledge base for the first RAG prototype

**487 records** = 447 (v4 core) + 40 batch-03 records, 19 of which were independently rechecked in this freeze (6 text fixes; 0 quarantined). The Flask/JWT records smi-0457 and smi-0459 are excluded from the six-domain set and preserved in `review_archive.csv`. v1-v4 and all original data are untouched.

## Use this
* `curated_questions.csv/json` - the dataset (one row per record). Retrieval fields: `domain`, `topic`, `difficulty`, `question_type` (empty for the 360 seed records), `question`, `answer`, `key_concepts`, `common_mistakes`, `sources`, `verification`, `v4_verification`, `v5_verification`.
* `manifest.json` - version, counts, verification limitations, **fingerprint** (recomputed by `validate_curated_v5.py`), file hashes.
* `human_review_queue.csv` (every record with a priority tier 1-5) and `unverified_claims.csv` - what still needs a human.

## Other files
`code_tests.json` + `cross_version_results.json` (executed reference solutions; Python 3.10/3.11/3.13, SQL on SQLite), `batch03_recheck.json` + `batch03_v5_corrections.csv` (v5 evidence and every text change), `batch02_verification.json`, `batch03_review.json`, `quarantine.csv` (empty), `review_queue.csv` (empty), `review_archive.csv`, `lineage.csv` (the two archived ids are `ARCHIVED_OUT_OF_SCOPE`), `removed_duplicates.csv`, `gap_analysis_v5.md`, `rag_readiness.json/.md`.

## Honest limits
No record has had human expert review. See `manifest.json -> verification_limitations` and the final report.

## Rebuild / validate
`python audit/remediation/build_curated_v5.py --force`, `python audit/remediation/validate_curated_v5.py`.
