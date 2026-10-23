#!/usr/bin/env python3
"""Updated gap analysis for curated v4. Reuses the Stage 1A concept checklist (audit/triage/gap_concepts.py, read-only).
Writes data/curated/v4/gap_analysis_v4.md. Usage: python audit/remediation/make_gap_analysis_v4.py [project_root]"""
import sys, warnings
warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parents[1]
sys.path.insert(0, str(ROOT / "audit/triage"))
from gap_concepts import C, REF
rd = lambda p: pd.read_csv(ROOT / p, keep_default_na=False, dtype=str)
v1, v2c, v3c, b2 = rd("data/curated/v1/curated_questions.csv"), rd("data/curated/v2/curated_questions.csv"), rd("data/curated/v4/curated_questions.csv"), rd("data/curated/v4/pilot_batch_03.csv")
v3b = pd.concat([v3c, b2], ignore_index=True)
qt = lambda d: d.question.str.lower()
qk = lambda d: (d.question + " " + d.key_concepts.str.replace(";", " ")).str.lower()
status = lambda n: "**gap**" if n <= 1 else ("thin" if n <= 3 else "")
lines = ["# Domain gap analysis - v4 (v4 core, plus batch 03 shown separately)", "",
 "Method (unchanged from Stages 1A/1B so counts are comparable): each domain has a checklist of core interview concepts, matched by keyword regex against the **question text**. "
 "A second column also matches the `key_concepts` field. A hit count is only a coverage indicator: a hit does not mean the answer is good, and 0 does not prove absence. 0-1 hits = gap, 2-3 = thin. "
 "Counts are per domain (the domain label each record carries). The checklist comes from standard curricula, not from this dataset; reference sources are suggestions only and their licences are unverified. "
 "Columns: 'v1' = 316 questions (Stage 1A); 'v2 core' = 360 (Stage 1B core); 'v4 core' = 447 (v2 core + audited pilot 01 + re-verified batch 02); '+batch 03' = v4 core plus the 40 batch-03 questions, which are NOT merged and await review.", ""]
summary = []
for dom, concepts in C.items():
    a1, a2, a3, a4 = [d[d.domain == dom] for d in (v1, v2c, v3c, v3b)]
    rows = []; g = [0, 0, 0, 0]
    for name, rx in concepts:
        n = [int(qt(a).str.contains(rx, regex=True).sum()) for a in (a1, a2, a3, a4)]
        k4 = int(qk(a4).str.contains(rx, regex=True).sum())
        for i in range(4): g[i] += n[i] <= 1
        rows.append((name, *n, k4, status(n[3]), status(k4)))
    summary.append((dom, len(a1), len(a2), len(a3), len(a4), len(concepts), *g, sum(1 for r in rows if r[6] == "**gap**")))
    lines += [f"## {dom}  (v1 {len(a1)} / v2 core {len(a2)} / v4 core {len(a3)} / +batch 03 {len(a4)} questions)", "",
              "| Concept | v1 | v2 core | v4 core | +batch 03 | +batch 03 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |", "|---|---:|---:|---:|---:|---:|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |" for r in rows]
    still = [r[0] for r in rows if r[6] == "**gap**"]; thin = [r[0] for r in rows if r[6] == "thin"]
    lines += ["", f"**Still a gap after batch 03 (question-text match, {len(still)}):** " + ("; ".join(still) if still else "none"),
              "", f"**Thin (2-3 questions, {len(thin)}):** " + ("; ".join(thin) if thin else "none"), "",
              "**Reference sources (licences unverified):** " + "; ".join(REF[dom]), ""]
lines += ["## Summary", "", "| Domain | Q v1 | Q v2 core | Q v4 core | Q +batch 03 | Concepts checked | Gaps v1 | Gaps v2 core | Gaps v4 core | Gaps +batch 03 | Gaps +batch 03 (incl. key_concepts) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
lines += ["| " + " | ".join(str(x) for x in s) + " |" for s in summary]
lines += ["", "Notes", "",
 "* The key_concepts-inclusive column is optimistic (a key concept shares keywords with many checklist items); treat the question-text column as the conservative measure.",
 "* Keyword matching on question text undercounts breadth: one scenario question (e.g. a production-debugging case) exercises several checklist concepts its wording does not name.",
 "* A concept can show as covered while represented only by older one-line definitions; Stage 1B rewrote the 121 shortest/most imprecise answers, not every concept's depth.",
 "* Statistics / A-B testing live under Data Analysis; MLE, likelihood, Bayes, bias-variance remain under Machine Learning.",
 "* This document identifies gaps and next-batch targets only; it contains no new question text."]
out = ROOT / "data/curated/v4/gap_analysis_v4.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8"); print("wrote", out)
for s in summary: print(s)
