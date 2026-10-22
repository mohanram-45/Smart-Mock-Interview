# Stage 2 RAG technical handoff (no embeddings/FAISS/LLM evaluation implemented)

## 1. Datasets and schemas
| Set | Path | Rows |
|---|---|---:|
| Frozen v5 core | `data/curated/v5/curated_questions.csv` (+ `.json`, `manifest.json`) | 487 |
| Batch 1-4 candidates | `data/expansion/batch_0N/batch_0N_accepted.csv` (+ `.json`, `manifest.json`) | 46/48/45/40 |
| Approval registry | `data/expansion/approved_batches.json` | - |
| Quarantine | `data/expansion/batch_0N/quarantine.csv` (only B4 non-empty: 13-4) | - |

v5 columns (37) are `id, domain, topic, difficulty, question_type, question, answer, key_concepts, common_mistakes, source_*..., verification, version, introduced_in, audit_*, v5_*`. Batch files carry the same 37 columns **in the same order** plus ten appended: `concise_answer, detailed_answer, practical_answer, answer_set, rubric_points, related_domains, tags, time_sensitive, review_by, v6_verification`. Read CSVs with `keep_default_na=False, dtype=str`. `common_mistakes` and `sources` are JSON-list strings; the 360 legacy v5 rows (`smi-NNNN`) have empty `question_type` and `common_mistakes` - parse defensively. Per-batch side files: `code_tests.json` (executed code), `configs.json` (SQL), `unverified_claims.csv`, `corrections.csv`.

## 2. Canonical vs alternative answers
* `answer` is the canonical reference answer; use it as the grading reference. For multi-variant records `answer == detailed_answer` exactly (verified for all 179).
* `answer_set` tells which variant columns exist: `single` (variants empty), `concise+detailed`, `detailed+practical`, `concise+detailed+practical` (counts across B1-B4: 56 / 30 / 77 / 16).
* `concise_answer` (<=80 words) = spoken-interview style; `practical_answer` = implementation-oriented (may contain code or config fences, some never executed); `rubric_points` (design questions) = checklist for scoring open answers. Variants never contradict `answer` (reviewed); do not use them as independent ground truth.

## 3. Stable IDs and provenance
* IDs are permanent: v5 `smi-NNNN` (360), `smi-hNNNN`, `smi-gNNNN`, `smi-iNNNN`; batches `smi-j####` (B1), `smi-k####` (B2), `smi-l####` (B3), `smi-m####` (B4). No collisions across the 666. Never renumber; a revised record keeps its ID and changes `v6_verification`/fingerprint.
* `plan_id` (e.g. `B4-MLO-14-6`) links to `data/expansion/plan/`; `introduced_in` = `v6-batch_NN`; `version` = `batch-staged`; `sources` lists cited URLs with quotes; `corrections.csv` logs each text change.
* Batch fingerprints: B1 `6051c667...`, B2 `d7162190...`, B3 `72911aaa...`, B4 rev2 `360c0063...` (full values in the registry). Re-hash before indexing to detect drift.

## 4. What to embed
* Retrieval document per record: `question` + `answer` + `key_concepts` (v5 baseline median ~243 tokens). Index `detailed_answer`/`practical_answer` as separate chunks only if you need finer recall, keyed `id#detailed` / `id#practical`, and always map back to `id`.
* Metadata to store with each vector, not embed: `id, domain, topic, difficulty, question_type, introduced_in, answer_set, time_sensitive, review_by, verification, v6_verification, has_code_test`.
* Do not embed `review_notes`, `audit_*`, `corrections.csv` or `unverified_claims.csv`.

## 5. Adding batches later without breaking indexes
* Treat v5 as index generation 0 (487 vectors, ids unchanged). Add each approved batch as an **append-only** segment keyed by batch name and fingerprint; never edit or reorder existing rows. Use ID as the vector key so incremental adds are upserts.
* Gate every merge on `approved_batches.json` (status and fingerprint match) and on the batch validator passing. Run the curator decision on the two overlap pairs before a v6 merge.
* If a batch is revised (as B4 was), delete and rebuild only that segment using its fingerprint.
* Domain filters must accept the two new domain labels; do not assume the v5 six-domain list.

## 6. Flags the RAG evaluator must respect
* **No human review anywhere**: `verification` always contains `ai_reviewed`; never report accuracy as human-validated.
* `time_sensitive == yes` (17 records) with `review_by`: exclude from fixed regression scoring after that date or re-verify first.
* `verification` containing `code_executed` or `source_opened` identifies stronger records; absence means reasoning-only.
* Backlog (`reports/verification_backlog.csv`): records with unexecuted configs (smi-l0034..l0038), unsupported-claim items and partial sources should be reported separately, not silently pooled.
* Quarantined B4-MLO-13-4 must not be indexed. Hypothetical figures in scenarios are illustrative; do not treat as benchmarks.
* Retrieval evaluation caveat from v5: lexical self-retrieval baseline top-1 0.682, top-5 0.869 (questions are not a held-out set); use paraphrased queries for real evaluation.
