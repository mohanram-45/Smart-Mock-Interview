# Stage 2A report: RAG retrieval foundation

Date 2026-10-11. Scope: unified corpus, SentenceTransformer embedding pipeline, FAISS index, BM25 baseline, independent evaluation, tests. No LLM, grading, frontend, API, Docker or MLflow work; no dataset file and no existing application file was modified.

## 1. Headline (read this first)

* **The infrastructure is built and tested; the SentenceTransformer retrieval quality is NOT measured.** The Hugging Face hub is blocked by network policy in my sandbox and on the linked-device VM (HTTP 403), so `all-MiniLM-L6-v2` could not be downloaded and **no MiniLM accuracy, latency, build-time or index-size figure exists in this report.** I did not work around the block.
* What I could measure for real: the corpus loader, the FAISS index, BM25, the evaluation set, and every metric calculation. The "semantic" rows below come from a **dev-only TF-IDF+SVD embedder (`dev-lsa`) pushed through the same FAISS pipeline**. They validate the plumbing and give a floor to compare against; they say nothing reliable about MiniLM.
* One command on your machine produces the real MiniLM numbers: `python -m src.retrieval.cli benchmark` (section 9).

## 2. What works

| Deliverable | Status | Evidence |
|---|---|---|
| Unified read-only corpus loader | Done. 666 records = 487 v5 + 46 + 48 + 45 + 40; quarantined `B4-MLO-13-4` excluded; 8 domains incl. the two new ones | Validates v5 fingerprint (`9eb94d8f...7123`), registry file hashes, per-batch manifests, recomputed batch fingerprints, counts, id uniqueness, required fields. Corpus manifest `data/retrieval/corpus_manifest.json`, `corpus_sha256 = db776e9fa135384ae26ba84263b0fbe8a66b326367977b0b97d2f278e4c6e7ef`. Dataset files untouched (hash-checked in tests). |
| Retrieval documents | Done | One entry per record; embedded text separate from full response metadata (answers, alternatives, sources, verification flags, provenance). Candidate answers cannot enter the index (tested). |
| SentenceTransformer pipeline | Code done and exercised with the real `sentence-transformers` library (6.1.0, torch 2.14) using a tiny randomly initialised local model; **not run with MiniLM** | Batching, unit-norm and dimension checks, content-addressed cache (adding a batch embeds only new records), model-version metadata, clear error when the model cannot be fetched. |
| FAISS persistent index | Done | Exact `IndexFlatIP`; stable id<->row mapping; top-k; domain filter via FAISS ID selector (equals post-filtered full ranking in tests); atomic save; verified load (file hash, dimensions, ids, corpus fingerprint, embedder config, doc mode); rebuild only when needed; deterministic rebuild (identical `index.faiss` bytes). |
| BM25 baseline | Done | Own deterministic Okapi BM25 (k1 1.5, b 0.75), domain filter, no dependency. |
| Independent evaluation set | Done (AI-labelled, see limits) | 166 queries, 539 graded-relevant (query, record) pairs, section 4. |
| Benchmark + error analysis | Done for BM25 and dev-lsa | `reports/retrieval_benchmark_dev-lsa.{md,json}`, `reports/stage2a_error_analysis_dev-lsa.md`. |
| Automated tests | 81 pass on Python 3.13 and 3.10 | 84 pass + 1 skipped when pointed at the tiny local SentenceTransformer. Four integration tests (real-model semantic check) skip unless `SMART_RAG_TEST_MODEL` is set. I mutation-checked that tests fail when domain filtering, normalisation, nDCG or stale-index detection is broken. |
| Setup + architecture docs, demo command | Done | `src/retrieval/README.md`, `requirements-rag.txt`, `python -m src.retrieval.cli demo`. |

No conflicts with existing code: the Flask app serves its own 4,085 legacy questions from `data/processed/questions_cleaned.json` and never reads `data/curated` or the expansion batches; the new package is additive (`src/retrieval/`, `tests/retrieval/`). The existing Sentence-BERT scorer uses the same `all-MiniLM-L6-v2` model, so on your machine the model is probably already cached (no duplicate download).

## 3. Corpus and document design

* Embedded text (`qka`, default): topic, question, key concepts, canonical answer (answer last because MiniLM truncates at 256 word pieces). Alternative answers (123 records have concise/practical variants) are metadata only: they restate the canonical answer, and extra vectors would duplicate the question. Default fixed before benchmarking; ablation below.
* Domain labels preserved exactly; `Generative AI & RAG` and `MLOps & Model Deployment` are not in the app's `ROLE_MAPPING`, a Stage 2B decision.

## 4. Evaluation set (how the labels were made)

* 144 targeted queries: 72 paraphrases, 24 keyword-style, 16 multi-concept, 16 similar-but-distinct (same domain, high similarity to a different topic), 16 domain-confusing (shared vocabulary with another domain) + 22 out-of-corpus queries (adjacent, off-domain, HR-style, vendor-specific).
* **Leakage control:** query authors saw only target topic + key concepts, never stored question/answer text. Relevance was then judged by separate labellers who were blind to the authors' targets, to which ranker retrieved what, and to ranks and scores. Candidate ids were anonymised and shuffled per pass.
* **Two independent labelling passes** over every pooled candidate (about 22 per query; pool = top 10 of four rankers + the authors' targets): raw agreement 94.5%, Cohen's kappa 0.81 (3-class) and 0.86 (grade >= 2). Final grade = the lower of the two (conservative); a "union" (higher) variant is kept for sensitivity. The authors' intended target received consensus grade 2 for 132 of 160 target slots and grade 1 for 27.
* 20 of 22 out-of-corpus queries were confirmed to have no relevant record; 2 turned out to be partly covered. 6 answerable queries have only grade-1 records and are excluded from the primary metrics (still in nDCG and the lenient metrics).
* **Pooling bias handling:** my first run showed ablation systems retrieving unjudged records (up to 29% of top-10 slots), which would unfairly penalise them. I labelled the 667 missing (query, record) pairs with the same two-pass procedure (raw agreement 98.7%); all reported systems now have `unjudged@10 = 0`. **A MiniLM run will surface new unjudged records**; the benchmark reports the fraction and `audit/retrieval/gap_label.py` labels the gap.
* Limits: authors and labellers are AI models of one family, so correlated errors are possible and labels are not human ground truth; 166 queries give wide intervals; topics hold several overlapping records, so "relevant" is partly judgement.

Metrics: Success@k (>=1 relevant in the top k), Recall@k (share of relevant records in the top k), MRR@10, nDCG@5 (gain 2^grade-1), over the 140 queries with a grade-2 record; no-answer queries analysed separately.

## 5. Results (166 queries; sandbox, Python 3.13, 2 vCPUs)

**BM25 is real; "dev-lsa" is the stand-in embedder, not MiniLM.**

| System (doc mode) | Success@1 | Success@3 | Success@5 | Recall@5 | MRR@10 | nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|
| BM25 question only (`q`) | 0.521 | 0.671 | 0.707 | 0.649 | 0.608 | 0.567 |
| BM25 + key concepts (`qk`) | 0.636 | 0.779 | 0.871 | 0.801 | 0.727 | 0.700 |
| **BM25 + concepts + answer (`qka`)** | **0.679** | **0.864** | **0.936** | **0.870** | **0.779** | **0.756** |
| dev-lsa `q` | 0.293 | 0.536 | 0.586 | 0.515 | 0.429 | 0.410 |
| dev-lsa `qk` | 0.457 | 0.679 | 0.779 | 0.708 | 0.597 | 0.597 |
| dev-lsa `qka` | 0.614 | 0.821 | 0.871 | 0.818 | 0.729 | 0.746 |
| **SentenceTransformer MiniLM + FAISS** | **not measured** | | | | | |

* Adding key concepts and answer text helps both systems; the default `qka` is the best mode for each (decision made before running, confirmed by the ablation).
* Paired bootstrap (2,000 resamples, 140 queries) of dev-lsa minus BM25 at `qka`: Success@1 -0.065 (95% CI -0.150 to +0.021), Success@5 -0.064 (-0.121 to -0.014), MRR@10 -0.050 (-0.108 to +0.004). The dev embedder is slightly worse than BM25 at the top of the ranking, which is expected from a bag-of-words LSA; the finding is about the stand-in only.
* Label sensitivity (union labels, `qka`): BM25 Success@1 0.757 / MRR 0.840, dev-lsa 0.701 / 0.797; the ranking of systems is unchanged.
* By category (`qka`, Success@1): keyword queries BM25 0.917 vs dev-lsa 0.667; paraphrase 0.667 vs 0.681; similar-but-distinct 0.600 vs 0.667; domain-confusing 0.562 vs 0.562; **multi-concept 0.562 vs 0.250** (a single dense vector blends two topics; this will matter for MiniLM too and is a hybrid/multi-vector question for 2B).
* By domain (`qka`, Success@1; n per domain 13-30, so noisy): weakest are MLOps (BM25 0.53, dev-lsa 0.40), Deep Learning (0.62 / 0.44), SQL for dev-lsa (0.44) and Machine Learning for BM25 (0.46). Python and Generative AI & RAG are strongest.
* **No-answer queries (n=20):** BM25's top-1 score separates answerable from no-answer queries well (AUROC 0.985; no no-answer query scored above the answerable median). The dev-lsa cosine does not (AUROC 0.760; 25% of no-answer queries scored above the median). So a score threshold is a viable "no knowledge" signal for BM25 on this set and not for dev-lsa; it has to be re-measured for MiniLM before any threshold is used.
* Oracle domain filter (query domain known): top-1 improves (BM25 0.679 -> 0.714; dev-lsa 0.614 -> 0.693) but Success@5 can fall (BM25 0.936 -> 0.900) because multi-concept queries legitimately need records from another domain. Filter only when the interview context truly fixes the domain.

## 6. Error analysis (full tables in `reports/stage2a_error_analysis_dev-lsa.md`)

BM25 `qka`, queries with a grade-2 record (140): top-1 correct 67.9%; top-1 only partially relevant 16.4%; wrong domain 7.9%; same domain but different topic 6.4%; right topic but a sibling record 1.4%. Only 9 queries had no relevant record in the top 5. Patterns:
* Most misses are near-misses inside a broad topic with several overlapping records (e.g. Naive Bayes, POS tagging, backpropagation). The dataset has many same-topic neighbours, so Success@1 understates usefulness and the Success@3/5 columns are the more informative view for interview-question retrieval.
* Vocabulary mismatch: queries phrased by symptom or colloquially ("online split test" for A/B testing, "right to be forgotten" for GDPR erasure, "most probable parameters" for maximum likelihood) defeat lexical matching: exactly the case semantic retrieval should help with, and the first thing to inspect in the MiniLM run.
* Multi-concept queries are the weakest category for the dense stand-in.
* Domain-confusing queries went to the wrong domain at top-1 in 5 of 16 (BM25) and 4 of 16 (dev-lsa).

## 7. Latency, build time, size (measured; BM25 and dev-lsa only)

| | BM25 `qka` | dev-lsa + FAISS `qka` |
|---|---:|---:|
| Query latency p50 / p95 / max | 1.0 / 2.2 / 2.7 ms | 5.0 / 5.9 / 9.2 ms (query embedding + exact search over 666 vectors; run-to-run variation about 10%) |
| Build time | 0.10 s | 0.21 s (fit + embed + index) |
| Index size on disk | n/a (in memory) | 535 KB (192-d); raw vectors 511 KB |
| Peak process RSS | not isolated | about 330 MB (whole benchmark process; **an upper bound, not an index cost**) |

**MiniLM latency, embedding time, index size and memory: not measured.** Only arithmetic is available: 666 x 384 floats = about 1.0 MB of vectors. Exact search over 666 vectors is not expected to be the bottleneck; query-time MiniLM encoding on CPU will dominate, and it must be measured.

## 8. Remaining limitations

1. No real MiniLM measurement (section 1). Until it is run, nothing here supports "semantic retrieval beats lexical".
2. Eval labels are AI-generated; no human adjudication; 166 queries; AI-reviewed reference answers are not verified ground truth (every record has `human_reviewed = false`).
3. Pool bias for new systems (handled for the current ones via gap labelling; must be repeated after the MiniLM run).
4. Not run on Windows (your machine): I cannot test there. `faiss-cpu` needs a wheel for your Python version; use 3.10-3.12 if pip cannot find one.
5. Device validation covers Python 3.10 on the linked VM only (see section 10).
6. Truncation: MiniLM sees roughly the first 256 word pieces of each document, so long answers contribute only their opening. BM25 sees all of it.
7. Multi-concept queries, same-topic sibling records and out-of-corpus detection are open retrieval-quality issues (hybrid retrieval, multi-vector or reranking are 2B questions; not implemented).
8. 17 records are time-sensitive; scores say nothing about answer freshness.

## 9. Run the real benchmark (one command each)

```
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements-rag.txt
python -m src.retrieval.cli benchmark                 # MiniLM vs BM25, writes reports/retrieval_benchmark_minilm.{md,json}
python audit/retrieval/error_analysis.py reports/retrieval_benchmark_minilm.json
python audit/retrieval/gap_label.py make reports/retrieval_benchmark_minilm.json minilm   # then label with two blind passes and `merge`
```

## 10. Is Stage 2A ready for integration?

**Ready as infrastructure, not yet validated as a retrieval system.** The loader, index, cache, BM25, evaluation harness and tests are solid and can be wired in. Do not integrate semantic retrieval on the strength of this report: first run the MiniLM benchmark above, label any unjudged hits, and compare with BM25 (which is a strong baseline here: Success@5 0.936). If MiniLM does not clearly beat BM25 on paraphrase and symptom-style queries, Stage 2B should consider hybrid (BM25 + dense) retrieval. I'm stopping here and waiting for your approval before Stage 2B.
