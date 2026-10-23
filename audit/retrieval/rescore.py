"""Stage 2B final: re-score the SAVED rankings of every system under original (v1.1) and pooled (v2) labels.

Rankings come from the actual Windows MiniLM run (immutable copy); nothing is re-embedded. Metric code is the
project's own `evaluate_retriever`, fed through a replay retriever, so definitions are identical to the earlier benchmarks.
Latency/index/model numbers are taken from the Windows run, not recomputed.
"""
import json, random, statistics, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from src.retrieval.evaluate import evaluate_retriever, load_eval_set, auroc

EV = ROOT / "data/retrieval/eval"; SRC = EV / "immutable_pre_pooling_stage2b"
bench = json.load(open(SRC / "retrieval_benchmark_minilm.json"))
LABELS = {"v1.1_original": SRC / "eval_set.jsonl", "v2_pooled": EV / "eval_set_v2.jsonl",
          "v2_conservative(min)": EV / "eval_set_v2_min.jsonl", "v2_lenient(max)": EV / "eval_set_v2_max.jsonl"}
SYS = list(bench["systems"])

class Replay:
    def __init__(self, rows): self.by = {r["_q"]: r for r in rows}
    def search(self, query, k=10, domain=None):
        r = self.by[query]
        return [{"question_id": d, "score": (r["top1_score"] if i == 0 else 0.0)} for i, d in enumerate(r["ranked"][:k])]

def replay_for(sysname, ev):
    q_by_id = {q["query_id"]: q["query"] for q in ev}
    rows = [dict(r, _q=q_by_id[r["query_id"]]) for r in bench["systems"][sysname]["rows"]]
    return Replay(rows)

def pb(vals, n=2000, seed=7):
    rnd = random.Random(seed); m = len(vals); bs = sorted(sum(vals[rnd.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return bs[int(.025 * n)], bs[int(.975 * n)]

out = {"source": "reports/retrieval_benchmark_minilm.json (Windows, real all-MiniLM-L6-v2)", "labels": {}}
for lname, path in LABELS.items():
    ev = load_eval_set(path); res = {}
    for s in SYS:
        r = evaluate_retriever(replay_for(s, ev), ev)
        r["latency_ms"] = bench["systems"][s]["latency_ms"]   # Windows-measured, not the replay's
        res[s] = r
    out["labels"][lname] = res
# --- paired bootstrap on the primary (v2_pooled) labels, per mode
ev = load_eval_set(LABELS["v2_pooled"]); P = out["labels"]["v2_pooled"]
def per_q(s, key):
    rows = {r["query_id"]: r for r in P[s]["rows"]}
    ans = [q["query_id"] for q in ev if not q["no_answer"]]
    prim = [q for q in ans if rows[q]["has_primary"]]
    ids = prim if key in ("success@1", "success@3", "success@5", "mrr@10", "recall@5") else ans
    return {q: rows[q][key] for q in ids}
out["paired"] = {}
for mode in ("q", "qk", "qka"):
    for key in ("success@1", "success@5", "mrr@10", "ndcg@5"):
        for a, b in ((f"minilm_{mode}", f"bm25_{mode}"), (f"hybrid_minilm_{mode}", f"bm25_{mode}"), (f"hybrid_minilm_{mode}", f"minilm_{mode}")):
            A, B = per_q(a, key), per_q(b, key); ids = sorted(set(A) & set(B)); d = [A[i] - B[i] for i in ids]
            lo, hi = pb(d)
            out["paired"][f"{mode}|{key}|{a} - {b}"] = {"n": len(d), "mean_diff": round(statistics.mean(d), 4), "ci95": [round(lo, 4), round(hi, 4)],
                                                      "wins": sum(x > 0 for x in d), "losses": sum(x < 0 for x in d), "ties": sum(x == 0 for x in d)}
# --- no-answer detection: top-1 score of the *component* retrievers (hybrid RRF score is rank-based, so use components)
na = {}
for mode in ("q", "qk", "qka"):
    for s in (f"bm25_{mode}", f"minilm_{mode}", f"hybrid_minilm_{mode}"):
        rows = {r["query_id"]: r for r in P[s]["rows"]}
        ans = [rows[q["query_id"]]["top1_score"] for q in ev if not q["no_answer"]]; no = [rows[q["query_id"]]["top1_score"] for q in ev if q["no_answer"]]
        na[s] = {"auroc_top1_score": auroc(ans, no), "n_answerable": len(ans), "n_no_answer": len(no),
                 "mean_top1_answerable": statistics.mean(ans), "mean_top1_no_answer": statistics.mean(no)}
out["no_answer_auroc"] = na
json.dump(out, open(ROOT / "reports/stage2b_final_benchmark.json", "w"), indent=1)
# compact print
def row(l, s):
    o = out["labels"][l][s]["overall"]; return f"{s:20s} S@1 {o['success@1']:.3f} S@3 {o['success@3']:.3f} S@5 {o['success@5']:.3f} R@1 {o['recall@1']:.3f} R@3 {o['recall@3']:.3f} R@5 {o['recall@5']:.3f} MRR {o['mrr@10']:.3f} nDCG@5 {o['ndcg@5']:.3f} unj {out['labels'][l][s]['unjudged_fraction_in_top10']:.3f}"
for l in LABELS:
    print("==", l, "n_primary", out["labels"][l][SYS[0]]["overall"]["n_primary"], "n_answerable", out["labels"][l][SYS[0]]["overall"]["n_answerable"])
    for s in SYS: print(row(l, s))
