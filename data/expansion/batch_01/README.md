# Stage 1D - Batch 1 (Generative AI & RAG, 46 records) - STAGED

Not merged into any curated version (v6 is built only after batch 6). Ids `smi-j0001..smi-j0046`, in plan order. v1-v5 are untouched.
Files: `batch_01_accepted.csv/json` (v5 columns + `concise_answer, detailed_answer, practical_answer, answer_set, rubric_points, related_domains, tags, time_sensitive, review_by, v6_verification`; for multi-field sets `answer` = `detailed_answer`), `code_tests.json`, `quarantine.csv` (empty), `corrections.csv` (69 text/metadata changes, two rounds), `unverified_claims.csv` (claims backed by background knowledge only), `work/` (reviews, rechecks, corrected records, lead source list, test runs), `manifest.json` (fingerprint).
Verification: AI-generated, blind AI review, AI recheck of every corrected record, code executed on Python 3.10/3.11/3.13. No human review.
Validate: `python -B audit/expansion/validate_batch.py data/expansion/batch_01`
