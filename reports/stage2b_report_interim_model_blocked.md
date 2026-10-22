# Stage 2B — Real Semantic Retrieval Verification

**Decision: BLOCKED — real model unavailable to this session.**
The retrieval code and tests are fine (94 pass); what is missing is a verified, pretrained all-MiniLM-L6-v2 to measure. No MiniLM or MiniLM-hybrid numbers exist, and none are reported here.

## 1. Local MiniLM availability (Phase 1)
| Check | Result |
|---|---|
| How the app loads it | `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")` by name in `src/model/Pretrained_NEURALN.py`; no local path, no `cache_folder`, no offline flag, so it relies on the default Hugging Face cache. |
| Project model directories | None. A search of the project for `*minilm*`, `config.json`, `modules.json`, `model.safetensors`, `pytorch_model.bin` found nothing (the project folder is the only folder this session can see). |
| Standard caches on your Windows PC | `~/.cache/huggingface` (contains `hub`, `xet`) and `~/.cache/torch` **exist**. This session could only list their top-level names; two folder-access requests (the caches, then `hub`) were refused, so I **could not open them** and cannot say whether the MiniLM snapshot is in them. |
| Offline load | Not attempted: nothing readable. Sandbox access to Hugging Face is blocked by policy (403); I did not use mirrors or workarounds. |
| What I did not use | The randomly initialised tiny test model and the TF-IDF/SVD stand-in are **not** pretrained MiniLM and are not used for any Stage 2B claim. |

### Manual action needed (pick one, ~2 minutes)
- **A (best):** copy the cached snapshot into the project, e.g. PowerShell:
  `Copy-Item -Recurse "$env:USERPROFILE\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\*" "D:\Projects\SMART-MOCK-INTERVIEW\models\all-MiniLM-L6-v2" -Force`
  (if the `models--…` folder isn't there, check the `torch\sentence_transformers` folder; if neither has it, the app has been downloading it some other way and you'll need to download it yourself once). Folder must contain `config.json`, `modules.json`, `tokenizer.json`/vocab, the weights file and `1_Pooling/`. Then tell me; I'll stage it and run `benchmark --model <dir> --local-files-only`, then hybrid.
- **B:** on your PC, with the project env and `pip install -r requirements-rag.txt`, run `python -m src.retrieval.cli benchmark --backend minilm` and send me `reports/retrieval_benchmark_minilm.json`.
- Keep `models/` out of git (add to `.gitignore`).

## 2–3. MiniLM and hybrid benchmarks (Phases 2–3)
**Not run.** What is ready:
- `src/retrieval/hybrid.py`: RRF (`1/(60+rank)`, depth 50, equal weights), deterministic ties, per-hit component ranks/scores; domain filter supported.
- `benchmark.run()` now reports, on the same fixed 166 queries and labels: `bm25_*`, `<backend>_*`, `hybrid_<backend>_*`.
- 94 tests pass (13 new: RRF values, ties, weights, invalid input, mismatched retrievers, domain filter, legacy guard). The hybrid pipeline ran end to end with the stand-in embedder purely as a smoke test; I am not reporting those numbers as evidence about MiniLM or hybrid.
- Known property to expect: RRF scores are rank-based, so the fused score can't detect no-answer queries; the component `semantic_score`/`bm25_score` fields are what a threshold should use.
- Expect new unjudged top-10 slots (the smoke test showed 3.1% for hybrid). When real results exist, run `audit/retrieval/gap_label.py make/merge` first so MiniLM/hybrid aren't penalised for pooling bias, as was done for BM25/stand-in.

Last measured (Stage 2A, real, unchanged): BM25 `qka` Success@1/3/5 = 0.679/0.864/0.936, MRR@10 0.779, nDCG@5 0.756, p50 latency ~1 ms.

## 4. Evaluation reliability (Phase 4)
Script: `audit/retrieval/eval_reliability.py` → `reports/stage2b_eval_reliability.json`.
- **Easy paraphrases?** No. Median token Jaccard between a paraphrase query and its best grade-2 question is 0.10 (p90 0.20; 0 of 69 ≥ 0.5). Overlap is low in every category, so the set isn't lexically trivial.
- **Missing judgments:** pools were built from BM25 and stand-in LSA only (~26 judged records per query, ~4% of the corpus). Gap labelling brought unjudged@10 to 0 for the reported systems, but any new system (MiniLM, hybrid) will surface unjudged items. **Bias risk runs in favour of BM25/LSA**, because their top results were always judged. Re-gap-label before comparing.
- **Label uncertainty:** both labelling passes and both authors are AI; kappa 0.81 (3-class), 0.86 (grade ≥2), 60 pairs disagreed on grade 2, consensus = the lower grade (conservative). Shared model-family bias between query authors and labellers can't be ruled out. No human review.
- **Thin grading:** 97 of 146 answerable queries have exactly one grade-2 record; 6 have only grade-1 records (Q041, Q082, Q101, Q141, Q157, Q165), reported separately from primary metrics.
- **Weak hard negatives:** in `similar_distinct`, 4 of 16 queries have no graded-0 judged record from the same topic as the target (mean 2.1). Hard-negative strength is moderate.
- **No-answer queries:** 20 intended no-answer (+2 that turned out to be covered: Q157 partly). Top-1 score AUROC (BM25 0.985, stand-in 0.760) says nothing about MiniLM yet.
- **Domain skew:** Machine Learning has 30 queries, NLP 13; per-domain metrics for small domains (13–20 queries) have wide uncertainty.
- **Challenge set:** not created. A challenge set built now would again be authored without MiniLM in the loop; it should be designed after seeing real MiniLM failures so it targets them, and reported separately.

## 5. Application readiness (Phase 5)
See `reports/stage2b_flask_integration_plan.md`. Key verified fact: the 666 approved records overlap 0 ids / 0 questions / 0 answers with the 3,618 boilerplate rows (`legacy_guard.check_disjoint`, tested). The app was not touched and its question source is unchanged; scoring code unchanged.

## 6. Verification
- `pytest tests/retrieval`: 94 passed, 1 skipped (sentence-transformers integration test; needs a local model).
- Not re-run on your Windows VM yet at the time of writing this section (see addendum if added).
- v1–v5 and Batches 1–4 untouched; no downloads or mirrors used.

## 7. Measured vs assumed
| Measured | Assumed / unknown |
|---|---|
| BM25 results; stand-in embedder plumbing; tests; corpus/legacy disjointness; eval-set statistics | Any MiniLM or hybrid quality; whether the cached model exists on your PC; Windows install of faiss/torch |

**Final decision: BLOCKED — Real model unavailable.** Retrieval infrastructure is integration-ready; semantic/hybrid quality is unverified. STOPPED after Stage 2B scope; waiting on the model files.

## Addendum — Windows fix (2026-10-14)
`python -m src.retrieval.cli benchmark --backend minilm` failed on Windows with `ModuleNotFoundError: No module named 'resource'` (`benchmark.py` line 7 — the only use in the package). `_rss_mb()` now imports `resource` lazily, falls back to `psutil` if already installed (Windows peak working set), else returns `None` and the JSON field `peak_rss_mb_after_build` is `null`. Linux calculations are unchanged. New `tests/retrieval/test_windows_compat.py` (4 tests; fails if a top-level `import resource` returns). Suite: 98 passed, 1 skipped on Linux sandbox and on the Linux VM with `resource` blocked. I could not run it on Windows Python itself. The MiniLM benchmark is still not run.
