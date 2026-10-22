# RAG-readiness measurements - v5 core

Records measured: 487. Measurements only; the verdict and its reasoning are in `reports/stage1c_freeze_report.md`.

| Domain | Records | Topics | Topics < 3 records | Checklist concepts >= 2 questions | median answer words | answers < 30 words |
|---|---:|---:|---:|---:|---:|---:|
| Data Analysis | 75 | 7 | 1 | 13/15 | 192 | 0 |
| Deep Learning | 86 | 18 | 10 | 17/20 | 116 | 1 |
| Machine Learning | 174 | 21 | 5 | 18/24 | 108 | 5 |
| NLP | 53 | 16 | 8 | 15/17 | 193 | 0 |
| Python | 45 | 11 | 2 | 14/16 | 193 | 1 |
| SQL | 54 | 13 | 4 | 14/15 | 202 | 0 |

* Metadata present: domain 100.0%, topic 100.0%, difficulty 100.0%, key_concepts 100.0%, source_type 100.0%, verification 100.0%, question_type 26.1%, plan_id 26.1%, sources 7.2%
* Estimated chunk size (question+answer+concepts): median 243 tokens, p90 590, max 1124
* Key concepts: 2079 distinct, 90.1% pass the token-grounding heuristic
* Duplicates: exact questions 0, exact answers 0; question pairs >= 0.85: 0; answer pairs >= 0.90: 0
* Lexical self-retrieval baseline (question -> own answer): top-1 0.682, top-5 0.869, MRR 0.767
* Verification: human-reviewed 0; code executed on 147; source opened on 35
