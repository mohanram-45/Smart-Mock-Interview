#!/usr/bin/env python3
"""Build data/curated/v3 (Stage 1B continuation).

v3 core   = v2 core (360, byte-identical text) + the 41 pilot-01 questions after independent audit corrections (401 records)
pilot 02  = 46 newly generated questions, independently reviewed, kept in a separate file (not merged)
quarantine= any audited record that could not be fixed locally (empty if none)

Reads (never modifies): data/curated/v1/*, data/curated/v2/*, audit/remediation/stage1b3/* (agent drafts and independent audits),
                        curated_v3_config.py
Writes (new files only): data/curated/v3/*
Usage: python audit/remediation/build_curated_v3.py [project_root] [--force]
Env:   SMI_XPYTHONS=path1,path2  optional extra interpreters on which every Python reference test is re-run (results -> cross_version_results.json)
"""
import sys, re, json, hashlib, os, subprocess
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = Path(args[0]).resolve() if args else HERE.parents[1]
sys.path.insert(0, str(HERE))
import curated_v3_config as C

V1, V2, OUT, ST = ROOT / "data/curated/v1", ROOT / "data/curated/v2", ROOT / "data/curated/v3", HERE / "stage1b3"
if OUT.exists() and any(OUT.iterdir()) and "--force" not in sys.argv:
    sys.exit(f"{OUT} already contains files; refusing to overwrite (use --force only for this version's own files)")
OUT.mkdir(parents=True, exist_ok=True)
jl = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
FENCE_PY = re.compile(r"```python\n(.*?)\n```", re.S)
log = []

# ------------------------------------------------------------------ audit engine
def apply_audit(rid, rec, code, verdict):
    """rec: dict with question/answer/common_mistakes(list)/key_concepts(list). code: dict or None. Mutates both. Returns (applied, unapplied, notes)."""
    applied, unapplied, notes = [], [], []
    for iss in verdict["issues"]:
        claim, rep, sev = iss["claim"], iss.get("replacement"), iss["severity"]
        if not rep:
            notes.append(f"[{sev}] {iss['problem']}"); continue
        if any(rid == k and claim.startswith(p) for k, p in C.MANUAL_SKIP):
            applied.append((sev, claim[:70], "manual patch")); continue
        done = False
        if claim.startswith("(not stated)"):
            rec["answer"] = rec["answer"].rstrip() + "\n\n" + rep.strip(); done = True
        else:
            for fld in ("answer", "question"):
                n = rec[fld].count(claim)
                if n:
                    assert n == 1, (rid, "ambiguous claim", claim[:60])
                    rec[fld] = rec[fld].replace(claim, rep); done = True
            if not done:
                for k, m in enumerate(rec.get("common_mistakes") or []):
                    if claim in m: rec["common_mistakes"][k] = m.replace(claim, rep); done = True; break
            if done and code:
                for k in ("solution", "test", "setup"):
                    if code.get(k) and claim in code[k]: code[k] = code[k].replace(claim, rep)
            if done and code and rid in C.DEMO_TO_TEST:
                old = set(FENCE_PY.findall(claim))
                for blk in FENCE_PY.findall(rep):
                    if blk not in old: code["test"] = code["test"].rstrip() + "\n\n# demonstration shown in the answer\n" + blk + "\n"
        if done: applied.append((sev, claim[:70], rep[:70]))
        else: unapplied.append((sev, claim[:90]))
    if verdict.get("suggested_key_concepts"): rec["key_concepts"] = list(verdict["suggested_key_concepts"])
    for old, new in C.KC_REPLACE.get(rid, {}).items():
        rec["key_concepts"] = [x for x in ([new if k == old else k for k in rec["key_concepts"]]) if x]
        assert len(rec["key_concepts"]) >= 3 and len({k.lower() for k in rec["key_concepts"]}) == len(rec["key_concepts"]), (rid, rec["key_concepts"])
    return applied, unapplied, notes

def apply_patches(rid, rec, code):
    for p in C.PATCHES:
        if p[0] != rid: continue
        _, fld, old, new = p
        holder, key = (code, fld.split(".")[1]) if fld.startswith("code.") else (rec, fld)
        assert old in holder[key], (rid, fld, "patch target not found")
        holder[key] = holder[key].replace(old, new)
    if rid in C.APPEND_ANSWER: rec["answer"] = rec["answer"].rstrip() + C.APPEND_ANSWER[rid]

# ------------------------------------------------------------------ inputs
core = pd.read_csv(V2 / "curated_questions.csv", keep_default_na=False, dtype=str)
pil = pd.read_csv(V2 / "pilot_batch_01.csv", keep_default_na=False, dtype=str)
v2_tests = jl(V2 / "code_tests.json")
queue = pd.read_csv(V2 / "review_queue.csv", keep_default_na=False, dtype=str)
audits = {}
for f in ("audit_out_N.json", "audit_out_D.json", "audit_out_S.json", "audit_out_X1.json", "audit_out_X2.json", "rev2_out_NLP.json", "rev2_out_DL.json", "rev2_out_PY.json", "rev2_out_DA.json"):
    for v in jl(ST / f):
        assert v["id"] not in audits, ("duplicate audit", v["id"]); audits[v["id"]] = dict(v, _file=f)
sample = set(jl(ST / "sample_ids.json"))
code_tests = {}
for rid in core.id:
    if rid in v2_tests: code_tests[rid] = v2_tests[rid]

# ------------------------------------------------------------------ 1. pilot 01 -> audited, corrected, merged
rows = {r["id"]: r for r in core.to_dict("records")}
for r in rows.values():
    r["introduced_in"] = "v1" if r["source_type"] == "seed_curated" else "v2"
    r["audit_scope"] = r["audit_verdict"] = ""; r["version"] = "v3"; r["interview_style_note"] = ""
quarantine, spot, corrections = [], [], []
unapplied_all = []
for p in pil.to_dict("records"):
    rid = p["id"]; v = audits[rid]
    rec = dict(question=p["question"], answer=p["answer"], common_mistakes=json.loads(p["common_mistakes"] or "[]"), key_concepts=[x for x in p["key_concepts"].split("; ") if x])
    code = json.loads(json.dumps(v2_tests[rid])) if rid in v2_tests else None
    before = dict(rec, difficulty=p["difficulty"], code=json.loads(json.dumps(code)) if code else None)
    applied, unapplied, notes = apply_audit(rid, rec, code, v)
    apply_patches(rid, rec, code)
    diff_before = p["difficulty"]; diff = C.DIFFICULTY.get(rid, p["difficulty"])
    if unapplied: unapplied_all += [(rid, u) for u in unapplied]
    sev = [i["severity"] for i in v["issues"]]
    status = "pass" if v["verdict"] == "pass" else "corrected"
    if v["verdict"] == "quarantine": status = "quarantined"
    scope = "stratified_sample_21" if rid in sample else "extension_audit_20"
    note = f"v3 independent audit ({scope}): {v['verdict']}" + (f"; {len(applied)} correction(s) applied" if applied else "") + (f"; open minor notes: {' / '.join(notes)}" if notes else "")
    if diff != diff_before: note += f"; difficulty {diff_before}->{diff} (blind auditor rating adopted)"
    if rid in C.DIFFICULTY_KEPT: note += "; " + C.DIFFICULTY_KEPT[rid]
    srcs = json.loads(p["sources"] or "[]")
    if srcs:
        stat = {}
        for f in (v.get("sources_findings") or []):
            stat.setdefault(f.get("url"), []).append(f.get("status"))
        for sx in srcs:
            st = stat.get(sx["url"])
            if st:
                worst = "supported" if all(x == "supported" for x in st) else next(x for x in st if x != "supported")
                sx["verification"] = "independent_reviewer_" + worst
                if worst != "supported":
                    note += f"; source {sx['url']} judged '{worst}' by the audit: the page supports the cited sentence but not every claim in the answer (the rest was verified by running code)"
    row = dict(p, sources=json.dumps(srcs, ensure_ascii=False), question=rec["question"], answer=rec["answer"].strip(), key_concepts="; ".join(rec["key_concepts"]), difficulty=diff,
               common_mistakes=json.dumps(rec["common_mistakes"], ensure_ascii=False), version="v3", introduced_in="v3-pilot01",
               audit_scope=scope, audit_verdict=status, review_notes=(p["review_notes"] + " | " + note).strip(" |"),
               has_code_test="yes" if code else "no", code_language=(code["language"] if code else ""))
    if status == "quarantined": quarantine.append(row)
    else:
        rows[rid] = row
        if code: code_tests[rid] = code
    spot.append(dict(id=rid, plan_id=p["plan_id"], domain=p["domain"], question_type=p["question_type"], scope=scope, verdict=v["verdict"], status=status,
                     major=sev.count("major"), minor=sev.count("minor"), corrections_applied=len(applied), difficulty_before=diff_before, difficulty_blind=v.get("difficulty_blind"),
                     difficulty_after=diff, code_findings=v.get("code_findings"), sources_findings=v.get("sources_findings"), reasons=v.get("reasons"),
                     issues=v["issues"], parts_answered=v.get("parts_answered"), nearest_existing=v.get("nearest_existing"), source_file=v["_file"]))
    for fld in ("question", "answer"):
        if before[fld] != rec[fld].strip() if fld == "answer" else before[fld] != rec[fld]:
            corrections.append(dict(id=rid, field=fld, change="text corrected after audit"))
    if before["code"] != code: corrections.append(dict(id=rid, field="code", change="reference code/test changed after audit"))
    if diff != diff_before: corrections.append(dict(id=rid, field="difficulty", change=f"{diff_before} -> {diff}"))
    if before["key_concepts"] != rec["key_concepts"]: corrections.append(dict(id=rid, field="key_concepts", change="revised"))

# ------------------------------------------------------------------ 2. batch 02 (separate)
plan = jl(ST / "pilot02_plan.json")
order = [it[0] for d in C.B2_ORDER for it in plan[d]]
gen = {}
for f in ("gen2_NLP.json", "gen2_DL.json", "gen2_PY.json", "gen2_DA.json"):
    for r in jl(ST / f): gen[r["id"]] = r
batch, b2_review = [], []
for n, pid in enumerate(order, 1):
    g = gen[pid]; v = audits[pid]; hid = f"smi-h{n:04d}"
    assert g["status"] == "ok", pid
    rec = dict(question=g["question"].strip(), answer=g["answer"].strip(), common_mistakes=list(g.get("common_mistakes") or []), key_concepts=list(g["key_concepts"]))
    code = json.loads(json.dumps(g["code"])) if g.get("code") else None
    applied, unapplied, notes = apply_audit(pid, rec, code, v)
    apply_patches(pid, rec, code)
    unapplied_all += [(pid, u) for u in unapplied]
    diff0 = g["difficulty"]; diff = C.DIFFICULTY.get(pid, diff0)
    status = {"pass": "pass", "correct": "corrected", "quarantine": "quarantined"}[v["verdict"]]
    note = f"independent review: {v['verdict']}" + (f"; {len(applied)} correction(s) applied" if applied else "") + (f"; open minor notes: {' / '.join(notes)}" if notes else "")
    if diff != diff0: note += f"; difficulty {diff0}->{diff} (blind auditor rating adopted)"
    srcs = g.get("sources") or []
    row = dict(id=hid, domain=g["domain"], topic=C.B2_TOPIC[pid], difficulty=diff, question_type=g["question_type"], question=rec["question"], answer=rec["answer"].strip(),
               key_concepts="; ".join(rec["key_concepts"]), common_mistakes=json.dumps(rec["common_mistakes"], ensure_ascii=False), source_type="ai_generated_original",
               source_file="", source_record_id="", source_processed_id="", source_domain="", source_difficulty="", domain_in_processed_data="", plan_id=pid,
               triage_status="", modification="new_in_stage1b_batch02", v1_modification="", correction_basis="", known_limitations="", review_notes=note,
               sources=json.dumps([dict(title=s["title"], url=s["url"], supports=s["supports"], verification="opened_by_author_agent_only") for s in srcs], ensure_ascii=False),
               has_code_test="yes" if code else "no", code_language=(code["language"] if code else ""),
               verification="ai_generated+ai_reviewed" + ("+code_executed" if code else "") + ("+source_opened" if srcs else ""),
               version="v3-pilot02", introduced_in="v3-batch02", audit_scope="batch02_independent_review", audit_verdict=status,
               interview_style_note=g.get("interview_style_note", ""))
    if status == "quarantined": quarantine.append(row)
    else:
        batch.append(row)
        if code: code_tests[hid] = code
    sev = [i["severity"] for i in v["issues"]]
    b2_review.append(dict(id=hid, plan_id=pid, domain=g["domain"], verdict=v["verdict"], status=status, major=sev.count("major"), minor=sev.count("minor"),
                          corrections_applied=len(applied), difficulty_author=diff0, difficulty_blind=v.get("difficulty_blind"), difficulty_final=diff,
                          code_findings=v.get("code_findings"), reasons=v.get("reasons"), issues=v["issues"], parts_answered=v.get("parts_answered"),
                          nearest_existing=v.get("nearest_existing")))
assert not unapplied_all, f"audit corrections that could not be applied: {unapplied_all}"

# ------------------------------------------------------------------ write
COLS = ["id", "domain", "topic", "difficulty", "question_type", "question", "answer", "key_concepts", "common_mistakes", "source_type", "source_file",
        "source_record_id", "source_processed_id", "source_domain", "source_difficulty", "domain_in_processed_data", "plan_id", "triage_status",
        "modification", "v1_modification", "correction_basis", "known_limitations", "review_notes", "sources", "has_code_test", "code_language",
        "verification", "version", "introduced_in", "audit_scope", "audit_verdict", "interview_style_note"]
core_df = pd.DataFrame(sorted(rows.values(), key=lambda r: r["id"]))[COLS]
b2_df = pd.DataFrame(batch)[COLS]
q_df = pd.DataFrame(quarantine, columns=COLS) if quarantine else pd.DataFrame(columns=COLS)
core_df.to_csv(OUT / "curated_questions.csv", index=False, encoding="utf-8")
b2_df.to_csv(OUT / "pilot_batch_02.csv", index=False, encoding="utf-8")
q_df.to_csv(OUT / "quarantine.csv", index=False, encoding="utf-8")
def to_json(df, p):
    recs = df.to_dict("records")
    for r in recs:
        r["key_concepts"] = [x for x in r["key_concepts"].split("; ") if x]
        r["sources"] = json.loads(r["sources"]); r["known_limitations"] = [x for x in re.split(r";\s*", r["known_limitations"]) if x]
        r["common_mistakes"] = json.loads(r["common_mistakes"]) if r.get("common_mistakes") else []
    Path(p).write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
to_json(core_df, OUT / "curated_questions.json"); to_json(b2_df, OUT / "pilot_batch_02.json")
(OUT / "code_tests.json").write_text(json.dumps({k: code_tests[k] for k in sorted(code_tests)}, indent=1, ensure_ascii=False), encoding="utf-8")
(OUT / "pilot01_spotcheck.json").write_text(json.dumps(dict(sampled_ids=sorted(sample), method="stratified sample of 21 (NLP 7, Deep Learning 5, SQL 9; Medium and Hard) audited first; "
    "because 5 of 21 needed content corrections the audit was extended to the remaining 20 (so all 41 were audited)", records=spot), indent=1, ensure_ascii=False), encoding="utf-8")
pd.DataFrame([{k: v for k, v in s.items() if k not in ("code_findings", "sources_findings", "reasons", "issues", "parts_answered", "nearest_existing")} for s in spot]).to_csv(OUT / "pilot01_spotcheck.csv", index=False, encoding="utf-8")
pd.DataFrame(corrections).to_csv(OUT / "pilot01_corrections.csv", index=False, encoding="utf-8")
(OUT / "batch02_review.json").write_text(json.dumps(b2_review, indent=1, ensure_ascii=False), encoding="utf-8")
queue.to_csv(OUT / "review_queue.csv", index=False, encoding="utf-8")
for f in ("lineage.csv", "removed_duplicates.csv"): (OUT / f).write_bytes((V2 / f).read_bytes())
pd.DataFrame(log, columns=["id", "event", "detail"]).to_csv(OUT / "build_log.csv", index=False, encoding="utf-8")

# cross-version execution of every Python reference test on extra interpreters (optional)
xres = {}
xp = [p for p in os.environ.get("SMI_XPYTHONS", "").split(",") if p]
for py in [sys.executable] + xp:
    tmp = OUT / "_x.json"; res = OUT / "_xr.json"
    tmp.write_text(json.dumps(code_tests)); subprocess.run([py, str(ST / "xrun.py"), str(tmp), str(res)], capture_output=True)
    ver = subprocess.run([py, "-c", "import sys;print('py'+sys.version.split()[0]);import numpy;print('np'+numpy.__version__)"], capture_output=True, text=True).stdout.split()
    try:
        pv = subprocess.run([py, "-c", "import pandas;print('pd'+pandas.__version__)"], capture_output=True, text=True).stdout.split()
    except Exception: pv = []
    key = "/".join(ver + pv)
    for k, v in jl(res).items(): xres.setdefault(k, {})[key] = v
    tmp.unlink(); res.unlink()
(OUT / "cross_version_results.json").write_text(json.dumps(xres, indent=1), encoding="utf-8")

(OUT / "README.md").write_text((HERE / "README_curated_v3.md").read_text(encoding="utf-8"), encoding="utf-8")
subprocess.run([sys.executable, str(HERE / "make_gap_analysis_v3.py"), str(ROOT)], check=True, capture_output=True)
files = ["README.md", "gap_analysis_v3.md", "curated_questions.csv", "curated_questions.json", "pilot_batch_02.csv", "pilot_batch_02.json", "quarantine.csv", "code_tests.json",
         "cross_version_results.json", "pilot01_spotcheck.json", "pilot01_spotcheck.csv", "pilot01_corrections.csv", "batch02_review.json", "review_queue.csv", "lineage.csv",
         "removed_duplicates.csv", "build_log.csv"]
manifest = {"version": "v3", "derived_from": ["data/curated/v1", "data/curated/v2"], "pilot_batch_02": "pending approval - not merged into curated_questions.csv",
            "counts": {"core": len(core_df), "pilot_batch_01_merged": len(pil) - sum(1 for q in quarantine if q["introduced_in"] == "v3-pilot01"), "pilot_batch_02": len(b2_df),
                       "quarantine": len(q_df), "review_queue": len(queue), "code_tests": len(code_tests)},
            "files": {f: sha(OUT / f) for f in files}}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print("core", len(core_df), "batch02", len(b2_df), "quarantine", len(q_df), "code tests", len(code_tests))
print(core_df.domain.value_counts().to_dict()); print(core_df.difficulty.value_counts().to_dict()); print(b2_df.difficulty.value_counts().to_dict())
