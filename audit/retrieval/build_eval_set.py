"""Merge two independent blind labelling passes into the final eval set (conservative consensus)."""
import json, collections, itertools
from pathlib import Path
H = Path(__file__).resolve().parent
OUT = H.parents[1] / "data/retrieval/eval"
OUT.mkdir(parents=True, exist_ok=True)
Q = {q["query_id"]: q for q in json.load(open(H / "queries_with_pools.json"))}
P2 = json.load(open(H / "labelling_pass2_pools.json"))
g1, g2 = {}, {}
for s in range(8):
    for x in json.load(open(H / f"labelling/out_{s}.json")):
        pool = Q[x["query_id"]]["pool"]
        g1[x["query_id"]] = {pool[int(c[1:]) - 1]: v for c, v in x["grades"].items()}
    for x in json.load(open(H / f"labelling/out2_{s}.json")):
        pool = P2[x["query_id"]]
        g2[x["query_id"]] = {pool[int(c[1:]) - 1]: v for c, v in x["grades"].items()}
assert set(g1) == set(g2) == set(Q)
for qid in Q:
    assert set(g1[qid]) == set(g2[qid]) == set(Q[qid]["pool"]), qid

def kappa(a, b, labels):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0
A, B = [], []
for qid in Q:
    for rid in Q[qid]["pool"]:
        A.append(g1[qid][rid]); B.append(g2[qid][rid])
stats = {"n_judgements": len(A),
         "raw_agreement_3class": sum(x == y for x, y in zip(A, B)) / len(A),
         "kappa_3class": kappa(A, B, [0, 1, 2]),
         "kappa_binary_grade>=2": kappa([int(x >= 2) for x in A], [int(y >= 2) for y in B], [0, 1]),
         "kappa_binary_grade>=1": kappa([int(x >= 1) for x in A], [int(y >= 1) for y in B], [0, 1]),
         "pairs_disagreeing_on_grade2": sum((x >= 2) != (y >= 2) for x, y in zip(A, B)),
         "pairs_with_any_relevance_by_either": sum(x > 0 or y > 0 for x, y in zip(A, B)),
         "confusion_pass1_rows_pass2_cols": {str(i): {str(j): sum(1 for x, y in zip(A, B) if x == i and y == j) for j in (0, 1, 2)} for i in (0, 1, 2)}}
final, union, disputed = [], [], []
for qid, q in sorted(Q.items()):
    for name, fn, dest in (("consensus", min, final), ("union", max, union)):
        rel = {rid: fn(g1[qid][rid], g2[qid][rid]) for rid in q["pool"]}
        rel = {k: v for k, v in rel.items() if v > 0}
        rec = {"query_id": qid, "query": q["query"], "category": q["category"], "domain": q["domain"], "relevant": rel,
               "judged": q["pool"], "no_answer": not rel,
               "label_method": f"two independent blind AI labelling passes (anonymised, differently shuffled candidates); grade = {fn.__name__} of the two passes",
               "author_intended": q["intended"], "no_answer_intent": q["no_answer_intent"]}
        dest.append(rec)
    c = [r for r in final if r["query_id"] == qid][0]
    if (not q["no_answer_intent"]) and c["no_answer"]:
        disputed.append(qid)
    if q["no_answer_intent"] and not c["no_answer"]:
        c["category"] = "no_answer_intended_but_covered"
# disputed answerable-intended queries with no consensus relevance: excluded from scoring (kept, flagged)
fin = [r for r in final if r["query_id"] not in disputed]
uni = [r for r in union if r["query_id"] not in disputed]
for path, rows in (("eval_set.jsonl", fin), ("eval_set_union_labels.jsonl", uni)):
    with open(OUT / path, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
intend_vs = collections.Counter()
for r in final:
    for rid in r["author_intended"]:
        intend_vs[r["relevant"].get(rid, 0)] += 1
rep = {"labelling": stats, "queries_total": len(Q), "queries_in_final_set": len(fin), "disputed_excluded": disputed,
       "category_counts": dict(collections.Counter(r["category"] for r in fin)),
       "no_answer_queries": sum(r["no_answer"] for r in fin),
       "author_intended_target_consensus_grade": dict(intend_vs),
       "relevant_per_query_mean": sum(len(r["relevant"]) for r in fin if not r["no_answer"]) / max(1, sum(not r["no_answer"] for r in fin)),
       "method": "authors saw only topic+key concepts of targets; pools = union of top-10 from BM25(q), BM25(qka), dev-LSA(qk), dev-LSA(qka) + author targets; labellers blind to author targets, rankers, scores"}
json.dump(rep, open(OUT / "eval_set_report.json", "w"), indent=1)
json.dump({"pass1": g1, "pass2": g2}, open(H / "all_labels_raw.json", "w"))
print(json.dumps(rep, indent=1))
