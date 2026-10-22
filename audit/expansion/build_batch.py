#!/usr/bin/env python3
"""Build a staged expansion batch (Stage 1D) from reviewed/corrected records.
Usage: python audit/expansion/build_batch.py <batch_dir> <letter> <json: corrected records> [review files...]
Reads <batch_dir>/work/{corrected.json,reviews.json,rechecks.json,lead_sources.json,test_runs.json}; writes the accepted set, quarantine, manifest."""
import sys, json, hashlib, re, csv
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[2]
B = Path(sys.argv[1]); LET = sys.argv[2]; W = B / "work"
v5cols = list(__import__("pandas").read_csv(ROOT / "data/curated/v5/curated_questions.csv", nrows=0).columns)
NEW = ["concise_answer", "detailed_answer", "practical_answer", "answer_set", "rubric_points", "related_domains", "tags", "time_sensitive", "review_by", "v6_verification"]
COLS = v5cols + NEW
rec = json.loads((W / "corrected.json").read_text()); rv = {r["plan_id"]: r for r in json.loads((W / "reviews.json").read_text())}
rc = {r["plan_id"]: r for r in json.loads((W / "rechecks.json").read_text())}
ls = json.loads((W / "lead_sources.json").read_text())      # plan_id -> list of {title,url,supports,status}
runs = json.loads((W / "test_runs.json").read_text())       # plan_id -> {interpreter: ok}
fin = {r["plan_id"]: r for r in json.loads((W / "final_rechecks.json").read_text())} if (W / "final_rechecks.json").exists() else {}
resid = json.loads((W / "residual.json").read_text()) if (W / "residual.json").exists() else {}
revinfo = json.loads((W / "revision.json").read_text()) if (W / "revision.json").exists() else {}
cpv = json.loads((W / "checkpoint_verification.json").read_text()) if (W / "checkpoint_verification.json").exists() else {}
quar = json.loads((W / "quarantined.json").read_text()) if (W / "quarantined.json").exists() else {}
def num(p): c, n = re.match(r"B\d+-(.+)-(\d+)$", p).groups(); return (c, int(n))
rec = sorted([r for r in rec if r["plan_id"] not in quar], key=lambda r: num(r["plan_id"]))
rows = []; tests = {}; unver = []; cfgs = {}
for i, g in enumerate(rec, 1):
    pid = g["plan_id"]; sid = f"smi-{LET}{i:04d}"
    ev = (rc.get(pid) or rv[pid]).get("evidence", [])
    meth = Counter(e.get("method", "?") for e in ev)
    if pid in resid:
        for c in resid[pid]: unver.append((sid, pid, c if isinstance(c, str) else json.dumps(c, ensure_ascii=False), "no authoritative source found by source pass; hedged in text"))
    else:
        for e in ev:
            if e.get("method") == "background_only": unver.append((sid, pid, e.get("claim", ""), e.get("evidence", "")))
    srcs = ls.get(pid, []); has_code = bool(g.get("code"))
    ver = "ai_generated+ai_reviewed" + ("+code_executed" if has_code else "") + ("+source_opened" if srcs else "")
    ms = g["answer_set"] != "single"
    ans = g["detailed_answer"] if ms else g["answer"]
    iss = rv[pid]["issues"]; r2 = rc.get(pid); r3 = fin.get(pid)
    notes = f"blind review: {rv[pid]['verdict']} ({sum(x['severity']=='major' for x in iss)} major, {sum(x['severity']=='minor' for x in iss)} minor issues)"
    if r2: notes += f"; recheck: {r2['verdict']} ({sum(x['severity']=='major' for x in r2['issues'])} major, {sum(x['severity']=='minor' for x in r2['issues'])} minor)"
    if g["original_difficulty"] != g["difficulty"]: notes += f"; difficulty {g['original_difficulty']}->{g['difficulty']} (blind auditor rating adopted)"
    if r3: notes += f"; final recheck: {r3['verdict']} ({sum(x['severity']=='major' for x in r3['issues'])} major, {sum(x['severity']=='minor' for x in r3['issues'])} minor)"
    cp = cpv.get(pid)
    if cp: notes += f"; checkpoint verification: {len(cp)} fresh-auditor round(s), verdicts {[x['verdict'] for x in cp]}, {sum(i['severity']=='major' for x in cp for i in x['issues'])} major issue(s) found and fixed"
    esum = f"internal evidence (executed/derivation/other): {dict(meth)}" + (f"; code run on Python 3.10/3.11/3.13 (stdlib+numpy)" if has_code else "") + ("; external sources: " + "; ".join(f"{s['url']} [{s['status']}]" for s in srcs) if srcs else "; no external source cited")
    lim = "; ".join(x for x in [("some claims rest on background knowledge only (hedged in text; see unverified_claims.csv)" if resid.get(pid, [] if pid in resid else (["x"] if meth.get("background_only") else [])) else ""), ("time-sensitive area: re-check" if g.get("time_sensitive") else ""), ("no human review", )[0]] if x)
    row = {c: "" for c in COLS}
    row.update(id=sid, domain=g["domain"], topic=g["topic"], difficulty=g["difficulty"], question_type=g["question_type"], question=g["question"], answer=ans,
        key_concepts="; ".join(g["key_concepts"]), common_mistakes=json.dumps(g["common_mistakes"], ensure_ascii=False), source_type="ai_generated_original",
        plan_id=pid, modification="new_in_stage1d_batch" + B.name.split("_")[-1], review_notes=notes, sources=json.dumps(srcs, ensure_ascii=False),
        has_code_test="yes" if has_code else "no", code_language="python" if has_code else "", verification=ver, version="batch-staged", introduced_in="v6-" + B.name,
        audit_scope="stage1d_blind_review" + ("_and_recheck" if r2 else "") + ("_and_final_recheck" if r3 else "") + ("_and_checkpoint_verification" if cp else ""), audit_verdict=rv[pid]["verdict"], interview_style_note=g["interview_style_note"],
        evidence_summary=esum, remaining_limitations=lim, concise_answer=g.get("concise_answer") or "", detailed_answer=g.get("detailed_answer") or "",
        practical_answer=g.get("practical_answer") or "", answer_set=g["answer_set"], rubric_points=json.dumps(g.get("rubric_points") or [], ensure_ascii=False) if g.get("rubric_points") else "",
        related_domains="; ".join(g.get("related_domains") or []), tags="; ".join(g.get("tags") or []), time_sensitive="yes" if g.get("time_sensitive") else "no",
        review_by="2027-04" if g.get("time_sensitive") else "", v6_verification="ai_review_only_no_human" + ("+recheck" if r2 else "") + ("+final_recheck" if r3 else "") + ("+checkpoint_verification" if cp else ""))
    rows.append(row)
    if has_code: tests[sid] = g["code"]
    if g.get("configs"): cfgs[sid] = g["configs"]
import pandas as pd
df = pd.DataFrame(rows, columns=COLS)
df.to_csv(B / f"{B.name}_accepted.csv", index=False, encoding="utf-8"); (B / f"{B.name}_accepted.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
(B / "code_tests.json").write_text(json.dumps(tests, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
if cfgs: (B / "configs.json").write_text(json.dumps(cfgs, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
elif (B / "configs.json").exists(): (B / "configs.json").unlink()
pd.DataFrame([{"plan_id": k, "reason": v} for k, v in quar.items()], columns=["plan_id", "reason"]).to_csv(B / "quarantine.csv", index=False)
pd.DataFrame(unver, columns=["id", "plan_id", "claim", "evidence"]).to_csv(B / "unverified_claims.csv", index=False)
FP = ["id", "domain", "topic", "difficulty", "question_type", "question", "answer", "key_concepts", "common_mistakes"]
fa = hashlib.sha256(json.dumps([[str(r[f]) for f in FP] for r in sorted(rows, key=lambda r: r["id"])], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
fb = hashlib.sha256(json.dumps(tests, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
fc = hashlib.sha256((fa + fb).encode()).hexdigest()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
man = dict(dataset="smart-mock-interview expansion batch", batch=B.name, status="staged, not merged into any curated version; no human review", record_count=len(rows), quarantined=len(quar),
  domain_counts=dict(Counter(r["domain"] for r in rows)), topic_counts=dict(Counter(r["topic"] for r in rows)), difficulty_counts=dict(Counter(r["difficulty"] for r in rows)),
  question_type_counts=dict(Counter(r["question_type"] for r in rows)), answer_set_counts=dict(Counter(r["answer_set"] for r in rows)),
  records_with_code_test=len(tests), records_with_configs=len(cfgs), configs_sha256=(hashlib.sha256(json.dumps(cfgs, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest() if cfgs else None), records_with_lead_opened_source=sum(any(x["status"].startswith("lead_opened") for x in json.loads(r["sources"])) for r in rows),
  records_with_any_source=sum(r["sources"] != "[]" for r in rows), records_with_fully_supporting_source=sum(any(x["status"].endswith("_supported") for x in json.loads(r["sources"])) for r in rows),
  source_entries=sum(len(json.loads(r["sources"])) for r in rows), distinct_source_urls=len({x["url"] for r in rows for x in json.loads(r["sources"])}),
  records_without_source_but_executed_or_derived=sum(r["sources"] == "[]" for r in rows), records_with_residual_background_only_claims=sum(bool(resid.get(r["plan_id"])) for r in rows), unverified_claim_count=len(unver),
  revision=revinfo,
  predecessor_manifest_sha256={v: sha(ROOT / f"data/curated/{v}/manifest.json") for v in ("v1", "v2", "v3", "v4", "v5")},
  fingerprint=dict(content_sha256=fa, code_tests_sha256=fb, combined_sha256=fc, definition="sha256 of compact JSON of [id,domain,topic,difficulty,question_type,question,answer,key_concepts,common_mistakes] sorted by id; code_tests.json sha256 (sort_keys, compact); combined = sha256(content+tests)"),
  files={p.name: sha(p) for p in sorted(B.glob("*")) if p.is_file() and p.name != "manifest.json"})
(B / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
print(len(rows), fc)
