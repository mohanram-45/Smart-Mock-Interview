# Stage 1D - Batch 4 final verification (MLOps part B), revision 2

Date 2026-10-11. Batch 4 revision 2 fingerprint `360c00635d32dd2d91d4f193aa93c415c3947fbd9e002dce23edd2982db99b99` (revision 1, `4e818e21...`, archived in `data/expansion/batch_04/archive_rev1/`). 40 accepted, 1 quarantined (13-4). **Not merged into v6.**

## What was verified, and how

* **Risk-based fresh-auditor rounds (fv, fv2, fv3).** Round fv re-audited all 40 records with an auditor that had not seen earlier reviews (priority: every record that ever had a major defect, 14-6, math/code records, security/governance/GDPR records). Exact-substring fixes were applied and rubric points added. Round fv2 re-audited 30 records; round fv3 re-audited 17 records (changed or previously flagged ones). **fv3 found no major defects**, which ended the loop. Lesson recorded: fixes introduced new defects in earlier rounds, so every changed record was re-reviewed by a reviewer who had not written the fix.
* **14-6** (whose last edits were never independently checked in revision 1) was re-audited in fv, fixed (2% now read as a loss rate while the incident lasts, with the alternative reading, about 445,700 saving, stated; saving about 51,440 per incident; 4-incident net +85,800; 438 words) and rechecked in fv2/fv3. I recomputed the arithmetic myself; my own earlier manual edit (85,700) had been wrong and was reverted.
* **11-2 GDPR claim.** Now sourced to EUR-Lex GDPR Recital 26 and the ICO pseudonymisation guidance, both opened by me. The operative articles (EUR-Lex) could not be read, so none is cited; the erasure sentence is hedged ("where they apply... depends on jurisdiction and legal advice"). Residual limitation: no legal review.
* **Other substantive fixes found by the extra rounds:** 10-1 (view/copy bug in code, tests extended), 12-8 (assumed traffic profile stated; "saves 36 units" corrected), 12-9 (question_type design with rubric), 09-4 (warm-start backtest wording), 11-3 (memorisation drivers), 11-5 (DP/noise and concise mitigations), 12-7 (shadow model has no clicks), 14-5 (non-numeric-value caveat), 09-3 (defence-in-depth framing).
* **Executed tests re-run today (25 Python tests across Batches 1-4, `reports/code_test_rerun.json`):** all pass on Python 3.13.16, 3.10.20 and 3.11.17. Batch 4 has 6 code records (08-1, 10-1, 10-2, 11-1, 12-8, 14-5); 10-2 and 14-5 are SQL, executed on in-memory SQLite 3.45.1 and matched verbatim to `configs.json` (`reports/config_check_batch04.json`, 2 blocks, 0 failed). Batch 4 contains no YAML or Dockerfile.
* **Sources:** 35 of 40 records cite a source (66 entries, 42 distinct URLs); 33 are fully supporting, 13 were opened by the lead; 5 uncited records are executed or derived. Nothing was cited that was not opened by a verifier.
* **Validator:** `validate_batch.py` 45/45 PASS for Batches 1-4 in the sandbox (Python 3.13, with sklearn semantic scan). Original-file regression, v1-v5 manifests, v5 fingerprint and per-batch fingerprints all pass.

## Distribution (Batch 4)
Difficulty: Medium 28, Hard 11, Easy 1. Types: scenario 11, design 9, debugging 7, evaluation 4, coding 3, concept 3, business_case 3. Time-sensitive: 13-1 and 13-3 (review_by 2027-04).

## Quality gate decision
No known correctness defect remains in the 40 records. Remaining items are hedged derived/illustrative claims (19 records carry background-only residual claims, see `unverified_claims.csv`) and the absence of human review. **Batch 4 passes the final gates and is marked approved for a future curated merge (registry: `data/expansion/approved_batches.json`).** 13-4 stays quarantined as an intent duplicate of smi-k0015.

## Limits of this verification
All authors, reviewers and the lead are the same model family; no human has reviewed any record. Fresh-auditor rounds reduce, but do not remove, shared blind spots. Three Python versions and SQLite were tested; no Docker, Kubernetes cluster or cloud service was used. Skipped here: device-side semantic scan (no sklearn on the device; done in the sandbox instead).
