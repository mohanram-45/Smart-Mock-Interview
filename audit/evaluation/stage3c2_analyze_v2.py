"""Stage 3C-2 analyzer v2 (tooling only; the v1 analyzer and the frozen thresholds are untouched and still do the criteria arithmetic).

Adds, for diagnosis and for honest labelling:
  * partial runs: criteria are shown as NOT_EVALUATED (with what the value would have been) instead of a bare PASS/FAIL;
  * repeat disagreement table, pre-gate (what the model returned) AND post-gate (what the frozen criterion measures);
  * cold-load detection: calls whose Ollama load_duration shows a model (re)load are excluded from the WARM latency figures;
  * warm-up context check: the context length Ollama reported after the warm-up must equal the frozen num_ctx;
  * per-verdict tables for reading.
No threshold, rule or scoring behaviour changes here.

  python audit/evaluation/stage3c2_analyze_v2.py data/evaluation/stage3c2_results/<run>/results.json [--verdicts SAMPLE_ID ...]
"""
import importlib.util, json, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "evaluation" / "stage3c2"
COLD_LOAD_NS = 2_000_000_000          # a load_duration above 2 s means the model was (re)loaded for that call


def _v1():
    spec = importlib.util.spec_from_file_location("ana3c2_v1", ROOT / "audit" / "evaluation" / "stage3c2_analyze.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _tiers(r):
    return {o["requirement_id"]: o["tier"] for o in r["outcomes"]}


def repeat_mismatches(doc):
    by = {}
    for m in doc["modular"]: by.setdefault(m["sample_id"], {})[m["repeat"]] = m["result"]
    rows, total, same_post, same_pre = [], 0, 0, 0
    for sid in sorted(by):
        reps = by[sid]
        if 0 not in reps or 1 not in reps: continue
        a = {(v["requirement_id"], v["member"]): v for v in reps[0]["verdicts"]}; b = {(v["requirement_id"], v["member"]): v for v in reps[1]["verdicts"]}
        tiers = _tiers(reps[0])
        for k in sorted(a.keys() & b.keys()):
            va, vb = a[k], b[k]; total += 1
            pa, pb = va.get("original_state") or va["state"], vb.get("original_state") or vb["state"]
            same_post += va["state"] == vb["state"]; same_pre += pa == pb
            if va["state"] != vb["state"] or pa != pb:
                rows.append({"sample_id": sid, "requirement_id": k[0], "member": k[1], "tier": tiers.get(k[0]),
                             "repeat0_model": pa, "repeat0_after_gate": va["state"], "repeat0_downgrade": va.get("downgrade_reason"),
                             "repeat1_model": pb, "repeat1_after_gate": vb["state"], "repeat1_downgrade": vb.get("downgrade_reason"),
                             "differs_before_gate": pa != pb, "differs_after_gate": va["state"] != vb["state"]})
    return {"members_compared": total, "agreement_after_gate": round(same_post / total, 4) if total else None,
            "agreement_before_gate": round(same_pre / total, 4) if total else None, "mismatches": rows}


def cold_calls(doc):
    out = []
    for m in doc["modular"]:
        for t in m["verifier_trace"]:
            ld = (t.get("usage") or {}).get("load_duration") or 0
            if ld > COLD_LOAD_NS: out.append({"kind": "modular", "sample_id": m["sample_id"], "repeat": m["repeat"], "load_s": round(ld / 1e9, 1), "call_s": round(t["latency_ms"] / 1000, 1)})
    for l in doc.get("legacy", []):
        for t in l.get("provider_log", []):
            ld = (t.get("usage") or {}).get("load_duration") or 0
            if ld > COLD_LOAD_NS: out.append({"kind": "legacy", "sample_id": l["sample_id"], "repeat": l["repeat"], "load_s": round(ld / 1e9, 1), "call_s": round(t["ms"] / 1000, 1)})
    return out


def warm_latency(doc):
    cold = {(c["kind"], c["sample_id"], c["repeat"]) for c in cold_calls(doc)}
    mod = [m["wall_ms"] / 1000 for m in doc["modular"] if ("modular", m["sample_id"], m["repeat"]) not in cold]
    leg = [l["wall_ms"] / 1000 for l in doc.get("legacy", []) if ("legacy", l["sample_id"], l["repeat"]) not in cold]
    f = lambda xs: None if not xs else {"n": len(xs), "median_s": round(statistics.median(xs), 2), "max_s": round(max(xs), 2), "min_s": round(min(xs), 2)}
    return {"modular_warm": f(mod), "legacy_warm": f(leg), "excluded_cold_calls": len(cold)}


def warmup_context(doc):
    cfg = doc["meta"]["frozen_config"]
    ms = (doc["meta"].get("ollama_ps_after_load") or {}).get("models") or []
    got = ms[0].get("context_length") if ms else None
    return {"frozen_num_ctx": cfg["num_ctx"], "context_length_after_warmup": got, "matches": None if got is None else got == cfg["num_ctx"]}


def verdict_rows(doc, sample_id):
    out = []
    for m in sorted([x for x in doc["modular"] if x["sample_id"] == sample_id], key=lambda x: x["repeat"]):
        r = m["result"]; claims = {c["id"]: c["text"] for c in r["claims"]}; tiers = _tiers(r)
        for v in r["verdicts"]:
            out.append({"repeat": m["repeat"], "requirement_id": v["requirement_id"], "tier": tiers.get(v["requirement_id"]), "member": v["member"],
                        "model_state": v.get("original_state") or v["state"], "after_gate": v["state"], "downgrade_reason": v.get("downgrade_reason"),
                        "cited": {c: claims.get(c, "?") for c in v["claim_ids"]}, "model_explanation": v.get("explanation") or ""})
    return out


def analyze_v2(doc, expectations, criteria):
    v1 = _v1()
    a = v1.analyze(doc, expectations, criteria)
    partial = bool(doc["meta"].get("partial_run"))
    if partial:
        for r in a["mechanical_criteria"]:
            r["v1_result"] = r["result"]; r["result"] = f"NOT_EVALUATED_PARTIAL_RUN (would be {r['v1_result']})"
    a["repeat_agreement"] = repeat_mismatches(doc)
    a["cold_calls"] = cold_calls(doc)
    a["warm_latency"] = warm_latency(doc)
    a["warmup_context_check"] = warmup_context(doc)
    a["analyzer_version"] = "v2 (tooling only; thresholds from the frozen acceptance_criteria.json)"
    return a


def to_markdown_v2(a):
    base = _v1().to_markdown(a)
    L = [base, "## v2 diagnostics", "", f"Warm-up context check: {json.dumps(a['warmup_context_check'])}", "",
         f"Cold calls (model loaded during the call): {json.dumps(a['cold_calls'])}", "", f"Warm latency: {json.dumps(a['warm_latency'])}", "",
         f"Repeat agreement: after gate {a['repeat_agreement']['agreement_after_gate']}, before gate {a['repeat_agreement']['agreement_before_gate']}", ""]
    for x in a["repeat_agreement"]["mismatches"]:
        L.append(f"- {x['sample_id']} {x['requirement_id']} ({x['tier']}) {x['member']!r}: repeat0 model={x['repeat0_model']} -> gate={x['repeat0_after_gate']} ({x['repeat0_downgrade']}); repeat1 model={x['repeat1_model']} -> gate={x['repeat1_after_gate']} ({x['repeat1_downgrade']})")
    return "\n".join(L) + "\n"


def main(argv):
    p = Path(argv[1]); doc = json.loads(p.read_text(encoding="utf-8"))
    exp = {json.loads(l)["sample_id"]: json.loads(l) for l in (D / "provisional_ai_expectations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    a = analyze_v2(doc, exp, json.loads((D / "acceptance_criteria.json").read_text(encoding="utf-8")))
    (p.parent / "analysis_v2.json").write_text(json.dumps(a, indent=1, ensure_ascii=False), encoding="utf-8")
    (p.parent / "analysis_v2.md").write_text(to_markdown_v2(a), encoding="utf-8")
    print(to_markdown_v2(a)[:4000])
    if "--verdicts" in argv:
        for sid in argv[argv.index("--verdicts") + 1:]:
            print(json.dumps(verdict_rows(doc, sid), indent=1))


if __name__ == "__main__":
    main(sys.argv)
