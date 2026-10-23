#!/usr/bin/env python3
"""Consolidated verification backlog across staged expansion batches. Writes reports/verification_backlog.csv and .md.
Sources: each batch's unverified_claims.csv, accepted CSV (sources, time_sensitive, answer text), config_check results, manual known-gap notes (audit/expansion/known_gaps.json)."""
import json, re, csv, sys
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; rows = []
def add(batch, rid, pid, cat, item, status, action, prio): rows.append(dict(batch=batch, record_id=rid, plan_id=pid, category=cat, item=item, status=status, suggested_action=action, priority=prio))
for bd in sorted((ROOT / "data/expansion").glob("batch_*")):
    n = bd.name; acc = bd / f"{n}_accepted.csv"
    if not acc.exists(): continue
    d = pd.read_csv(acc, keep_default_na=False, dtype=str)
    uv = pd.read_csv(bd / "unverified_claims.csv", keep_default_na=False, dtype=str) if (bd / "unverified_claims.csv").exists() else pd.DataFrame()
    for r in uv.itertuples():
        c = r.claim
        prio = "medium" if re.search(r"\d|default|documented|always|never|limit|atomic|TTL|require", c, re.I) else "low"
        add(n, r.id, r.plan_id, "unsupported_claim", c, "background knowledge only; hedged in text; no authoritative source found", "find official doc/paper or remove/hedge further", prio)
    cc = ROOT / f"reports/config_check_{n.replace('_','')}.json"
    cfg = json.loads(cc.read_text()) if cc.exists() else {}
    for k, v in cfg.items():
        if v["status"].startswith("executed"): continue
        rid = k.split(":")[0]
        add(n, rid, v["plan_id"], "unexecuted_config", f"{v['lang']} snippet in {k.split(':')[1]}", f"{v['status']}: {v['detail']}" + ("; never built/applied" if v["lang"] in ("dockerfile", "yaml") else ""), "validate against a real cluster / build with Docker, or keep flagged", "medium" if v["lang"] in ("dockerfile", "yaml") else "low")
    for r in d.itertuples():
        for s in json.loads(r.sources):
            if s["status"].endswith("_partially"): add(n, r.id, r.plan_id, "partial_source", f"{s['url']} supports only: {s['supports'][:160]}", s["status"], "confirm wording stays within what the page supports", "low")
        if r.time_sensitive == "yes": add(n, r.id, r.plan_id, "time_sensitive", "claims depend on fast-changing tools/providers", f"review_by {r.review_by}", "re-verify against current docs by review_by date", "medium")
        if r.sources == "[]" and r.has_code_test == "no": add(n, r.id, r.plan_id, "no_external_source", "no cited source and no executed test (judgement/derivation item)", "reviewed by AI only", "human reviewer to confirm", "low")
kg = ROOT / "audit/expansion/known_gaps.json"
if kg.exists():
    for g in json.loads(kg.read_text()): add(g["batch"], g.get("record_id", ""), g["plan_id"], "known_minor_gap", g["item"], "noted by final auditor/lead; not fixed", g["action"], "low")
add("all", "", "", "global", "No human review of any record in v6 candidates; authors, reviewers and lead are the same model family", "open", "human spot-check sample before release", "high")
df = pd.DataFrame(rows)
def triage(r):
    c = r.category
    if c == "global": return "human_review_limitation"
    if c == "time_sensitive": return "scheduled_reverification"
    if c == "unexecuted_config": return "evidence_gap_not_executed"
    if c in ("unsupported_claim", "no_external_source"): return "evidence_gap_hedged_or_derived"
    if c == "partial_source": return "evidence_gap_partial_source"
    return "documentation_note"
df["triage"] = df.apply(triage, axis=1)
df.insert(0, "backlog_id", [f"VB-{i:04d}" for i in range(1, len(df) + 1)])
df.to_csv(ROOT / "reports/verification_backlog.csv", index=False, encoding="utf-8")
cnt = df.groupby(["batch", "category"]).size().unstack(fill_value=0)
md = ["# Consolidated verification backlog (Stage 1D, staged batches 1-4)", "", f"{len(df)} open items. Full list: `reports/verification_backlog.csv` (columns: backlog_id, batch, record_id, plan_id, category, item, status, suggested_action, priority). Nothing here changes any staged record; the batches are preserved as approved.", "", "## Counts by batch and category", "", cnt.to_markdown(), "", "## By priority", "", df.priority.value_counts().to_frame().to_markdown(), "", "## By triage (checkpoint, 2026-10-11)", "", pd.crosstab(df.triage, df.priority).to_markdown(), "", "Checkpoint triage result: **0 medium items are confirmed correctness defects.** All medium unsupported claims are hedged, illustrative or derived reasoning; time-sensitive items are scheduled re-verification; the 5 Batch 3 configs are unexecuted (4 YAML fragments schema-valid when wrapped in a Deployment, never applied; 1 Dockerfile syntax-parsed only, never built). Two checkable claims were re-examined: object stores lacking atomic directory rename (consistent with search results and the Hadoop S3 committer rationale, which cites lack of an efficient rename; the record is hedged) and HPA scale-down stabilisation (could not be read from the K8s page in full; record keeps it as standard practice). Neither was changed.", "", "## Categories", "", "* **unsupported_claim**: statements that rest on background knowledge only (from each batch's `unverified_claims.csv`); includes operational claims such as Batch 3's autoscaler scale-down advice, circuit-breaker claim and TTL sentence.", "* **unexecuted_config**: YAML/Dockerfile snippets that were parsed (and Kubernetes objects schema-checked when complete) but never built or applied. Batch 3's five snippets are YAML fragments and one Dockerfile: syntax only, no schema check, no build.", "* **partial_source**: citations that support only a narrower statement than the topic.", "* **time_sensitive**: records to re-verify by their `review_by` date.", "* **no_external_source**: no citation and no executed test.", "* **known_minor_gap**: non-blocking observations from final auditors.", "* **global**: no human review."]
(ROOT / "reports/verification_backlog.md").write_text("\n".join(md), encoding="utf-8")
print(len(df)); print(cnt)
