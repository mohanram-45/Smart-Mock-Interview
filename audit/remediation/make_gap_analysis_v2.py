#!/usr/bin/env python3
"""Updated gap analysis for curated v2. Reuses the Stage 1A concept checklist (audit/triage/gap_concepts.py, read-only).
Writes data/curated/v2/gap_analysis_v2.md. Usage: python audit/remediation/make_gap_analysis_v2.py [project_root]"""
import sys, re, warnings
warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parents[1]
sys.path.insert(0, str(ROOT / "audit/triage"))
from gap_concepts import C, REF
rd = lambda p: pd.read_csv(ROOT / p, keep_default_na=False, dtype=str)
v1, core, pil = rd("data/curated/v1/curated_questions.csv"), rd("data/curated/v2/curated_questions.csv"), rd("data/curated/v2/pilot_batch_01.csv")
allr = pd.concat([core, pil], ignore_index=True)
qt = lambda d: (d.question).str.lower()
qk = lambda d: (d.question + " " + d.key_concepts.str.replace(";", " ")).str.lower()
status = lambda n: "**gap**" if n <= 1 else ("thin" if n <= 3 else "")
lines = ["# Domain gap analysis - v2 (after Stage 1B)", "",
 "Method (unchanged from Stage 1A so counts are comparable): each domain has a checklist of core interview concepts, matched by keyword regex against the **question text**. "
 "A second column also matches the `key_concepts` field. A hit count is only a coverage indicator: a hit does not mean the answer is good, and 0 does not prove absence. 0-1 hits = gap, 2-3 = thin. "
 "Counts are per domain: records are matched within the domain label they carry. The concept checklist comes from standard curricula, not from this dataset; reference sources below are suggestions only and their licences are unverified. "
 "'v1' = the 316 questions of Stage 1A, 'v2 core' = 360 questions after Stage 1B, '+pilot' = core plus the 41 pilot questions (pending approval).", ""]
summary = []
for dom, concepts in C.items():
    a1, a2, a3 = [d[d.domain == dom] for d in (v1, core, allr)]
    rows = []; g_v1 = g_core = g_all = 0
    for name, rx in concepts:
        n1 = int(qt(a1).str.contains(rx, regex=True).sum()); n2 = int(qt(a2).str.contains(rx, regex=True).sum()); n3 = int(qt(a3).str.contains(rx, regex=True).sum())
        k3 = int(qk(a3).str.contains(rx, regex=True).sum())
        g_v1 += n1 <= 1; g_core += n2 <= 1; g_all += n3 <= 1
        rows.append((name, n1, n2, n3, k3, status(n3), status(k3)))
    summary.append((dom, len(a1), len(a2), len(a3), len(concepts), g_v1, g_core, g_all, sum(1 for r in rows if r[6] == "**gap**")))
    lines += [f"## {dom}  (v1 {len(a1)} / v2 core {len(a2)} / +pilot {len(a3)} questions)", "",
              "| Concept | v1 | v2 core | +pilot | +pilot incl. key_concepts | Status (question text) | Status (incl. key_concepts) |", "|---|---:|---:|---:|---:|---|---|"]
    lines += [f"| {n} | {a} | {b} | {c} | {k} | {s} | {s2} |" for n, a, b, c, k, s, s2 in rows]
    still = [r[0] for r in rows if r[5] == "**gap**"]
    lines += ["", f"**Still a gap after the pilot (question-text match, {len(still)}):** " + ("; ".join(still) if still else "none"), "",
              "**Reference sources (licences unverified):** " + "; ".join(REF[dom]), ""]
lines += ["## Summary", "", "| Domain | Questions v1 | v2 core | +pilot | Concepts checked | Gaps v1 | Gaps v2 core | Gaps +pilot | Gaps +pilot (incl. key_concepts) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
lines += [f"| {d} | {a} | {b} | {c} | {n} | {g1} | {g2} | {g3} | {g4} |" for d, a, b, c, n, g1, g2, g3, g4 in summary]
lines += ["", "Notes", "",
 "* The key_concepts-inclusive column is optimistic (a key concept shares keywords with many checklist items); treat the question-text column as the conservative measure.",
 "* Keyword matching on question text undercounts breadth: a single scenario question (e.g. a production-debugging case) exercises several checklist concepts that its wording does not name.",
 "* A concept can show as covered while only being represented by one-line definitions in the older records; the Stage 1B rewrites addressed the 121 shortest/most imprecise answers, not every concept's depth.",
 "* Statistics / A-B testing live under Data Analysis; MLE, likelihood, Bayes, bias-variance remain under Machine Learning.",
 "* This document identifies gaps and next-batch targets only; it contains no new question text."]
out = ROOT / "data/curated/v2/gap_analysis_v2.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8"); print("wrote", out)
for s in summary: print(s)
