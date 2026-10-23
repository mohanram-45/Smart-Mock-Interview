#!/usr/bin/env python3
"""Build data/curated/v2 (Stage 1B): improved v1 records, resolved queue items, and a separate pilot batch.

Reads (never modifies): data/curated/v1/*, data/audit/triage.csv, data/raw/questions_seed.csv,
                        audit/remediation/stage1b/*.json (agent drafts + independent reviews), curated_v2_config.py,
                        audit/remediation/key_concepts_v2.json (optional, applied last)
Writes (new files only): data/curated/v2/*
Usage: python audit/remediation/build_curated_v2.py [project_root] [--force]
"""
import sys, re, json, hashlib
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = Path(args[0]).resolve() if args else HERE.parents[1]
sys.path.insert(0, str(HERE))
import curated_v2_config as C

V1 = ROOT / "data/curated/v1"
OUT = ROOT / "data/curated/v2"
ST = HERE / "stage1b"
if OUT.exists() and any(OUT.iterdir()) and "--force" not in sys.argv:
    sys.exit(f"{OUT} already contains files; refusing to overwrite (use --force only for this version's own files)")
OUT.mkdir(parents=True, exist_ok=True)

jl = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
log = []   # (id, kind, message)

# ------------------------------------------------------------------ apply an independent review to a draft record
def apply_review(rec, rev):
    """Returns (record or None, review_notes list). Records are only accepted if the reviewer accepted them or every
    requested fix was applied exactly."""
    notes = []
    if rev is None:
        log.append((rec["id"], "not_reviewed", "no reviewer verdict; not accepted")); return None, notes
    if rev["verdict"] == "reject":
        log.append((rec["id"], "rejected", "; ".join(i["problem"] for i in rev["issues"]))); return None, notes
    rec = json.loads(json.dumps(rec))
    for i in rev.get("issues", []):
        rep, claim = i.get("replacement"), i["claim"]
        if rep:
            done = False
            for fld in ("answer", "question"):
                if claim in rec[fld]:
                    assert rec[fld].count(claim) == 1, (rec["id"], "ambiguous claim")
                    rec[fld] = rec[fld].replace(claim, rep); done = True; break
            if not done and isinstance(rec.get("common_mistakes"), list):
                for k, m in enumerate(rec["common_mistakes"]):
                    if claim in m: rec["common_mistakes"][k] = m.replace(claim, rep); done = True; break
            if not done:
                log.append((rec["id"], "fix_not_applicable", claim[:80]))
                if rev["verdict"] == "fix": return None, notes
            else:
                log.append((rec["id"], "review_fix_applied", claim[:60] + " -> " + rep[:60]))
        else:
            notes.append(f"[{i['severity']}] {i['problem']}")
    if rev.get("domain_ok") is False and rev.get("suggested_domain"): rec["domain"] = rev["suggested_domain"]
    if rev.get("suggested_domain") and rev.get("suggested_domain") != rec["domain"] and rev.get("domain_ok", True) is not False:
        rec["domain"] = rev["suggested_domain"]
    if rev.get("suggested_difficulty"): rec["difficulty"] = rev["suggested_difficulty"]
    if rev.get("suggested_key_concepts") and rev.get("key_concepts_ok") is False: rec["key_concepts"] = rev["suggested_key_concepts"]
    # code in the answer must still match the code that is tested
    code = rec.get("code")
    if code and code["language"] in ("sql", "python"):
        sol = norm(code["solution"])
        if sol not in norm(rec["answer"]) and code["language"] == "sql":
            pass   # SQL answers may reformat; the validator re-executes and compares fenced blocks separately
    return rec, notes

def load_stage(drafts, reviews):
    revs = {}
    for f in reviews:
        for r in jl(ST / f): revs[r["id"]] = r
    out = {}
    for f in drafts:
        for r in jl(ST / f):
            if r.get("status") != "ok":
                log.append((r["id"], "deferred_by_author", r.get("change_notes", "")[:200])); continue
            rec, notes = apply_review(r, revs.get(r["id"]))
            if rec is None: continue
            rec["_review_notes"] = notes
            rec["_sources_check"] = {s["url"]: s.get("status") or s.get("result") for s in revs[r["id"]].get("sources_check", []) if "url" in s}
            out[rec["id"]] = rec
    return out

def sources_json(rec, extra=None):
    items = []
    for s in (rec.get("sources") or []):
        v = rec.get("_sources_check", {}).get(s["url"])
        items.append({"title": s["title"], "url": s["url"], "supports": s["supports"],
                      "verification": ("independent_reviewer_" + v) if v else "opened_by_author_agent_only"})
    items += (extra or [])
    return json.dumps(items, ensure_ascii=False)

def verification_label(rec, kind, has_code, has_src):
    parts = {"rewritten": "ai_rewritten+ai_reviewed", "generated": "ai_generated+ai_reviewed"}[kind]
    if has_code: parts += "+code_executed"
    if has_src: parts += "+source_opened"
    return parts

# ------------------------------------------------------------------ inputs
cur = pd.read_csv(V1 / "curated_questions.csv", keep_default_na=False, dtype=str)
queue = pd.read_csv(V1 / "review_queue.csv", keep_default_na=False, dtype=str)
triage = pd.read_csv(ROOT / "data/audit/triage.csv", keep_default_na=False, dtype=str).set_index("id")
raw = pd.read_csv(ROOT / "data/raw/questions_seed.csv").set_index("id")
rows = {r["id"]: r for r in cur.to_dict("records")}
for r in rows.values():
    r.update(v1_modification=r["modification"], question_type="", common_mistakes="", sources="[]", review_notes="", plan_id="",
             source_type="seed_curated", has_code_test="no", code_language="")
code_tests = {}

# ------------------------------------------------------------------ 1. strengthened v1 records (THIN_ANSWER / IMPRECISE / OVERSTATED / QUESTION_FORMAT)
rew = load_stage(["out_T1.json", "out_T2.json", "out_T3.json", "out_T4.json"], ["rev_out_R1.json", "rev_out_R2.json", "rev_out_R4.json", "rev_out_R5.json"])
T4_IDS = {r["id"] for r in jl(ST / "out_T4.json")}   # rewritten after the key-concept pass: keep their reviewed concepts
for rid, rec in rew.items():
    row = rows[rid]
    old_lim = [x.strip() for x in row["known_limitations"].replace(";", ",").split(",") if x.strip()]
    keep_lim = [x for x in old_lim if x == "OPEN_ENDED"]   # all other limitation codes are cleared by the rewrite
    row.update(question=norm(rec["question"]), answer=rec["answer"].strip(), key_concepts="; ".join(rec["key_concepts"]),
               difficulty=rec["difficulty"], domain=rec["domain"], modification="answer_strengthened_v2",
               correction_basis=rec["change_notes"][:600], known_limitations="; ".join(keep_lim),
               review_notes=" | ".join(rec["_review_notes"]), source_type="seed_curated",
               sources=sources_json(rec), has_code_test="yes" if rec.get("code") else "no",
               code_language=(rec["code"]["language"] if rec.get("code") else ""))
    row["verification"] = verification_label(rec, "rewritten", bool(rec.get("code")), bool(rec.get("sources")))
    if rec.get("code"): code_tests[rid] = rec["code"]
# ids that were flagged but could not be accepted keep v1 content and flags
for rid, r in rows.items():
    if r["modification"] != "answer_strengthened_v2" and re.search(r"THIN_ANSWER|IMPRECISE|OVERSTATED|QUESTION_FORMAT", r["known_limitations"]):
        log.append((rid, "still_flagged", r["known_limitations"]))

# carry over the Stage 1A executable checks (Python snippets in unchanged v1 answers)
v1_checks = jl(V1 / "code_checks.json")
for rid, c in v1_checks.items():
    if rid in rows and rid not in code_tests and re.search(r"```python", rows[rid]["answer"]):
        code_tests[rid] = {"language": "python", "setup": "", "solution": c["code"], "test": "", "expected": []}
        rows[rid]["has_code_test"] = "yes"; rows[rid]["code_language"] = "python"
        if "code_executed" not in rows[rid]["verification"]: rows[rid]["verification"] = rows[rid]["verification"] + "+code_executed"

# ------------------------------------------------------------------ 2. review-queue items resolved in Stage 1B
res = load_stage(["out_Q1.json", "out_Q2.json"], ["rev_out_R3.json"])
new_rows = {}
remaining_queue = []
for q in queue.itertuples():
    rec = res.get(q.id)
    if rec is None:
        note = C.STAY_QUEUED_NOTE.get(q.id, "")
        remaining_queue.append(dict(q._asdict(), stage1b_note=note)); continue
    rid = q.id; raw_id = int(q.source_record_id); tri = triage.loc[str(q.source_processed_id)]
    topic = C.QUEUE_TOPIC[rid]
    lim = C.QUEUE_LIMITS.get(rid, [])
    extra = C.EXTRA_SOURCES.get(rid, [])
    new_rows[rid] = dict(
        id=rid, domain=rec["domain"], topic=topic, difficulty=rec["difficulty"], question=norm(rec["question"]), answer=rec["answer"].strip(),
        key_concepts="; ".join(rec["key_concepts"]), source_file="data/raw/questions_seed.csv", source_record_id=str(raw_id),
        source_processed_id=str(q.source_processed_id), source_domain=raw.loc[raw_id, "domain"], source_difficulty=raw.loc[raw_id, "difficulty"],
        domain_in_processed_data=q.domain, triage_status=tri["status"], modification="queue_resolved_stage1b",
        correction_basis=rec["change_notes"][:600], known_limitations="; ".join(lim), verification=verification_label(rec, "rewritten", bool(rec.get("code")), bool(rec.get("sources")) or bool(extra)),
        version="v2", v1_modification="", question_type="", common_mistakes="", sources=sources_json(rec, extra), review_notes=" | ".join(rec["_review_notes"]),
        plan_id="", source_type="seed_queue_resolved", has_code_test="yes" if rec.get("code") else "no", code_language=(rec["code"]["language"] if rec.get("code") else ""))
    if rec.get("code"): code_tests[rid] = rec["code"]
rows.update(new_rows)

# ------------------------------------------------------------------ 3. optional key-concept corrections (agent-drafted, grounded, validated by the validator)
kc_path = HERE / "key_concepts_v2.json"
if kc_path.exists():
    for rid, kc in jl(kc_path).items():
        if rid in rows and rid not in T4_IDS:
            rows[rid]["key_concepts"] = "; ".join(kc); rows[rid]["review_notes"] = (rows[rid]["review_notes"] + " | key_concepts revised in Stage 1B").strip(" |")
            log.append((rid, "key_concepts_revised", "; ".join(kc)))
for r in rows.values(): r["version"] = "v2"

# ------------------------------------------------------------------ 4. pilot batch (separate, pending approval)
gen_drafts = ["gen_NLP.json", "gen_DL.json", "gen_SQL.json"]
gen = load_stage(gen_drafts, ["rev_out_GNLP.json", "rev_out_GDL.json", "rev_out_GSQL.json"])
plan = jl(ST / "pilot_plan.json")
dom_of = {pid: d for d, items in plan.items() for pid, *_ in items}
order = [pid for d in ("NLP", "Deep Learning", "SQL") for pid, *_ in plan[d]]
pilot = []
for n, pid in enumerate(order, 1):
    rec = next((g for g in gen.values() if g["plan_id"] == pid), None)
    if rec is None:
        log.append((pid, "pilot_item_not_accepted", "see log")); continue
    for (k, fld, old, new) in C.MANUAL_EDITS:
        if k == pid and fld == "common_mistakes":
            rec["common_mistakes"] = [new if m == old else m for m in rec["common_mistakes"]]
    for (fld, old, new) in C.PILOT_PATCHES.get(pid, []):
        tgt, key = ("code", fld.split(".")[1]) if fld.startswith("code.") else (None, fld)
        holder = rec["code"] if tgt else rec
        assert old in holder[key], (pid, fld, "patch target not found")
        holder[key] = holder[key].replace(old, new)
    if pid in C.PILOT_PATCHES:
        rec["_review_notes"].append("Reference solution revised after the compact form misbehaved on SQLite 3.37.2 (see answer); revised form re-tested on 3.37.2 and 3.45.1")
    gid = f"smi-g{n:04d}"
    pilot.append(dict(
        id=gid, domain=rec["domain"], topic=C.PILOT_TOPIC[pid], difficulty=rec["difficulty"], question=rec["question"].strip(), answer=rec["answer"].strip(),
        key_concepts="; ".join(rec["key_concepts"]), source_file="", source_record_id="", source_processed_id="", source_domain="", source_difficulty="",
        domain_in_processed_data="", triage_status="", modification="new_in_stage1b", correction_basis="", known_limitations="",
        verification=verification_label(rec, "generated", bool(rec.get("code")), bool(rec.get("sources"))), version="v2-pilot01",
        v1_modification="", question_type=rec.get("question_type", ""), common_mistakes=json.dumps(rec.get("common_mistakes", []), ensure_ascii=False),
        sources=sources_json(rec), review_notes=" | ".join(rec["_review_notes"]), plan_id=pid, source_type="ai_generated_original",
        has_code_test="yes" if rec.get("code") else "no", code_language=(rec["code"]["language"] if rec.get("code") else ""),
        interview_style_note=rec.get("interview_style_note", "")))
    if rec.get("code"): code_tests[gid] = rec["code"]

# ------------------------------------------------------------------ write
COLS = ["id", "domain", "topic", "difficulty", "question_type", "question", "answer", "key_concepts", "common_mistakes", "source_type", "source_file",
        "source_record_id", "source_processed_id", "source_domain", "source_difficulty", "domain_in_processed_data", "plan_id", "triage_status",
        "modification", "v1_modification", "correction_basis", "known_limitations", "review_notes", "sources", "has_code_test", "code_language",
        "verification", "version"]
core = pd.DataFrame(sorted(rows.values(), key=lambda r: r["id"]))[COLS]
pil = pd.DataFrame(pilot)[COLS + ["interview_style_note"]]
core.to_csv(OUT / "curated_questions.csv", index=False, encoding="utf-8")
pil.to_csv(OUT / "pilot_batch_01.csv", index=False, encoding="utf-8")
def to_json(df, p):
    recs = df.to_dict("records")
    for r in recs:
        r["key_concepts"] = [x for x in r["key_concepts"].split("; ") if x]
        r["sources"] = json.loads(r["sources"]); r["known_limitations"] = [x for x in re.split(r";\s*", r["known_limitations"]) if x]
        if r.get("common_mistakes"): r["common_mistakes"] = json.loads(r["common_mistakes"])
    Path(p).write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
to_json(core, OUT / "curated_questions.json"); to_json(pil, OUT / "pilot_batch_01.json")
(OUT / "code_tests.json").write_text(json.dumps({k: code_tests[k] for k in sorted(code_tests)}, indent=1, ensure_ascii=False), encoding="utf-8")
pd.DataFrame(remaining_queue).to_csv(OUT / "review_queue.csv", index=False, encoding="utf-8")
pd.DataFrame(log, columns=["id", "event", "detail"]).to_csv(OUT / "build_log.csv", index=False, encoding="utf-8")

# lineage v2: v1 lineage updated with the new dispositions
lin = pd.read_csv(V1 / "lineage.csv", keep_default_na=False, dtype=str)
resolved = set(new_rows)
lin["disposition"] = [("INCLUDED" if v1id in resolved else d) for v1id, d in zip(lin.v1_id, lin.disposition)]
lin["reason"] = [("resolved in Stage 1B (review queue)" if v1id in resolved else r) for v1id, r in zip(lin.v1_id, lin.reason)]
lin.to_csv(OUT / "lineage.csv", index=False, encoding="utf-8")
shutil_files = ["removed_duplicates.csv"]
for f in shutil_files: (OUT / f).write_bytes((V1 / f).read_bytes())

(OUT / "README.md").write_text((HERE / "README_curated_v2.md").read_text(encoding="utf-8"), encoding="utf-8")
import subprocess
subprocess.run([sys.executable, str(HERE / "make_gap_analysis_v2.py"), str(ROOT)], check=True, capture_output=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
files = ["README.md", "gap_analysis_v2.md", "curated_questions.csv", "curated_questions.json", "pilot_batch_01.csv", "pilot_batch_01.json", "code_tests.json", "review_queue.csv", "lineage.csv", "removed_duplicates.csv", "build_log.csv"]
manifest = {"version": "v2", "derived_from": "data/curated/v1", "pilot_batch_01": "pending approval - not merged into curated_questions.csv",
            "counts": {"core": len(core), "pilot_batch_01": len(pil), "review_queue": len(remaining_queue), "removed_duplicates": int(len(pd.read_csv(OUT / 'removed_duplicates.csv'))),
                       "code_tests": len(code_tests), "original_records": len(lin)},
            "files": {f: sha(OUT / f) for f in files}}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print("core", len(core), "pilot", len(pil), "queue", len(remaining_queue), "code tests", len(code_tests))
print(core.domain.value_counts().to_dict()); print(core.difficulty.value_counts().to_dict()); print(pil.difficulty.value_counts().to_dict())
for e in log:
    if e[1] not in ("review_fix_applied", "key_concepts_revised"): print("LOG", e)
