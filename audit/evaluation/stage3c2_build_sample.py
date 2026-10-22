"""Stage 3C-2: build the FROZEN evaluation sample and the blind human-review sheet (deterministic; re-running reproduces the same bytes).

Sample = 18 answers from the fresh Stage 3C benchmark (bench_v2) written for the scope-eligible questions + 2 fresh answers written for this stage
(one off-topic, one non-substantive; bench_v2 has no off-topic answer on an eligible question). Selection rule (fixed before any model run):
  quota per answer_kind, taking candidates ordered by (times that question was already picked, answer_id).
The bench_v2 answer_kind label is used ONLY to stratify the sample. All labels/expectations are AI-written and provisional; none is human-reviewed.
Outputs (data/evaluation/stage3c2/): sample.jsonl (evaluator inputs only), provisional_ai_expectations.jsonl (kept apart; never shown to a reviewer or the
evaluator), review/blind_review_sheet.{csv,md} (+ review_key.json mapping review ids back to sample ids; do not give the key to the reviewer).
"""
import csv, json, random, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.evaluation.modular import ScopeStore                      # noqa: E402
from src.evaluation.modular.requirements import build_requirements  # noqa: E402

BENCH = ROOT / "data" / "evaluation" / "bench_v2"
OUT = ROOT / "data" / "evaluation" / "stage3c2"
QUOTA = [("correct_full", 2), ("concise_sufficient", 3), ("valid_alternative", 3), ("partial", 3), ("incorrect", 2), ("hallucinated", 2),
         ("injection", 1), ("injection_weak", 1), ("injection_with_correct", 1)]
FRESH = [
    {"sample_id": "s2-f01", "question_id": "smi-0449", "kind": "off_topic", "answer_text": "I prefer Python because the syntax is readable and the community is large, and I enjoy using it for cleaning data before building charts."},
    {"sample_id": "s2-f02", "question_id": "smi-0118", "kind": "non_substantive", "answer_text": "It makes the network more powerful and better at learning, so the results turn out good in the end."},
]
FRESH_EXPECT = {"s2-f01": {"expected": "no essential concept stated; off-topic; low score if scoring were possible", "flags": ["off_topic"]},
                "s2-f02": {"expected": "vague; no essential concept demonstrated; low completeness", "flags": ["non_substantive"]}}


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    store = ScopeStore.load()
    elig = set(store.eligible_ids())
    qs = {q["question_id"]: q for q in jl(BENCH / "questions.jsonl")}
    labels = {l["answer_id"]: l for l in jl(BENCH / "ai_labels.jsonl")}
    answers = [a for a in jl(BENCH / "answers.jsonl") if a["question_id"] in elig]
    picked, per_q = [], Counter()
    for kind, n in QUOTA:
        cands = [a for a in answers if labels[a["answer_id"]]["answer_kind"] == kind and a["answer_id"] not in {p["answer_id"] for p in picked}]
        for _ in range(n):
            if not cands:
                raise SystemExit(f"not enough candidates for {kind}")
            cands.sort(key=lambda a: (per_q[a["question_id"]], a["answer_id"]))
            a = cands.pop(0); per_q[a["question_id"]] += 1; picked.append(a)
    sample, expect = [], []
    for a in sorted(picked, key=lambda a: a["answer_id"]):
        l = labels[a["answer_id"]]
        sample.append({"sample_id": a["answer_id"], "question_id": a["question_id"], "question": qs[a["question_id"]]["question"], "answer_text": a["answer_text"], "source": "bench_v2"})
        expect.append({"sample_id": a["answer_id"], "kind": l["answer_kind"], "expected_score_min": l["expected_score_min"], "expected_score_max": l["expected_score_max"],
                       "factual_correctness": l["factual_correctness"], "flags": l["flags"], "rationale": l["rationale"], "label_status": "ai_provisional_not_human_reviewed"})
    for f in FRESH:
        sample.append({"sample_id": f["sample_id"], "question_id": f["question_id"], "question": qs[f["question_id"]]["question"], "answer_text": f["answer_text"], "source": "stage3c2_fresh_ai_written"})
        expect.append({"sample_id": f["sample_id"], "kind": f["kind"], **FRESH_EXPECT[f["sample_id"]], "label_status": "ai_provisional_not_human_reviewed"})
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "review").mkdir(exist_ok=True)
    w = lambda p, rows: Path(p).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8", newline="\n")
    w(OUT / "sample.jsonl", sample); w(OUT / "provisional_ai_expectations.jsonl", expect)

    # blind review sheet: shuffled with a fixed seed, neutral ids, no kind / expectation / model output
    order = list(range(len(sample))); random.Random(3202).shuffle(order)
    rows, key = [], {}
    for n, i in enumerate(order, 1):
        s = sample[i]; rid = f"r{n:02d}"; key[rid] = s["sample_id"]
        rs = build_requirements(store.get(s["question_id"]), s["question"])
        reqs = []
        for r in rs.essentials():
            reqs.append(f"{r.id}: " + (f"at least {r.min_required} of [{'; '.join(r.members)}]" if r.is_group else r.label))
        rows.append({"review_id": rid, "interview_question": s["question"], "candidate_answer": s["answer_text"], "essential_requirements_ai_drafted": "\n".join(reqs),
                     "technical_correctness (correct / partly_correct / incorrect)": "", "completeness (complete / partial / minimal)": "",
                     "requirement_judgements (per requirement: stated_correctly / stated_incorrectly / not_stated)": "", "reviewer_score_0_100": "", "reviewer_comments": "", "reviewer_id": ""})
    cols = list(rows[0])
    with open(OUT / "review" / "blind_review_sheet.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); wr.writeheader(); wr.writerows(rows)
    md = ["# Stage 3C-2 blind review sheet", "",
          "Please judge each answer yourself. Do not look at any model output. The essential requirements below were drafted by an AI and are NOT human-verified: "
          "if you think a requirement is wrong or too coarse, say so in the comments. Fill the blank fields; leave nothing pre-filled.", "",
          "Scale hint (optional): technical_correctness = is what the candidate says right? completeness = does it cover what the question needs? reviewer_score_0_100 = your overall mark.", ""]
    for r in rows:
        md += [f"## {r['review_id']}", "", f"**Question:** {r['interview_question']}", "", "**Candidate answer:**", "", "```text", r["candidate_answer"], "```", "",
               "**Essential requirements (AI-drafted):**", ""] + [f"- {x}" for x in r["essential_requirements_ai_drafted"].split("\n")] + [
               "", "| Field | Your judgement |", "|---|---|", "| Technical correctness (correct / partly_correct / incorrect) | |", "| Completeness (complete / partial / minimal) | |",
               "| Per requirement (stated_correctly / stated_incorrectly / not_stated) | |", "| Reviewer score (0-100) | |", "| Comments | |", ""]
    (OUT / "review" / "blind_review_sheet.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    (OUT / "review" / "review_key.json").write_text(json.dumps(key, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(len(sample), "answers;", dict(Counter(e["kind"] for e in expect)), "| questions:", len({s["question_id"] for s in sample}))


if __name__ == "__main__":
    main()
