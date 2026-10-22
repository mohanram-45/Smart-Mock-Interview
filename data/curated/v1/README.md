# curated/v1 - Stage 1 curated question set

New, versioned dataset. No original raw/interim/processed file was modified (SHA-256 baseline: `audit/remediation/original_files_sha256.json`).

| File | Content |
|---|---|
| `curated_questions.csv` / `.json` | 316 approved records: id, domain, topic, difficulty, question, answer, key_concepts, provenance, triage_status, modification, known_limitations, verification, version |
| `review_queue.csv` | 46 records NOT approved (35 from triage + 11 moved after factual review), each with reason and what is needed to resolve |
| `removed_duplicates.csv` | 5 duplicates removed, with the version kept |
| `lineage.csv` | Disposition of all 4,085 original processed records |
| `code_checks.json` | Executable checks for the 13 records with Python snippets |
| `manifest.json` | Counts and SHA-256 of every file here |

IDs are `smi-NNNN` where NNNN is the id in `data/raw/questions_seed.csv`.
`verification` is `ai_reviewed` or `ai_reviewed+code_executed`; no human subject-matter reviewer has signed off.

Rebuild: `python audit/remediation/build_curated_v1.py <root> --force`; validate: `python audit/remediation/validate_curated_v1.py <root>`.
