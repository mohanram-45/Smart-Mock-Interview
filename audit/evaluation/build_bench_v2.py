"""Stage 3C-0 deterministic builder for bench_v2 + the human-review pilot sheet.
Evaluator inputs: questions.jsonl, answers.jsonl.  Labels (never given to an evaluator): ai_labels.jsonl, scoring_rubric.md.
Run: python -m audit.evaluation.build_bench_v2"""
import csv, hashlib, json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from audit.evaluation.bench_v2_source import ANS
from audit.evaluation.build_scope_v1 import build_rows

USED = "smi-0003 smi-0004 smi-0007 smi-0010 smi-0029 smi-0041 smi-0264 smi-0339 smi-0340 smi-0427 smi-0431 smi-0441 smi-0453 smi-0467 smi-j0024 smi-k0014 smi-l0040".split()
SEED = 20261014
BENCH = ROOT / "data/evaluation/bench_v2"
REVIEW = ROOT / "data/evaluation/stage3c_review"

RUBRIC = """# bench_v2 scoring rubric (LABEL-SIDE; never an evaluator input)

Status: AI-authored (Claude) and PROVISIONAL. No human has reviewed any label.

Dimensions (same weights as the Flask rubric): correctness 40, completeness 30, relevance 15, reasoning 15.

Provisional AI score bands used when drafting ranges:

| Band | Meaning |
|---|---|
| 85-100 | All essential requirements demonstrated, nothing materially wrong. Concise answers qualify. |
| 75-100 | Technically valid alternative: essentials met in a different but correct way. |
| 60-85 | Essentials mostly met but approximate or one minor gap. |
| 40-70 | Partly correct: some essentials missing, or a correct core with a major factual error (cap 60). |
| 15-40 | Mostly missing or mostly wrong, some on-topic content. |
| 0-25 | Incorrect, hallucinated or contradicts the question. |
| 0-10 | Off topic, no content, or only an instruction aimed at the grader. |

Rules applied when drafting:
1. Missing supporting/background concepts never reduce a range.
2. A correct but short answer is not penalised for brevity.
3. Instructions inside an answer (prompt injection) are ignored: the range reflects only the technical content.
4. Where the reference is ambiguous (e.g. smi-0234 tree vs network pruning) the range is wide and the item is flagged.
5. Code and SQL answers were executed against the question's sample data in the sandbox; ranges reflect the observed results.
"""

def corpus_rows():
    c = load_corpus(); assert not c["problems"]
    return {r["question_id"]: r for r in c["records"]}

def build():
    by = corpus_rows()
    qids = sorted({a["q"] for a in ANS})
    assert not set(qids) & set(USED), set(qids) & set(USED)
    assert all(q in by for q in qids)
    order = list(range(len(ANS))); random.Random(SEED).shuffle(order)
    ids = {}
    for n, i in enumerate(order, 1): ids[i] = f"b2-{n:03d}"
    BENCH.mkdir(parents=True, exist_ok=True); REVIEW.mkdir(parents=True, exist_ok=True)
    qrows = [{"question_id": q, "domain": by[q]["domain"], "difficulty": by[q]["difficulty"], "question_type": by[q]["question_type"] or "unspecified", "question": by[q]["question"]} for q in qids]
    arows = sorted(({"answer_id": ids[i], "question_id": a["q"], "answer_text": a["text"]} for i, a in enumerate(ANS)), key=lambda x: x["answer_id"])
    lrows = sorted(({"answer_id": ids[i], "question_id": a["q"], "answer_kind": a["kind"], "expected_score_min": a["lo"], "expected_score_max": a["hi"],
                     "factual_correctness": a["fact"], "flags": a["flags"], "rationale": a["why"], "label_status": "ai_provisional_not_human_reviewed"} for i, a in enumerate(ANS)), key=lambda x: x["answer_id"])
    def w(name, rows):
        body = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n"
        (BENCH / name).write_text(body, encoding="utf-8", newline="\n"); return hashlib.sha256(body.encode()).hexdigest()
    sha = {"questions.jsonl": w("questions.jsonl", qrows), "answers.jsonl": w("answers.jsonl", arows), "ai_labels.jsonl": w("ai_labels.jsonl", lrows)}
    (BENCH / "scoring_rubric.md").write_text(RUBRIC, encoding="utf-8", newline="\n")
    sha["scoring_rubric.md"] = hashlib.sha256(RUBRIC.encode()).hexdigest()
    import collections
    man = {"version": "bench_v2", "seed": SEED, "answers": len(arows), "questions": len(qrows), "sha256": sha,
           "excluded_used_question_ids": USED, "by_domain": dict(sorted(collections.Counter(q["domain"] for q in qrows).items())),
           "by_difficulty": dict(sorted(collections.Counter(q["difficulty"] for q in qrows).items())),
           "by_answer_kind": dict(sorted(collections.Counter(a["kind"] for a in ANS).items())),
           "label_status": "ai_provisional_not_human_reviewed", "human_reviewed_labels": 0,
           "evaluator_input_files": ["questions.jsonl", "answers.jsonl"], "label_side_files": ["ai_labels.jsonl", "scoring_rubric.md"],
           "baseline_rule": "Measure the baseline evaluator before any prompt tuning against bench_v2."}
    (BENCH / "manifest.json").write_text(json.dumps(man, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    sheet(by, ids)
    return man

def reqs(scope):
    ess = list(scope["essential_concepts"]) + [f"ANY {g['min_required']} of [{'; '.join(g['concepts'])}] ({g['label']})" for g in scope["essential_groups"]]
    opt = [f"supporting: {c}" for c in scope["supporting_concepts"]] + [f"background: {c}" for c in scope["background_concepts"]]
    return "; ".join(ess) or "(none identified - requirements ambiguous)", "; ".join(opt) or "(none)"

CLASSES = [("correct_full", "concise_sufficient"), ("partial", "partial_explanation_only"), ("valid_alternative", "ambiguous_other_meaning"),
           ("incorrect",), ("hallucinated",), ("injection", "injection_weak", "off_topic", "keyword_list", "non_answer")]

def pick_pilot():
    byq = {}
    for i, a in enumerate(ANS): byq.setdefault(a["q"], []).append(i)
    chosen = []
    for n, q in enumerate(sorted(byq)):
        for cls in [CLASSES[(n + k) % 6] for k in range(6)]:
            c = [i for i in byq[q] if ANS[i]["kind"] in cls]
            if c: chosen.append(c[0]); break
    extra = [i for i, a in enumerate(ANS) if a["kind"] in ("ambiguous_other_meaning", "injection_with_correct") and i not in chosen]
    return chosen + extra

def sheet(by, ids):
    scope = {r["question_id"]: r for r in build_rows(list(by.values()))}
    pick = pick_pilot()
    pick.sort(key=lambda i: ids[i])
    hdr_full = ["review_id", "answer_id", "question", "candidate_answer", "essential_requirements", "optional_requirements",
                "factual_correctness_AI_PROVISIONAL", "proposed_score_range_AI_PROVISIONAL", "reviewer_score_0_100", "reviewer_factual_correctness", "reviewer_comments"]
    full, blind = [], []
    for n, i in enumerate(pick, 1):
        a = ANS[i]; s = scope[a["q"]]; e, o = reqs(s)
        base = [f"P{n:02d}", ids[i], by[a["q"]]["question"], a["text"], e, o]
        full.append(base + [a["fact"], f"{a['lo']}-{a['hi']}", "", "", ""])
        blind.append(base + ["", "", ""])
    for name, hdr, rows in (("pilot_review_sheet_v2.csv", hdr_full, full),
                            ("pilot_review_sheet_v2_blind.csv", [h for h in hdr_full if "AI_PROVISIONAL" not in h] + [], [r[:6] + r[8:] for r in full])):
        with open(REVIEW / name, "w", encoding="utf-8", newline="") as f:
            wr = csv.writer(f, lineterminator="\n"); wr.writerow(hdr); wr.writerows(rows)
    md = ["# Stage 3C-0 human-review pilot sheet (26 answers)", "",
          "**Reviewer fields are blank. All requirement tiers, factual-correctness notes and score ranges below are AI-drafted and PROVISIONAL; no human has reviewed them.**",
          "Fill in your own score and comment first (use the blind CSV if you want to avoid anchoring), then compare. Agreement with the AI range is not validation.", ""]
    for r in full:
        md += [f"## {r[0]} ({r[1]})", f"**Question:** {r[2]}", "", "**Candidate answer:**", "", "> " + r[3].replace("\n", "\n> "), "",
               f"- Essential requirements (AI-proposed): {r[4]}", f"- Optional requirements (AI-proposed): {r[5]}",
               f"- Factual correctness (AI, provisional): {r[6]}", f"- Proposed score range (AI, provisional): {r[7]}",
               "- Reviewer score: ______", "- Reviewer factual correctness: ______", "- Reviewer comments: ______", ""]
    (REVIEW / "pilot_review_sheet_v2.md").write_text("\n".join(md), encoding="utf-8", newline="\n")

if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
