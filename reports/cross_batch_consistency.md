# Cross-batch consistency results (frozen v5 + Batches 1-4)

Script: `audit/expansion/cross_batch_check.py` (raw: `reports/cross_batch_results.json`). Population: 487 v5 + 46 + 48 + 45 + 40 = **666 records**.

| Check | Result |
|---|---|
| ID collisions | **0** |
| Exact duplicate questions / answers | **0 / 0** |
| Semantic duplicates (TF-IDF, question + answer, 1-2 grams) | Highest cosine for any new record against anything else is **0.41** (j0036 vs j0020; both ask about filtered ANN search with different numbers). No pair above 0.55 on questions alone. |
| Contradictory technical answers | 36 highest-overlap pairs (answer TF-IDF) reviewed by an independent agent: **0 major, 0 minor contradictions**. Two pairs share intent: j0020/j0036 (selective-filter ANN search) and j0029/k0017 (90% raw agreement judge validation). Both approved earlier with different scenarios and added content; flagged for curator decision at merge, not changed. |
| Domain classification | Each batch uses one domain: B1, B2 = "Generative AI & RAG"; B3, B4 = "MLOps & Model Deployment". These two domain labels are **new relative to v5** (v5 has Data Analysis, Deep Learning, Machine Learning, NLP, Python, SQL). No misfiled records found by spot check; the RAG evaluator must treat the taxonomy as extended. |
| Metadata | New batches: no missing core fields; `version`=batch-staged, `introduced_in`=v6-batch_NN; difficulty in {Easy, Medium, Hard} everywhere. v5 legacy rows (360 of 487) have empty `question_type` and `common_mistakes` - pre-existing, unchanged. |
| Answer variants vs canonical | For all multi-variant records (`concise+detailed`, `detailed+practical`, `concise+detailed+practical`), `answer == detailed_answer` exactly; `single` records have empty variant columns. 0 inconsistencies. Variant-vs-canonical *content* consistency was covered by the per-record reviews. |
| 13-4 | Remains quarantined (overlaps smi-k0015). |

Limitation: contradiction review is limited to the highest-overlap pairs and cannot find contradictions between topically distant records. Semantic scan ran in the sandbox only; the device lacks sklearn.
