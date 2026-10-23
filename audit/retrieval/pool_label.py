"""Stage 2B pooled relevance assessment (immutable inputs; writes NEW v2 files only).

  make    <benchmark.json> <tag> [n_shards]   pass-1/pass-2 shards: every unjudged top-10 pair from ALL systems/modes
                                              (bm25/minilm/hybrid x q/qk/qka), pooled per query, anonymised, shuffled,
                                              plus up to 2 previously-judged "anchor" candidates per query per pass.
  merge12 <tag>                               read out{1,2}_i.json -> agreement, anchor agreement, disputed pairs -> pass-3 shards
  merge3  <tag>                               read out3_i.json -> eval_set_v2*.jsonl (3 variants) + pooling_report.json

Labellers never see which system returned a candidate, its rank or score, nor which candidates are anchors.
Final grade (primary variant) = agreed grade; for pairs where passes 1 and 2 differ, the median of three passes.
Variants: _min = min(pass1, pass2) (the original Stage-2A convention), _max = max(pass1, pass2).
"""
import json, random, sys, statistics
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
EV = ROOT / "data/retrieval/eval"; H = ROOT / "audit/retrieval/pooling"
SRC = EV / "immutable_pre_pooling_stage2b"          # frozen inputs
def _load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def _cand(by, rid, j):
    r = by[rid]
    return {"c": f"c{j}", "domain": r["domain"], "topic": r["topic"], "question": r["question"],
            "key_concepts": r["key_concepts"], "answer_excerpt": r["canonical_answer"][:450]}

def gaps_from(bench):
    ev = {q["query_id"]: q for q in _load(SRC / "eval_set.jsonl")}
    res = json.load(open(bench)); gaps = defaultdict(set); by_sys = defaultdict(lambda: defaultdict(set))
    for sysname, r in res["systems"].items():
        for row in r["rows"]:
            J = set(ev[row["query_id"]]["judged"])
            for d in row["ranked"][:10]:
                if d not in J: gaps[row["query_id"]].add(d); by_sys[sysname][row["query_id"]].add(d)
    return ev, {q: sorted(v) for q, v in gaps.items()}

def make(bench, tag, n_shards=8):
    from src.retrieval.corpus import load_corpus
    by = {r["question_id"]: r for r in load_corpus()["records"]}
    ev, pairs = gaps_from(bench)
    d = H / tag; d.mkdir(parents=True, exist_ok=True)
    json.dump(pairs, open(d / "pairs.json", "w"))
    for p in (1, 2):
        rnd = random.Random(2000 * p + 11); qids = sorted(pairs); rnd.shuffle(qids)
        order, anchors = {}, {}
        for s in range(n_shards):
            items = []
            for qid in qids[s::n_shards]:
                q = ev[qid]; judged = [j for j in q["judged"]]
                pos = [j for j in judged if q["relevant"].get(j, 0) >= 1]; neg = [j for j in judged if q["relevant"].get(j, 0) == 0]
                an = ([rnd.choice(sorted(pos))] if pos else []) + ([rnd.choice(sorted(neg))] if neg else [])
                pool = pairs[qid] + an; rnd.shuffle(pool)
                order[qid] = pool; anchors[qid] = an
                items.append({"query_id": qid, "query": q["query"], "candidates": [_cand(by, r, j) for j, r in enumerate(pool, 1)]})
            json.dump(items, open(d / f"shard{p}_{s}.json", "w"), indent=1, ensure_ascii=False)
        json.dump(order, open(d / f"order{p}.json", "w")); json.dump(anchors, open(d / f"anchors{p}.json", "w"))
    n = sum(len(v) for v in pairs.values())
    print(f"{n} gap pairs over {len(pairs)} queries; shards in {d}")

def _read_pass(d, p, n_shards):
    order = json.load(open(d / f"order{p}.json")); g = {}
    for s in range(n_shards):
        for x in json.load(open(d / f"out{p}_{s}.json")):
            pool = order[x["query_id"]]
            exp = {f"c{j}" for j in range(1, len(pool) + 1)}
            assert exp <= set(x["grades"]), (p, x["query_id"], "missing grades")   # every real candidate must be graded
            extra = set(x["grades"]) - exp
            if extra: print(f"WARNING pass {p} {x['query_id']}: ignoring spurious grade keys {sorted(extra)} (not in shard)")
            assert all(v in (0, 1, 2) for v in x["grades"].values())
            g[x["query_id"]] = {pool[int(c[1:]) - 1]: v for c, v in x["grades"].items() if c in exp}
    return g

def kappa(a, b, cats=(0, 1, 2)):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0

def merge12(tag, n_shards=8):
    from src.retrieval.corpus import load_corpus
    by = {r["question_id"]: r for r in load_corpus()["records"]}
    d = H / tag; pairs = json.load(open(d / "pairs.json")); ev = {q["query_id"]: q for q in _load(SRC / "eval_set.jsonl")}
    g1, g2 = _read_pass(d, 1, n_shards), _read_pass(d, 2, n_shards)
    assert set(g1) == set(g2) == set(pairs)
    a1, a2 = [], []; dispute = {}
    for q in pairs:
        for r in pairs[q]:
            a1.append(g1[q][r]); a2.append(g2[q][r])
            if g1[q][r] != g2[q][r]: dispute.setdefault(q, []).append(r)
    # anchors: new labels vs existing consensus
    anch = {"n": 0, "agree": 0, "by_pass": {}}
    for p, g in ((1, g1), (2, g2)):
        an = json.load(open(d / f"anchors{p}.json")); n = ag = 0; cm = Counter()
        for q, ids in an.items():
            for r in ids:
                old = ev[q]["relevant"].get(r, 0); new = g[q][r]; n += 1; ag += (old == new); cm[(old, new)] += 1
        anch["by_pass"][p] = {"n": n, "agree": ag, "rate": round(ag / n, 3), "confusion_old_new": {f"{o}->{nw}": c for (o, nw), c in sorted(cm.items())}}
    stats = {"n_pairs": len(a1), "raw_agreement": round(sum(x == y for x, y in zip(a1, a2)) / len(a1), 4),
             "kappa_3class": round(kappa(a1, a2), 4),
             "kappa_grade>=2": round(kappa([int(x >= 2) for x in a1], [int(x >= 2) for x in a2], (0, 1)), 4),
             "kappa_grade>=1": round(kappa([int(x >= 1) for x in a1], [int(x >= 1) for x in a2], (0, 1)), 4),
             "n_disputed": sum(len(v) for v in dispute.values()), "disputed_grade2_involved": sum(1 for q in dispute for r in dispute[q] if 2 in (g1[q][r], g2[q][r])),
             "pass1_distribution": dict(Counter(a1)), "pass2_distribution": dict(Counter(a2)), "anchors": anch}
    json.dump(stats, open(d / "stats12.json", "w"), indent=1); json.dump(dispute, open(d / "disputed.json", "w"))
    # pass-3 shards: disputed pairs only, fresh shuffle, no pass-1/2 grades shown
    rnd = random.Random(3033); qids = sorted(dispute); rnd.shuffle(qids); order = {}; n3 = max(1, min(n_shards, len(qids)))
    for s in range(n3):
        items = []
        for qid in qids[s::n3]:
            pool = dispute[qid][:]; rnd.shuffle(pool); order[qid] = pool
            items.append({"query_id": qid, "query": ev[qid]["query"], "candidates": [_cand(by, r, j) for j, r in enumerate(pool, 1)]})
        json.dump(items, open(d / f"shard3_{s}.json", "w"), indent=1, ensure_ascii=False)
    json.dump(order, open(d / "order3.json", "w")); json.dump({"n_shards": n3}, open(d / "meta3.json", "w"))
    print(json.dumps(stats, indent=1)); print("pass-3 shards:", n3, "disputed pairs:", stats["n_disputed"])

def merge3(tag, n_shards=8):
    d = H / tag; pairs = json.load(open(d / "pairs.json")); dispute = json.load(open(d / "disputed.json"))
    g1, g2 = _read_pass(d, 1, n_shards), _read_pass(d, 2, n_shards)
    n3 = json.load(open(d / "meta3.json"))["n_shards"]; order = json.load(open(d / "order3.json")); g3 = {}
    for s in range(n3):
        for x in json.load(open(d / f"out3_{s}.json")):
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
    variants = {"eval_set_v2.jsonl": lambda q, r: final[(q, r)],
                "eval_set_v2_min.jsonl": lambda q, r: min(g1[q][r], g2[q][r]),
                "eval_set_v2_max.jsonl": lambda q, r: max(g1[q][r], g2[q][r])}
    flips, summary = [], {}
    for name, fn in variants.items():
        rows = _load(SRC / "eval_set.jsonl"); new_rel = 0
        for row in rows:
            q = row["query_id"]; orig_no = row["no_answer"]
            if q in pairs:
                for r in pairs[q]:
                    v = fn(q, r)
                    if v > 0: row["relevant"][r] = v; new_rel += 1
                    if r not in row["judged"]: row["judged"].append(r)
                row["label_method"] += f"; v2 pooled assessment '{tag}' (variant {name})"
            row["no_answer_original"] = orig_no
            row["no_answer"] = not row["relevant"]
            if orig_no and not row["no_answer"] and name == "eval_set_v2.jsonl":
                flips.append({"query_id": q, "query": row["query"], "new_relevant": row["relevant"]})
        with open(EV / name, "w", encoding="utf-8") as f:
            for row in rows: f.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary[name] = {"new_relevant_pairs": new_rel, "no_answer_queries": sum(r["no_answer"] for r in rows)}
    dist = Counter(final.values())
    rep = {"tag": tag, "n_pairs": len(final), "final_grade_distribution": dict(dist), "variants": summary,
           "no_answer_to_answerable_flips (primary variant)": flips, "unresolved_three_way_splits": unresolved,
           "pass3_changed_vs": {"pass1": sum(final[(q, r)] != g1[q][r] for (q, r) in final), "pass2": sum(final[(q, r)] != g2[q][r] for (q, r) in final)},
           "note": "AI-generated judgements; no human ground truth."}
    json.dump(rep, open(d / "pooling_report.json", "w"), indent=1); json.dump(rep, open(EV / "pooling_report_v2.json", "w"), indent=1)
    print(json.dumps(rep, indent=1)[:2500])

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "make": make(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 8)
    elif c == "merge12": merge12(sys.argv[2])
    else: merge3(sys.argv[2])
