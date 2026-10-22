"""Merge authored queries, build the candidate pool per query and write anonymised labeller shards.

The pool is the union of the top-POOL_K of four independent rankers (BM25 on question-only and full docs,
dev-LSA on two doc modes) plus the author's intended target records. Labellers see neither ranker
provenance, ranks, scores nor the intended targets; candidate order is shuffled and ids are anonymised per query.
"""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from src.retrieval.documents import build_documents
from src.retrieval.embeddings_dev import DevLsaEmbedder
from src.retrieval.index import VectorIndex
from src.retrieval.retriever import LexicalRetriever, SemanticRetriever

POOL_K = 10
H = ROOT / "audit/retrieval"
R = load_corpus()["records"]
by_id = {r["question_id"]: r for r in R}
tasks = {t["task_id"]: t for t in json.load(open(H / "tasks_with_ids.json"))}
queries = []
for i in range(4):
    for x in json.load(open(H / f"authors/out_{i}.json")):
        t = tasks[x["task_id"]]
        queries.append({"task_id": x["task_id"], "query": x["query"].strip(), "category": t["category"],
                        "domain": t["targets"][0]["domain"], "intended": [g["id"] for g in t["targets"]], "no_answer_intent": False})
for x in json.load(open(H / "authors/out_noanswer.json")):
    queries.append({"task_id": None, "query": x["query"].strip(), "category": "no_answer", "domain": None, "intended": [],
                    "no_answer_intent": True, "kind": x["kind"]})
queries.sort(key=lambda q: (q["task_id"] or "Z", q["query"]))
for n, q in enumerate(queries, 1):
    q["query_id"] = f"Q{n:03d}"
assert len({q["query"] for q in queries}) == len(queries)

rankers = []
for mode in ("q", "qka"):
    rankers.append(LexicalRetriever(R, mode))
for mode in ("qk", "qka"):
    docs = build_documents(R, mode)
    emb = DevLsaEmbedder([d["text"] for d in docs])
    vi = VectorIndex.build(R, emb, mode)
    rankers.append(SemanticRetriever(R, vi, emb))
rnd = random.Random(99)
for q in queries:
    pool = list(q["intended"])
    for rk in rankers:
        for h in rk.search(q["query"], POOL_K):
            if h["question_id"] not in pool:
                pool.append(h["question_id"])
    rnd.shuffle(pool)
    q["pool"] = pool
json.dump(queries, open(H / "queries_with_pools.json", "w"), indent=1)  # master (kept out of labeller view)
# anonymised labeller shards
rnd.shuffle(queries)
n_shards = 8
for s in range(n_shards):
    items = []
    for q in queries[s::n_shards]:
        cands = []
        for j, rid in enumerate(q["pool"], 1):
            r = by_id[rid]
            cands.append({"c": f"c{j}", "domain": r["domain"], "topic": r["topic"], "question": r["question"],
                          "key_concepts": r["key_concepts"], "answer_excerpt": r["canonical_answer"][:450]})
        items.append({"query_id": q["query_id"], "query": q["query"], "candidates": cands})
    json.dump(items, open(H / f"labelling/shard_{s}.json", "w"), indent=1, ensure_ascii=False)
print(len(queries), sum(len(q["pool"]) for q in queries) / len(queries))
