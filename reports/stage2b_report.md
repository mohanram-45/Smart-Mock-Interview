# Stage 2B — final verification report

**Verdict: PASS WITH LIMITATIONS — restricted integration only.**
**Recommended retrieval strategy: MiniLM + FAISS on `qka` documents, with MiniLM-cosine abstention. BM25 stays as fallback and diagnostic; hybrid (RRF) stays experimental until confirmed on fresh queries.**

All results below are measured on the real pretrained all-MiniLM-L6-v2 run on your Windows PC, scored against AI-generated relevance judgements (not human ground truth). Superseded interim report: `reports/stage2b_report_interim_model_blocked.md`.

## 1. What was done
1. **Artifacts inspected** (Windows benchmark JSON, three index metas, corpus manifest, eval labels). Model provenance and config: `reports/stage2b_model_provenance.md`. The model is the real pretrained one on strong evidence; its snapshot hash/weights SHA-256 are **not yet recorded** (one-command script provided).
2. **Immutable originals** saved with SHA-256 (`data/retrieval/eval/immutable_pre_pooling_stage2b/`; a test enforces them).
3. **Pooled relevance assessment** — all unjudged top-10 pairs from the 9 systems (BM25 / MiniLM / hybrid × q / qk / qka): **1,535 unique pairs over 165 queries** (reproduces your 42.1% / 19.0% for qka). Two independent blind passes (anonymised, shuffled, no system/rank/score shown; 2 previously judged “anchor” candidates per query hidden in each pass), then a third blind adjudication pass on the 54 disputed pairs.
4. **Re-scored** every system under the original labels and three pooled variants; paired bootstrap CIs; no-answer analysis; error analysis; design/leakage checks.
5. **Regression tests**: 106 pass, 1 skipped (needs a local model), on Linux and on your machine's VM.

## 2. Judgement quality (`data/retrieval/eval/pooling_report_v2.json`, `audit/retrieval/pooling/pool1/stats12.json`)
- Pass 1 vs 2 on the 1,535 new pairs: raw agreement 96.5%, Cohen's kappa 0.72 (3 grades), 0.76 (grade ≥ 1). Kappa for grade ≥ 2 is 0.20 and **not meaningful**: there were only 9 (pass 1) and 1 (pass 2) grade-2 calls, so the statistic is dominated by chance.
- 54 pairs disputed (8 involved grade 2). The adjudicator changed 25 pass-1 and 29 pass-2 grades; **1 pair remains an unresolved three-way split** (Q055/smi-l0030: 1, 0, 2 → assigned the median, 1).
- Final grades of the new pairs: 1,426 grade 0, 106 grade 1, **3 grade 2**. So MiniLM's and hybrid's unjudged hits were overwhelmingly irrelevant — the 42% “missing judgements” were not hiding missed relevant answers. No no-answer query became answerable.
- Calibration check against existing labels (anchors): agreement 91.0% (pass 1) and 84.2% (pass 2) with the original consensus. Disagreements are mostly upgrades of old grade-1 to 2 (18 and 27 of ~80) because the original consensus used the stricter minimum of two passes; this shows the 1-vs-2 boundary is the least reliable part of the labels.
- Variants provided: `eval_set_v2.jsonl` (primary, adjudicated), `_min` (conservative, original convention), `_max` (lenient). Original 166 queries and all original judgements preserved (tested). **All grades are AI-generated; no human review.**
- Remaining incomplete judgements: none for the top-10 of the 9 evaluated systems (Unjudged@10 = 0.000). Any other system or deeper cutoff will again surface unjudged items.

## 3. Results (qka, pooled labels v2; 140 primary queries, 146 answerable, 20 no-answer)
| | BM25 | MiniLM + FAISS | Hybrid (RRF) |
|---|---:|---:|---:|
| Success@1 | 0.679 | 0.729 | **0.807** |
| Success@3 | 0.864 | 0.914 | 0.914 |
| Success@5 | 0.936 | 0.950 | 0.957 |
| Recall@1 / @3 / @5 | 0.567 / 0.768 / 0.861 | 0.602 / 0.835 / 0.893 | 0.651 / 0.823 / 0.897 |
| MRR@10 | 0.779 | 0.821 | **0.870** |
| nDCG@5 | 0.738 | 0.789 | 0.805 |
| No-answer AUROC (top-1 score) | 0.985 | **0.990** | 0.939 (RRF score; use component) |
| Domain-mismatch top-1 | 18.1% | 14.6% | 12.5% |
| Latency mean / p95 (ms, Windows CPU) | 1.0 / 2.0 | 9.8 / 12.0 | 10.9 / 13.3 |
| Build / index | 0.15 s / in-memory | 16.3 s / 1.05 MB | both |
| Peak process memory (whole process) | n/a | ≈ 940 MB | ≈ 940 MB |

Full tables (all modes, per-domain, per-category, label variants, paired CIs): `reports/stage2b_final_benchmark.md`. Pooling did not change Success@k or MRR@10 (new relevant pairs were almost all grade 1); only Recall and nDCG changed, by ≤ 0.02.

**Is hybrid's advantage genuine?** Partly, and fragile.
- In `qka`: paired CIs exclude 0 for hybrid vs BM25 (MRR +0.091 [0.049, 0.133], S@1 +0.129 [0.064, 0.200]) and just exclude 0 for hybrid vs MiniLM (MRR +0.049 [0.008, 0.090], S@1 +0.079 [0.014, 0.143]; 16 wins / 5 losses). Success@5 differences among all three are within noise.
- MiniLM vs BM25 in `qka` is **not** significant (S@1 +0.050 [−0.043, +0.143]; MRR +0.042 [−0.020, +0.103]).
- In `q` and `qk` the hybrid is **worse than MiniLM alone** (S@5 0.829 vs 0.914 and 0.907 vs 0.950; CIs exclude 0). It beats MiniLM only when BM25 has the long answer text. BM25 on short `q` text is weak and drags the fusion down.
- Hybrid helps most where MiniLM is weak (Data Analysis, Deep Learning, new-domain records), but no domain has more than 28 queries.

## 4. Strategy decision
| Criterion | BM25 | MiniLM | Hybrid |
|---|---|---|---|
| Relevance (qka) | lowest S@1/MRR; strong S@5 | middle | best S@1/MRR, S@5 equal within noise |
| Robustness across modes/domains | very mode-dependent (S@5 0.71 → 0.94) | most stable across q/qk/qka (S@5 0.91–0.95) | beats MiniLM only in qka; worse in q, qk |
| Multi-concept / new-domain scenario queries | good (multi S@5 0.94) | weakest (multi S@5 0.75; S@1 0.60 on Gen-AI) | in between (0.81) |
| Out-of-corpus | good, scale-dependent | **best, portable cosine threshold** | needs component score |
| Latency / memory | ~1 ms, tiny | ~10 ms, ~0.9 GB process | ~11 ms, ~0.9 GB |
| Complexity | lowest | moderate | highest (two retrievers + fusion, two failure modes) |
| Evidence reliability | single AI-labelled set | same | same, plus mode-dependence and post-hoc mode choice |

**Choice: MiniLM + FAISS (`qka`)** with abstention on MiniLM top-1 cosine. Reasons: it beats BM25 significantly in `q` and on most `qk` metrics, and is not significantly different from BM25 in `qka`; it is stable across document modes; it has the best, most portable no-answer signal; and the hybrid's extra top-1 gain is statistically thin, depends on one document mode, was measured only on the set used to choose that mode, and adds complexity. Hybrid is the best candidate for the next confirmation step (it fixes MiniLM's multi-concept and scenario-record weakness) but should be adopted only if it holds on fresh independent queries. **The 0.807 / 0.870 hybrid numbers are not an independent generalisation result.** Do not integrate a no-answer threshold chosen on these queries; calibrate it on new ones.

## 5. Regression and safety checks (all pass)
- Tests: **106 passed, 1 skipped** (Linux sandbox and the device VM). New: pooled-label integrity, immutability, variant ordering, replay equals the Windows numbers exactly, no-leakage, no silent no-answer flips, kappa helper; earlier: Windows `resource` compatibility, RRF, legacy guard.
- Datasets unchanged: strict corpus loader passes on the device (666 records, fingerprint `db776e9f…`, 0 problems); v1–v5 and batches untouched. `data/curated` and `data/expansion` are not tracked by git, so unchanged-ness is proven by the registry/manifest fingerprints, not by git.
- Stable IDs and FAISS persistence/reload, corrupt/mismatched-index detection, domain filtering, deterministic rebuild: covered by the existing suite (unchanged, passing).
- Legacy contamination: 0 ids / 0 questions / 0 answers shared between the 666 approved records and the 3,618 boilerplate rows (`legacy_guard`).
- Flask: `main/`, `src/components/`, `src/model/` and `data/processed/` are byte-identical to git HEAD (`git diff --quiet`); scoring code was not touched. The project has no Flask/scoring tests (`tests/` contains only `retrieval/`), so scoring behaviour is protected by the unchanged-code check only, not by tests.

## 6. Limitations (what would change the verdict)
- **Labels are AI-generated** (authors and judges are the same model family), one 166-query set, domains of 12–28 queries; the 1-vs-2 grade boundary is the weakest part.
- **Document truncation**: ~60% of `qka` documents likely exceed MiniLM's 256-token limit (estimate; exact figure pending `model_provenance.py`). Chunking is unexplored.
- **Model weights not hash-pinned** (script provided).
- **Threshold** for out-of-corpus abstention is untested on independent data.
- **Multi-concept and scenario-record queries** are MiniLM's weak spot.
- Memory ≈ 0.9 GB for a process that loads PyTorch; fine for a desktop/dev app, relevant if deployed small.
- Latency is from one Windows machine.

## 7. Readiness
Ready for **restricted** integration of MiniLM+FAISS as a read-only “find related reference questions” capability behind a feature flag, with the app's question source unchanged (`reports/stage2b_flask_integration_plan.md`, which already excludes the 3,618 boilerplate rows and keeps scoring untouched). Not ready to be treated as validated for production retrieval, for automated grading, or for hybrid adoption.

## 8. Deliverables
- Updated judgements: `data/retrieval/eval/eval_set_v2.jsonl` (+ `_min`, `_max`), `pooling_report_v2.json`, `audit/retrieval/pooling/pool1/` (shards, orders, outputs, stats), scripts `pool_label.py`, `rescore.py`, `final_analysis.py`, `render_final_md.py`.
- Benchmark: `reports/stage2b_final_benchmark.{md,json}`. Error analysis: `reports/stage2b_error_analysis.md`, `stage2b_final_analysis.json`, `stage2b_eval_reliability.json`. Provenance: `reports/stage2b_model_provenance.md`, script `audit/retrieval/model_provenance.py`.
- Tests: `tests/retrieval/test_stage2b_eval.py` and the existing suite.

**Stopped after Stage 2B. Awaiting your approval; I have not started Stage 2C, LLM grading, FastAPI, Docker or MLflow.**
