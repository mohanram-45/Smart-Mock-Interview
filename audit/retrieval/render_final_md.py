"""Render reports/stage2b_final_benchmark.md from reports/stage2b_final_benchmark.json (no hand-typed numbers)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
F = json.load(open(ROOT / "reports/stage2b_final_benchmark.json")); B = json.load(open(ROOT / "data/retrieval/eval/immutable_pre_pooling_stage2b/retrieval_benchmark_minilm.json"))
A = json.load(open(ROOT / "reports/stage2b_final_analysis.json"))
f3 = lambda x: "-" if x is None else f"{x:.3f}"
NAMES = {"bm25": "BM25", "minilm": "MiniLM+FAISS", "hybrid_minilm": "Hybrid (RRF)"}
L = ["# Stage 2B — final benchmark (real all-MiniLM-L6-v2, Windows run; pooled labels v2)", "",
     "Source rankings: `data/retrieval/eval/immutable_pre_pooling_stage2b/retrieval_benchmark_minilm.json` (Windows 11, Python 3.12.7, 12 CPUs). Metrics recomputed with the project's own metric code; replaying the original labels reproduces the Windows numbers exactly (test `test_replay_reproduces_windows_benchmark_under_original_labels`).",
     "Labels: AI-generated pooled judgements (two blind passes + adjudication), **not human ground truth**. 166 queries: 146 answerable (140 have a grade-2 record), 20 no-answer. Success/Recall/MRR use grade ≥ 2 over the 140; nDCG@5 uses graded gain over the 146.", ""]
def tbl(label):
    P = F["labels"][label]; r = ["| Mode | System | S@1 | S@3 | S@5 | R@1 | R@3 | R@5 | MRR@10 | nDCG@5 | Unjudged@10 |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m in ("q", "qk", "qka"):
        for fam in ("bm25", "minilm", "hybrid_minilm"):
            s = f"{fam}_{m}"; o = P[s]["overall"]
            r.append(f"| {m} | {NAMES[fam]} | " + " | ".join(f3(o[k]) for k in ("success@1", "success@3", "success@5", "recall@1", "recall@3", "recall@5", "mrr@10", "ndcg@5")) + f" | {P[s]['unjudged_fraction_in_top10']:.3f} |")
    return r
L += ["## 1. Main comparison — pooled labels (v2, primary)", ""] + tbl("v2_pooled") + [""]
L += ["## 2. Before pooling (original labels v1.1) — shows the effect of the missing judgements", ""] + tbl("v1.1_original") + [""]
L += ["Unjudged@10 under v1.1 for MiniLM was 46.4% / 43.9% / 42.1% (q / qk / qka) and for hybrid 23.0% / 19.6% / 19.0%; all are 0.000 under v2.", ""]
L += ["## 3. Label-variant sensitivity (qka)", "", "| Labels | System | S@1 | S@5 | R@5 | MRR@10 | nDCG@5 |", "|---|---|---:|---:|---:|---:|---:|"]
for lab in ("v1.1_original", "v2_conservative(min)", "v2_pooled", "v2_lenient(max)"):
    for fam in ("bm25", "minilm", "hybrid_minilm"):
        o = F["labels"][lab][f"{fam}_qka"]["overall"]; L.append(f"| {lab} | {NAMES[fam]} | {f3(o['success@1'])} | {f3(o['success@5'])} | {f3(o['recall@5'])} | {f3(o['mrr@10'])} | {f3(o['ndcg@5'])} |")
L += ["", "Success@k and MRR are identical across variants because the pooled pairs added only 3 grade-2 judgements (and 106 grade-1); only Recall and nDCG move, by ≤ 0.02.", ""]
L += ["## 4. Paired differences with 95% bootstrap CI (v2 labels; 2,000 query resamples, seed 7; per-query)", "", "| Mode | Metric | Comparison | Mean diff | 95% CI | W / L / T |", "|---|---|---|---:|---|---|"]
for k, v in F["paired"].items():
    mode, met, cmp_ = k.split("|")
    if met in ("success@1", "mrr@10", "ndcg@5", "success@5"):
        cmp_ = cmp_.replace("hybrid_minilm", "Hybrid").replace("minilm", "MiniLM").replace("bm25", "BM25").replace(f"_{mode}", "")
        L.append(f"| {mode} | {met} | {cmp_} | {v['mean_diff']:+.3f} | [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}] | {v['wins']}/{v['losses']}/{v['ties']} |")
L += ["", "A CI excluding 0 means the difference is unlikely to be query-sampling noise **on this set only**; it says nothing about other queries or about label error, and the same 166 queries were used to choose the document mode (see §9).", ""]
L += ["## 5. By domain (qka, v2 labels; n = primary queries; S@1 / S@5 / MRR@10)", "", "| Domain | n | BM25 | MiniLM | Hybrid |", "|---|---:|---|---|---|"]
P = F["labels"]["v2_pooled"]
for d in sorted(P["bm25_qka"]["by_domain"]):
    c = [P[s]["by_domain"][d] for s in ("bm25_qka", "minilm_qka", "hybrid_minilm_qka")]
    L.append(f"| {d} | {c[0]['n_primary']} | " + " | ".join(f"{x['success@1']:.2f} / {x['success@5']:.2f} / {x['mrr@10']:.2f}" for x in c) + " |")
L += ["", "Domains have 12–28 queries each: one query is 4–8 points of Success. Do not read rank differences between domains as established.", ""]
L += ["## 6. By query category (qka; S@1 / S@5 / nDCG@5)", "", "| Category | n answerable | BM25 | MiniLM | Hybrid |", "|---|---:|---|---|---|"]
for c in sorted(P["bm25_qka"]["by_category"]):
    x = [P[s]["by_category"][c] for s in ("bm25_qka", "minilm_qka", "hybrid_minilm_qka")]
    if x[0]["n_answerable"] == 0: continue
    L.append(f"| {c} | {x[0]['n_answerable']} | " + " | ".join(f"{f3(y['success@1'])} / {f3(y['success@5'])} / {f3(y['ndcg@5'])}" for y in x) + " |")
L += ["", "## 7. Out-of-corpus (no-answer) detection — 20 no-answer vs 146 answerable queries", "", "| Mode | System | AUROC of top-1 score | mean top-1 (answerable) | mean top-1 (no-answer) |", "|---|---|---:|---:|---:|"]
for k, v in F["no_answer_auroc"].items():
    fam = "hybrid_minilm" if k.startswith("hybrid") else "minilm" if k.startswith("minilm") else "bm25"
    L.append(f"| {k.split('_')[-1]} | {NAMES[fam]}{' (RRF score, rank-based)' if fam=='hybrid_minilm' else ''} | {v['auroc_top1_score']:.3f} | {v['mean_top1_answerable']:.3f} | {v['mean_top1_no_answer']:.3f} |")
op = A["no_answer_operating_points"]["minilm_qka"]
L += ["", "MiniLM top-1 cosine (qka) — highest-scoring no-answer queries: " + "; ".join(f"{s} {q} “{t}…”" for s, q, t in op["highest_scoring_no_answer_queries"][:3]) + ".", "",
      "Illustrative abstention thresholds on MiniLM top-1 cosine (**chosen on these same queries → optimistic; must be re-calibrated on fresh data**):", "", "| Threshold | no-answer rejected | answerable wrongly rejected |", "|---:|---:|---:|"]
for p in op["operating_points (illustrative; thresholds chosen on these same queries -> optimistic)"]:
    if 0.35 <= p["threshold"] <= 0.55: L.append(f"| {p['threshold']:.2f} | {p['no_answer_rejected']:.2f} | {p['answerable_wrongly_rejected']:.3f} |")
L += ["", "The hybrid's fused RRF score is rank-based (its top-1 value is nearly constant), so abstention for the hybrid has to read the MiniLM cosine or BM25 score from `components`.", ""]
L += ["## 8. Cost (Windows run, CPU)", "", "| Item | BM25 | MiniLM+FAISS | Hybrid |", "|---|---:|---:|---:|"]
lat = lambda s: B["systems"][s]["latency_ms"]
L.append(f"| Query latency qka, mean / median / p95 / max (ms; 166 queries, single-threaded loop) | {lat('bm25_qka')['mean']:.2f} / {lat('bm25_qka')['median']:.2f} / {lat('bm25_qka')['p95']:.2f} / {lat('bm25_qka')['max']:.2f} | {lat('minilm_qka')['mean']:.1f} / {lat('minilm_qka')['median']:.1f} / {lat('minilm_qka')['p95']:.1f} / {lat('minilm_qka')['max']:.1f} | {lat('hybrid_minilm_qka')['mean']:.1f} / {lat('hybrid_minilm_qka')['median']:.1f} / {lat('hybrid_minilm_qka')['p95']:.1f} / {lat('hybrid_minilm_qka')['max']:.1f} |")
mq = B["systems"]["minilm_qka"]
L.append(f"| Build (666 docs, qka) | {B['systems']['bm25_qka']['build_seconds']:.2f} s | {mq['index_build']['total_build_seconds']:.1f} s (embedding {mq['index_build']['embed_seconds']:.1f} s; cold, 0 cache hits) | both |")
L.append(f"| Index on disk (qka) | in memory | {mq['index_bytes']/1e6:.2f} MB (vectors {mq['vector_bytes_theoretical']/1e6:.2f} MB) | both |")
L.append(f"| Model load | – | {mq['model_load_seconds']:.2f} s | same |")
L.append(f"| Peak process memory after qka build | not measured | {mq['peak_rss_mb_after_build']:.0f} MB (whole process incl. PyTorch; cumulative across the three modes, so an upper bound for qka alone) | same |")
L += ["", "Latency includes query encoding for MiniLM and hybrid. It is measured on this PC, not a server.", ""]
L += ["## 9. Design validation", "", "See `reports/stage2b_error_analysis.md` §1 for leakage checks, answer-text effect and truncation.", ""]
(ROOT / "reports/stage2b_final_benchmark.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L)[:6000])
