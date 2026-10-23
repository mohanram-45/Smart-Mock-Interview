#!/usr/bin/env python3
"""Build data/curated/v4 (Stage 1B final consolidation).

v4 core     = v3 core (401, unchanged) + batch-02 records that passed Phase 1 re-verification (46 minus quarantined), corrections applied
batch 03    = 40 new questions (ML, SQL, Python, Data Analysis), independently reviewed, kept separate (not merged)
quarantine  = any record whose correctness remained uncertain (header only if empty)

Reads (never modifies): data/curated/v1, v2, v3; audit/remediation/stage1b4/* (drafts, verifications, reviews); curated_v4_config.py
Writes (new files only): data/curated/v4/*
Usage: python audit/remediation/build_curated_v4.py [project_root] [--force]
Env:   SMI_XPYTHONS=py1,py2  extra interpreters on which every Python reference test is re-run (-> cross_version_results.json)
"""
import sys, re, json, hashlib, os, subprocess
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = Path(args[0]).resolve() if args else HERE.parents[1]
sys.path.insert(0, str(HERE))
import curated_v4_config as C

V1, V2, V3, OUT, ST = ROOT / "data/curated/v1", ROOT / "data/curated/v2", ROOT / "data/curated/v3", ROOT / "data/curated/v4", HERE / "stage1b4"
if OUT.exists() and any(OUT.iterdir()) and "--force" not in sys.argv:
    sys.exit(f"{OUT} already contains files; refusing to overwrite (use --force only for this version's own files)")
OUT.mkdir(parents=True, exist_ok=True)
jl = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
FENCE_PY = re.compile(r"```python\n(.*?)\n```", re.S)

def apply_fixes(rid, rec, code, issues, sync_code):
    """Exact-substring replacements. issues: [{severity, claim, replacement|None, problem}]. Returns (applied, unapplied, notes)."""
    applied, unapplied, notes = [], [], []
    for iss in issues:
        claim, rep, sev = iss["claim"], iss.get("replacement"), iss["severity"]
        if not rep:
            notes.append(f"[{sev}] {iss['problem']}"); continue
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
            if done and sync_code and code:
                for k in ("solution", "test", "setup"):
                    if code.get(k) and claim in code[k]: code[k] = code[k].replace(claim, rep)
        (applied if done else unapplied).append((sev, claim[:80], (rep or "")[:80]))
    return applied, unapplied, notes

def apply_patches(rid, rec, code):
    for fld_key, fld, old, new in C.PATCHES:
        if fld_key != rid: continue
        holder, key = (code, fld.split(".")[1]) if fld.startswith("code.") else (rec, fld)
        assert old in holder[key], (rid, fld, "patch target not found")
        holder[key] = holder[key].replace(old, new, 1)
    if rid in C.APPEND_ANSWER: rec["answer"] = rec["answer"].rstrip() + C.APPEND_ANSWER[rid]

# ------------------------------------------------------------------ inputs
core3 = pd.read_csv(V3 / "curated_questions.csv", keep_default_na=False, dtype=str)
b2 = pd.read_csv(V3 / "pilot_batch_02.csv", keep_default_na=False, dtype=str)
tests3 = jl(V3 / "code_tests.json")
queue = pd.read_csv(V3 / "review_queue.csv", keep_default_na=False, dtype=str)
p1 = {}
for f in ("p1_out_NLP.json", "p1_out_DLPY.json", "p1_out_DA.json"):
    for v in jl(ST / f): p1[v["id"]] = v
rev3 = {}
for f in ("rev3_out_ML.json", "rev3_out_SQL.json", "rev3_out_PY.json", "rev3_out_DA.json"):
    for v in jl(ST / f): rev3[v["id"]] = v
NEWCOLS = ["v4_verification", "evidence_summary", "remaining_limitations"]
code_tests = {k: v for k, v in tests3.items() if k in set(core3.id)}
rows = {r["id"]: dict(r, **{c: "" for c in NEWCOLS}) for r in core3.to_dict("records")}
for r in rows.values(): r["version"] = "v4"
unapplied_all, quarantine, b2corr, b2ver = [], [], [], []

# ------------------------------------------------------------------ 1. batch 02: Phase 1 re-verification applied
for p in b2.to_dict("records"):
    rid = p["id"]
    rec = dict(question=p["question"], answer=p["answer"], common_mistakes=json.loads(p["common_mistakes"] or "[]"), key_concepts=[x for x in p["key_concepts"].split("; ") if x])
    code = json.loads(json.dumps(tests3[rid])) if rid in tests3 else None
    before = json.loads(json.dumps(dict(rec, code=code, difficulty=p["difficulty"])))
    v = p1.get(rid); note = ""; ver = "independent_review_v3_only"; ev = ""; lim = ""
    if v:
        applied, unapplied, notes = apply_fixes(rid, rec, code, [dict(severity=x["severity"], claim=x["claim"], replacement=x["replacement"], problem=x["problem"]) for x in v["fixes"]], sync_code=False)
        unapplied_all += [(rid, u) for u in unapplied]
        cp = v.get("code_patch")
        if cp:
            for k in ("setup", "solution", "test"):
                if cp.get(k): code[k] = cp[k]
        if v.get("suggested_key_concepts"): rec["key_concepts"] = list(v["suggested_key_concepts"])
        meth = {}
        for e in v["evidence"]: meth[e.get("method", "?")] = meth.get(e.get("method", "?"), 0) + 1
        ver = "reverified_v4_" + ("verified" if v["verdict"] == "verified" else "corrected")
        ev = "claims by method " + ", ".join(f"{k}:{n}" for k, n in sorted(meth.items())) + "; code re-run " + "/".join(f"{k}={x}" for k, x in v["code_rerun"].items())
        lim = " | ".join(v.get("remaining_limitations") or [])
        note = f"v4 re-verification: {v['verdict']}" + (f"; {len(applied)} text fix(es)" if applied else "") + ("; code patched and re-tested" if cp else "")
        if v["verdict"] == "quarantine": ver = "quarantined"
        b2ver.append(dict(id=rid, plan_id=p["plan_id"], verdict=v["verdict"], evidence=v["evidence"], remaining_limitations=v.get("remaining_limitations"), fixes=v["fixes"],
                          code_patch_applied=bool(cp), code_rerun=v["code_rerun"], difficulty_ok=v.get("difficulty_ok"), suggested_difficulty=v.get("suggested_difficulty")))
    apply_patches(rid, rec, code)
    diff = p["difficulty"]
    if rid in C.DIFFICULTY_KEPT: note += "; " + C.DIFFICULTY_KEPT[rid]
    row = dict(p, question=rec["question"], answer=rec["answer"].strip(), key_concepts="; ".join(rec["key_concepts"]), difficulty=diff, version="v4",
               common_mistakes=json.dumps(rec["common_mistakes"], ensure_ascii=False), introduced_in="v3-batch02", has_code_test="yes" if code else "no",
               review_notes=(p["review_notes"] + (" | " + note if note else "")).strip(" |"), v4_verification=ver, evidence_summary=ev, remaining_limitations=lim,
               audit_scope="batch02_independent_review" + ("+v4_reverification" if v else ""))
    if ver == "quarantined": quarantine.append(row)
    else:
        rows[rid] = row
        if code: code_tests[rid] = code
    for fld in ("question", "answer"):
        if before[fld] != rec[fld].strip(): b2corr.append(dict(id=rid, field=fld, change="text corrected in v4"))
    if before["code"] != code: b2corr.append(dict(id=rid, field="code", change="reference code/test changed in v4"))
    if before["key_concepts"] != rec["key_concepts"]: b2corr.append(dict(id=rid, field="key_concepts", change="revised"))

# ------------------------------------------------------------------ 2. batch 03 (separate)
plan = jl(ST / "pilot03_plan.json")
order = [it[0] for d in C.B3_ORDER for it in plan[d]]
gen = {}
for f in ("gen3_ML.json", "gen3_SQL.json", "gen3_PY.json", "gen3_DA.json"):
    for r in jl(ST / f): gen[r["id"]] = r
batch, b3rev = [], []
for n, pid in enumerate(order, 1):
    g = gen[pid]; v = rev3[pid]; iid = f"smi-i{n:04d}"
    assert g["status"] == "ok", pid
    rec = dict(question=g["question"].strip(), answer=g["answer"].strip(), common_mistakes=list(g.get("common_mistakes") or []), key_concepts=list(g["key_concepts"]))
    code = json.loads(json.dumps(g["code"])) if g.get("code") else None
    applied, unapplied, notes = apply_fixes(pid, rec, code, v["issues"], sync_code=True)
    unapplied_all += [(pid, u) for u in unapplied if not (v.get("suggested_key_concepts") and "key concept" in str(u).lower() or (v.get("suggested_key_concepts") and u[1].startswith("COUNT DISTINCT")))]
    if v.get("suggested_key_concepts"): rec["key_concepts"] = list(v["suggested_key_concepts"])
    apply_patches(pid, rec, code)
    diff0 = g["difficulty"]; diff = v.get("difficulty_blind") or diff0
    status = {"pass": "pass", "correct": "corrected", "quarantine": "quarantined"}[v["verdict"]]
    note = f"independent review: {v['verdict']}" + (f"; {len(applied)} correction(s) applied" if applied else "") + (f"; open minor notes: {' / '.join(notes)}" if notes else "")
    if diff != diff0: note += f"; difficulty {diff0}->{diff} (blind auditor rating adopted)"
    stat = {}
    for f in (v.get("sources_findings") or []): stat.setdefault(f.get("url"), []).append(f.get("status"))
    srcs = []
    for s in (g.get("sources") or []):
        st = stat.get(s["url"])
        ver = ("independent_reviewer_" + ("supported" if all(x == "supported" for x in st) else next(x for x in st if x != "supported"))) if st else "opened_by_author_agent_only"
        srcs.append(dict(title=s["title"], url=s["url"], supports=s["supports"], verification=ver))
    row = dict(id=iid, domain=g["domain"], topic=C.B3_TOPIC[pid], difficulty=diff, question_type=g["question_type"], question=rec["question"], answer=rec["answer"].strip(),
               key_concepts="; ".join(rec["key_concepts"]), common_mistakes=json.dumps(rec["common_mistakes"], ensure_ascii=False), source_type="ai_generated_original",
               source_file="", source_record_id="", source_processed_id="", source_domain="", source_difficulty="", domain_in_processed_data="", plan_id=pid,
               triage_status="", modification="new_in_stage1b_batch03", v1_modification="", correction_basis="", known_limitations="", review_notes=note,
               sources=json.dumps(srcs, ensure_ascii=False), has_code_test="yes" if code else "no", code_language=(code["language"] if code else ""),
               verification="ai_generated+ai_reviewed" + ("+code_executed" if code else "") + ("+source_opened" if srcs else ""),
               version="v4-batch03", introduced_in="v4-batch03", audit_scope="batch03_independent_review", audit_verdict=status, interview_style_note=g.get("interview_style_note", ""),
               v4_verification="", evidence_summary="", remaining_limitations="")
    if status == "quarantined": quarantine.append(row)
    else:
        batch.append(row)
        if code: code_tests[iid] = code
    sev = [i["severity"] for i in v["issues"]]
    b3rev.append(dict(id=iid, plan_id=pid, domain=g["domain"], verdict=v["verdict"], status=status, major=sev.count("major"), minor=sev.count("minor"), corrections_applied=len(applied),
                      difficulty_author=diff0, difficulty_blind=v.get("difficulty_blind"), difficulty_final=diff, code_findings=v.get("code_findings"), reasons=v.get("reasons"),
                      issues=v["issues"], parts_answered=v.get("parts_answered"), nearest_existing=v.get("nearest_existing"), sources_findings=v.get("sources_findings")))
assert not unapplied_all, f"corrections that could not be applied: {unapplied_all}"

# ------------------------------------------------------------------ write
COLS = ["id", "domain", "topic", "difficulty", "question_type", "question", "answer", "key_concepts", "common_mistakes", "source_type", "source_file",
        "source_record_id", "source_processed_id", "source_domain", "source_difficulty", "domain_in_processed_data", "plan_id", "triage_status",
        "modification", "v1_modification", "correction_basis", "known_limitations", "review_notes", "sources", "has_code_test", "code_language",
        "verification", "version", "introduced_in", "audit_scope", "audit_verdict", "interview_style_note"] + NEWCOLS
core_df = pd.DataFrame(sorted(rows.values(), key=lambda r: r["id"]))[COLS]
b3_df = pd.DataFrame(batch)[COLS]
q_df = pd.DataFrame(quarantine, columns=COLS) if quarantine else pd.DataFrame(columns=COLS)
core_df.to_csv(OUT / "curated_questions.csv", index=False, encoding="utf-8")
b3_df.to_csv(OUT / "pilot_batch_03.csv", index=False, encoding="utf-8")
q_df.to_csv(OUT / "quarantine.csv", index=False, encoding="utf-8")
def to_json(df, p):
    recs = df.to_dict("records")
    for r in recs:
        r["key_concepts"] = [x for x in r["key_concepts"].split("; ") if x]
        r["sources"] = json.loads(r["sources"]); r["known_limitations"] = [x for x in re.split(r";\s*", r["known_limitations"]) if x]
        r["common_mistakes"] = json.loads(r["common_mistakes"]) if r.get("common_mistakes") else []
    Path(p).write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
to_json(core_df, OUT / "curated_questions.json"); to_json(b3_df, OUT / "pilot_batch_03.json")
(OUT / "code_tests.json").write_text(json.dumps({k: code_tests[k] for k in sorted(code_tests)}, indent=1, ensure_ascii=False), encoding="utf-8")
(OUT / "batch02_verification.json").write_text(json.dumps(b2ver, indent=1, ensure_ascii=False), encoding="utf-8")
pd.DataFrame(b2corr).to_csv(OUT / "batch02_corrections.csv", index=False, encoding="utf-8")
(OUT / "batch03_review.json").write_text(json.dumps(b3rev, indent=1, ensure_ascii=False), encoding="utf-8")
queue.to_csv(OUT / "review_queue.csv", index=False, encoding="utf-8")
for f in ("lineage.csv", "removed_duplicates.csv"): (OUT / f).write_bytes((V3 / f).read_bytes())

xres = {}
xp = [p for p in os.environ.get("SMI_XPYTHONS", "").split(",") if p]
for py in [sys.executable] + xp:
    tmp, res = OUT / "_x.json", OUT / "_xr.json"
    tmp.write_text(json.dumps(code_tests)); subprocess.run([py, str(HERE / "stage1b3" / "xrun.py"), str(tmp), str(res)], capture_output=True)
    ver = subprocess.run([py, "-c", "import sys,numpy,pandas;print('py'+sys.version.split()[0]);print('np'+numpy.__version__);print('pd'+pandas.__version__)"], capture_output=True, text=True).stdout.split()
    for k, v in jl(res).items(): xres.setdefault(k, {})["/".join(ver)] = v
    tmp.unlink(); res.unlink()
(OUT / "cross_version_results.json").write_text(json.dumps(xres, indent=1), encoding="utf-8")

(OUT / "README.md").write_text((HERE / "README_curated_v4.md").read_text(encoding="utf-8"), encoding="utf-8")
subprocess.run([sys.executable, str(HERE / "make_gap_analysis_v4.py"), str(ROOT)], check=True, capture_output=True)
subprocess.run([sys.executable, str(HERE / "rag_readiness_v4.py"), str(ROOT)], check=True, capture_output=True)
files = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name != "manifest.json")
manifest = {"version": "v4", "derived_from": ["data/curated/v1", "data/curated/v2", "data/curated/v3"], "batch_03": "kept separate - awaiting review",
            "counts": {"core": len(core_df), "batch_02_merged": int((core_df.introduced_in == "v3-batch02").sum()), "batch_03": len(b3_df), "quarantine": len(q_df),
                       "review_queue": len(queue), "code_tests": len(code_tests)},
            "files": {f: sha(OUT / f) for f in files}}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print("core", len(core_df), "batch03", len(b3_df), "quarantine", len(q_df), "code tests", len(code_tests))
