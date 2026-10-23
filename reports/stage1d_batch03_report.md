# Stage 1D - Batch 3 report (MLOps & Model Deployment, part A, 45 records)

Stopped here for your approval; Batch 4 has not been started. The batch is **staged** in `data/expansion/batch_03/` (not merged). v1-v5 and Batches 1-2 are unchanged, no RAG work, no application code touched.

| | |
|---|---:|
| Generated / **accepted** / **quarantined** | 45 / **45** / **0** (target 40-50) |
| Fingerprint (combined sha256) | `72911aaa33bb82d7beaf07a53960e0e4691c07d551918d76c9cc35f21d210688` |
| Validator | **44 checks, 0 failed** (sandbox, Python 3.13; device run reported separately) |
| Duplicates | 0 exact; max question similarity to v5 + Batches 1-2 well under 0.85 (max 0.22 word-level); max 5-gram answer Jaccard under 0.25 |

## Coverage, types, difficulty, formats

| Topic (cell) | Records |
|---|---:|
| Lifecycle, reproducibility, experiment tracking, data/model versioning (MLO-01) | 7 |
| CI/CD for ML plus data and model validation (MLO-02) | 8 |
| Serving patterns plus serving-layer monitoring fundamentals (MLO-04) | 7 |
| Deployment strategies: shadow, canary, A/B, blue-green, rollback (MLO-05) | 6 |
| Containers, orchestration, ML pipelines (MLO-06) | 6 |
| Feature stores and training-serving skew (MLO-07) | 6 |
| Model registry and packaging (MLO-03) | 5 |

Types: scenario 10, debugging 9, design 9, concept 7, coding 5, evaluation 4, business_case 1. Difficulty (blind auditors' ratings, 12 labels changed from the author's): Medium 31, Hard 12, Easy 2. Answer sets: detailed+practical 23, single 10, concise+detailed 8, all three 4. Only 2 Easy items, so warm-up recall is thin; I did not force a ratio. Drift monitoring and retraining are deliberately left for Batch 4.

## Review path and major defects

1. Blind review of all 45 (3 independent auditors): 32 corrected, 13 passed. **8 records had a major defect (17.8%)**, under the 25% regenerate rule: 02-2, 02-4, 02-5, 03-3, 04-4, 05-4, 06-2, 06-3.
2. Recheck of all 32 corrected records by fresh auditors, plus source verification of every cited page: **3 more major defects, all introduced by first-round fixes**: 03-4 (the answer listed extra columns as rejected by MLflow schema enforcement, but they are ignored with a warning), 05-3 (sample-size and power arithmetic labelled with the wrong formula), 06-3 (the probe design only holds if loading blocks the liveness endpoint).
3. Final recheck of the 21 records changed after that (including all three above): **0 major**, 8 minor fixes applied. 03-4, 05-3 and 06-3 each got an extra suspicious pass; the 05-3 numbers were recomputed with both formulas.
4. Quarantine: none. `corrections.csv` logs all 98 changes (58 round 1, 32 round 2, 8 final).

## Tests

* 6 coding records (01-4 float32 order and per-worker seeding, 02-2, 02-4 promotion gate with slice checks, 04-3 batching simulation, 07-2, 07-6). All pass on **Python 3.13.16, 3.10.20 and 3.11.17**; the fenced code in each answer equals the tested solution. Stdlib + numpy only, no network, no timing. The final auditor also ran extra edge cases for 02-4 and 04-3 on all three interpreters.
* Numbers in the other records (power and sample size, SRM, p95 and serialization sizes, memory budgets, probe timing, skew probabilities) were recomputed by at least two reviewers.
* **Not executed:** five records (06-1 to 06-5) carry YAML/Dockerfile snippets. These are configuration examples checked against documentation by reviewers, not applied to a real cluster or build. The validator exempts yaml/dockerfile/shell fences from the "fence equals tested solution" rule; I changed it to do that.
* The validator now compares duplicates against v5 **and all lower-numbered batches**. Batches 1 and 2 were re-validated with it and still pass with unchanged fingerprints.

## Source coverage and verification

| | |
|---|---:|
| Records citing a source | **38 of 45 (84%)** (target 70%) |
| Source entries / distinct pages | 74 / 51 |
| Fully supporting / partially supporting entries | 68 / 6 (approx.; partials are narrowed to what the page says) |
| Records with a page I opened myself | 9 |

The 7 records without a source: 02-2 and 04-3 are coded and rest on executed tests; 01-2, 01-3, 01-7 and 04-1 are conceptual or judgement items; 07-5 lost its only source. `unverified_claims.csv` lists 37 claims across 30 records that rest on background knowledge only and are hedged in the text.

Source notes:
* Executed or derived evidence is kept separate from external sources in `evidence_summary`.
* Three padding sources were dropped (ML Test Score from 02-2 and 02-8, the Feast point-in-time page from 07-5), which is why 07-5 is uncited.
* Kubernetes claims were checked against the kubernetes/website GitHub markdown when rendered pages were truncated. Feast's docs site was blocked from the agent shell and was read through WebFetch.
* MLflow behaviour (03-4 extra columns ignored with a warning, float-to-int rejection) was verified in the MLflow source (`_enforce_schema`) plus the signatures docs, not docs alone; the 03-3 skl2onnx float32 flips by executed runs plus docs.
* **Prompt-injection note:** one source verifier reported that a fetched Feast docs page contained text addressed to AI agents asking for an HTTP GET. It was ignored and nothing was fetched on its behalf.

## Remaining limitations

1. No human review of any record; authors, reviewers and I are the same model family.
2. The 13 records that passed their first blind review have had only that one AI review.
3. First-round fixes introduced 3 major defects, so the corrected records' quality depends on the later rechecks, which found 0 major.
4. Version-sensitive claims (MLflow, PyTorch determinism, Kubernetes gang scheduling, Feast) are flagged `time_sensitive` for 6 records with `review_by` 2027-04.
5. Only 2 Easy items, 1 business_case; MLO cells were written by three author agents, so style may cluster per cell.
6. 04-4 autoscaler scale-down advice and 04-5 circuit-breaker claim remain unsourced; 07-5's TTL sentence is hedged as store-dependent.
7. Minor non-blocking gaps noted by the final auditors: 01-5's rubric mentions retention that the answers do not discuss; 03-5's interview note says "atomic" without the registry-dependent hedge.
8. Original-file integrity and the device validator run: see the message accompanying this report.
