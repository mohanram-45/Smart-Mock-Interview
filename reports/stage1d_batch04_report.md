> **SUPERSEDED (2026-10-11):** this is the revision-1 report. Batch 4 is now revision 2 (fingerprint `360c00635d32dd2d91d4f193aa93c415c3947fbd9e002dce23edd2982db99b99`) after checkpoint verification. See `reports/stage1d_batch04_final_verification.md` and `reports/stage1d_checkpoint_report.md`. Figures below (fingerprint, difficulty 26/13/1, 14-6 net +85,700) are revision 1 and are no longer current.

# Stage 1D - Batch 4 report (MLOps & Model Deployment, part B, 40 records)

Stopped here for your approval; Batch 5 has not been started. The batch is **staged** in `data/expansion/batch_04/` (not merged into v6). v1-v5, the original files and Batches 1-3 are unchanged, no RAG work, no application code touched.

| | |
|---|---:|
| Drafted / **accepted** / **quarantined** | 41 / **40** / **1** (target 35-45) |
| Fingerprint (combined sha256) | `4e818e213ece1799fa9960ab56010e45792275e73deb38a298dfbae1999405d0` |
| Validator | **45 checks, 0 failed** (sandbox, Python 3.13); Batches 1-3 re-validated with the same validator, 45/45 each, fingerprints unchanged |
| Duplicates | 0 exact; max question similarity to v5 + Batches 1-3 is 0.23 (word level); max 5-gram answer Jaccard under 0.25 |

## Coverage, types, difficulty, formats

| Topic (cell) | Records |
|---|---:|
| Reliability, incidents, rollback/recovery, performance and cost (MLO-12) | 9 |
| Production monitoring and drift operations (MLO-08) | 8 |
| Case studies: canary/shadow/A-B and online/offline consistency incidents (MLO-14) | 6 |
| Retraining and automation (MLO-09) | 5 |
| Security, governance, lineage, compliance (MLO-11) | 5 |
| Data and model validation (MLO-10) | 4 |
| LLMOps (MLO-13) | 3 |

Types: scenario 12, design 8, debugging 7, evaluation 4, coding 3, concept 3, business_case 3. Difficulty (blind auditor ratings, not forced): Medium 26, Hard 13, Easy 1 (continuous training vs CI/CD). 11 author labels changed. Answer sets: detailed+practical 18, single 14, concise+detailed 6, all three 2.

MLOps now has 85 staged records (Batch 3 + 4) on top of the v5 baseline. Your priority list maps like this: drift and monitoring (8), incident diagnosis and rollback/recovery (cells 12 and 14), canary/shadow/A-B diagnosis (14-1 to 14-3), online/offline consistency (14-5, plus 10-2 on point-in-time leakage), cost and scaling (12-8, 12-9, 13-3), security and governance (5 records). Easy items are thin again (1); I did not force them.

## Defects and corrections

1. **Blind review of all 41** (3 auditors): 29 needed corrections, 11 passed, 1 passed but was an intent duplicate. **6 records had a major defect (14.6%)**, under the 25% regenerate rule: 08-1 (PSI returned 0 for a constant reference, i.e. no drift for the most extreme shift), 10-1 (integer truncation made the directional test miss a wrong-sign model), 08-8 (a pooled 7-day baseline does not remove weekend false alarms), 11-1 (no "what it does not protect against" for three of five controls), 14-4 (inverse-propensity weighting stated without the logged-propensity condition), 14-5 (a tolerance on windowed counts would hide the off-by-one incident the check exists to catch).
2. **Recheck of all 29 corrected records** plus source verification of every citation: **5 major defects, all in first-round-fixed text**: 11-5 (label-only attacks overstated as needing hundreds of queries), 14-4 (plan sentence contradicted the requested order), 12-7 (impact baseline overlapped the bad period), 13-3 (concise answer 83 words), 14-5 (lateness rule did not work for a trailing as-of count). All fixed.
3. **Final recheck of 18 records** (every record changed after round two, plus every record that ever had a major defect): 13 corrected with minor fixes, 5 passed, **1 major**: 14-6 (a "much higher variance" claim contradicted the record's own sensitivity table). The auditor supplied the fix.
4. **Not independently rechecked after that:** 14-6 got the final fix, and I also corrected its 4-incident net from +85,800 to +85,700 (rounding consistency with the 154,300 figure) after recomputing every number myself; 14-6 and 11-1 each lost a sentence or two to meet the 450-word limit (no claim changed). These edits are logged as `lead` in `corrections.csv` and in the backlog. Treat 14-6 as the least-reviewed record.
5. **Quarantine:** 13-4 (prompt-regression gate sizing), technically correct but the same scenario and intent as Batch 2's smi-k0015. It is listed in `quarantine.csv`; reinstating it is your call. No record has an unresolved factual defect.
6. `corrections.csv` logs 130 entries across rounds 1, 2, final and lead edits.

## Tests and configuration validation

* **Code:** 6 records with executed code (08-1 PSI, 10-1 behavioural tests, 10-2 and 14-5 SQL, 11-1 artifact-integrity check, 12-8 cost model). All pass on **Python 3.13.16, 3.10.20 and 3.11.17**; the fenced Python equals the tested solution. 08-1 and 10-1 were patched during recheck and re-run on all three interpreters.
* **SQL:** both queries (10-2 point-in-time leakage audit, 14-5 served-vs-recomputed consistency check) ran against in-memory SQLite (3.45.1) with fixtures; the SQL text in `configs.json` appears verbatim in the executed solution. SQLite dialect only.
* **YAML / Dockerfile:** **this batch contains none**, so there was nothing to validate. I built `audit/expansion/config_check.py` anyway: PyYAML parse, offline Kubernetes schema validation (kubernetes-validate, strict, k8s 1.31) for complete objects, dockerfile-parse plus an instruction whitelist for Dockerfiles; no Docker daemon is available, so nothing is ever built. Run on Batch 3's five snippets: all five parse, but four are YAML fragments (syntax only, no schema check) and one is a Dockerfile (syntax only, never built). They stay in the backlog as unexecuted.
* Validator changes: duplicate checks cover v5 and all lower-numbered batches (already added for Batch 3), SQL fences are allowed when they match `configs.json` and the tested code, and the import allowlist gained sqlite3, hashlib, hmac, tempfile and os (11-1's test writes to a temporary directory).
* Numbers (PSI noise floors, KS vs PSI at scale, sample-ratio and power arithmetic, memory-growth and cost figures, expected-value tables) were recomputed by at least two auditors.

## Source coverage and verification

| | |
|---|---:|
| Records citing a source | **35 of 40 (88%)** (target 70%) |
| Source entries / distinct pages | 59 / 35 |
| Fully supporting / partially supporting entries | 55 / 4 |
| Records with a page I opened myself | 13 |

The 5 uncited records: 08-5, 08-8, 09-5, 10-2 and 12-8 (derivations, simulations and executed code). 27 records carry 31 claims that rest on background knowledge only (hedged in text; listed in `unverified_claims.csv`). Source verifiers re-opened every URL: 0 unsupported or unreachable; 7 entries were narrowed (for example PSI cut-offs are conventions attributed to Lewis, not derived; ML Test Score contains no prediction-distribution test). A wrong OWASP URL was caught and replaced; three padding or unused sources were dropped (an OpenAI deprecations page, a Rules of ML entry on 12-6, an arXiv paper on 08-4) and one abstract link was replaced with the PDF that holds the claim. Pages that curl could not fetch (Google-hosted PDFs, GDPR text) were read via WebFetch or left unsourced. No fetched page contained instructions aimed at an AI.

## Updated consolidated verification backlog

`reports/verification_backlog.md` / `.csv` (built by `audit/expansion/build_backlog.py`): **290 open items** across Batches 1-4 (1 high, 55 medium, 234 low). Batch 3 follow-up as requested: its 5 unexecuted YAML/Dockerfile snippets are listed with their parse results, and its 37 unsupported (background-only) claims, including the autoscaler scale-down advice, circuit-breaker claim and the Feast/registry TTL sentence, are itemised. Categories: unsupported claims, unexecuted configs, partial sources, time-sensitive records, records with neither source nor test, known minor gaps, and one global item (no human review). Batch 3 files were not modified.

## Remaining limitations

1. No human review; authors, reviewers and I are the same model family. The 11 records that passed their first review have had only that one review.
2. 14-6 (and the small trims in 11-1) were edited after the last independent check.
3. First-round fixes introduced 5 major defects and a recheck round introduced one more, so the correction process itself is a risk; the pattern now holds across four batches.
4. Only 2 records flagged time-sensitive (13-1, 13-3, review by 2027-04); LLMOps provider behaviour and tool docs may drift.
5. Only 3 LLMOps records after the quarantine, 1 Easy question, and no Kubernetes/Docker configuration at all, so config validation was exercised only on Batch 3.
6. Security/governance answers are engineering controls, not legal advice; the GDPR pseudonymisation claim in 11-2 is unsourced.
7. Original-file integrity and the device validator run: see the message accompanying this report.
