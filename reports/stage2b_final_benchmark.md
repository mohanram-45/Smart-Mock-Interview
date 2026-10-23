# Stage 2B — final benchmark (real all-MiniLM-L6-v2, Windows run; pooled labels v2)

Source rankings: `data/retrieval/eval/immutable_pre_pooling_stage2b/retrieval_benchmark_minilm.json` (Windows 11, Python 3.12.7, 12 CPUs). Metrics recomputed with the project's own metric code; replaying the original labels reproduces the Windows numbers exactly (test `test_replay_reproduces_windows_benchmark_under_original_labels`).
Labels: AI-generated pooled judgements (two blind passes + adjudication), **not human ground truth**. 166 queries: 146 answerable (140 have a grade-2 record), 20 no-answer. Success/Recall/MRR use grade ≥ 2 over the 140; nDCG@5 uses graded gain over the 146.

## 1. Main comparison — pooled labels (v2, primary)

| Mode | System | S@1 | S@3 | S@5 | R@1 | R@3 | R@5 | MRR@10 | nDCG@5 | Unjudged@10 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| q | BM25 | 0.521 | 0.671 | 0.707 | 0.441 | 0.604 | 0.643 | 0.608 | 0.552 | 0.000 |
| q | MiniLM+FAISS | 0.686 | 0.850 | 0.914 | 0.570 | 0.756 | 0.843 | 0.781 | 0.730 | 0.000 |
| q | Hybrid (RRF) | 0.629 | 0.814 | 0.829 | 0.524 | 0.717 | 0.746 | 0.722 | 0.662 | 0.000 |
| qk | BM25 | 0.636 | 0.779 | 0.871 | 0.528 | 0.690 | 0.792 | 0.727 | 0.682 | 0.000 |
| qk | MiniLM+FAISS | 0.714 | 0.907 | 0.950 | 0.593 | 0.851 | 0.890 | 0.812 | 0.780 | 0.000 |
| qk | Hybrid (RRF) | 0.729 | 0.900 | 0.907 | 0.603 | 0.800 | 0.826 | 0.811 | 0.747 | 0.000 |
| qka | BM25 | 0.679 | 0.864 | 0.936 | 0.567 | 0.768 | 0.861 | 0.779 | 0.738 | 0.000 |
| qka | MiniLM+FAISS | 0.729 | 0.914 | 0.950 | 0.602 | 0.835 | 0.893 | 0.821 | 0.789 | 0.000 |
| qka | Hybrid (RRF) | 0.807 | 0.914 | 0.957 | 0.651 | 0.823 | 0.897 | 0.870 | 0.805 | 0.000 |

## 2. Before pooling (original labels v1.1) — shows the effect of the missing judgements

| Mode | System | S@1 | S@3 | S@5 | R@1 | R@3 | R@5 | MRR@10 | nDCG@5 | Unjudged@10 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| q | BM25 | 0.521 | 0.671 | 0.707 | 0.441 | 0.610 | 0.649 | 0.608 | 0.567 | 0.000 |
| q | MiniLM+FAISS | 0.686 | 0.850 | 0.914 | 0.570 | 0.757 | 0.846 | 0.781 | 0.726 | 0.464 |
| q | Hybrid (RRF) | 0.629 | 0.814 | 0.829 | 0.526 | 0.727 | 0.755 | 0.722 | 0.675 | 0.230 |
| qk | BM25 | 0.636 | 0.779 | 0.871 | 0.529 | 0.696 | 0.801 | 0.727 | 0.700 | 0.000 |
| qk | MiniLM+FAISS | 0.714 | 0.907 | 0.950 | 0.593 | 0.852 | 0.896 | 0.812 | 0.779 | 0.439 |
| qk | Hybrid (RRF) | 0.729 | 0.900 | 0.907 | 0.604 | 0.810 | 0.836 | 0.811 | 0.764 | 0.196 |
| qka | BM25 | 0.679 | 0.864 | 0.936 | 0.568 | 0.774 | 0.870 | 0.779 | 0.756 | 0.000 |
| qka | MiniLM+FAISS | 0.729 | 0.914 | 0.950 | 0.602 | 0.836 | 0.895 | 0.821 | 0.792 | 0.421 |
| qka | Hybrid (RRF) | 0.807 | 0.914 | 0.957 | 0.652 | 0.833 | 0.907 | 0.870 | 0.824 | 0.190 |

Unjudged@10 under v1.1 for MiniLM was 46.4% / 43.9% / 42.1% (q / qk / qka) and for hybrid 23.0% / 19.6% / 19.0%; all are 0.000 under v2.

## 3. Label-variant sensitivity (qka)

| Labels | System | S@1 | S@5 | R@5 | MRR@10 | nDCG@5 |
|---|---|---:|---:|---:|---:|---:|
| v1.1_original | BM25 | 0.679 | 0.936 | 0.870 | 0.779 | 0.756 |
| v1.1_original | MiniLM+FAISS | 0.729 | 0.950 | 0.895 | 0.821 | 0.792 |
| v1.1_original | Hybrid (RRF) | 0.807 | 0.957 | 0.907 | 0.870 | 0.824 |
| v2_conservative(min) | BM25 | 0.679 | 0.936 | 0.867 | 0.779 | 0.744 |
| v2_conservative(min) | MiniLM+FAISS | 0.729 | 0.950 | 0.895 | 0.821 | 0.791 |
| v2_conservative(min) | Hybrid (RRF) | 0.807 | 0.957 | 0.903 | 0.870 | 0.811 |
| v2_pooled | BM25 | 0.679 | 0.936 | 0.861 | 0.779 | 0.738 |
| v2_pooled | MiniLM+FAISS | 0.729 | 0.950 | 0.893 | 0.821 | 0.789 |
| v2_pooled | Hybrid (RRF) | 0.807 | 0.957 | 0.897 | 0.870 | 0.805 |
| v2_lenient(max) | BM25 | 0.679 | 0.936 | 0.846 | 0.779 | 0.730 |
| v2_lenient(max) | MiniLM+FAISS | 0.729 | 0.950 | 0.886 | 0.821 | 0.786 |
| v2_lenient(max) | Hybrid (RRF) | 0.807 | 0.957 | 0.885 | 0.870 | 0.798 |

Success@k and MRR are identical across variants because the pooled pairs added only 3 grade-2 judgements (and 106 grade-1); only Recall and nDCG move, by ≤ 0.02.

## 4. Paired differences with 95% bootstrap CI (v2 labels; 2,000 query resamples, seed 7; per-query)

| Mode | Metric | Comparison | Mean diff | 95% CI | W / L / T |
|---|---|---|---:|---|---|
| q | success@1 | MiniLM - BM25 | +0.164 | [+0.071, +0.250] | 35/12/93 |
| q | success@1 | Hybrid - BM25 | +0.107 | [+0.050, +0.171] | 18/3/119 |
| q | success@1 | Hybrid - MiniLM | -0.057 | [-0.136, +0.021] | 11/19/110 |
| q | success@5 | MiniLM - BM25 | +0.207 | [+0.136, +0.286] | 32/3/105 |
| q | success@5 | Hybrid - BM25 | +0.121 | [+0.071, +0.179] | 17/0/123 |
| q | success@5 | Hybrid - MiniLM | -0.086 | [-0.150, -0.029] | 4/16/120 |
| q | mrr@10 | MiniLM - BM25 | +0.173 | [+0.103, +0.243] | 55/13/72 |
| q | mrr@10 | Hybrid - BM25 | +0.114 | [+0.073, +0.157] | 45/3/92 |
| q | mrr@10 | Hybrid - MiniLM | -0.059 | [-0.117, -0.001] | 18/32/90 |
| q | ndcg@5 | MiniLM - BM25 | +0.178 | [+0.127, +0.231] | 89/30/27 |
| q | ndcg@5 | Hybrid - BM25 | +0.109 | [+0.076, +0.146] | 79/19/48 |
| q | ndcg@5 | Hybrid - MiniLM | -0.069 | [-0.107, -0.032] | 41/62/43 |
| qk | success@1 | MiniLM - BM25 | +0.079 | [-0.007, +0.164] | 25/14/101 |
| qk | success@1 | Hybrid - BM25 | +0.093 | [+0.036, +0.150] | 16/3/121 |
| qk | success@1 | Hybrid - MiniLM | +0.014 | [-0.057, +0.093] | 15/13/112 |
| qk | success@5 | MiniLM - BM25 | +0.079 | [+0.036, +0.129] | 12/1/127 |
| qk | success@5 | Hybrid - BM25 | +0.036 | [+0.007, +0.064] | 5/0/135 |
| qk | success@5 | Hybrid - MiniLM | -0.043 | [-0.086, -0.007] | 1/7/132 |
| qk | mrr@10 | MiniLM - BM25 | +0.085 | [+0.028, +0.142] | 37/18/85 |
| qk | mrr@10 | Hybrid - BM25 | +0.084 | [+0.048, +0.123] | 35/5/100 |
| qk | mrr@10 | Hybrid - MiniLM | -0.001 | [-0.046, +0.045] | 23/20/97 |
| qk | ndcg@5 | MiniLM - BM25 | +0.098 | [+0.055, +0.144] | 74/41/31 |
| qk | ndcg@5 | Hybrid - BM25 | +0.065 | [+0.039, +0.093] | 69/24/53 |
| qk | ndcg@5 | Hybrid - MiniLM | -0.033 | [-0.065, -0.004] | 48/51/47 |
| qka | success@1 | MiniLM - BM25 | +0.050 | [-0.043, +0.143] | 24/17/99 |
| qka | success@1 | Hybrid - BM25 | +0.129 | [+0.064, +0.200] | 22/4/114 |
| qka | success@1 | Hybrid - MiniLM | +0.079 | [+0.014, +0.143] | 16/5/119 |
| qka | success@5 | MiniLM - BM25 | +0.014 | [-0.036, +0.071] | 8/6/126 |
| qka | success@5 | Hybrid - BM25 | +0.021 | [-0.021, +0.064] | 6/3/131 |
| qka | success@5 | Hybrid - MiniLM | +0.007 | [-0.021, +0.036] | 3/2/135 |
| qka | mrr@10 | MiniLM - BM25 | +0.042 | [-0.020, +0.103] | 33/23/84 |
| qka | mrr@10 | Hybrid - BM25 | +0.091 | [+0.049, +0.133] | 36/8/96 |
| qka | mrr@10 | Hybrid - MiniLM | +0.049 | [+0.008, +0.090] | 24/9/107 |
| qka | ndcg@5 | MiniLM - BM25 | +0.051 | [+0.009, +0.093] | 71/49/26 |
| qka | ndcg@5 | Hybrid - BM25 | +0.067 | [+0.041, +0.094] | 73/27/46 |
| qka | ndcg@5 | Hybrid - MiniLM | +0.016 | [-0.012, +0.044] | 58/46/42 |

A CI excluding 0 means the difference is unlikely to be query-sampling noise **on this set only**; it says nothing about other queries or about label error, and the same 166 queries were used to choose the document mode (see §9).

## 5. By domain (qka, v2 labels; n = primary queries; S@1 / S@5 / MRR@10)

| Domain | n | BM25 | MiniLM | Hybrid |
|---|---:|---|---|---|
| Data Analysis | 17 | 0.82 / 0.94 / 0.86 | 0.71 / 0.94 / 0.81 | 0.94 / 1.00 / 0.96 |
| Deep Learning | 16 | 0.62 / 0.94 / 0.74 | 0.69 / 0.94 / 0.77 | 0.81 / 1.00 / 0.87 |
| Generative AI & RAG | 20 | 0.80 / 0.95 / 0.87 | 0.60 / 0.95 / 0.74 | 0.85 / 0.95 / 0.90 |
| MLOps & Model Deployment | 15 | 0.53 / 0.93 / 0.63 | 0.60 / 0.87 / 0.72 | 0.53 / 0.93 / 0.71 |
| Machine Learning | 28 | 0.46 / 0.89 / 0.65 | 0.89 / 0.96 / 0.92 | 0.82 / 0.93 / 0.86 |
| NLP | 12 | 0.67 / 0.92 / 0.79 | 0.83 / 1.00 / 0.90 | 0.92 / 0.92 / 0.92 |
| Python | 14 | 1.00 / 1.00 / 1.00 | 0.86 / 1.00 / 0.93 | 0.86 / 1.00 / 0.93 |
| SQL | 18 | 0.67 / 0.94 / 0.77 | 0.61 / 0.94 / 0.75 | 0.72 / 0.94 / 0.83 |

Domains have 12–28 queries each: one query is 4–8 points of Success. Do not read rank differences between domains as established.

## 6. By query category (qka; S@1 / S@5 / nDCG@5)

| Category | n answerable | BM25 | MiniLM | Hybrid |
|---|---:|---|---|---|
| concept_keywords | 24 | 0.917 / 1.000 / 0.848 | 0.917 / 1.000 / 0.884 | 1.000 / 1.000 / 0.905 |
| domain_confusing | 16 | 0.562 / 0.938 / 0.693 | 0.625 / 1.000 / 0.756 | 0.625 / 1.000 / 0.731 |
| multi_concept | 16 | 0.562 / 0.938 / 0.638 | 0.438 / 0.750 / 0.558 | 0.625 / 0.812 / 0.659 |
| no_answer_intended_but_covered | 2 | - / - / 0.925 | - / - / 0.807 | - / - / 1.000 |
| paraphrase | 72 | 0.667 / 0.913 / 0.720 | 0.725 / 0.957 / 0.792 | 0.826 / 0.971 / 0.807 |
| similar_distinct | 16 | 0.600 / 0.933 / 0.775 | 0.867 / 1.000 / 0.893 | 0.800 / 0.933 / 0.838 |

## 7. Out-of-corpus (no-answer) detection — 20 no-answer vs 146 answerable queries

| Mode | System | AUROC of top-1 score | mean top-1 (answerable) | mean top-1 (no-answer) |
|---|---|---:|---:|---:|
| q | BM25 | 0.968 | 18.695 | 7.736 |
| q | MiniLM+FAISS | 0.988 | 0.558 | 0.312 |
| q | Hybrid (RRF) (RRF score, rank-based) | 0.883 | 0.032 | 0.029 |
| qk | BM25 | 0.970 | 24.488 | 8.930 |
| qk | MiniLM+FAISS | 0.992 | 0.569 | 0.296 |
| qk | Hybrid (RRF) (RRF score, rank-based) | 0.921 | 0.032 | 0.030 |
| qka | BM25 | 0.985 | 32.116 | 11.621 |
| qka | MiniLM+FAISS | 0.990 | 0.582 | 0.299 |
| qka | Hybrid (RRF) (RRF score, rank-based) | 0.939 | 0.033 | 0.030 |

MiniLM top-1 cosine (qka) — highest-scoring no-answer queries: 0.413 Q155 “How do you evaluate an automatic speech recognition system? WER vs CER…”; 0.406 Q156 “How does JVM garbage collection work? G1 vs ZGC tuning…”; 0.397 Q164 “What is quantum machine learning and could a variational quantum circuit beat a classical …”.

Illustrative abstention thresholds on MiniLM top-1 cosine (**chosen on these same queries → optimistic; must be re-calibrated on fresh data**):

| Threshold | no-answer rejected | answerable wrongly rejected |
|---:|---:|---:|
| 0.35 | 0.65 | 0.021 |
| 0.40 | 0.90 | 0.027 |
| 0.45 | 1.00 | 0.096 |
| 0.50 | 1.00 | 0.205 |
| 0.55 | 1.00 | 0.404 |

The hybrid's fused RRF score is rank-based (its top-1 value is nearly constant), so abstention for the hybrid has to read the MiniLM cosine or BM25 score from `components`.

## 8. Cost (Windows run, CPU)

| Item | BM25 | MiniLM+FAISS | Hybrid |
|---|---:|---:|---:|
| Query latency qka, mean / median / p95 / max (ms; 166 queries, single-threaded loop) | 0.98 / 0.93 / 1.97 / 2.61 | 9.8 / 9.8 / 12.0 / 13.7 | 10.9 / 10.8 / 13.3 / 15.2 |
| Build (666 docs, qka) | 0.15 s | 16.3 s (embedding 16.3 s; cold, 0 cache hits) | both |
| Index on disk (qka) | in memory | 1.05 MB (vectors 1.02 MB) | both |
| Model load | – | 0.13 s | same |
| Peak process memory after qka build | not measured | 940 MB (whole process incl. PyTorch; cumulative across the three modes, so an upper bound for qka alone) | same |

Latency includes query encoding for MiniLM and hybrid. It is measured on this PC, not a server.

## 9. Design validation

See `reports/stage2b_error_analysis.md` §1 for leakage checks, answer-text effect and truncation.
