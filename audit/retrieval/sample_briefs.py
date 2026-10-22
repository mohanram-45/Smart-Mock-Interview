"""Sample targets for the independent eval set and write brief files for query authors.

Authors see ONLY id, domain, topic, difficulty, question_type and key_concepts of the target
records (never question/answer text), so queries cannot copy index wording.
"""
import json, random, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from src.retrieval.documents import build_documents
from src.retrieval.embeddings_dev import DevLsaEmbedder
from src.retrieval.embeddings import embed_texts

SEED = 20261011
rnd = random.Random(SEED)
R = load_corpus()["records"]
docs = build_documents(R, "qk")
emb = DevLsaEmbedder([d["text"] for d in docs])
V, _ = embed_texts(emb, [d["text"] for d in docs])
S = V @ V.T
np.fill_diagonal(S, -1)
domains = sorted({r["domain"] for r in R})
by_dom = {d: [i for i, r in enumerate(R) if r["domain"] == d] for d in domains}
used = set()

def brief(i):
    r = R[i]
    return {"id": r["question_id"], "domain": r["domain"], "topic": r["topic"], "difficulty": r["difficulty"],
            "key_concepts": r["key_concepts"]}

def take(pool, n):
    pool = [i for i in pool if i not in used]
    rnd.shuffle(pool)
    out = pool[:n]
    used.update(out)
    return out

tasks = []
# 1. paraphrase: 9 per domain
for d in domains:
    for i in take(by_dom[d], 9):
        tasks.append({"category": "paraphrase", "targets": [brief(i)]})
# 2. concept keywords: 3 per domain
for d in domains:
    for i in take(by_dom[d], 3):
        tasks.append({"category": "concept_keywords", "targets": [brief(i)]})
# 3. multi-concept: two records with LOW similarity (different concepts), 16
cands = list(range(len(R)))
for _ in range(16):
    while True:
        a = rnd.choice(cands); b = rnd.choice(cands)
        if a != b and a not in used and b not in used and S[a, b] < 0.05:
            used.update([a, b]); tasks.append({"category": "multi_concept", "targets": [brief(a), brief(b)]}); break
# 4. similar-but-distinct: same domain, different topic, high similarity; target is the first, 16
pairs = [(S[a, b], a, b) for a in range(len(R)) for b in range(a + 1, len(R))
         if R[a]["domain"] == R[b]["domain"] and R[a]["topic"] != R[b]["topic"] and S[a, b] > 0.35]
rnd.shuffle(pairs)
n = 0
for s, a, b in sorted(pairs[:200], reverse=True):
    if a in used or b in used: continue
    if n >= 16: break
    used.update([a, b]); tasks.append({"category": "similar_distinct", "targets": [brief(a)], "confusable_with": brief(b), "sim": round(float(s), 3)}); n += 1
# 5. domain confusing: cross-domain high similarity, target first, 16
pairs = [(S[a, b], a, b) for a in range(len(R)) for b in range(len(R))
         if R[a]["domain"] != R[b]["domain"] and S[a, b] > 0.3]
pairs.sort(reverse=True)
n = 0
for s, a, b in pairs:
    if a in used or b in used: continue
    if n >= 16: break
    used.update([a, b]); tasks.append({"category": "domain_confusing", "targets": [brief(a)], "confusable_with": brief(b), "sim": round(float(s), 3)}); n += 1
topics = sorted({(r["domain"], r["topic"]) for r in R})
json.dump({"seed": SEED, "tasks": tasks, "n": len(tasks)}, open(ROOT / "audit/retrieval/sampled_tasks.json", "w"), indent=1)
json.dump([{"domain": d, "topic": t} for d, t in topics], open(ROOT / "audit/retrieval/corpus_topic_list.json", "w"), indent=1)
from collections import Counter
print(len(tasks), Counter(t["category"] for t in tasks), len(topics))
print(Counter(d for t in tasks for d in [t["targets"][0]["domain"]]))
