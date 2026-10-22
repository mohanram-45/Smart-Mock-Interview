"""Stage 8B: offline, read-only probe of two retrieval ideas on the STORED Stage 2C MiniLM rankings (no model, no download, no network).

    python scripts/stage8_retrieval_probe.py            # prints the table and writes reports/stage8_retrieval_probe.json
    python scripts/stage8_retrieval_probe.py --check    # exit 1 if the committed JSON differs from a recomputation

1. Key-concept-coverage reranking of the stored top-30 dense (qk_concise) candidates: score' = cosine + w * (share of key concepts mentioned in the query).
2. The top-score evidence band from src/retrieval/evidence.py, on the dev set and on the frozen challenge set.
Labels are AI-pooled (not human ground truth). The dev set is where the band was chosen; the challenge set was frozen before and is reported separately."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.retrieval import evidence  # noqa: E402
from src.retrieval.corpus import load_corpus  # noqa: E402
from src.retrieval.evaluate import load_eval_set, mrr_at_k, ndcg_at_k, success_at_k  # noqa: E402
from src.retrieval.lexical import tokenize  # noqa: E402

OUT = ROOT / "reports" / "stage8_retrieval_probe.json"
SETS = {"dev": "data/retrieval/eval/stage2c_dev_v2plus.jsonl", "challenge": "data/retrieval/eval/challenge_v1/eval_set.jsonl"}
WEIGHTS = (0.0, 0.05, 0.1, 0.2, 0.3)


def coverage(query, record):
    qt = set(tokenize(query))
    cs = record["key_concepts"]
    if not cs:
        return 0.0
    return sum(1 for c in cs if (ct := set(tokenize(c))) and len(ct & qt) / len(ct) >= 0.5) / len(cs)


def compute():
    recs = {r["question_id"]: r for r in load_corpus(None, strict=True)["records"]}
    R = json.loads((ROOT / "data/retrieval/stage2c/rankings_minilm.json").read_text(encoding="utf-8"))["sets"]
    out = {"basis": "stored Stage 2C MiniLM rankings (dense_qk_concise, top-30); AI-pooled labels, not human ground truth", "rerank": {}, "evidence_band": {}}
    for name, path in SETS.items():
        ev = load_eval_set(ROOT / path)
        rk = R[name]["rankings"]["dense_qk_concise"]
        answerable = [e for e in ev if e["relevant"]]
        rows = {}
        for w in WEIGHTS:
            s1 = mrr = nd = 0.0
            for e in answerable:
                ids = [i for _, i in sorted(((s + w * coverage(e["query"], recs[i]), i) for i, s in rk[e["query_id"]]), reverse=True)]
                s1 += success_at_k(ids, e["relevant"], 1)
                mrr += mrr_at_k(ids, e["relevant"])
                nd += ndcg_at_k(ids, e["relevant"], 5)
            n = len(answerable)
            rows[str(w)] = {"success@1": round(s1 / n, 4), "mrr@10": round(mrr / n, 4), "ndcg@5": round(nd / n, 4)}
        out["rerank"][name] = {"n_answerable": len(answerable), "by_weight": rows}
        bands = {}
        for label, sel in (("no_answer", [e for e in ev if not e["relevant"]]), ("answerable", answerable)):
            c = {"insufficient": 0, "weak": 0, "adequate": 0}
            for e in sel:
                c[evidence.assess_evidence([rk[e["query_id"]][0][1]], "cosine")["band"]] += 1
            bands[label] = {"n": len(sel), **c}
        out["evidence_band"][name] = bands
    d, c = out["rerank"]["dev"]["by_weight"], out["rerank"]["challenge"]["by_weight"]
    out["conclusion"] = {
        "rerank": "NOT adopted: no weight improves success@1 on the dev set (w=0 is best or tied) and the challenge-set change at w=0.1 is 1 query of 40",
        "evidence_band": "kept as an uncalibrated diagnostic only; on the challenge set it misses 4 of 18 no-answer queries",
        "dev_success@1_w0_vs_w0.1": [d["0.0"]["success@1"], d["0.1"]["success@1"]],
        "challenge_success@1_w0_vs_w0.1": [c["0.0"]["success@1"], c["0.1"]["success@1"]],
    }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    res = compute()
    text = json.dumps(res, indent=1, sort_keys=True) + "\n"
    if a.check:
        same = OUT.is_file() and json.loads(OUT.read_text(encoding="utf-8")) == res
        print("probe output matches the committed report" if same else "probe output DIFFERS from the committed report")
        return 0 if same else 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
