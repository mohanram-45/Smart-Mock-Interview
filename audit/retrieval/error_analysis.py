"""Failure taxonomy for a benchmark run:  python audit/retrieval/error_analysis.py <benchmark.json> [out.md]"""
import json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
R = {r["question_id"]: r for r in load_corpus()["records"]}
ev = {json.loads(l)["query_id"]: json.loads(l) for l in open(ROOT / "data/retrieval/eval/eval_set.jsonl")}
res = json.load(open(sys.argv[1]))
L = [f"# Error analysis ({res['backend']})", ""]
def kind(top1, q):
    g = q["relevant"].get(top1, 0)
    if g >= 2: return "correct"
    if g == 1: return "top1_partially_relevant (grade 1)"
    rel2 = [k for k, v in q["relevant"].items() if v >= 2]
    t = R[top1]
    if any(R[k]["topic"] == t["topic"] for k in rel2): return "same-topic sibling record (wrong record, right topic)"
    if any(R[k]["domain"] == t["domain"] for k in rel2): return "same domain, different topic"
    return "different domain"
for name, r in res["systems"].items():
    rows = [x for x in r["rows"] if not x["no_answer"] and x["has_primary"]]
    c = collections.Counter(kind(x["ranked"][0], ev[x["query_id"]]) if x["ranked"] else "no results" for x in rows)
    L += [f"## {name}", "", "| top-1 outcome | queries | share |", "|---|---:|---:|"]
    for k, v in c.most_common():
        L.append(f"| {k} | {v} | {v / len(rows):.1%} |")
    miss5 = [x for x in rows if x["success@5"] == 0]
    L += ["", f"Queries with no relevant record in the top 5: {len(miss5)} of {len(rows)}"]
    dc = [x for x in rows if x["category"] == "domain_confusing"]
    xdom = sum(1 for x in dc if x["ranked"] and R[x["ranked"][0]]["domain"] != ev[x["query_id"]]["domain"])
    L += [f"Domain-confusing queries whose top-1 is in the wrong domain: {xdom} of {len(dc)}", ""]
    if name.endswith("_qka"):
        L += ["Worst misses (no relevant record in top 5):", ""]
        for x in miss5[:10]:
            q = ev[x["query_id"]]
            tgt = [k for k, v in q["relevant"].items() if v >= 2][0]
            L.append(f"* {x['query_id']} [{q['category']}] \"{q['query'][:110]}\" -> wanted {tgt} ({R[tgt]['topic'][:45]}); got {x['ranked'][0]} ({R[x['ranked'][0]]['topic'][:45]})")
        L.append("")
Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / f"reports/stage2a_error_analysis_{res['backend']}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[:60]))
