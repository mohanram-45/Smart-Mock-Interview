# curated/v2 - Stage 1B interview knowledge base

Derived from `data/curated/v1/` (unchanged). Original raw/interim/processed data, the pipeline and the models are untouched.

| File | Content |
|---|---|
| `curated_questions.csv` / `.json` | **Core set** - every v1 record (strengthened where flagged) plus review-queue items that could be confidently resolved |
| `pilot_batch_01.csv` / `.json` | **Pilot expansion batch** - 41 newly written NLP / Deep Learning / SQL questions. Kept separate; *not* part of the core set until approved |
| `code_tests.json` | Reference solutions and tests (SQL: setup, solution, expected rows; Python: solution + asserts) keyed by record id; re-executed by the validator |
| `review_queue.csv` | Records still not approved (with the reason) |
| `lineage.csv`, `removed_duplicates.csv` | Disposition of all 4,085 original processed records |
| `gap_analysis_v2.md` | Concept-coverage gap analysis after Stage 1B |
| `build_log.csv` | Review fixes applied, deferrals, key-concept revisions |
| `manifest.json` | Counts and SHA-256 of every file |

Key fields: `id` (`smi-NNNN` = raw seed id; `smi-gNNNN` = pilot), `domain`, `topic`, `difficulty` (Easy/Medium/Hard by content), `question`, `answer`,
`key_concepts` (3-8, `; `-separated in the CSV), `source_type` (`seed_curated`, `seed_queue_resolved`, `ai_generated_original`), provenance columns
(`source_file`, `source_record_id`, `source_processed_id`, `plan_id`), `sources` (JSON list; each entry carries its own verification status),
`verification`, `known_limitations`, `review_notes`, `has_code_test`.

`verification` values: `ai_reviewed` (v1, unchanged text), `ai_rewritten+ai_reviewed[+code_executed][+source_opened]`, `ai_generated+ai_reviewed[+code_executed][+source_opened]`.
**No record has had human subject-matter review.** Generated questions are original AI-written items; none is claimed to come from a real interview.

Rebuild: `python audit/remediation/build_curated_v2.py <root> --force`; validate: `python audit/remediation/validate_curated_v2.py <root>`.
