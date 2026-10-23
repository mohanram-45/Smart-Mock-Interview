"""Stage 3C-0 quality controls. Returns a dict of named checks -> (ok, detail). Run: python -m audit.evaluation.stage3c_validate [--json]"""
import csv, hashlib, json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from audit.evaluation import build_scope_v1 as BS, build_bench_v2 as BB

FROZEN_CORPUS_SHA = "4c7700c489aa5d1e64b1a42924d80a749538081e28ec3e8429804b4eaa5fa2f4"
SCOPE = ROOT / "data/evaluation/scope"
BENCH = ROOT / "data/evaluation/bench_v2"
REVIEW = ROOT / "data/evaluation/stage3c_review"
ALT_BASIS = {"existing_alternative_answers", "ai_proposed_technical_equivalent", "default_policy"}
STATUSES = {"ai_heuristic_draft", "ai_reviewed_pilot"}

def read_jsonl(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def penalty_relevant_concepts(row):
    """The ONLY concepts that may lower completeness. Supporting/background/label concepts never appear here."""
    out = list(row["essential_concepts"]) + [("GROUP", g["label"], g["min_required"]) for g in row["essential_groups"]]
    return out if row.get("completeness_penalty_eligible") else []

def run():
    R = {}
    c = load_corpus(); recs = c["records"]; by = {r["question_id"]: r for r in recs}
    rows = read_jsonl(SCOPE / "scope_v1.jsonl"); man = json.loads((SCOPE / "scope_v1_manifest.json").read_text())
    ids = [r["question_id"] for r in rows]
    R["ids_map_666"] = (len(rows) == 666 and set(ids) == set(by) and len(set(ids)) == 666 and ids == [r["question_id"] for r in recs],
                        f"rows={len(rows)} unique={len(set(ids))} missing={len(set(by)-set(ids))} extra={len(set(ids)-set(by))} order_matches_corpus={ids == [r['question_id'] for r in recs]}")
    R["question_type_matches"] = (all(r["question_type"] == (by[r["question_id"]]["question_type"] or "unspecified") for r in rows), "question_type copied from corpus")
    R["corpus_unchanged"] = (not c["problems"] and BS.corpus_hash(recs) == FROZEN_CORPUS_SHA == man["corpus_content_sha256"],
                             f"problems={len(c['problems'])} content_sha_matches_pin={BS.corpus_hash(recs) == FROZEN_CORPUS_SHA}")
    csv_ok = all(sha(ROOT / m["csv"]) == m["csv_sha256"] for m in c["manifest"]["components"] if (ROOT / m["csv"]).exists())
    present = sum((ROOT / m["csv"]).exists() for m in c["manifest"]["components"])
    R["frozen_csv_sha"] = (csv_ok and present == len(c["manifest"]["components"]), f"csv present={present}/{len(c['manifest']['components'])} sha ok={csv_ok}")
    bad = []
    for r in rows:
        kc = set(by[r["question_id"]]["key_concepts"]); add = set(r["added_concepts"])
        flat = list(r["essential_concepts"]) + [x for g in r["essential_groups"] for x in g["concepts"]] + list(r["supporting_concepts"]) + list(r["background_concepts"]) + list(r["label_concepts"])
        tiers = [list(r["essential_concepts"]), [x for g in r["essential_groups"] for x in set(g["concepts"])], list(r["supporting_concepts"]), list(r["background_concepts"]), list(r["label_concepts"])]
        # tiers must be disjoint; a concept may sit in two different essential groups (separate parts of a multi-part question)
        seen = [set(t) for t in tiers]
        if any(len(t) != len(set(t)) for t in tiers[:1] + tiers[2:]) or any(seen[i] & seen[j] for i in range(5) for j in range(i + 1, 5)) or any(len(g["concepts"]) != len(set(g["concepts"])) for g in r["essential_groups"]):
            bad.append((r["question_id"], "duplicate/overlapping tiers"))
        if set(flat) - kc - add: bad.append((r["question_id"], "concept not from key_concepts/added", sorted(set(flat) - kc - add)))
        if kc - set(flat): bad.append((r["question_id"], "unassigned key concept", sorted(kc - set(flat))))
        for g in r["essential_groups"]:
            if not (1 <= g["min_required"] <= len(g["concepts"])): bad.append((r["question_id"], "group unsatisfiable", g["label"]))
        if not (r["essential_concepts"] or r["essential_groups"]) and "no_essential_concept" not in r["ambiguity_flags"] and r["verification_status"] == "ai_heuristic_draft":
            bad.append((r["question_id"], "no essential and not flagged"))
    R["tiers_consistent"] = (not bad, f"violations={len(bad)} {bad[:3]}")
    R["optional_never_penalised"] = (all(not (set(r["supporting_concepts"]) | set(r["background_concepts"]) | set(r["label_concepts"])) & {x for x in penalty_relevant_concepts(r) if isinstance(x, str)} for r in rows)
                                     and all((not r["completeness_penalty_eligible"]) or (r["verification_status"] == "ai_reviewed_pilot" and not r["human_review_required"]) for r in rows)
                                     and "never penalised" in man["penalty_policy"]["background"] + man["penalty_policy"]["supporting"],
                                     f"penalty_eligible_rows={sum(r['completeness_penalty_eligible'] for r in rows)}; supporting/background/label excluded by construction")
    # essential requirements vs question: heuristic rows must overlap question or headline (proxy); manual rows were individually read
    from audit.evaluation.scope_heuristic import words, stem, sentences
    weak = []
    for r in rows:
        if r["tier_source"] != "heuristic_v2": continue
        rec = by[r["question_id"]]; q = words(rec["question"]); sents = sentences(rec["canonical_answer"]); head = words(sents[0]) if sents else set()
        for e in r["essential_concepts"]:
            kw = words(e)
            if kw and not (kw & q or kw <= head): weak.append((r["question_id"], e))
    R["essential_vs_question_proxy"] = (not weak, f"heuristic essentials without question/headline overlap={len(weak)}; contradiction beyond this proxy needs human review")
    altbad = []
    for r in rows:
        for a in r["acceptable_alternative_explanations"]:
            if a["basis"] not in ALT_BASIS or not a["text"].strip(): altbad.append((r["question_id"], a))
            if a["basis"] == "existing_alternative_answers":
                for v in (by[r["question_id"]]["alternative_answers"] or {}):
                    if v not in a["text"]: altbad.append((r["question_id"], "variant missing", v))
        if not r["acceptable_alternative_explanations"]: altbad.append((r["question_id"], "no alternatives entry"))
    R["alternatives_have_basis"] = (not altbad, f"ai_proposed={sum(a['basis']=='ai_proposed_technical_equivalent' for r in rows for a in r['acceptable_alternative_explanations'])}; technical justification by AI only, not human-verified; problems={len(altbad)}")
    R["human_review_identifiable"] = (all(isinstance(r["human_review_required"], bool) and r["verification_status"] in STATUSES for r in rows) and man["human_verified"] == 0
                                      and man["human_review_required"] == sum(r["human_review_required"] for r in rows),
                                      f"human_review_required={man['human_review_required']} human_verified={man['human_verified']}")
    # reproducibility
    with tempfile.TemporaryDirectory() as t:
        m2 = BS.build(Path(t)); same = m2["sidecar_sha256"] == man["sidecar_sha256"] == sha(SCOPE / "scope_v1.jsonl")
    R["scope_reproducible"] = (same and man["sidecar_sha256"] == sha(SCOPE / "scope_v1.jsonl"), f"sidecar_sha256={man['sidecar_sha256'][:16]}..")
    # bench
    q = read_jsonl(BENCH / "questions.jsonl"); a = read_jsonl(BENCH / "answers.jsonl"); l = read_jsonl(BENCH / "ai_labels.jsonl"); bm = json.loads((BENCH / "manifest.json").read_text())
    R["bench_size_and_ids"] = (96 <= len(a) <= 120 and len({x["answer_id"] for x in a}) == len(a) and {x["answer_id"] for x in a} == {x["answer_id"] for x in l}
                               and {x["question_id"] for x in a} == {x["question_id"] for x in q}, f"answers={len(a)} questions={len(q)}")
    R["bench_fresh"] = (not {x["question_id"] for x in q} & set(BB.USED) and all(x["question_id"] in by for x in q) and all(
        by[x["question_id"]]["question"] == x["question"] for x in q), f"overlap_with_tuning_questions={sorted({x['question_id'] for x in q} & set(BB.USED))}")
    R["bench_inputs_label_free"] = (all(set(x) == {"answer_id", "question_id", "answer_text"} for x in a) and all(set(x) == {"question_id", "domain", "difficulty", "question_type", "question"} for x in q), "evaluator input files carry no kind/score/label fields")
    kinds = {x["answer_kind"] for x in l}; need = {"correct_full", "concise_sufficient", "valid_alternative", "partial", "incorrect", "hallucinated", "off_topic", "injection"}
    types = {x["question_type"] for x in q}
    R["bench_coverage"] = (len({x["domain"] for x in q}) == 8 and {x["difficulty"] for x in q} == {"Easy", "Medium", "Hard"} and need <= kinds
                           and {"coding", "sql_exercise", "scenario", "design"} <= types and any("ambiguous_reference" in x["flags"] for x in l) and sum("prompt_injection" in x["flags"] for x in l) >= 5,
                           f"domains=8 types={sorted(types)} kinds_missing={sorted(need-kinds)}")
    R["bench_labels_provisional"] = (all(x["label_status"] == "ai_provisional_not_human_reviewed" and 0 <= x["expected_score_min"] <= x["expected_score_max"] <= 100 for x in l) and bm["human_reviewed_labels"] == 0, "all labels AI-provisional, ranges valid")
    shs = {k: sha(BENCH / k) for k in bm["sha256"]}
    R["bench_manifest_matches"] = (shs == bm["sha256"], "file sha256 equals manifest")
    with tempfile.TemporaryDirectory():
        before = {k: sha(BENCH / k) for k in bm["sha256"]}
        BB.build(); after = {k: sha(BENCH / k) for k in bm["sha256"]}
    R["bench_reproducible"] = (before == after, "rebuild is byte-identical")
    sh = list(csv.DictReader(open(REVIEW / "pilot_review_sheet_v2.csv", encoding="utf-8")))
    blank = all(not r["reviewer_score_0_100"] and not r["reviewer_factual_correctness"] and not r["reviewer_comments"] for r in sh)
    R["review_sheet"] = (20 <= len(sh) <= 30 and blank and all("AI_PROVISIONAL" in k for k in sh[0] if k.startswith(("factual", "proposed"))) and {r["answer_id"] for r in sh} <= {x["answer_id"] for x in a},
                         f"rows={len(sh)} reviewer fields blank={blank}")
    return R

if __name__ == "__main__":
    R = run()
    if "--json" in sys.argv: print(json.dumps({k: {"ok": v[0], "detail": v[1]} for k, v in R.items()}, indent=1))
    else:
        for k, (ok, d) in R.items(): print(("PASS " if ok else "FAIL ") + k + " :: " + d)
    sys.exit(0 if all(v[0] for v in R.values()) else 1)
