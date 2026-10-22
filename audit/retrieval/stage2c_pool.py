"""Stage 2C-final pooled blind relevance assessment for the NEW format results (immutable inputs; writes NEW files only).

  make    <dev|challenge> [n_shards]   shards of every top-10 candidate (dev: only pairs not already judged in eval_set_v2)
  merge12 <dev|challenge>              agreement stats + pass-3 shards for disputed pairs
  merge3  <dev|challenge>              final grades -> data/retrieval/eval/stage2c_dev_v2plus*.jsonl  |  challenge_v1/eval_set*.jsonl

Pools come from the DENSE rankings of all four formats (+ BM25-qka for the challenge set, as the lexical baseline). Labellers see only
anonymised, shuffled candidates: never the format, rank, score or system. Same protocol/brief as Stage 2B (two independent passes, third pass
on disputes only, final = median). Labels are AI-generated; no human review.
"""
import json, random, statistics, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "audit/retrieval"))
from pool_label import _cand, kappa            # same candidate rendering + kappa as Stage 2B
EV = ROOT / "data/retrieval/eval"
RANK = ROOT / "data/retrieval/stage2c/rankings_minilm.json"
FM = ["qka", "question", "qk", "qk_concise"]

def _load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def H(s): return ROOT / "audit/retrieval/pooling" / f"stage2c_{s}"

def base_rows(s):
    return _load(EV / "eval_set_v2.jsonl") if s == "dev" else _load(EV / "challenge_v1/queries.jsonl")

def pairs_for(s):
    rk = json.load(open(RANK))["sets"][s]["rankings"]; rows = {q["query_id"]: q for q in base_rows(s)}; out = {}
    for qid, q in rows.items():
        cand = set()
        for f in FM: cand |= {d for d, _ in rk[f"dense_{f}"][qid][:10]}
        if s == "challenge": cand |= {d for d, _ in rk["bm25_qka"][qid][:10]}
        else: cand -= set(q["judged"])
        if cand: out[qid] = sorted(cand)
    return rows, out

def make(s, n_shards=8):
    from src.retrieval.corpus import load_corpus
    by = {r["question_id"]: r for r in load_corpus()["records"]}
    rows, pairs = pairs_for(s); d = H(s); d.mkdir(parents=True, exist_ok=True); json.dump(pairs, open(d / "pairs.json", "w"))
    for p in (1, 2):
        rnd = random.Random(7000 * p + (1 if s == "dev" else 2)); qids = sorted(pairs); rnd.shuffle(qids); order, anchors = {}, {}
        for sh in range(n_shards):
            items = []
            for qid in qids[sh::n_shards]:
                q = rows[qid]; an = []
                if s == "dev":
                    J = q["judged"]; pos = [j for j in J if q["relevant"].get(j, 0) >= 1]; neg = [j for j in J if q["relevant"].get(j, 0) == 0]
                    an = ([rnd.choice(sorted(pos))] if pos else []) + ([rnd.choice(sorted(neg))] if neg else [])
                pool = pairs[qid] + an; rnd.shuffle(pool); order[qid] = pool; anchors[qid] = an
                items.append({"query_id": qid, "query": q["query"], "candidates": [_cand(by, r, j) for j, r in enumerate(pool, 1)]})
            json.dump(items, open(d / f"shard{p}_{sh}.json", "w"), indent=1, ensure_ascii=False)
        json.dump(order, open(d / f"order{p}.json", "w")); json.dump(anchors, open(d / f"anchors{p}.json", "w"))
    json.dump({"n_shards": n_shards}, open(d / "meta.json", "w"))
    print(f"{s}: {sum(map(len, pairs.values()))} pairs over {len(pairs)} queries, {n_shards} shards/pass in {d}")

def _read_pass(d, p, n):
    order = json.load(open(d / f"order{p}.json")); g = {}
    for sh in range(n):
        for x in json.load(open(d / f"out{p}_{sh}.json")):
            pool = order[x["query_id"]]; exp = {f"c{j}" for j in range(1, len(pool) + 1)}
            assert exp <= set(x["grades"]), (p, x["query_id"], "missing grades")
            extra = set(x["grades"]) - exp
            if extra: print(f"WARNING pass {p} {x['query_id']}: ignoring spurious keys {sorted(extra)}")
            assert all(v in (0, 1, 2) for v in x["grades"].values())
            g[x["query_id"]] = {pool[int(c[1:]) - 1]: v for c, v in x["grades"].items() if c in exp}
    return g

def merge12(s):
    from src.retrieval.corpus import load_corpus
    by = {r["question_id"]: r for r in load_corpus()["records"]}
    d = H(s); n = json.load(open(d / "meta.json"))["n_shards"]; pairs = json.load(open(d / "pairs.json")); rows = {q["query_id"]: q for q in base_rows(s)}
    g1, g2 = _read_pass(d, 1, n), _read_pass(d, 2, n); assert set(g1) == set(g2) == set(pairs)
    a1, a2, dispute = [], [], {}
    for q in pairs:
        for r in pairs[q]:
            a1.append(g1[q][r]); a2.append(g2[q][r])
            if g1[q][r] != g2[q][r]: dispute.setdefault(q, []).append(r)
    anch = {}
    if s == "dev":
        for p, g in ((1, g1), (2, g2)):
            an = json.load(open(d / f"anchors{p}.json")); nn = ag = 0; cm = Counter()
            for q, ids in an.items():
                for r in ids:
                    old = rows[q]["relevant"].get(r, 0); new = g[q][r]; nn += 1; ag += (old == new); cm[f"{old}->{new}"] += 1
            anch[p] = {"n": nn, "agree": ag, "rate": round(ag / nn, 3), "confusion_old_new": dict(sorted(cm.items()))}
    st = {"n_pairs": len(a1), "raw_agreement": round(sum(x == y for x, y in zip(a1, a2)) / len(a1), 4), "kappa_3class": round(kappa(a1, a2), 4),
          "kappa_grade>=2": round(kappa([int(x >= 2) for x in a1], [int(x >= 2) for x in a2], (0, 1)), 4),
          "kappa_grade>=1": round(kappa([int(x >= 1) for x in a1], [int(x >= 1) for x in a2], (0, 1)), 4),
          "n_disputed": sum(map(len, dispute.values())), "disputed_grade2_involved": sum(1 for q in dispute for r in dispute[q] if 2 in (g1[q][r], g2[q][r])),
          "pass1_distribution": dict(Counter(a1)), "pass2_distribution": dict(Counter(a2)), "anchors": anch}
    json.dump(st, open(d / "stats12.json", "w"), indent=1); json.dump(dispute, open(d / "disputed.json", "w"))
    rnd = random.Random(9033); qids = sorted(dispute); rnd.shuffle(qids); order = {}; n3 = max(1, min(n, len(qids)))
    for sh in range(n3):
        items = []
        for qid in qids[sh::n3]:
            pool = dispute[qid][:]; rnd.shuffle(pool); order[qid] = pool
            items.append({"query_id": qid, "query": rows[qid]["query"], "candidates": [_cand(by, r, j) for j, r in enumerate(pool, 1)]})
        json.dump(items, open(d / f"shard3_{sh}.json", "w"), indent=1, ensure_ascii=False)
    json.dump(order, open(d / "order3.json", "w")); json.dump({"n_shards": n3}, open(d / "meta3.json", "w"))
    print(json.dumps(st, indent=1)); print("pass-3 shards:", n3)

def merge3(s):
    d = H(s); n = json.load(open(d / "meta.json"))["n_shards"]; pairs = json.load(open(d / "pairs.json")); dispute = json.load(open(d / "disputed.json"))
    g1, g2 = _read_pass(d, 1, n), _read_pass(d, 2, n); n3 = json.load(open(d / "meta3.json"))["n_shards"]; order = json.load(open(d / "order3.json")); g3 = {}
    for sh in range(n3):
        for x in json.load(open(d / f"out3_{sh}.json")):
            pool = order[x["query_id"]]; exp = {f"c{j}" for j in range(1, len(pool) + 1)}; assert exp <= set(x["grades"])
            g3[x["query_id"]] = {pool[int(c[1:]) - 1]: v for c, v in x["grades"].items() if c in exp}
    assert set(g3) == set(dispute)
    final, unresolved = {}, []
    for q in pairs:
        for r in pairs[q]:
            a, b = g1[q][r], g2[q][r]
            if a == b: v = a
            else:
                c = g3[q][r]; v = int(statistics.median([a, b, c]))
                if len({a, b, c}) == 3: unresolved.append({"query_id": q, "record": r, "grades": [a, b, c], "assigned": v})
            final[(q, r)] = v
    variants = {"": lambda q, r: final[(q, r)], "_min": lambda q, r: min(g1[q][r], g2[q][r]), "_max": lambda q, r: max(g1[q][r], g2[q][r])}
    rep = {"set": s, "n_pairs": len(final), "final_grade_distribution": dict(Counter(final.values())), "unresolved_three_way_splits": unresolved,
           "pass3_changed_vs": {"pass1": sum(final[k] != g1[k[0]][k[1]] for k in final), "pass2": sum(final[k] != g2[k[0]][k[1]] for k in final)},
           "note": "AI-generated judgements; no human ground truth. Same model family as the query author and the retrieval-format designer."}
    flips = []
    for suffix, fn in variants.items():
        rows = base_rows(s); out = []
        for row in rows:
            q = row["query_id"]
            if s == "dev":
                row = json.loads(json.dumps(row)); row["no_answer_v2"] = row["no_answer"]
                for r in pairs.get(q, []):
                    v = fn(q, r)
                    if v > 0: row["relevant"][r] = v
                    if r not in row["judged"]: row["judged"].append(r)
                row["no_answer"] = not row["relevant"]
                row["label_method"] += "; + Stage 2C pooled assessment of new-format candidates"
                if row["no_answer_v2"] and not row["no_answer"] and suffix == "": flips.append({"query_id": q, "query": row["query"], "new_relevant": row["relevant"]})
            else:
                rel = {r: fn(q, r) for r in pairs.get(q, []) if fn(q, r) > 0}
                row = {"query_id": q, "query": row["query"], "category": row["category"], "domain": row["domain_hint"], "relevant": rel,
                       "judged": pairs.get(q, []), "no_answer": not rel, "intended_no_answer": row["intended_no_answer"],
                       "label_method": "Stage 2C blind pooled assessment (2 independent AI passes + adjudication of disputes; grade = " + {"": "median of 3 on disputes", "_min": "min of 2 passes", "_max": "max of 2 passes"}[suffix] + ")"}
                if suffix == "" and row["intended_no_answer"] != row["no_answer"]: flips.append({"query_id": q, "intended_no_answer": row["intended_no_answer"], "labelled_no_answer": row["no_answer"], "relevant": rel})
            out.append(row)
        path = (EV / f"stage2c_dev_v2plus{suffix}.jsonl") if s == "dev" else (EV / f"challenge_v1/eval_set{suffix}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for row in out: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    rep["flips_vs_prior_or_intent"] = flips
    json.dump(rep, open(d / "pooling_report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1)[:3000])

if __name__ == "__main__":
    c, s = sys.argv[1], sys.argv[2]
    {"make": lambda: make(s, int(sys.argv[3]) if len(sys.argv) > 3 else 8), "merge12": lambda: merge12(s), "merge3": lambda: merge3(s)}[c]()
