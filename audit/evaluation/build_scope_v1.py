"""Stage 3C-0 deterministic builder for the concept-scope sidecar scope_v1 (666 rows). AI-drafted; NEVER human-verified.
Run: python -m audit.evaluation.build_scope_v1 [--out DIR]"""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from audit.evaluation.scope_heuristic import tier_record
from audit.evaluation.scope_manual_zero import ZERO
from audit.evaluation.scope_manual_pilot import PILOT

VERSION = "scope_v1"
BUILDER_VERSION = "3c0.1"
POLICY = {
    "essential": "may reduce completeness if not demonstrated (state not_stated); an unverified essential concept lowers confidence, never correctness",
    "essential_groups": "at least min_required members must be demonstrated; any valid member counts; extra valid members are never required",
    "supporting": "may add credit or feedback only; absence is never penalised",
    "background": "feedback only; absence and extra content are never penalised or credited",
    "label_concepts": "restate the question topic; satisfied by the essentials; never graded separately",
    "completeness_penalty_eligible": "false => tiers are an unreviewed draft or flagged ambiguous: essential items may be reported as missing but must not reduce the score automatically",
    "unverified": "no credit, no penalty, lower confidence; never treated as incorrect",
}

def corpus_hash(recs):
    rows = [{k: r[k] for k in ("question_id", "question", "canonical_answer", "key_concepts", "difficulty", "domain")} for r in recs]
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def build_rows(recs):
    rows = []
    for r in recs:
        q = r["question_id"]
        manual = PILOT.get(q) or ZERO.get(q)
        src = "manual_pilot" if q in PILOT else "manual_zero_essential" if q in ZERO else "heuristic_v2"
        variants = sorted((r.get("alternative_answers") or {}).keys())
        if manual:
            ess, grp, sup, bg = list(manual["E"]), manual["G"], list(manual["S"]), list(manual["B"])
            lab = list(manual.get("L", []))
            alts = [{"text": t, "basis": "ai_proposed_technical_equivalent"} for t in manual.get("alt", [])]
            added = list(manual.get("added", []))
            flags = list(manual.get("flags", []))
            note = manual.get("note", "")
            status = "ai_reviewed_pilot"
        else:
            t = tier_record(r)
            ess = [c for c in r["key_concepts"] if t["tiers"][c] == "essential"]
            sup = [c for c in r["key_concepts"] if t["tiers"][c] == "supporting"]
            bg = [c for c in r["key_concepts"] if t["tiers"][c] == "background"]
            grp, lab, alts, added = [], [], [], []
            flags = list(t["flags"])
            note = "Heuristic v2 draft (question/reference word overlap); not individually reviewed."
            status = "ai_heuristic_draft"
        if variants:
            alts.append({"text": "Reference variants exist: " + ", ".join(variants) + " (same content, different style).", "basis": "existing_alternative_answers"})
        if not alts:
            alts.append({"text": "No specific alternatives recorded; verifier should accept synonyms, mathematical equivalents and valid technical alternatives.", "basis": "default_policy"})
        needs = status == "ai_heuristic_draft" and bool({"no_essential_concept", "all_essential_suspicious", "many_concepts_few_essential",
            "open_ended_design_or_scenario", "multi_part_question", "long_reference", "code_or_sql_exercise"} & set(flags))
        if status == "ai_reviewed_pilot":
            needs = bool(set(flags) & {"open_ended_requirement", "list_type_question_any_valid_members", "reference_broader_than_question",
                         "question_read_truncated_needs_full_review", "multi_part_question", "label_is_a_definition"}) or bool(manual.get("note", "").lower().count("human"))
        rows.append({
            "question_id": q, "question_type": r["question_type"] or "unspecified", "domain": r["domain"], "difficulty": r["difficulty"],
            "essential_concepts": ess, "essential_groups": grp, "supporting_concepts": sup, "background_concepts": bg,
            "label_concepts": lab, "added_concepts": added,
            "acceptable_alternative_explanations": alts, "verification_status": status, "tier_source": src,
            "ambiguity_flags": sorted(set(flags)), "human_review_required": bool(needs),
            "completeness_penalty_eligible": status == "ai_reviewed_pilot" and not needs,
            "review_notes": note})
    return rows

def build(out: Path):
    c = load_corpus()
    assert not c["problems"], c["problems"]
    recs = c["records"]
    rows = build_rows(recs)
    out.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in rows) + "\n"
    (out / "scope_v1.jsonl").write_text(body, encoding="utf-8", newline="\n")
    man = {"version": VERSION, "builder_version": BUILDER_VERSION, "records": len(rows),
           "sidecar_sha256": hashlib.sha256(body.encode()).hexdigest(), "corpus_content_sha256": corpus_hash(recs),
           "corpus_component_fingerprints": [{k: m[k] for k in ("name", "fingerprint", "csv_sha256")} for m in c["manifest"]["components"]],
           "verification_counts": {s: sum(1 for x in rows if x["verification_status"] == s) for s in sorted({x["verification_status"] for x in rows})},
           "human_verified": 0, "human_review_required": sum(1 for x in rows if x["human_review_required"]),
           "completeness_penalty_eligible": sum(1 for x in rows if x["completeness_penalty_eligible"]),
           "penalty_policy": POLICY, "ai_authored": True}
    (out / "scope_v1_manifest.json").write_text(json.dumps(man, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    return man

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "data/evaluation/scope"))
    print(json.dumps(build(Path(ap.parse_args().out)), indent=1)[:1500])
