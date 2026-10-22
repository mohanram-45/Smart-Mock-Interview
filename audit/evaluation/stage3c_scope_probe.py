"""Stage 3C exploratory probe (read-only, no model, does not modify the frozen corpus).
Proposes a deterministic first-pass scope tier for each key concept from EXISTING fields only:
  essential  = the concept's content words appear in the question text, or in the canonical answer's first sentence (the headline claim)
  supporting = appears elsewhere in the canonical answer
  background = key concept not stated in the canonical answer at all
This is a heuristic to size the problem and seed human review; it is NOT ground truth.
    python audit/evaluation/stage3c_scope_probe.py [question_id ...]"""
import collections
import re
import statistics
import sys

sys.path.insert(0, ".")
from src.retrieval.corpus import load_corpus  # noqa: E402

STOP = set("the a of and in to is for vs what are how do does with on an between difference explain why when you your can it be or as at by from that this which".split())


def words(s):
    return {w for w in re.findall(r"[a-z0-9²_=]+", s.lower()) if w not in STOP}


def tiers(rec):
    q, ans = words(rec["question"]), rec["canonical_answer"]
    first = re.split(r"(?<=[.!?])\s+", ans)[0]
    fw, aw = words(first), words(ans)
    out = {}
    for k in rec["key_concepts"]:
        kw = words(k)
        if not kw:
            out[k] = "supporting"
        elif kw & q or (kw <= fw):
            out[k] = "essential"
        elif kw <= aw or k.lower() in ans.lower():
            out[k] = "supporting"
        else:
            out[k] = "background"
    return out


def main(ids):
    recs = load_corpus()["records"]
    by = {r["question_id"]: r for r in recs}
    c, per = collections.Counter(), []
    zero_ess = 0
    for r in recs:
        t = tiers(r)
        c.update(t.values())
        per.append(sum(v == "essential" for v in t.values()) / len(t))
        zero_ess += not any(v == "essential" for v in t.values())
    n = sum(c.values())
    print(f"{len(recs)} records, {n} key concepts: " + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in c.items()))
    print(f"mean essential share per question {statistics.mean(per):.2f}; records with NO essential concept: {zero_ess}")
    for i in ids or ["smi-0441", "smi-0431", "smi-0453", "smi-0339"]:
        r = by[i]
        print(f"\n{i} {r['question']}\n  ", tiers(r))


if __name__ == "__main__":
    main(sys.argv[1:])
