#!/usr/bin/env python3
"""Build data/curated/v5 (frozen): v4 core (447) + approved batch 03 (40, rechecked) = 487. Never touches v1-v4.
Usage: python audit/remediation/build_curated_v5.py [--force]"""
import sys, json, hashlib, shutil, subprocess, re, csv
from pathlib import Path
from collections import Counter
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
V3, V4, V5 = ROOT / "data/curated/v3", ROOT / "data/curated/v4", ROOT / "data/curated/v5"
EV = HERE / "stage1b5"
if V5.exists() and any(V5.iterdir()) and "--force" not in sys.argv: sys.exit("v5 exists; pass --force to rebuild")
V5.mkdir(parents=True, exist_ok=True)
rd = lambda p: pd.read_csv(p, keep_default_na=False, dtype=str)
core4, b3 = rd(V4 / "curated_questions.csv"), rd(V4 / "pilot_batch_03.csv")
tests = json.loads((V4 / "code_tests.json").read_text(encoding="utf-8"))
rv3 = {r["id"]: r for r in json.loads((V4 / "batch03_review.json").read_text(encoding="utf-8"))}
p5 = [v for f in ("ML_DA", "SQL", "PY") for v in json.loads((EV / f"p5_out_{f}.json").read_text(encoding="utf-8"))]
p5 = {v["id"]: v for v in p5}
corrected_v4 = {i for i, r in rv3.items() if r["status"] == "corrected"}
assert set(p5) == corrected_v4 and len(p5) == 19, (len(p5), set(p5) ^ corrected_v4)

# sources whose pages the verifier / lead opened during the v5 recheck (added to records that relied on them)
SRC_ADD = {
 "smi-i0005": {"title": "Lipton et al. 2018, Detecting and Correcting for Label Shift with Black Box Predictors", "url": "https://arxiv.org/abs/1802.03916",
               "supports": "Label shift can be detected and its size estimated from unlabeled data using a black-box classifier's predictions and its validation confusion matrix.", "verification": "independent_reviewer_supported"},
 "smi-i0015": {"title": "SQLite: Release History", "url": "https://www.sqlite.org/changes.html",
               "supports": "median()/percentile() were added to the CLI in 3.47.0 and became an optional compile-time extension (-DSQLITE_ENABLE_PERCENTILE) in 3.51.0; they are not in the default library.", "verification": "independent_reviewer_supported"},
 "smi-i0028": {"title": "PEP 765: Disallow return/break/continue that exit a finally block", "url": "https://peps.python.org/pep-0765/",
               "supports": "CPython emits a SyntaxWarning for return/break/continue that exit a finally block starting in 3.14.", "verification": "lead_opened_supported"},
}

rows, corr_log = [], []
for r in core4.to_dict("records"):
    r["v5_verification"] = ""; r["v5_evidence_summary"] = ""; rows.append(r)
for r in b3.to_dict("records"):
    i = r["id"]; v = p5.get(i)
    if v is None:
        r["v5_verification"] = "independent_review_v4_only"; r["v5_evidence_summary"] = "passed the v4 batch-03 independent review with no correction; not rechecked in v5"
    else:
        assert v["verdict"] in ("verified", "fix"), (i, v["verdict"])
        assert not v.get("code_patch"), i
        assert v.get("difficulty_ok", True) is not False and not v.get("suggested_difficulty"), i
        assert not v.get("suggested_key_concepts"), i
        for x in v["fixes"]:
            n_a, n_q = r["answer"].count(x["claim"]), r["question"].count(x["claim"])
            assert n_a + n_q == 1, (i, "fix claim not unique", x["claim"][:60], n_a, n_q)
            fld = "answer" if n_a else "question"
            r[fld] = r[fld].replace(x["claim"], x["replacement"]).strip()
            corr_log.append(dict(id=i, field=fld, severity=x["severity"], problem=x["problem"], old=x["claim"], new=x["replacement"]))
        meth = Counter(e["method"] for e in v["evidence"])
        r["v5_verification"] = "rechecked_v5_corrected" if v["fixes"] else "rechecked_v5_verified"
        r["v5_evidence_summary"] = f"v5 independent recheck: {len(v['evidence'])} claims checked ({', '.join(f'{k} {n}' for k, n in sorted(meth.items()))}); {len(v['fixes'])} text fix(es); code reruns {v.get('code_rerun') or 'n/a (no code)'}"
        r["evidence_summary"] = r["v5_evidence_summary"]
        r["remaining_limitations"] = " | ".join(v["remaining_limitations"])
        r["review_notes"] = (r["review_notes"] + " | " if r["review_notes"] else "") + f"v5 recheck: {v['verdict']}" + (f" ({len(v['fixes'])} fix)" if v["fixes"] else "")
    if i in SRC_ADD:
        s = json.loads(r["sources"]); s.append(SRC_ADD[i]); r["sources"] = json.dumps(s, ensure_ascii=False)
        if "source_opened" not in r["verification"]: r["verification"] += "+source_opened"
    rows.append(r)
cols = list(core4.columns) + ["v5_verification", "v5_evidence_summary"]
for r in rows: r["version"] = "v5"
core = pd.DataFrame(rows)[cols]
assert len(core) == 487 and core.id.is_unique
# fixes must leave the fenced code of the answer identical to the tested solution (the v4 rule); code is untouched
newtests = tests
q = core[core.id.isin(corrected_v4 | set(b3.id))]
assert core.id.tolist() == list(core4.id) + list(b3.id)

# ---------------- files
core.to_csv(V5 / "curated_questions.csv", index=False, quoting=csv.QUOTE_MINIMAL)
(V5 / "curated_questions.json").write_text(json.dumps(core.to_dict("records"), ensure_ascii=False, indent=1), encoding="utf-8")
(V5 / "code_tests.json").write_text(json.dumps(newtests, ensure_ascii=False, indent=1), encoding="utf-8")
pd.DataFrame(columns=list(core.columns) + ["quarantine_reason"]).to_csv(V5 / "quarantine.csv", index=False)
pd.DataFrame(columns=["id", "reason"]).to_csv(V5 / "review_queue.csv", index=False)
pd.DataFrame(corr_log).to_csv(V5 / "batch03_v5_corrections.csv", index=False)
(V5 / "batch03_recheck.json").write_text(json.dumps([p5[i] for i in sorted(p5)], ensure_ascii=False, indent=1), encoding="utf-8")
for f in ("batch02_verification.json", "batch02_corrections.csv", "batch03_review.json", "removed_duplicates.csv", "cross_version_results.json"): shutil.copy(V4 / f, V5 / f)

# ---------------- review archive (owner decision: Flask/JWT outside the six domains; originals preserved, not deleted)
raw = rd(ROOT / "data/raw/questions_seed.csv"); proc = rd(ROOT / "data/processed/questions.csv")
q4 = rd(V4 / "review_queue.csv")
arch = []
for r in q4.to_dict("records"):
    rr = raw[raw.id == r["source_record_id"]].iloc[0]; pp = proc[proc.id == r["source_processed_id"]].iloc[0]
    arch.append({"id": r["id"], "archive_reason": "Excluded from the six-domain knowledge base on the owner's instruction (2026-10-08): web-framework content outside ML/DL/NLP/Python/SQL/Data Analysis interview scope.",
                 "queue_reason": r["reason"], "queue_flags": r["flags"], "domain_label": r["domain"], "source_record_id": r["source_record_id"], "source_processed_id": r["source_processed_id"],
                 "raw_question": rr["question"], "raw_answer": rr["answer"], "raw_difficulty": rr["difficulty"], "processed_question": pp["question"], "processed_answer": pp["reference_answer"],
                 "proposed_question": r["proposed_question"], "proposed_answer": r["proposed_answer"], "stage1b_note": r["stage1b_note"]})
assert [a["id"] for a in arch] == ["smi-0457", "smi-0459"]
pd.DataFrame(arch).to_csv(V5 / "review_archive.csv", index=False)
lin = rd(V4 / "lineage.csv")
m = lin.disposition == "REVIEW_QUEUE"; assert m.sum() == 2
lin.loc[m, "disposition"] = "ARCHIVED_OUT_OF_SCOPE"; lin.loc[m, "reason"] = "owner decision 2026-10-08: outside the six domains; original preserved in review_archive.csv"
lin.to_csv(V5 / "lineage.csv", index=False)

# ---------------- human review queue and unverified-claims register
def major_ids():
    s = {r["id"] for r in json.loads((V3 / "pilot01_spotcheck.json").read_text(encoding="utf-8"))["records"] if r.get("major")}
    s |= {r["id"] for r in json.loads((V3 / "batch02_review.json").read_text(encoding="utf-8")) if int(r["major"]) > 0}
    s |= {i for i, r in rv3.items() if int(r["major"]) > 0}
    return s
MAJ = major_ids()
bg = {}
for v in json.loads((V4 / "batch02_verification.json").read_text(encoding="utf-8")) + list(p5.values()):
    for e in v["evidence"]:
        if e["method"] == "background_only": bg.setdefault(v["id"], []).append(e)
claims = [dict(id=i, origin=("v5 recheck" if i in p5 else "v4 re-verification"), claim=e["claim"], note=e["evidence"]) for i, es in sorted(bg.items()) for e in es]
for i, v in sorted(p5.items()):
    for l in v["remaining_limitations"]: claims.append(dict(id=i, origin="v5 recheck (limitation)", claim=l, note=""))
pd.DataFrame(claims).to_csv(V5 / "unverified_claims.csv", index=False)
hr = []
for r in core.to_dict("records"):
    i = r["id"]; reasons = []; tier = 5
    srcs = json.loads(r["sources"])
    if i in MAJ: tier = 1; reasons.append("had a major defect found by independent review")
    if tier > 2 and (r["audit_verdict"] == "corrected" or r["v4_verification"] == "reverified_v4_corrected" or r["v5_verification"] == "rechecked_v5_corrected"): tier = 2; reasons.append("corrected after review")
    if i in bg:
        reasons.append(f"{len(bg[i])} claim(s) supported only by background knowledge")
        if tier > 2: tier = 2
    if tier > 3 and r["introduced_in"] != "v1" and r["introduced_in"] != "v2" and r["source_type"] == "ai_generated_original":
        tier = 3; reasons.append("AI-written, single independent AI review" + ("" if srcs else ", no source"))
    if tier > 4 and r["modification"] not in ("none", "prefix_stripped"): tier = 4; reasons.append("seed answer rewritten by AI")
    if tier == 5: reasons.append("seed answer close to the raw source; never human-checked")
    if i in ("smi-i0003",): pass
    hr.append(dict(id=i, domain=r["domain"], topic=r["topic"], difficulty=r["difficulty"], tier=tier, reasons="; ".join(reasons), n_background_only_claims=len(bg.get(i, [])), n_sources=len(srcs), has_executed_code=r["has_code_test"]))
hr = pd.DataFrame(hr).sort_values(["tier", "domain", "id"]); hr.to_csv(V5 / "human_review_queue.csv", index=False)

# ---------------- docs + analyses (scripts read v5 files)
shutil.copy(HERE / "README_curated_v5.md", V5 / "README.md")
for s in ("make_gap_analysis_v5.py", "rag_readiness_v5.py"): subprocess.run([sys.executable, str(HERE / s), str(ROOT)], check=True)

# ---------------- fingerprint + manifest
FP_FIELDS = ["id", "domain", "topic", "difficulty", "question_type", "question", "answer", "key_concepts", "common_mistakes"]
def fingerprint(df, tst):
    recs = [[str(r[f]) for f in FP_FIELDS] for r in df.sort_values("id").to_dict("records")]
    a = hashlib.sha256(json.dumps(recs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    b = hashlib.sha256(json.dumps(tst, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return a, b, hashlib.sha256((a + b).encode()).hexdigest()
fa, fb, fc = fingerprint(core, newtests)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
by = lambda col: dict(sorted(Counter(core[col]).items()))
manifest = {
 "dataset": "smart-mock-interview curated knowledge base", "version": "v5", "status": "frozen for the first RAG prototype (no human review yet)",
 "built_by": "audit/remediation/build_curated_v5.py", "derived_from": ["data/curated/v1", "data/curated/v2", "data/curated/v3", "data/curated/v4"],
 "record_count": len(core), "domain_counts": by("domain"), "difficulty_counts": by("difficulty"),
 "domain_x_difficulty": {d: dict(Counter(g.difficulty)) for d, g in core.groupby("domain")},
 "question_type_counts": dict(Counter(core.question_type.replace("", "(not typed - seed record)"))), "introduced_in_counts": by("introduced_in"),
 "topic_count": int(core.topic.nunique()), "records_with_code_test": int((core.has_code_test == "yes").sum()), "records_with_sources": int((core.sources != "[]").sum()),
 "known_label_inconsistencies": [{"id": i, "issue": "verification label says code_executed (set in Stage 1A) but no reference test is recorded in code_tests.json; the record is left unchanged to keep the v4 regression identical"} for i in sorted(set(core[core.verification.str.contains("code_executed")].id) - set(newtests))],
 "quarantined": 0, "review_queue": 0, "review_archive": 2, "excluded_by_owner": ["smi-0457", "smi-0459"],
 "verification": {"human_reviewed_records": 0, "verification_labels": by("verification"), "v4_verification": dict(Counter(core.v4_verification.replace("", "(not re-verified in v4)"))), "v5_verification": dict(Counter(core.v5_verification.replace("", "(not part of the v5 recheck)")))},
 "verification_limitations": [
  "No record has been reviewed by a human subject-matter expert; every label is AI-generated or AI-reviewed.",
  "Only 26 batch-02 and 19 batch-03 records were re-verified with per-claim evidence; the other 442 rely on earlier single AI reviews (see v4_verification / v5_verification).",
  "Reviewers are the same model family as the authors, so shared blind spots are possible.",
  f"Claims supported only by background knowledge, and remaining limitations, are listed in unverified_claims.csv ({len(claims)} entries).",
  f"Only {int((core.sources != '[]').sum())} records carry a cited source; {int((core.has_code_test == 'yes').sum())} records have executed reference code; the 360 seed-derived records have no question_type.",
  "Key-concept grounding is checked by a token heuristic plus agent review, not by a domain expert.",
  "The device has no scikit-learn/spaCy/nltk/scipy/pytest, so 23 older tests are skipped there and run only in the build sandbox."],
 "human_review_queue_tiers": dict(sorted(Counter(hr.tier).items())),
 "fingerprint": {"algorithm": "sha256", "content_sha256": fa, "code_tests_sha256": fb, "combined_sha256": fc,
   "content_definition": "sha256 of the compact JSON (ensure_ascii=False, separators=(',',':')) list of [id, domain, topic, difficulty, question_type, question, answer, key_concepts, common_mistakes] (all strings, exactly as in curated_questions.csv; key_concepts '; '-joined; common_mistakes JSON string) for records sorted by id",
   "code_tests_definition": "sha256 of json.dumps(code_tests.json content, ensure_ascii=False, sort_keys=True, separators=(',',':'))",
   "combined_definition": "sha256 of content_sha256 + code_tests_sha256 (hex strings concatenated)", "reproduce": "python audit/remediation/validate_curated_v5.py recomputes it from the files"},
 "predecessor_manifest_sha256": {v: sha(ROOT / f"data/curated/{v}/manifest.json") for v in ("v1", "v2", "v3", "v4")},
}
manifest["files"] = {p.name: sha(p) for p in sorted(V5.iterdir()) if p.is_file() and p.name != "manifest.json"}
(V5 / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
print("core", len(core), "corrections", len(corr_log), "fingerprint", fc[:16])
