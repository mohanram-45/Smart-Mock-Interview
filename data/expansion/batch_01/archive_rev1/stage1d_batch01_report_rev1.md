# Stage 1D - Batch 1 report (Generative AI & RAG, 46 records)

Stopped here for your approval. Batch 2 has not been started. v1-v5, the originals, models and application code are unchanged (hash-checked), and there is no RAG work. The batch is **staged** in `data/expansion/batch_01/` and is not merged into any curated version.

## 1. Accepted and quarantined

| | |
|---|---:|
| Generated drafts | 46 (7 cells; blueprint target 40 accepted) |
| **Accepted** | **46** (`smi-j0001` to `smi-j0046`) |
| **Quarantined** | **0** |
| Batch fingerprint (combined sha256) | `86b22d4e80379f42b50c2fec51b572de0f6b9f4712ff7bbb93733ac27446e027` |

I kept all 46 valid records instead of trimming to 40, so the batch is 6 over its target. The ceiling of 1,150 is not at risk, but say if you want the surplus held back.

Review path: every record got a blind review by an agent that had not seen the draft's difficulty, confidence or authoring notes. 24 needed corrections and 22 passed. Every corrected record then got a second, fresh auditor; that recheck found 12 more fixes needed (3 of them major, all introduced by first-round corrections), which I applied. 69 changes are logged in `corrections.csv`.

## 2. Domain and topic coverage (all Generative AI & RAG)

| Topic | Records |
|---|---:|
| Retrieval strategies (dense, BM25, hybrid, RRF, query rewriting, MMR) | 8 |
| RAG evaluation (recall@k, MRR, nDCG, faithfulness, golden sets, LLM judges) | 8 |
| Embeddings and similarity search (metrics, normalisation, ANN) | 7 |
| Chunking and document ingestion | 6 |
| Reranking and context assembly | 6 |
| Vector databases and index operations | 6 |
| RAG failure diagnosis | 5 |

Only one domain is covered so far (the other 11 start in later batches), and the next 5 batches fill in the rest of the GenAI cells.

## 3. Question types and difficulty (not forced)

| Type | Easy | Medium | Hard | Total |
|---|---:|---:|---:|---:|
| scenario | 0 | 9 | 3 | 12 |
| debugging | 0 | 3 | 6 | 9 |
| design | 0 | 2 | 6 | 8 |
| coding | 0 | 6 | 0 | 6 |
| evaluation | 0 | 5 | 1 | 6 |
| concept | 1 | 4 | 0 | 5 |
| **Total** | **1** | **29** | **16** | **46** |

Blind auditors changed 7 difficulty labels and I adopted all of them. This batch is Hard-heavy (35%) and has almost no Easy; that comes from the topics (diagnosis and design questions) and is not a quota result. If you want more Easy recall items for mock-interview warm-ups, that is a later-batch decision.

Only 2 of 46 questions open with a definitional pattern; no 4-word opener repeats more than 3 times. Median nearest-neighbour similarity inside the batch and to v5 is 0.11 (max 0.18 to v5, 0.21 inside the batch); the closest existing questions are smi-h0003, smi-h0009, smi-h0010, smi-g0011 and smi-g0026, none with the same intent.

## 4. Answer-format coverage

| Answer set | Records |
|---|---:|
| single | 10 |
| concise + detailed | 11 |
| detailed + practical | 20 |
| concise + detailed + practical | 5 |

36 of 46 (78%) have more than one answer field, well above the ~40% I aimed for, because many records are scenario/debugging questions where the worked example adds real value. The auditors checked each extra field for distinct value; none were dropped as a pure paraphrase (the practical answer of GEN-02-4 was rated borderline and kept). `answer` is populated for all records (equal to `detailed_answer` for multi-field sets), concise answers are all at most 80 words, detailed answers 120-450 words. 8 design questions carry `rubric_points`.

## 5. Tests executed and skipped

* **9 records have reference code** (6 coding questions plus 3 with tested helpers): all 9 pass on **Python 3.13.16, 3.10.20 and 3.11.17** (27 runs). The authors, both auditors and I all ran them; recorded code imports only stdlib and numpy, and every fenced block in an answer equals the tested solution.
* The other 37 records are conceptual; their numeric claims (chunk counts, memory sizes, recall curves, kappa, bootstrap, token budgets, RRF scores) were recomputed by the reviewers in code, and 53 claims are labelled `executed`, 30 `derivation`.
* Validator `audit/expansion/validate_batch.py`: **44 checks, 0 failed** in the sandbox. On a Python 3.10 environment without scikit-learn it gives 41 pass, 1 skipped (the TF-IDF duplicate scan; the exact-duplicate and 5-gram checks still run). Only 5 of the 22 original files exist in this sandbox mirror, so that regression check covers 5 here; the full 22 are checked where the project is complete.
* **Skipped / not possible:** nothing was skipped for the code. No DAX or cloud-service tests apply in this batch.

## 6. Source verification

| | |
|---|---:|
| Records citing an opened source | **8 of 46 (17%)** |
| Of those, opened by me and supporting the claim (`lead_opened_supported`) | 7 |
| Opened by a reviewer only (`independent_reviewer_supported`, MMR paper) | 1 |

Sources I opened: the FAISS index guidelines (nlist about 4 to 16 times sqrt(N), HNSW memory per vector, PQ code size), the Reciprocal Rank Fusion paper (k = 60, "near-optimal but not critical"), Bruch et al. (convex combination beats RRF, RRF sensitive to its parameters), Lost in the Middle (position effect in the abstract), and HyDE (hypothetical documents may contain false details).

**This misses the blueprint target** of at least 70% of records citing an opened source in the GenAI domain. The reason is that most of these questions are about mechanisms and calculations that were checked by running code (53 claims) or by derivation (30), not by a page. But 31 claims in 29 records remain `background_only` (hedged in the text; listed in `unverified_claims.csv`), mostly model-behaviour claims (judge biases, position effects beyond the abstract, HNSW delete behaviour, filter behaviour under restrictive filters, nlist rules of thumb). I hedged them rather than removing them. I'd treat this as the batch's main open item.

## 7. Major defects found and corrected

First blind review: 7 of 46 records (15%) had a major defect, under the 25% rule that would have forced a regenerate.

* **GEN-03-5 (MMR):** claimed lambda = 0 "ignores the query after the start"; it ignores the query from the first pick.
* **GEN-02-4 (stale index):** diagnosed the wrong bug (re-inserting every page would double the index nightly, not grow it 4%). The first fix then repeated an arithmetic error ("roughly double"), and the recheck corrected it again; the final diagnosis is an append-only job that re-inserts changed pages and never deletes old chunks.
* **GEN-05-3:** the "faithful" verdict assumed the retrieved page says something the question never states.
* **GEN-05-6:** used the standard error of one accuracy for a paired comparison on the same questions; also an impossible flip count (net +3 from exactly 10 flips), fixed to 11 flips.
* **GEN-05-7:** called measured recall a "lower bound" (only precision@k is, with incomplete judgments).
* **GEN-05-8:** the question referred to an example the candidate cannot see; the data is now in the question.
* **GEN-06-3:** the update procedure briefly served old and new chunks together, contradicting the "single consistent version" claim.

The recheck found 3 more major defects, **all introduced by first-round fixes**: GEN-01-7 (a self-contradictory sentence; a stale-centroid test showed recall at fixed nprobe can go *up* if only a few cells absorb the new data), GEN-02-4 (above), GEN-06-6 (concise answer still advised rank merging after the detailed answer called it unsafe). This is the reason every corrected record gets a second check. Also fixed: a signature mismatch in GEN-01-2's code (patched and retested), 2 question-type changes, 2 key-concept lists, and 7 difficulty labels.

## 8. Remaining risks

1. **No human review of any record.** Authors, reviewers and I share a model family. The 3 major defects the recheck caught in first-round fixes show that a single AI review is not enough; the 22 records that passed their first review were **not** rechecked (`v6_verification = ai_review_only_no_human`, no "+recheck").
2. **Source coverage at 17%** against the 70% target (section 6). 29 records have at least one `background_only` claim.
3. **Time-sensitive:** only GEN-04-3 (lost in the middle) is flagged (`review_by` 2027-04); the position effect is model-dependent and my source is the abstract only.
4. **Small code gaps (not patched):** MMR crashes on an empty candidate list, BM25 on an empty corpus, `aggregate([])` and `hnsw_memory_gb` with `m = 1` raise ZeroDivisionError. They are outside what the questions ask.
5. **Distribution:** Hard 35%, Easy 2%; batch is 6 records over target; one domain only.
6. The semantic duplicate scan needs scikit-learn, so on your machine it is skipped (it ran here). The sandbox mirror lacks 17 of the 22 original files, so the full original-file regression should be run on your machine.

## Files

`data/expansion/batch_01/` (accepted CSV/JSON, code tests, quarantine, corrections, unverified claims, manifest, `work/` evidence), `audit/expansion/build_batch.py`, `validate_batch.py`, `audit/expansion/batch_01/` (briefs, drafts, reviews, rechecks, test scripts), `reports/validation_batch01_sandbox.json`.

Waiting for your approval before Batch 2.
