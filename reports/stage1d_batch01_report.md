# Stage 1D - Batch 1 report, revision 2 (Generative AI & RAG, 46 records)

Revision 2 follows your conditional approval. All 46 records are kept, none quarantined. The batch is still **staged** (`data/expansion/batch_01/`), not merged into a curated release. v1-v5 are unchanged. The revision-1 files and report are preserved in `data/expansion/batch_01/archive_rev1/` (rev-1 fingerprint `86b22d4e...e027`).

| | Rev 1 | **Rev 2** |
|---|---:|---:|
| Accepted / quarantined | 46 / 0 | **46 / 0** |
| Records citing a source page | 8 (17%) | **38 (83%)** |
| ...with at least one *fully supporting* source | 7 | **35 (76%)** |
| Source entries / distinct URLs | 9 | **85 / 62** |
| Fingerprint (combined sha256) | `86b22d4e...` | `6051c6675e756cc101098f714438f0ca2d3d30989df12748ce1c7ab33b5a9efa` |

## 1. Recheck of the three major-defect records

B1-GEN-01-7 (stale IVF centroids), B1-GEN-02-4 (stale index), B1-GEN-06-6 (sharded BM25 + hybrid) went to a **third, fresh auditor** on their final text, along with the 11 other records the source pass edited (14 in total). Result: 0 major defects; 8 pass, 6 minor corrections (13 wording fixes, applied).
* 01-7: the auditor ran its own FAISS IVF-Flat experiment (stale quantiser, new data). It confirmed the answer's two-branch claim: when only a few oversized cells hold the new content, recall at fixed nprobe usually does *not* drop and latency rises; recall drops when the new region spans more oversized cells than nprobe probes (0.888 vs 1.000 in its run). Quantisation error on new data was about 5x old data, so the proposed monitor is valid. Fixes: PQ retraining wording, re-sweeping nprobe, "not a bug" wording.
* 02-4: growth arithmetic re-derived (two edits of a page give three copies; re-inserting every page nightly would add about 100% of baseline, not 4%). One consistency fix between chunk keys in two fields.
* 06-6: idf 10.72 vs 8.73 and RRF 0.032266 vs 0.032258 recomputed; the earlier concise/detailed contradiction is gone; four wording fixes (e.g. normalised scores are not "rank-based").

## 2-4. Source coverage

Process: a source-finding agent per record set (open the page, quote it, say whether it supports our sentence *as worded*, otherwise `partially`/`not_found`) -> a **separate verifier re-opened every one of the 85 citations** (85 supported/partial: 61 supported, 24 partial, 0 not supported, 0 unreachable) -> I opened 6 of the key pages myself (FAISS index wiki, Qdrant filterable HNSW, MT-Bench paper, Ragas faithfulness, Elasticsearch RRF docs, sentence-transformers retrieve & re-rank) plus the 5 I opened in rev 1; all support their claims.
* **Statuses are explicit.** `lead_opened_*` = I opened it (21 records); `independent_reviewer_*` = two separate AI agents opened it, I did not; `*_partially` = the page supports only a narrower statement and the `supports` text says which (24 entries). Sources are 44 papers, 39 official docs and 2 secondary (Elastic blog posts used because the official page for shard-local scoring was not reachable).
* **The sources changed the text.** The source pass caught 14 overstatements, all fixed: "float16 is usually near-lossless" (FAISS says it may lose precision), HNSW "best latency at high recall" (not supported), silent context truncation (the provider docs describe an error), self-preference bias in LLM judges stated as fact (MT-Bench says it cannot determine this), rare-ID embedding mechanism (only the retrieval gap is shown), HyDE, RAG-Fusion, MMR lambda (an illustrative value in the paper, not a default), soft-delete behaviour in HNSW, Weaviate vs Qdrant filtered traversal.
* **Not padded.** 8 records have no source: 01-2 and 05-8 (code), 02-1 (chunk-count arithmetic), 02-3 (ingestion design), 02-4 (stale-index debugging), 02-5 and 02-6 (chunking concepts), 03-8 (unjudged-document evaluation). Nothing authoritative that I could open says what these records say, so I left them uncited. **Chunking and ingestion is the weakest topic: 1 of 6 records cites a source**, because chunk-size and overlap guidance is mostly empirical practice, not documented behaviour.
* **Executed or derived evidence is kept separate from sources.** Each record's `evidence_summary` lists internal evidence (53 claims executed, 30 derived) apart from external sources; a record can have both. 9 records have code that passed on Python 3.10/3.11/3.13.
* **Still unsupported:** 67 claims in 38 records have no authoritative source found (`unverified_claims.csv`), e.g. IVF drift and retraining, larger norms for generic chunks, inner product not being a metric, Kappa depending on prevalence, clustered bootstrap, compression risks, LSM-style compaction analogy, per-shard rank merging. All are hedged in the text.

## 5-6. Quarantine and defects

No record has an unresolved material factual defect, so none is quarantined. Cumulative major defects: 7 on first review, 3 on the second (all introduced by first-round fixes), **0 on the third**. Source pass added 14 corrections, final recheck 13; `corrections.csv` logs all 96 changes (rounds: round1, round2, source_pass, final_recheck).

## 7. Validation

`validate_batch.py`: **44 checks, 0 failed** in the sandbox (Python 3.13), including 9 code tests on 3.13, 3.10, 3.11, the 5-gram template check, duplicates (max similarity to v5 0.18, inside the batch 0.21), the fingerprint recomputation, and v1-v5 regression. The validator now requires `source_opened` in a record's label if and only if it cites a source. Counts unchanged from rev 1: Easy 1, Medium 29, Hard 16; answer sets 10 / 11 / 20 / 5.

## Limitations

1. No human review of anything; reviewers and authors share a model family. The third recheck covered only the 14 records that changed, so the other 32 have had a blind review (and, if corrected, a recheck) but not the final pass.
2. `independent_reviewer_*` sources were opened by AI agents, not by me; fetch tools return summaries, so some quotes were verified by substance, not punctuation.
3. 24 of 85 citations support only a narrower statement than the question's topic; and chunking is thinly sourced.
4. Hard-heavy mix (35%), one domain only; GEN-04-3 is the only time-sensitive record (review by 2027-04).
