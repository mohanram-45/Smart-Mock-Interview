"""Compare two stage3b run files item-by-item (before vs after a fix), with the AI-authored expected band.
    python audit/evaluation/stage3b_compare.py <before_runs.json> <after_runs.json>
Prints status, score, calls, factual errors kept, dropped items and median latency. Read-only. Expected bands are AI-authored (Claude), unreviewed."""
import json
import statistics
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "bench_v1" / "expectations.jsonl"


def load(p):
    d = json.load(open(p, encoding="utf-8"))
    out = {}
    for r in d["runs"]:
        res = r["result"]
        out.setdefault(r["item_id"], []).append(dict(
            status=res["evaluation_status"], score=res.get("provisional_score"), calls=len(r.get("provider_log", [])), wall=r.get("wall_ms", 0) / 1000,
            errs=len(res.get("factual_errors") or []), conc=len(res.get("correct_concepts") or []),
            dropped=sum(((res.get("flags") or {}).get("dropped_unverifiable") or {}).values()),
            contra=len((res.get("flags") or {}).get("contradicted_missing_concepts") or [])))
    return out


def band(item, score, exps):
    e = exps.get(item)
    if not e or score is None:
        return "-"
    return "IN" if e["score_min"] <= score <= e["score_max"] else f"OUT({e['score_min']}-{e['score_max']})"


def fmt(x, exps, k):
    if not x:
        return "-"
    return f"{x['status'][:14]:14} score={x['score']!s:>4} {band(k, x['score'], exps):12} calls={x['calls']} err={x['errs']} conc={x['conc']} drop={x['dropped']} contra={x['contra']} {x['wall']:.0f}s"


def main(a, b):
    exps = {}
    if EXP.exists():
        exps = {e["item_id"]: e for e in map(json.loads, EXP.read_text(encoding="utf-8").splitlines() if EXP.exists() else [])}
    A, B = load(a), load(b)
    for k in sorted(set(A) | set(B)):
        print(f"{k}\n  BEFORE {fmt(A.get(k, [None])[0], exps, k)}\n  AFTER  {fmt(B.get(k, [None])[0], exps, k)}")
    for name, X in (("before", A), ("after", B)):
        w = [v[0]["wall"] for v in X.values()]
        print(f"median latency {name}: {statistics.median(w):.1f}s over {len(w)} cases")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
