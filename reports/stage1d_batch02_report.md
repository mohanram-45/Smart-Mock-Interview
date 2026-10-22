# Stage 1D - Batch 2 report (Generative AI & RAG part B, 48 records)

Stopped here for your approval; Batch 3 has not been started. The batch is **staged** in `data/expansion/batch_02/` (not merged), v1-v5 and Batch 1 are unchanged, no RAG work, no application code touched. Batch 1 closeout (rev 2) was reported separately; its fingerprint is `6051c667...9efa`.

| | |
|---|---:|
| Generated / **accepted** / **quarantined** | 48 / **48** / **0** (target 42, planned range 27-54) |
| Fingerprint (combined sha256) | `d7162190def12a05a04b8c385037475b250cca64eb3af610ac06fe5135da91e9` |
| Validator | **44 checks, 0 failed** (sandbox, Python 3.13) |

## Coverage, types, difficulty, formats

| Topic (cell) | Records |
|---|---:|
| Tool use and agents (GEN-09) | 7 |
| LLM evaluation (GEN-10) | 7 |
| Serving, latency and cost (GEN-13) | 7 |
| Prompting and structured output (GEN-08) | 6 |
| Fine-tuning vs RAG vs prompting (GEN-11) | 6 |
| Safety, security and privacy (GEN-12) | 6 |
| Hallucination, grounding, long context (GEN-14) | 6 |
| GenAI product scenarios (GEN-15) | 3 |

Types: scenario 14, evaluation 10, design 9, coding 4, business_case 4, concept 4, debugging 3. Difficulty (blind auditors' ratings, not forced): Medium 34, Hard 14, Easy 0. No Easy items again, so warm-up recall questions are still a gap. Answer sets: single 22, detailed+practical 16, concise+detailed 5, all three 5 (54% multi-field). 9 design questions carry rubric points. 0 of 48 questions open with a definitional pattern (limit 35%); median nearest-neighbour similarity 0.09, max to v5 0.21, 0 pairs in 0.70-0.85.

## Review path and major defects

1. Blind review of all 48 (3 independent auditors, source-finding built in): 34 needed corrections, 14 passed. **6 records had a major defect (12.5%)**, under the 25% regenerate rule: 08-1 (JSON mode wrongly said to guarantee types/enums), 09-1 (tool schema called "only a hint" although strict modes exist), 10-7 (30/30 passes called consistent with "a few percent" failure; the Wilson bound allows about 11%), 12-2 (design's own acceptance test contradicted its policy table), 14-1 (unsupported universal claim that models cannot check what they know), 15-1 (rollback rule needed 100 reviewed conversations a day; the described volume gives about 36).
2. Recheck of all 34 corrected records by fresh auditors, plus an independent source verification of every cited page: **3 more major defects, all introduced by first-round fixes** (08-1: "invented date is the only schema-valid way", 11-3: an impossible McNemar table, 15-1: "3 days at 20% traffic"). Fixed (25 changes).
3. Final recheck of the 18 records changed after that: **0 major**, 7 minor fixes, 2 sources dropped as unused (LIMA in 11-1, Greshake in 12-2). `corrections.csv` logs all 83 changes.
4. Quarantine: none. No record has an unresolved material defect.

## Tests

* 4 coding records (08-2 JSON extraction/validation with retry, 10-7 Wilson interval, 13-1 KV-cache size calculator, 13-3 static vs continuous batching simulator). All pass on **Python 3.13.16, 3.10.20 and 3.11.17**; recorded code uses only stdlib and numpy and fenced code equals the tested solution. Auditors ran extra edge cases on all three interpreters.
* Numbers in the other records (McNemar and sign tests, Wilson intervals, rule of three, KV-cache and token arithmetic, roofline, A/B z-scores) were recomputed by at least two reviewers; the authors had already found their own first guesses wrong in 13-1 and the code-derived values replaced them. These are internal evidence (executed/derived), listed separately from sources in each record's `evidence_summary`.
* Skipped: the scikit-learn semantic duplicate scan on the 3.10/3.11 environments (ran on 3.13). Nothing else skipped.

## Source coverage and verification

| | |
|---|---:|
| Records citing a source | **29 of 48 (60%)** |
| Source entries / distinct pages | 44 / 36 (33 papers, 8 official docs, 3 secondary) |
| Fully supporting / partially supporting entries | 40 / 4 |
| Records with a page I opened myself | 12 |

**This is below the blueprint's 70% target.** The 19 records without a source are statistics and arithmetic items (McNemar, Wilson, rule of three, roofline, A/B z-tests), code, and product/process judgement (rollout gates, prompt versioning, cache design) where no authoritative page states what the record says; I did not pad them. Every cited page was opened by the finding auditor and re-opened by a separate verifier or recheck auditor (the verifiers judged 36 of 40 first-pass entries supported and 4 partial, none unsupported); I re-opened Stripe idempotency, OpenAI Structured Outputs, vLLM/PagedAttention, Kadavath et al., OWASP LLM01 and Greshake et al., and they support the sentences as worded (Stripe supports "conflicting requests are not saved and can be retried", not that an error is returned). `independent_reviewer_*` statuses mean AI agents, not me, opened it. Source checks narrowed several sentences (LIMA "output style", model collapse "indiscriminately", P(True) vs P(IK) calibration, Greshake not covering markdown-image exfiltration). 54 claims across the batch remain without a source (`unverified_claims.csv`), all hedged. 8 records that cite vendor documentation are flagged `time_sensitive` with `review_by` 2027-04.

## Remaining limitations

1. No human review of any record; authors, reviewers and I are the same model family.
2. Source coverage 60% (target 70%); GEN-15 (product scenarios) and the statistical evaluation items have no external source.
3. Fixes themselves introduced defects (3 in round two), which is why every corrected record was rechecked again; the 14 records that passed their first blind review have had that one AI review only.
4. Hard-heavy among design/evaluation, no Easy items; GenAI cells were generated by three author agents, so style may cluster per cell.
5. Original-file integrity and device validation: see the message accompanying this report.
