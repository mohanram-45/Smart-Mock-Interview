# RAG-readiness measurements - v4 core

Records measured: 447. Measurements only; the verdict and its reasoning are in `reports/stage1b_final_report.md`.

| Domain | Records | Topics | Topics < 3 records | Checklist concepts >= 2 questions | median answer words | answers < 30 words |
|---|---:|---:|---:|---:|---:|---:|
| Data Analysis | 65 | 7 | 1 | 12/15 | 165 | 0 |
| Deep Learning | 86 | 18 | 10 | 17/20 | 116 | 1 |
| Machine Learning | 164 | 17 | 1 | 16/24 | 83 | 5 |
| NLP | 53 | 16 | 8 | 15/17 | 193 | 0 |
| Python | 35 | 8 | 2 | 12/16 | 145 | 1 |
| SQL | 44 | 13 | 5 | 13/15 | 177 | 0 |

* Metadata present: domain 100.0%, topic 100.0%, difficulty 100.0%, key_concepts 100.0%, source_type 100.0%, verification 100.0%, question_type 19.5%, plan_id 19.5%, sources 3.6%
* Estimated chunk size (question+answer+concepts): median 232 tokens, p90 564, max 1124
* Key concepts: 1861 distinct, 90.7% pass the token-grounding heuristic
* Duplicates: exact questions 0, exact answers 0; question pairs >= 0.85: 0; answer pairs >= 0.90: 0
* Lexical self-retrieval baseline (question -> own answer): top-1 0.66, top-5 0.857, MRR 0.751
* Verification: human-reviewed 0; code executed on 131; source opened on 16
