#!/usr/bin/env python3
"""Build data/curated/v1 from the audit triage (Stage 1 remediation).

Reads (never modifies): data/audit/triage.csv, data/raw/questions_seed.csv, audit/triage/dec_*.py (code checks only).
Writes (new files only): data/curated/v1/*
Usage: python audit/remediation/build_curated_v1.py [project_root]
"""
import sys, re, json, hashlib, csv
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parents[1]
sys.path.insert(0, str(HERE))
import curated_v1_config as C

OUT = ROOT / "data" / "curated" / "v1"
if OUT.exists() and any(OUT.iterdir()) and "--force" not in sys.argv:
    sys.exit(f"{OUT} already contains files; refusing to overwrite (use --force only for this version's own files)")
OUT.mkdir(parents=True, exist_ok=True)

norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
PFX = re.compile(r"^(Ans\.\s*|Solution:\s*|-\s+)")
triage = pd.read_csv(ROOT / "data/audit/triage.csv", keep_default_na=False)
raw = pd.read_csv(ROOT / "data/raw/questions_seed.csv").set_index("id")
seed = triage[triage.source_type == "seed"]

KEEP_LIMITS = {"THIN_ANSWER", "IMPRECISE", "OPEN_ENDED", "TIME_SENSITIVE", "QUESTION_FORMAT", "OVERSTATED"}
FIX_LIMITS = {"OPEN_ENDED", "TIME_SENSITIVE"}

cands = []
for r in seed.itertuples():
    ok = r.status == "KEEP" or (r.status == "FIX" and r.review_state == "ready_for_approval")
    if not ok:
        continue
    flags = set(f for f in r._asdict()["flags"].split(";") if f)
    if r.status == "KEEP":
        a = PFX.sub("", r.reference_answer).strip()
        first = a.split(" ", 1)[0]
        if first.isalpha() and len(first) > 1 and first[0].islower():   # sentence-case fragments only; notation like "p > n", "k-means" untouched
            a = a[0].upper() + a[1:]
        mod = "prefix_stripped" if a != r.reference_answer else "none"
        q, basis = r.question, ""
        limits = sorted(flags & KEEP_LIMITS)
    else:
        a = r.proposed_answer or PFX.sub("", r.reference_answer).strip()
        if not r.proposed_answer:
            f0 = a.split(" ", 1)[0]
            if f0.isalpha() and len(f0) > 1 and f0[0].islower(): a = a[0].upper() + a[1:]
        q = r.proposed_question or r.question
        mod = ("answer_and_question_corrected" if r.proposed_answer and r.proposed_question else
               "answer_corrected" if r.proposed_answer else
               "question_corrected" if r.proposed_question else "metadata_only")
        basis = r.proposal_basis
        limits = sorted(flags & FIX_LIMITS)
    cands.append(dict(pid=int(r.id), raw_id=int(r.raw_id), status=r.status, mod=mod, basis=basis, domain_processed=r.domain,
                      domain=(C.DOMAIN_OVERRIDE.get(int(r.id)) or r.proposed_domain or r.domain),
                      diff_prop=r.proposed_difficulty, question=q, answer=a, limits=limits,
                      raw_domain=r.raw_domain, raw_difficulty=r.raw_difficulty))
cand = pd.DataFrame(cands)

dispo = {}
for pid, (kept, why) in C.DUPLICATES_REMOVED.items():
    dispo[pid] = ("REMOVED_DUPLICATE", f"duplicate of {kept}: {why}")
for pid, why in C.MOVED_TO_QUEUE.items():
    dispo[pid] = ("REVIEW_QUEUE", "moved from approved set after factual review: " + why)
final = cand[~cand.pid.isin(dispo)].copy().reset_index(drop=True)
removed = cand[cand.pid.isin(C.DUPLICATES_REMOVED)]
moved = cand[cand.pid.isin(C.MOVED_TO_QUEUE)]

# ---- fields
KC = json.loads((HERE / "key_concepts_v1.json").read_text(encoding="utf-8"))   # tags drafted by an AI assistant from each record's own text; grounding checked by the validator

rows = []
for r in final.itertuples():
    d, t = C.TOPIC[r.pid]
    assert d == r.domain, (r.pid, d, r.domain)
    kc = [("database normalization" if (k == "normalization" and r.domain == "SQL") else k) for k in KC[f"smi-{r.raw_id:04d}"]]
    rows.append(dict(
        id=f"smi-{r.raw_id:04d}", domain=r.domain, topic=t, difficulty=C.DIFF_OVERRIDE.get(r.pid, r.diff_prop),
        question=norm(r.question), answer=r.answer.strip(), key_concepts="; ".join(kc),
        source_file="data/raw/questions_seed.csv", source_record_id=r.raw_id, source_processed_id=r.pid,
        source_domain=raw.loc[r.raw_id, "domain"], source_difficulty=raw.loc[r.raw_id, "difficulty"],
        domain_in_processed_data=r.domain_processed, triage_status=r.status, modification=r.mod, correction_basis=r.basis,
        known_limitations="; ".join(r.limits), verification="", version="v1"))
cur = pd.DataFrame(rows)

# ---- code checks (executed answers)
sys.path.insert(0, str(ROOT / "audit/triage"))
import load_all  # noqa  (registers decisions)
D = load_all.D
import dec_11_py as PYD
FENCE = re.compile(r"```python\n(.*?)\n```", re.S)
code_checks = {}
for r in cur.itertuples():
    pid = r.source_processed_id
    blocks = FENCE.findall(r.answer)
    tests = getattr(PYD, f"T{pid}", None)
    if blocks or D[pid].get("code"):
        body = "\n\n".join(blocks)
        if tests is None:  # inline example (e.g. 3681): the stored check is the whole snippet
            body, tests = "", D[pid]["code"]
        code_checks[r.id] = {"blocks": len(blocks), "code": (body + "\n" + tests).strip() + "\n"}
cur["verification"] = cur.id.map(lambda i: "ai_reviewed+code_executed" if i in code_checks else "ai_reviewed")

# ---- queue
queue_rows = []
for r in seed[(seed.status == "FIX") & (seed.review_state != "ready_for_approval")].itertuples():
    need = {"needs_review": "subject-matter reviewer must confirm or edit the proposal",
            "needs_code_test": "run the example in an environment with the missing dependency/data, then confirm",
            "needs_source": "a citable source is required before any answer is written"}[r.review_state]
    queue_rows.append(dict(id=f"smi-{int(r.raw_id):04d}", source_processed_id=int(r.id), source_record_id=int(r.raw_id), queue_origin="triage_FIX_not_ready",
        review_state=r.review_state, proposal_confidence=r.proposal_confidence, domain=r.domain, proposed_domain=r.proposed_domain,
        proposed_difficulty=r.proposed_difficulty, flags=r._asdict()["flags"], reason=r.note, required_to_resolve=need,
        original_question=r.question, original_answer=r.reference_answer, proposed_question=r.proposed_question, proposed_answer=r.proposed_answer))
for r in moved.itertuples():
    queue_rows.append(dict(id=f"smi-{r.raw_id:04d}", source_processed_id=r.pid, source_record_id=r.raw_id, queue_origin="moved_after_factual_review",
        review_state="needs_review", proposal_confidence="", domain=r.domain_processed, proposed_domain="", proposed_difficulty=r.diff_prop,
        flags="IMPRECISE", reason=C.MOVED_TO_QUEUE[r.pid], required_to_resolve="decide whether to correct the wording (suggestion in reason) or drop",
        original_question=seed[seed.id == r.pid].iloc[0].question, original_answer=seed[seed.id == r.pid].iloc[0].reference_answer,
        proposed_question=r.question if r.question != seed[seed.id == r.pid].iloc[0].question else "", proposed_answer=r.answer))
queue = pd.DataFrame(queue_rows).sort_values("source_processed_id")

# ---- lineage (every original record)
lin = []
inc = {int(x): v for x, v in zip(cur.source_processed_id, cur.id)}
qids = {int(x): v for x, v in zip(queue.source_processed_id, queue.id)}
for r in triage.itertuples():
    pid = int(r.id)
    if r.source_type == "generated":
        disp, vid, why = "EXCLUDED_TEMPLATE", "", "generated template record"
    elif pid in inc:
        disp, vid, why = "INCLUDED", inc[pid], ""
    elif pid in qids:
        disp, vid, why = "REVIEW_QUEUE", qids[pid], ""
    elif pid in C.DUPLICATES_REMOVED:
        disp, vid, why = "REMOVED_DUPLICATE", "", dispo[pid][1]
    else:
        assert r.status == "EXCLUDE", pid
        disp, vid, why = "EXCLUDED", "", r.note
    lin.append(dict(source_processed_id=pid, source_record_id=r.raw_id, source_file=r.source_file, triage_status=r.status,
                    disposition=disp, v1_id=vid, reason=why))
lin = pd.DataFrame(lin)

# ---- write
cur.to_csv(OUT / "curated_questions.csv", index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
recs = cur.to_dict("records")
for x in recs:
    x["key_concepts"] = [c for c in x["key_concepts"].split("; ") if c]
    x["known_limitations"] = [c for c in x["known_limitations"].split("; ") if c]
(OUT / "curated_questions.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
queue.to_csv(OUT / "review_queue.csv", index=False, encoding="utf-8")
lin.to_csv(OUT / "lineage.csv", index=False, encoding="utf-8")
pd.DataFrame([dict(removed_id=f"smi-{r.raw_id:04d}", removed_processed_id=r.pid, kept_id=f"smi-{int(seed[seed.id == C.DUPLICATES_REMOVED[r.pid][0]].iloc[0].raw_id):04d}",
                   kept_processed_id=C.DUPLICATES_REMOVED[r.pid][0], reason=C.DUPLICATES_REMOVED[r.pid][1], removed_question=r.question) for r in removed.itertuples()]
             ).to_csv(OUT / "removed_duplicates.csv", index=False, encoding="utf-8")
(OUT / "code_checks.json").write_text(json.dumps(code_checks, indent=1), encoding="utf-8")
def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest = {"version": "v1", "built_from": ["data/audit/triage.csv", "data/raw/questions_seed.csv"],
            "counts": {"original_records": len(lin), "included": len(cur), "review_queue": len(queue), "removed_duplicates": len(removed),
                       "excluded": int((lin.disposition == "EXCLUDED").sum()), "excluded_template": int((lin.disposition == "EXCLUDED_TEMPLATE").sum())},
            "files": {f: _sha(OUT / f) for f in ["curated_questions.csv", "curated_questions.json", "review_queue.csv", "lineage.csv", "removed_duplicates.csv", "code_checks.json"]}}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print("included", len(cur), "queue", len(queue), "removed dups", len(removed), "lineage", len(lin))
print(cur.domain.value_counts().to_dict()); print(cur.difficulty.value_counts().to_dict())
