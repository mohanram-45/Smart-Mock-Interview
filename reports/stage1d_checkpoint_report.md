# Frozen expansion checkpoint report (2026-10-11)

Nothing is merged into v6. v1-v5 and the 22 original files are unchanged; Batches 1-3 are unchanged since approval; Batch 4 is revision 2. Registry: `data/expansion/approved_batches.json`.

## Record counts
| | Records |
|---|---:|
| Frozen v5 (fingerprint `9eb94d8f...7123`) | **487** |
| Batch 1 - Generative AI & RAG A (approved) | 46 |
| Batch 2 - Generative AI & RAG B (approved) | 48 |
| Batch 3 - MLOps A (approved) | 45 |
| Batch 4 - MLOps B (approved at this checkpoint, rev 2) | 40 |
| **Accepted candidates (B1-B4)** | **179** |
| Combined if later merged | 666 |
| Quarantined | 1 (B4-MLO-13-4, intent duplicate of smi-k0015) |

## Coverage (v5 + B1-B4)
| Domain | v5 | B1 | B2 | B3 | B4 | All |
|---|---:|---:|---:|---:|---:|---:|
| Machine Learning | 174 | | | | | 174 |
| Deep Learning | 86 | | | | | 86 |
| Generative AI & RAG | | 46 | 48 | | | 94 |
| MLOps & Model Deployment | | | | 45 | 40 | 85 |
| Data Analysis | 75 | | | | | 75 |
| SQL | 54 | | | | | 54 |
| NLP | 53 | | | | | 53 |
| Python | 45 | | | | | 45 |

| Difficulty | v5 | B1 | B2 | B3 | B4 | All |
|---|---:|---:|---:|---:|---:|---:|
| Easy | 121 | 1 | 0 | 2 | 1 | 125 |
| Medium | 313 | 29 | 34 | 31 | 28 | 435 |
| Hard | 53 | 16 | 14 | 12 | 11 | 106 |

Note: the new batches are Medium/Hard heavy (Easy 4 of 179); the Easy tier of the new domains is thin.

## Verification status (AI-only)
| Batch | Fingerprint (sha256, first 16) | Validator (sandbox) | Executed code tests | Records citing a source |
|---|---|---|---|---|
| 1 | 6051c6675e756cc1 | 45/45 | 9 | 38/46 |
| 2 | d7162190def12a05 | 45/45 | 4 | 29/48 |
| 3 | 72911aaa33bb82d7 | 45/45 | 6 | 38/45 |
| 4 | 360c00635d32dd2d | 45/45 | 6 | 35/40 |

* All 25 Python tests re-run on 3.13.16, 3.10.20 and 3.11.17: all pass (`reports/code_test_rerun.json`). SQL runs on SQLite 3.45.1.
* Config validation: Batch 3 has 4 YAML fragments (schema-valid for Kubernetes 1.31 when wrapped in a Deployment, never applied) and 1 Dockerfile (syntax-parsed, never built). Batch 4: no YAML/Dockerfile.
* Cross-batch: 0 ID collisions, 0 exact or semantic duplicates, 0 contradictions in 36 high-overlap pairs (`reports/cross_batch_consistency.md`).
* Skipped / not done: Docker build, Kubernetes apply, cloud services, any human review, semantic scan on the device (no sklearn; run in sandbox).

## Remaining verification risks (`reports/verification_backlog.csv`, 282 items)
| Priority | Items | What they are |
|---|---:|---|
| High | 1 | No human review of any v6 candidate; authors, reviewers and lead are the same model family. Cannot be resolved by me. |
| Medium | 54 | 0 confirmed defects. 32 hedged/derived/illustrative claims, 17 time-sensitive re-verification dates, 5 unexecuted Batch 3 configs. |
| Low | 227 | Background-only claims, partial-source citations, minor observations. |

## Outstanding human-review limitations
1. No record has been reviewed by a human; "reviewed" everywhere means AI review. Highest value targets for a human: the 17 time-sensitive records (re-check by `review_by`), the Batch 3 YAML/Dockerfile examples, 11-2 (GDPR - legal review), and 14-6 / 12-8 (assumption-laden cost arithmetic).
2. HPA scale-down stabilisation (smi-l0024) and object-store atomic-rename (smi-l0039) claims remain background knowledge, hedged in text; one official page could not be read in full.
3. Two topic-overlap pairs (j0020/j0036, j0029/k0017) are left for the curator at merge.
4. New domains "Generative AI & RAG" and "MLOps & Model Deployment" are not in v5's taxonomy.

**Verdict: PASS WITH LIMITATIONS - READY FOR RAG PROTOTYPE.**
