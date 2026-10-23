# Stage 2B — retrieval error analysis and design validation
All numbers: real MiniLM Windows rankings re-scored with pooled labels v2 (`reports/stage2b_final_analysis.json`). AI-generated labels, 166 queries; descriptive, not a generalisation study.

## 1. Design validation
**Leakage and contamination checks (all pass).**
- Documents are built only from corpus records: `doc_id`, `text`, `metadata` keys only; searchable text equals `search_text(record, mode)` for every one of the 666 documents in each mode; doc ids equal corpus ids in order; no duplicate document texts.
- No eval query text or query id appears in any document (0 of 166). Non-canonical alternative answers appear in no document (0). Every record's provenance origin is v5 or batch_01–04, so no candidate/user answer can be indexed (`documents.py` raises otherwise).
- Authored queries are not near-copies of stored questions: max token-Jaccard with any stored question has median 0.13, p95 0.28, max 0.50.
- Eval labels live in separate files that `build_documents` never reads.

**Biases that do remain (disclosed, not fixable here).**
- The query authors saw each target's topic and key concepts. Key concepts are in the `qk`/`qka` documents but not in `q`, so `qk`/`qka` are favoured over `q` by construction (strongest for BM25, which jumps from S@5 0.707 to 0.871 when key concepts are added). 24 queries are explicitly “concept keywords”.
- Labellers saw a 450-character excerpt of the answer. Relevance is judged on question/topic fit, so this is a weak influence, but it is not zero.
- Authors and labellers are AI models from the same family; shared blind spots cannot be excluded. No human review.
- The document mode (`qka`) was fixed before benchmarking, but the same 166 queries were then used to compare modes and systems. The highest score is **not** an independent generalisation result.
- RRF settings (k=60, depth 50, equal weights) were set before any run and not tuned. Nothing was tuned on the benchmark.

**q vs qk vs qka.** Adding answer text helps more than it misleads, for all three systems, at rank 1 (primary queries, n=140): BM25 30 queries gained vs 8 lost; MiniLM 17 vs 11; hybrid 31 vs 6. Queries that got worse with answer text (candidates for “misleading answer match”): BM25 Q035 Q058 Q061 Q096 Q098 Q107 Q123 Q125; MiniLM Q014 Q034 Q053 Q058 Q065 Q069 Q075 Q103 Q105 Q134 Q138; hybrid Q014 Q058 Q065 Q105 Q123 Q134. Answer text is legitimate reference knowledge for this use, but it also lets a long answer's incidental vocabulary win.

**Truncation risk for MiniLM (estimate, not measured on the real tokenizer).** `max_seq_length` is 256 word-pieces; by a words×1.3 proxy about 60% of the `qka` documents (median 252 words, p90 489) exceed it, so for those only the topic, question, key concepts and the first part of the answer are embedded. This is consistent with MiniLM gaining little from answer text (S@1 0.714 → 0.729, qk → qka) while BM25 gains a lot. The exact share needs `model_provenance.py`. Chunking or multi-vector indexing is a Stage 2C question; nothing was changed.

## 2. Failure analysis (qka, v2 labels)
Queries with no grade-2 record in the top 5 (of 140): BM25 9, MiniLM 7, hybrid 6. Only **Q098** (LLM ignores mid-prompt passages in RAG) is missed by all three. Hybrid misses nothing that both others got, but it inherits BM25's misses on Q060 and Q118, where MiniLM alone was right.
- **Multi-concept queries** are the weakest category for MiniLM: S@5 0.75 (BM25 0.94, hybrid 0.81). MiniLM's embedding blends two topics and lands on a neighbour of neither (Q003 feature store + SQL ranking; Q040 leakage + atomic file write; Q043 sharding + RAG test-set drift). BM25 finds the target at rank 3–4 in all three because each concept's keywords match.
- **Short definitional v5 records vs long scenario records.** MiniLM's S@1 is 0.78 when the target is a v5 record but 0.61 when it is a batch (scenario) record (n=101 / 28); BM25 is flat (0.66 / 0.68); hybrid 0.84 / 0.68. Small n.
- **Near-topic confusions**: Q060 (POS tagging → “What is Parsing”), Q139 (backprop → gradient-descent steps), Q097 (dropout → generic overfitting), Q118 (MLE in general → “log-likelihood in logistic regression”, a deliberate similar-but-distinct trap that only MiniLM solves). Several top-1 errors are reasonable neighbours; a human reviewer might grade some as 1.
- **Lexical mismatch for BM25**: Q120 (right to be forgotten → relevant record uses “customer asks for personal data deleted”), Q060, Q083, Q118: BM25 top-5 contains none of the target.
- **MiniLM bad miss**: Q110 (time-ordered data components) ranks “bubble sort time complexity” first and the target at rank 8; BM25/hybrid get it at rank 1.
- **Domain confusion** (top-1 in a different domain than the intended one, 144 queries with a domain): BM25 18.1%, MiniLM 14.6%, hybrid 12.5%.
- **Weak domains** (S@1 BM25 / MiniLM / hybrid): MLOps & Model Deployment 0.53 / 0.60 / 0.53 (n=15; S@5 0.93 / 0.87 / 0.93); Generative AI & RAG 0.80 / 0.60 / 0.85 (n=20); SQL 0.67 / 0.61 / 0.72 (n=18). The new-domain records are mostly long scenario texts, so the two new domains and SQL scenario items are where MiniLM underperforms.

## 3. Out-of-corpus behaviour
- All 20 no-answer queries have MiniLM top-1 cosine ≤ 0.413 (highest: ASR evaluation WER/CER 0.413, JVM GC 0.406, quantum ML 0.397). Answerable queries: 10th percentile 0.452, median 0.578. On this set a cut near 0.43–0.45 rejects all 20 no-answer queries and wrongly rejects ≈ 3–10% of answerable ones (0.40 → 90% / 2.7%; 0.45 → 100% / 9.6%). **Chosen on the same queries, so optimistic.**
- BM25 raw top-1 score also separates (AUROC 0.985) but its scale depends on query length and corpus statistics, so a threshold is less portable. Hybrid's RRF score separates less well (AUROC 0.939) and should not be thresholded; use the MiniLM cosine.
- Q157 (Cox model) was designed as no-answer but has a real partially relevant record (grade 1); it is treated as answerable, as in Stage 2A. Pooling did not turn any of the 20 no-answer queries into answerable ones.

## 4. Separate hard-query inspection
The 15 distinct top-5 misses above were inspected individually and are listed with their target records in `reports/stage2b_final_analysis.json` (`hard_case_detail`). They were not used to tune anything or to build a new benchmark; no challenge set was created (it would be authored after seeing these failures and must not be mixed into the 166-query results).
