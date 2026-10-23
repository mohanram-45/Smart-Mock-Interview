"""Label retrieved-but-unjudged (query, record) pairs so pooling bias is removed for a given benchmark run.

  python audit/retrieval/gap_label.py make  <benchmark.json> <tag> [n_shards]   -> labelling/gap_<tag>/shard{1,2}_i.json
  (label shards with two independent blind passes, same LABEL_BRIEF.md, output out{1,2}_i.json)
  python audit/retrieval/gap_label.py merge <tag>                              -> updates data/retrieval/eval/*.jsonl

Both passes see only anonymised candidates (no ranker, rank, score or author-target information).
Grade = min of the two passes in eval_set.jsonl (consensus) and max in eval_set_union_labels.jsonl.
"""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
H = ROOT / "audit/retrieval"
EV = ROOT / "data/retrieval/eval"

def _load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def make(bench, tag, n_shards=4):
    from src.retrieval.corpus import load_corpus
    by = {r["question_id"]: r for r in load_corpus()["records"]}
    res = json.load(open(bench))
    ev = {q["query_id"]: q for q in _load(EV / "eval_set.jsonl")}
    gaps = {}
    for sysname, r in res["systems"].items():
        for row in r["rows"]:
            q = ev[row["query_id"]]
            for rid in row["ranked"][:10]:
                if rid not in set(q["judged"]):
                    gaps.setdefault(row["query_id"], set()).add(rid)
    d = H / f"labelling/gap_{tag}"; d.mkdir(parents=True, exist_ok=True)
    pairs = {qid: sorted(v) for qid, v in gaps.items()}
    json.dump(pairs, open(d / "pairs.json", "w"))
    for p in (1, 2):
        rnd = random.Random(1000 * p + 7)
        qids = sorted(pairs); rnd.shuffle(qids)
        order = {}
        for s in range(n_shards):
            items = []
            for qid in qids[s::n_shards]:
                pool = pairs[qid][:]; rnd.shuffle(pool); order[qid] = pool
                items.append({"query_id": qid, "query": ev[qid]["query"], "candidates": [
                    {"c": f"c{j}", "domain": by[r]["domain"], "topic": by[r]["topic"], "question": by[r]["question"],
                     "key_concepts": by[r]["key_concepts"], "answer_excerpt": by[r]["canonical_answer"][:450]} for j, r in enumerate(pool, 1)]})
            json.dump(items, open(d / f"shard{p}_{s}.json", "w"), indent=1, ensure_ascii=False)
        json.dump(order, open(d / f"order{p}.json", "w"))
    print(f"{sum(len(v) for v in pairs.values())} gap pairs over {len(pairs)} queries -> {d}")

def merge(tag, n_shards=4):
    d = H / f"labelling/gap_{tag}"
    g = {1: {}, 2: {}}
    for p in (1, 2):
        order = json.load(open(d / f"order{p}.json"))
        for s in range(n_shards):
            for x in json.load(open(d / f"out{p}_{s}.json")):
                pool = order[x["query_id"]]
                assert set(x["grades"]) == {f"c{j}" for j in range(1, len(pool) + 1)}, x["query_id"]
                g[p][x["query_id"]] = {pool[int(c[1:]) - 1]: v for c, v in x["grades"].items()}
    pairs = json.load(open(d / "pairs.json"))
    assert set(g[1]) == set(g[2]) == set(pairs)
    for name, fn in (("eval_set.jsonl", min), ("eval_set_union_labels.jsonl", max)):
        rows = _load(EV / name)
        for r in rows:
            qid = r["query_id"]
            if qid not in pairs: continue
            for rid in pairs[qid]:
                v = fn(g[1][qid][rid], g[2][qid][rid])
                if v > 0: r["relevant"][rid] = v
                if rid not in r["judged"]: r["judged"].append(rid)
            r["no_answer"] = not r["relevant"]
            r["label_method"] += f"; extended by gap labelling '{tag}'"
        with open(EV / name, "w", encoding="utf-8") as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    agree = sum(g[1][q][r] == g[2][q][r] for q in pairs for r in pairs[q]); tot = sum(len(v) for v in pairs.values())
    print(f"merged {tot} judgements; raw agreement {agree/tot:.3f}")

if __name__ == "__main__":
    if sys.argv[1] == "make": make(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 4)
    else: merge(sys.argv[2])
