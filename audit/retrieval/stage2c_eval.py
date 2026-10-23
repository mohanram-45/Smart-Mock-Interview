"""Stage 2C-final scoring of the four embedding-text formats (+BM25-qka reference) from the saved real-MiniLM rankings.

Reads: data/retrieval/stage2c/{rankings,formats}_minilm.json, the eval sets (labels never modified):
  dev  : eval_set_v2.jsonl (original Stage 2B labels)  and  stage2c_dev_v2plus.jsonl (+ blind pooled labels for the new candidates)
  chal : challenge_v1/eval_set.jsonl (+ _min/_max sensitivity)
Writes data/retrieval/stage2c/eval_results.json
"""
import json, random, statistics, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from src.retrieval.evaluate import evaluate_retriever, load_eval_set, auroc

S2C = ROOT / "data/retrieval/stage2c"; EV = ROOT / "data/retrieval/eval"
SYSTEMS = ["dense_qka", "dense_question", "dense_qk", "dense_qk_concise", "bm25_qka"]
METRICS = ["success@1", "success@3", "success@5", "mrr@10", "ndcg@5", "success@5_lenient"]


class Dump:
    """Retriever backed by saved rankings (so the exact Stage 2B metric code is reused)."""
    def __init__(self, rank_by_text): self.r = rank_by_text
    def search(self, query, k=10, domain=None):
        return [{"question_id": d, "score": s} for d, s in self.r[query][:k]]


def run_set(name, eval_path, rk, qtext):
    ev = load_eval_set(eval_path)
    out = {}
    for sysname in SYSTEMS:
        r = {qtext[q]: rk[sysname][q] for q in rk[sysname]}
        out[sysname] = evaluate_retriever(Dump(r), ev)
    return ev, out


def boot_ci(a, b, n=3000, seed=7):
    """Paired bootstrap of mean(b - a) over queries."""
    d = [y - x for x, y in zip(a, b)]
    if not d: return None
    rnd = random.Random(seed); m = len(d); means = []
    for _ in range(n):
        means.append(sum(d[rnd.randrange(m)] for _ in range(m)) / m)
    means.sort()
    return {"mean_diff": round(sum(d) / m, 4), "ci95": [round(means[int(.025 * n)], 4), round(means[int(.975 * n)], 4)],
            "wins": sum(x > 0 for x in d), "losses": sum(x < 0 for x in d), "ties": sum(x == 0 for x in d), "n": m}


def paired(res, key, base="dense_qka", primary=True):
    out = {}
    rows = {s: {r["query_id"]: r for r in res[s]["rows"]} for s in res}
    for s in res:
        if s == base: continue
        qs = [q for q, r in rows[base].items() if not r["no_answer"] and (r["has_primary"] or not primary)]
        out[s] = boot_ci([rows[base][q][key] for q in qs], [rows[s][q][key] for q in qs])
    return out


def slim(r):
    o = r["overall"]
    return {"n_answerable": o["n_answerable"], "n_primary": o["n_primary"], **{m: o[m] for m in METRICS},
            "recall@5": o["recall@5"], "unjudged_top10": r["unjudged_fraction_in_top10"],
            "no_answer": r["no_answer"], "by_category": {c: {k: v[k] for k in ("n_queries", "n_primary", "success@1", "success@5", "mrr@10", "ndcg@5")} for c, v in r["by_category"].items()},
            "by_domain": {c: {k: v[k] for k in ("n_primary", "success@1", "success@5", "mrr@10")} for c, v in r["by_domain"].items()}}


def split_by_flag(res, ev, flagset, label):
    """Primary metrics for queries whose best (grade-2) records include / exclude a flagged record."""
    out = {}
    evd = {q["query_id"]: q for q in ev}
    for s, r in res.items():
        g = {"flagged": [], "clean": []}
        for row in r["rows"]:
            if row["no_answer"] or not row["has_primary"]: continue
            prim = {k for k, v in evd[row["query_id"]]["relevant"].items() if v >= 2}
            g["flagged" if prim & flagset else "clean"].append(row)
        out[s] = {k: {"n": len(v), "success@1": round(sum(x["success@1"] for x in v) / len(v), 4) if v else None,
                      "success@5": round(sum(x["success@5"] for x in v) / len(v), 4) if v else None,
                      "mrr@10": round(sum(x["mrr@10"] for x in v) / len(v), 4) if v else None} for k, v in g.items()}
    return {label: out}


def main():
    R = json.load(open(S2C / "rankings_minilm.json")); F = json.load(open(S2C / "formats_minilm.json"))
    docs = {fmt: {d["id"]: d for d in F["docs"][fmt]} for fmt in F["docs"]}
    out = {"corpus_sha256": R["corpus_sha256"], "embedder": R["embedder"], "tokenizer": F["tokenizer"], "token_stats": F["stats"],
           "query_encode_ms": R["query_encode_ms"], "embed_seconds": R["embed_seconds"], "faiss_vs_numpy": R["faiss_vs_numpy_top10_identical_queries"], "sets": {}}
    sets = [("dev_v2", EV / "eval_set_v2.jsonl", "dev"), ("dev_v2plus", EV / "stage2c_dev_v2plus.jsonl", "dev"),
            ("challenge", EV / "challenge_v1/eval_set.jsonl", "challenge"), ("challenge_min", EV / "challenge_v1/eval_set_min.jsonl", "challenge"),
            ("challenge_max", EV / "challenge_v1/eval_set_max.jsonl", "challenge")]
    flagged = {"head_over_budget": {d for d, x in docs["qk_concise"].items() if x["flags"]["head_over_budget"]},
               "answer_cut": {d for d, x in docs["qk_concise"].items() if x["flags"]["answer_cut"]},
               "no_answer_sentence": {d for d, x in docs["qk_concise"].items() if x["flags"]["answer_sentences"] == 0},
               "qka_truncated": {d for d, x in docs["qka"].items() if x["tokens"] > 256}}
    out["flagged_counts"] = {k: len(v) for k, v in flagged.items()}
    for name, path, which in sets:
        if not path.exists(): continue
        ev0 = load_eval_set(path)
        qtext = {q["query_id"]: q["query"] for q in ev0}
        rk = {s: R["sets"][which]["rankings"][s] for s in SYSTEMS}
        ev, res = run_set(name, path, rk, qtext)
        entry = {"systems": {s: slim(r) for s, r in res.items()},
                 "paired_vs_qka": {k: paired(res, k, primary=(k not in ("ndcg@5",))) for k in ("success@1", "success@5", "mrr@10", "ndcg@5")}}
        for lab, fs in flagged.items():
            entry.setdefault("by_relevant_record_flag", {}).update(split_by_flag(res, ev, fs, lab))
        # failures of every system at top-1 (primary)
        fails = {}
        for s, r in res.items():
            fails[s] = [{"query_id": row["query_id"], "category": row["category"], "ranked": row["ranked"][:3]} for row in r["rows"]
                        if not row["no_answer"] and row["has_primary"] and row["success@1"] == 0]
        entry["top1_failures"] = fails
        # rows needed by later analyses
        entry["_rows"] = {s: [{k: row[k] for k in ("query_id", "category", "domain", "no_answer", "has_primary", "success@1", "success@5", "mrr@10", "ndcg@5", "top1_score", "ranked")} for row in r["rows"]] for s, r in res.items()}
        out["sets"][name] = entry
    json.dump(out, open(S2C / "eval_results.json", "w"), indent=1)
    for name, e in out["sets"].items():
        print(f"\n== {name} ==")
        for s, r in e["systems"].items():
            print(f"{s:18s} n_prim={r['n_primary']:3d} S@1={r['success@1']:.3f} S@3={r['success@3']:.3f} S@5={r['success@5']:.3f} MRR={r['mrr@10']:.3f} nDCG@5={r['ndcg@5']:.3f} unj={r['unjudged_top10']:.3f} AUROC_noans={r['no_answer']['top1_score_auroc_answerable_vs_no_answer']}")


if __name__ == "__main__":
    main()
