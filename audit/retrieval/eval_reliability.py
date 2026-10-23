"""Stage 2B Phase 4: descriptive reliability checks on the frozen 166-query benchmark (read-only)."""
import json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from src.retrieval.lexical import tokenize

R = {r["question_id"]: r for r in load_corpus()["records"]}
ev = [json.loads(l) for l in (ROOT / "data/retrieval/eval/eval_set.jsonl").read_text().splitlines() if l.strip()]

def jac(a, b):
    a, b = set(tokenize(a)), set(tokenize(b)); return len(a & b) / max(1, len(a | b))

out = {}
# 1. lexical overlap query vs best grade-2 record question (easy-paraphrase check)
ov = defaultdict(list)
for q in ev:
    g2 = [k for k, g in q["relevant"].items() if g >= 2]
    if g2: ov[q["category"]].append(max(jac(q["query"], R[k]["question"]) for k in g2))
out["jaccard_query_vs_best_grade2_question"] = {c: {"n": len(v), "median": round(statistics.median(v), 3), "p90": round(sorted(v)[int(.9 * (len(v) - 1))], 3), "share_ge_0.5": round(sum(x >= .5 for x in v) / len(v), 3)} for c, v in ov.items()}
# 2. label structure
out["queries_with_grade2"] = sum(any(g >= 2 for g in q["relevant"].values()) for q in ev if not q["no_answer"])
out["answerable_queries"] = sum(not q["no_answer"] for q in ev)
out["grade1_only_queries"] = [q["query_id"] for q in ev if not q["no_answer"] and not any(g >= 2 for g in q["relevant"].values())]
out["mean_relevant_per_query"] = round(statistics.mean(len(q["relevant"]) for q in ev if not q["no_answer"]), 2)
out["single_relevant_queries"] = sum(len([g for g in q["relevant"].values() if g >= 2]) == 1 for q in ev if not q["no_answer"])
out["judged_pool_size"] = {"mean": round(statistics.mean(len(q["judged"]) for q in ev), 1), "min": min(len(q["judged"]) for q in ev)}
out["judged_fraction_of_corpus_mean"] = round(statistics.mean(len(q["judged"]) for q in ev) / len(R), 3)
# 3. hard negatives: similar_distinct queries - how many graded-0 judged records share the primary domain/topic
hn = []
for q in ev:
    if q["category"] != "similar_distinct": continue
    prim = [R[k] for k, g in q["relevant"].items() if g >= 2]
    topics = {p["topic"] for p in prim}
    neg_same_topic = [k for k in q["judged"] if q["relevant"].get(k, 0) == 0 and R[k]["topic"] in topics]
    hn.append(len(neg_same_topic))
out["similar_distinct_graded0_same_topic_as_target"] = {"n": len(hn), "mean": round(statistics.mean(hn), 2), "zero": sum(x == 0 for x in hn)}
# 4. domain skew & answer-writer homogeneity
out["domain_counts"] = dict(Counter(q["domain"] or "none" for q in ev))
out["label_methods"] = dict(Counter(q["label_method"][:60] for q in ev))
(ROOT / "reports/stage2b_eval_reliability.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
