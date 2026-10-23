# Stage 2C-final - Retrieval Optimisation Report

**Verdict: READY FOR LLM EVALUATOR - with conditions (section 9).** Real-MiniLM Flask verification is *not yet run on your machine*; the script is provided (section 8).

## 1. Bubble-sort / FizzBuzz diagnosis
* The demo queried smi-0453 with its own text; self is excluded by design, so the "neighbours" are the next-best records.
* The corpus has exactly one other sorting record (quicksort, smi-0452). It is in the top 3 in every format (qka rank 2-3, qk 3-4, question-only 2).
* FizzBuzz 0.454 vs Quicksort 0.446 (qka) is a near-tie on weak absolute scores (~0.37-0.45). Shared topic prefix and "Implement ... algorithm" phrasing lift FizzBuzz in `qk` (0.472 vs 0.375).
* Not truncation (all involved docs <= 256 tokens) and not a logic bug. A paraphrased query ranks smi-0453 #1 (0.74) with quicksort #2.
* Conclusion: corpus coverage + weak-score near-ties, not a defect. Regression tests assert relevance properties, not exact ranks (`tests/retrieval/test_recorded_real_minilm.py`).

## 2. Provenance (real run, your Windows PC)
all-MiniLM-L6-v2 revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; weights sha256 `53aa5117...28d9db`; tokenizer.json `be50c362...572037`; sentence-transformers 5.6.0, torch 2.12.1+cpu, transformers 5.12.1; max_seq_length 256. FAISS IndexFlatIP and NumPy agree on 166/166 queries. Corpus sha `db776e9fa135...`.

## 3. Token truncation (real tokenizer)
| format | docs > 256 tokens | notes |
|---|---|---|
| qka | 450/666 (67.6%) | median 403, p90 757, max 1774 |
| question | 19 (2.9%) | |
| qk | 31 (4.7%) | |
| qk_concise | 31 (4.7%) | median 236, max 509; share of answer words kept (median) 0.545 |

Truncation by itself did not measurably hurt qka: S@1 .718 on truncated vs .767 on non-truncated targets (confounded by difficulty).

## 4. Records accounted for
* **31 head-over-budget**: topic + question + key concepts alone exceed the window (long scenario/code). No answer sentence added; flagged. Same 31 as qk over-limit.
* **36 with no answer sentence** = those 31 + 5 with < 12 tokens left.
* **15 answer_cut**: first answer sentence cut at a word boundary to fit.
* Embedded text is always a verbatim prefix of the canonical answer (test-enforced); the full answer and metadata remain available by id.

## 5. Format comparison (labels are AI-generated, blind pooled, two passes + dispute pass; **not human-reviewed**; query author, designer and labeller share a model family)
### Dev set (166 queries; 140 primary)
| format | S@1 | S@3 | S@5 | MRR@10 | nDCG@5 |
|---|---|---|---|---|---|
| qka | 0.729 | 0.914 | 0.950 | 0.821 | 0.788 |
| question | 0.614 | 0.779 | 0.864 | 0.714 | 0.676 |
| qk | 0.714 | 0.907 | 0.950 | 0.812 | 0.779 |
| qk_concise | 0.743 | 0.929 | 0.950 | 0.832 | 0.790 |
| bm25_qka | 0.679 | 0.864 | 0.936 | 0.779 | 0.737 |

Paired S@1 vs qka (mean diff, bootstrap 95% CI, wins/losses/ties):

| format | diff | CI | W/L/T |
|---|---|---|---|
| question | -0.114 | [-0.193, -0.043] | 7/23/110 |
| qk | -0.014 | [-0.079, +0.057] | 11/13/116 |
| qk_concise | +0.014 | [-0.014, +0.043] | 3/1/136 |
| bm25_qka | -0.050 | [-0.136, +0.043] | 17/24/99 |

### Challenge set (58 queries; 34 primary, 7 corpus-gap queries)
| format | S@1 | S@3 | S@5 | MRR@10 | nDCG@5 |
|---|---|---|---|---|---|
| qka | 0.765 | 0.912 | 0.971 | 0.847 | 0.820 |
| question | 0.765 | 0.882 | 0.941 | 0.827 | 0.732 |
| qk | 0.765 | 0.912 | 0.971 | 0.846 | 0.790 |
| qk_concise | 0.735 | 0.941 | 0.971 | 0.839 | 0.814 |
| bm25_qka | 0.676 | 0.824 | 0.853 | 0.754 | 0.670 |

| format | diff | CI | W/L/T |
|---|---|---|---|
| question | +0.000 | [-0.147, +0.147] | 3/3/28 |
| qk | +0.000 | [-0.147, +0.147] | 3/3/28 |
| qk_concise | -0.029 | [-0.176, +0.088] | 2/3/29 |
| bm25_qka | -0.088 | [-0.265, +0.088] | 3/6/25 |

Label-sensitivity (min/max labelling) changes challenge qka S@1 between .735 and .824, i.e. larger than any difference between formats.

**Reading:** question-only is clearly worse on dev (-0.114 S@1, CI excludes 0). qk and qk_concise are tied with qka everywhere (all CIs include 0; S@5 identical for qka/qk_concise on both sets). qk_concise: dev +0.014, challenge -0.029. Gains do not generalise as gains - they are noise. BM25 is consistently a little worse than dense (not significant on S@1, S@5 gap on challenge -0.118).

## 6. Weak spots
* Long-scenario records (31): dev n=11 S@1 .455 vs .752 for the rest (confounded). No format fixes this. Untested idea: chunked / head+tail embedding.
* Multi-concept and domain-confusing queries dominate top-1 failures (`top1_failures` in `data/retrieval/stage2c/eval_results.json`).
* 7 algorithm queries have no matching record: a data-coverage issue, not retrieval.

## 7. Latency and cold start
Query encode median 14.05 ms, p95 27.72 ms; warm HTTP p50 ~16.6 ms. Embed whole corpus: qka 24.5 s, qk_concise 12.3 s.
The legacy 15.4 s first request is the **answer scorer's lazy SentenceTransformer load** on the first `bert` session, not retrieval. Nothing changed; retrieval loads a second MiniLM copy lazily on first curated use. `stage2c_verify_flask.py` times it directly (pending).

## 8. Flask verification
Passed in sandbox with the dev stand-in (ids/metadata, stable id mapping, filters, loaded-once, self-exclusion, BM25 fallback, no-answer, dataset unchanged; 77 app tests, 137 retrieval tests). **Real-MiniLM live run still needed on Windows:**
`python scripts/stage2c_verify_flask.py`, `python -m pytest tests/retrieval tests/app -q`. Evidence JSON goes to `reports/stage2c_flask_verification.json`.

## 9. Selection and verdict
Selected **qk_concise** on engineering grounds: quality tied with qka within noise, no silent truncation for 635/666 docs, 2x faster index build. It is not a proven quality gain; `SMART_RETRIEVAL_DOC_FORMAT=qka` restores the old behaviour.

**Why READY:** an LLM evaluator should ground on the ID-linked canonical reference answer (direct lookup) and use retrieval only as supplementary context at k>=5 (S@5 = 0.95-0.97).
**Conditions:** (1) no validated no-answer threshold (dev-derived 0.415 was optimistic: 12/18 on the independent set; challenge-derived 0.457 rejects 20/20 no-answers but wrongly rejects 13% of answerable) - do not ship a default; (2) 31 long-scenario records are weaker; (3) corpus coverage gaps; (4) labels are AI-generated; (5) run the Windows verification before relying on this.
Semantic similarity is not a validated measure of candidate correctness.

STOPPED after Stage 2C; awaiting approval.
