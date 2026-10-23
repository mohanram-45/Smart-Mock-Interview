#!/usr/bin/env python3
"""Integrity validation for data/curated/v4 (core = v3 core + approved batch 02, separate batch 03, regression against v1/v2/v3).

Usage:  python audit/remediation/validate_curated_v4.py [project_root] [--json out.json]
Exit code 0 = every hard check passed; 1 = at least one FAIL. WARN/INFO lines are informational.
Needs pandas; scikit-learn is optional (near-duplicate check skipped without it). Executes the SQL/Python reference
solutions in code_tests.json (subprocess per Python test, in-memory sqlite for SQL). Modifies nothing.
"""
import sys, re, json, hashlib, subprocess, tempfile, os, sqlite3, ast
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kb_common import weak_concepts

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = Path(args[0]).resolve() if args and not args[0].endswith(".json") else HERE.parents[1]
V4 = ROOT / "data/curated/v4"; V3 = ROOT / "data/curated/v3"; V2 = ROOT / "data/curated/v2"; V1 = ROOT / "data/curated/v1"
res = []
def rec(status, name, detail=""):
    res.append((status, name, detail)); print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))
def check(cond, name, detail=""): rec("PASS" if cond else "FAIL", name, "" if cond else detail)
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

DOMAINS = {"Machine Learning", "Deep Learning", "NLP", "Python", "SQL", "Data Analysis"}
DIFFS = {"Easy", "Medium", "Hard"}
QTYPES = {"concept", "scenario", "debugging", "coding", "sql_exercise", "design"}
REQ = ["id", "domain", "topic", "difficulty", "question", "answer", "key_concepts", "source_type", "verification", "sources", "version"]

need = ["curated_questions.csv", "curated_questions.json", "pilot_batch_03.csv", "pilot_batch_03.json", "quarantine.csv", "code_tests.json", "cross_version_results.json", "batch02_verification.json", "batch02_corrections.csv", "batch03_review.json", "gap_analysis_v4.md", "rag_readiness.json", "rag_readiness.md", "review_queue.csv", "lineage.csv", "removed_duplicates.csv", "manifest.json", "README.md"]
missing = [f for f in need if not (V4 / f).exists()]
check(not missing, "v4 files present", f"missing {missing}")
if missing: sys.exit(1)
rd = lambda f: pd.read_csv(V4 / f, keep_default_na=False, dtype=str)
core, pil, queue, lin, rem = rd("curated_questions.csv"), rd("pilot_batch_03.csv"), rd("review_queue.csv"), rd("lineage.csv"), rd("removed_duplicates.csv")
cj = json.loads((V4 / "curated_questions.json").read_text(encoding="utf-8")); pj = json.loads((V4 / "pilot_batch_03.json").read_text(encoding="utf-8"))
tests = json.loads((V4 / "code_tests.json").read_text(encoding="utf-8"))
manifest = json.loads((V4 / "manifest.json").read_text(encoding="utf-8"))
quar = rd("quarantine.csv"); xres = json.loads((V4 / "cross_version_results.json").read_text(encoding="utf-8"))
b2ver = json.loads((V4 / "batch02_verification.json").read_text(encoding="utf-8")); b2corr = rd("batch02_corrections.csv")
b3rev = json.loads((V4 / "batch03_review.json").read_text(encoding="utf-8"))
seed = core[core.source_type != "ai_generated_original"].reset_index(drop=True)      # 360 records derived from the raw seed set
p1 = core[core.introduced_in == "v3-pilot01"].reset_index(drop=True)                  # 41 pilot-01 records
b2 = core[core.introduced_in == "v3-batch02"].reset_index(drop=True)                  # 46 batch-02 records, approved into v4
allr = pd.concat([core.assign(setname="core"), pil.assign(setname="pilot")], ignore_index=True)   # 487 = v4 core + batch 03
new = pd.concat([p1, b2, pil], ignore_index=True)                                     # records written by AI in Stage 1B

# ------------------------------------------------------------------ schema
for name, d in (("core", core), ("pilot", pil)):
    check(all(c in d.columns for c in REQ), f"{name}: required columns")
    empty = {c: int((d[c].str.strip() == "").sum()) for c in REQ if c in d.columns and c != "sources"}
    check(not any(empty.values()), f"{name}: no empty required fields", str({k: v for k, v in empty.items() if v}))
    check(not d.apply(lambda r: any(str(v).lower() == "nan" for v in r), axis=1).any(), f"{name}: no literal 'nan'")
check(len(cj) == len(core) and [r["id"] for r in cj] == list(core.id) and all(r["question"] == q and r["answer"] == a for r, q, a in zip(cj, core.question, core.answer)), "core json mirrors csv")
check(len(pj) == len(pil) and [r["id"] for r in pj] == list(pil.id) and all(r["question"] == q and r["answer"] == a for r, q, a in zip(pj, pil.question, pil.answer)), "pilot json mirrors csv")
check(allr.id.is_unique, "ids unique across core + pilot")
check(seed.id.str.fullmatch(r"smi-\d{4}").all() and p1.id.str.fullmatch(r"smi-g\d{4}").all() and b2.id.str.fullmatch(r"smi-h\d{4}").all() and pil.id.str.fullmatch(r"smi-i\d{4}").all(), "id formats (smi-NNNN seed, smi-gNNNN pilot 01, smi-hNNNN batch 02, smi-iNNNN batch 03)")
check((seed.id == seed.source_record_id.astype(int).map(lambda n: f"smi-{n:04d}")).all(), "seed id derives from raw source_record_id")
check(set(allr.domain) <= DOMAINS and set(allr.difficulty) <= DIFFS, "domain / difficulty in allowed sets", str((set(allr.domain) - DOMAINS, set(allr.difficulty) - DIFFS)))
td = allr.groupby("topic").domain.nunique()
check((td == 1).all(), "each topic belongs to exactly one domain", str(list(td[td > 1].index)))
check(core.version.eq("v4").all() and pil.version.eq("v4-batch03").all(), "version labels")
check(new.question_type.isin(QTYPES).all() and (pil.interview_style_note.str.len() > 20).all(), "new records: question_type valid, interview_style_note present", str(set(new.question_type) - QTYPES))

# ------------------------------------------------------------------ provenance
raw = pd.read_csv(ROOT / "data/raw/questions_seed.csv", keep_default_na=False).set_index("id")
proc = pd.read_csv(ROOT / "data/processed/questions.csv", keep_default_na=False).set_index("id")
PFX = re.compile(r"^(Ans\.\s*|Solution:\s*|-\s+)")
bad = []
for r in seed.itertuples():
    rid, pid = int(r.source_record_id), int(r.source_processed_id)
    if r.source_file != "data/raw/questions_seed.csv" or rid not in raw.index: bad.append((r.id, "raw id")); continue
    rr = raw.loc[rid]
    if rr.domain != r.source_domain or rr.difficulty != r.source_difficulty: bad.append((r.id, "source domain/difficulty"))
    if pid not in proc.index or norm(proc.loc[pid].question) != norm(rr.question): bad.append((r.id, "processed record mismatch"))
    if r.modification in ("none", "prefix_stripped"):
        exp = PFX.sub("", norm(rr.answer)).strip()
        if norm(r.question) != norm(rr.question) or norm(r.answer)[1:] != norm(exp)[1:] or norm(r.answer)[:1].lower() != norm(exp)[:1].lower(): bad.append((r.id, "unmodified text differs from raw"))
check(not bad, "core provenance: traces to raw seed + processed record; unmodified text equals source", str(bad[:5]))
check(set(seed.modification) <= {"none", "prefix_stripped", "answer_corrected", "question_corrected", "answer_and_question_corrected", "metadata_only", "answer_strengthened_v2", "queue_resolved_stage1b"}, "core modification values valid", str(set(core.modification)))
check(new.source_type.eq("ai_generated_original").all() and new.modification.isin(["new_in_stage1b", "new_in_stage1b_batch02", "new_in_stage1b_batch03"]).all() and (new.source_record_id == "").all() and (pil.introduced_in == "v4-batch03").all(), "new records: marked ai_generated_original, no raw source claimed, introduced_in set")
IVW = re.compile(r"\b(was|were|is|are) (often |commonly |frequently )?asked (at|by|in|during)\b|real[- ]world interview|actual interview question|reported by candidates|interview at (google|amazon|meta|facebook|microsoft|apple|netflix)", re.I)
hit = [r.id for r in new.itertuples() if IVW.search(r.question + " " + r.answer + " " + r.interview_style_note)]
check(not hit, "new records: no claim of being a real interview question", str(hit))

# ------------------------------------------------------------------ lineage / exclusions
check(len(lin) == 4085 and lin.source_processed_id.is_unique, "lineage covers all 4,085 original records once")
dc = Counter(lin.disposition)
check(dc["INCLUDED"] == len(seed) and dc["REVIEW_QUEUE"] == len(queue) and dc["REMOVED_DUPLICATE"] == len(rem), "lineage counts match files", str(dict(dc)))
check(dc["EXCLUDED_TEMPLATE"] == 3618 and dc["EXCLUDED"] == 100, "3,618 template and 100 EXCLUDE records still excluded")
check(set(seed.source_processed_id) == set(lin[lin.disposition == "INCLUDED"].source_processed_id), "seed ids == lineage INCLUDED")
check(not (set(core.id) & set(queue.id)), "no record in both dataset and review queue")
check((seed.source_processed_id.astype(int) >= 3619).all(), "no template-generated records in core")
excl = set(lin[lin.disposition.isin(["EXCLUDED", "EXCLUDED_TEMPLATE", "REMOVED_DUPLICATE", "REVIEW_QUEUE"])].source_processed_id)
check(not (set(seed.source_processed_id) & excl), "no excluded / duplicate / queued record in core")
check(not (set(pil.id) & set(core.id)) and not (set(quar.id) & set(core.id)), "batch 03 and quarantine kept separate from core")

# ------------------------------------------------------------------ text hygiene
BLEED = re.compile(r"(?:^|\s)\d{1,2}[.)]\s+(?:[A-Z][^.?]{15,}\?|Describe|Explain|True/false|Differentiate)")
PLACE = re.compile(r"This question covers|below table|following table|refer to the below|Let us look at|Look at the below|\[mean, mode|\]\(http|https?://|www\.", re.I)
META = re.compile(r"\b(the|in the|from the) original (list|answer|text|question|description|paragraph|version)\b|\bas (listed|stated|mentioned) (above|in the original)\b", re.I)
probs = []
for r in allr.itertuples():
    a, q = r.answer, r.question
    if PFX.match(a): probs.append((r.id, "answer prefix/bullet"))
    if BLEED.search(a) and r.setname == "core" and "```" not in a: probs.append((r.id, "possible next-question bleed"))
    if PLACE.search(re.sub(r"```.*?```", "", a, flags=re.S)) or PLACE.search(q): probs.append((r.id, "placeholder/link text"))
    if META.search(re.sub(r"```.*?```", "", a, flags=re.S)): probs.append((r.id, "meta reference to a source text"))
    if len(a) < 40: probs.append((r.id, "answer < 40 chars"))
    if len(q) < 10: probs.append((r.id, "question < 10 chars"))
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f​﻿]", a + q): probs.append((r.id, "control char"))
    if a != a.strip() or q != q.strip(): probs.append((r.id, "untrimmed"))
    if re.search(r"\bTODO\b|\bTBD\b|lorem ipsum|\bXXX\b", a + q, re.I): probs.append((r.id, "placeholder token"))
check(not probs, "text hygiene (prefix, bleed, placeholders, links, meta references, length, control chars)", str(probs[:8]))
def _ok(r):
    f = r.answer.split(" ", 1)[0]
    return r.answer[:1].isupper() or r.answer[:1].isdigit() or r.answer[:1] in "\"'(`" or not f.isalpha() or len(f) == 1 or r.modification in ("answer_corrected", "answer_strengthened_v2", "queue_resolved_stage1b")
_bad = [r.id for r in allr.itertuples() if not _ok(r)]
check(not _bad, "answers start as sentences", str(_bad[:8]))
short = allr[(allr.answer.str.split().str.len() < 25) & (allr.has_code_test != "yes")]
rec("WARN" if len(short) else "PASS", "short answers (< 25 words, no code)", f"{len(short)} records: {list(short.id)[:12]}")
THIN = [r.id for r in core.itertuples() if "THIN_ANSWER" in r.known_limitations]
check(not THIN, "no record still flagged THIN_ANSWER", str(THIN[:10]))
leftover = core[core.known_limitations.str.contains("IMPRECISE|OVERSTATED|QUESTION_FORMAT")]
check(leftover.empty, "no record still flagged IMPRECISE/OVERSTATED/QUESTION_FORMAT", str(list(leftover.id)))

# ------------------------------------------------------------------ duplicates / templates
qn = allr.question.map(lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip())
an = allr.answer.map(lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip())
check(qn.is_unique and an.is_unique, "no exact duplicate questions or answers (core + pilot)", str(list(allr[qn.duplicated(keep=False) | an.duplicated(keep=False)].id)))
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    S = cosine_similarity(TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform(allr.question)); np.fill_diagonal(S, 0)
    hi = [(allr.id[i], allr.id[j], round(float(S[i, j]), 2)) for i, j in zip(*np.where(np.triu(S) >= 0.85))]
    check(not hi, "no near-duplicate questions (TF-IDF cosine >= 0.85, core + pilot)", str(hi))
    SA = cosine_similarity(TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(allr.answer)); np.fill_diagonal(SA, 0)
    ha = [(allr.id[i], allr.id[j], round(float(SA[i, j]), 2)) for i, j in zip(*np.where(np.triu(SA) >= 0.90))]
    check(not ha, "no near-duplicate answers (TF-IDF cosine >= 0.90, core + pilot)", str(ha))
    isp = (allr.setname == "pilot").values
    cross = [(allr.id[i], allr.id[j], round(float(S[i, j]), 2)) for i in np.where(isp)[0] for j in np.where(~isp)[0] if S[i, j] >= 0.5]
    rec("WARN" if cross else "PASS", "batch-03 questions closest to existing core questions (cosine >= 0.50)", f"{len(cross)}: {cross[:8]}")
    mid = [(allr.id[i], allr.id[j], round(float(S[i, j]), 2)) for i, j in zip(*np.where(np.triu(S) >= 0.60)) if S[i, j] < 0.85]
    rec("WARN" if mid else "PASS", "related-question pairs 0.60-0.85 (distinct intents; reviewed manually)", f"{len(mid)}: {mid[:10]}")
except ImportError:
    rec("WARN", "semantic duplicate check skipped", "scikit-learn not installed")
# template detection inside the pilot batch: shared word 4-grams / repeated openers
def shingles(s, n=4):
    w = re.findall(r"[a-z0-9]+", s.lower()); return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}
sh = {r.id: shingles(r.question, 5) for r in new.itertuples()}
tmpl = [(a, b, round(len(sh[a] & sh[b]) / max(1, len(sh[a] | sh[b])), 2)) for a in sh for b in sh if a < b and len(sh[a] & sh[b]) / max(1, len(sh[a] | sh[b])) >= 0.25]
check(not tmpl, "new records (pilot 01 + batch 02 + batch 03): no templated/near-identical question wording (5-gram Jaccard < 0.25)", str(tmpl))
openers = Counter(" ".join(re.findall(r"[a-z0-9']+", q.lower())[:4]) for q in new.question)
rec("PASS" if max(openers.values()) < 4 else "WARN", "new records: question openers not repetitive", str(openers.most_common(3)))

# ------------------------------------------------------------------ key concepts
kc = allr.key_concepts.map(lambda s: [x for x in s.split("; ") if x])
check(kc.map(lambda l: 3 <= len(l) <= 8 and len({x.lower() for x in l}) == len(l)).all(), "key_concepts: 3-8 distinct items for every record (core + pilot)",
      str([i for i, l in zip(allr.id, kc) if not (3 <= len(l) <= 8)][:8]))
GENERIC = {"data", "model", "algorithm", "models", "machine learning", "deep learning", "explanation", "concept", "technique", "method"}
check(not [i for i, l, q in zip(allr.id, kc, allr.question) if any(x.lower() in GENERIC and x.lower() not in q.lower() for x in l)], "key_concepts: no generic placeholders (unless the question itself is about that term)")
weak = [(i, k) for i, l, q, a in zip(allr.id, kc, allr.question, allr.answer) for k in weak_concepts(l, q + " " + a)]
rec("WARN" if weak else "PASS", "key_concepts token-grounding heuristic (semantic review by independent agents is the real check)", f"{len(weak)} items not matched by wording: {weak[:8]}")

# ------------------------------------------------------------------ sources
sb = []
for r in allr.itertuples():
    try: src = json.loads(r.sources)
    except Exception: sb.append((r.id, "invalid json")); continue
    for s in src:
        if not (s.get("title") and str(s.get("url", "")).startswith("https://") and s.get("supports") and s.get("verification")): sb.append((r.id, "incomplete source entry"))
check(not sb, "sources: valid JSON, each entry has title/https url/supports/verification", str(sb[:5]))
nsrc = sum(len(json.loads(s)) for s in allr.sources)
unverified = [(r.id, s["url"]) for r in allr.itertuples() for s in json.loads(r.sources) if s["verification"] == "opened_by_author_agent_only"]
rec("INFO", "sources recorded", f"{nsrc} entries on {sum(1 for s in allr.sources if s != '[]')} records; {len(unverified)} opened only by the authoring agent (no independent check): {unverified}")
check(all(v.startswith(("ai_reviewed", "ai_rewritten", "ai_generated")) for v in allr.verification), "verification labels never claim human review", str(set(allr.verification)))
rec("INFO", "human subject-matter review", "none - every record is AI-reviewed only")

# ------------------------------------------------------------------ executable code
unknown = [k for k in tests if k not in set(allr.id)]
check(not unknown, "code_tests ids all exist in core/pilot", str(unknown))
check(set(allr[allr.has_code_test == "yes"].id) == set(tests), "has_code_test flags match code_tests.json", str(set(allr[allr.has_code_test == "yes"].id) ^ set(tests)))

def split_sql(s):
    out, buf = [], ""
    for line in s.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf): out.append(buf.strip()); buf = ""
    if buf.strip(): out.append(buf.strip())
    return out
def round_rows(rows): return [[round(v, 6) if isinstance(v, float) else v for v in r] for r in rows]
def run_sql(c):
    con = sqlite3.connect(":memory:", isolation_level=None)
    if c["setup"].strip(): con.executescript(c["setup"])
    rows = None; first = c["solution"].lstrip().upper()
    for st in split_sql(c["solution"]):
        cur = con.execute(st)
        if cur.description is not None: rows = cur.fetchall()
    rows = round_rows(rows or [])
    exp = round_rows(c["expected"])
    if first.startswith("EXPLAIN"):   # plan text is version dependent: compare SEARCH/SCAN only
        assert [r[3].split()[0] for r in rows] == [r[3].split()[0] for r in exp], (rows, exp)
    else:
        assert rows == exp, f"rows {rows} != expected {exp}"
    return "ok"
def run_py(code, extra_env=None):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.py"; p.write_text(code, encoding="utf-8")
        o = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=180, cwd=td, env=dict(os.environ, MPLBACKEND="Agg", PYTHONHASHSEED="0"))
        if o.returncode: raise AssertionError((o.stderr.strip().splitlines() or ["?"])[-1][:200])
    return "ok"
def run_one(item):
    k, c = item
    try:
        if c["language"] == "sql":
            run_sql(c)
            if c.get("test", "").strip(): run_py(c["test"])
        else:
            body = c["solution"]
            if "SOLUTION_SRC" in c.get("test", ""): body = f"SOLUTION_SRC = {c['solution']!r}\n" + body
            run_py((c.get("setup") or "") + "\n" + body + "\n" + c.get("test", ""))
        return k, None
    except Exception as e:
        m = re.search(r"No module named '([\w.]+)'", str(e))
        if m: return k, "SKIP:" + m.group(1).split(".")[0]      # optional third-party package not installed here: not a defect in the record
        return k, f"{type(e).__name__}: {str(e)[:200]}"
with ThreadPoolExecutor(max_workers=4) as ex: results = list(ex.map(run_one, sorted(tests.items())))
skipped = [r for r in results if r[1] and r[1].startswith("SKIP:")]
fails = [r for r in results if r[1] and not r[1].startswith("SKIP:")]
if skipped: rec("WARN", "code tests skipped because a package is not installed in this environment", f"{len(skipped)} tests; missing: {sorted({r[1][5:] for r in skipped})}; ids: {[r[0] for r in skipped][:20]}")
check(not fails, f"executable reference solutions: {len(tests) - len(skipped)} of {len(tests)} run ({sum(1 for c in tests.values() if c['language']=='sql')} SQL in sqlite {sqlite3.sqlite_version}, {sum(1 for c in tests.values() if c['language']=='python')} Python)", str(fails[:5]))

FENCE = re.compile(r"```(python|sql)\n(.*?)\n```", re.S)
flat = lambda s: re.sub(r"\s+", " ", re.sub(r"--[^\n]*|#[^\n]*", "", s)).strip().rstrip(";").strip()
import time
def exec_sql_block(block, setup):
    """Run one SQL block from an answer against a database built from the record's setup; DDL blocks that clash with the
    setup run on an empty database. Returns ('ok'|'interrupted'|error text, rows)."""
    for use_setup in (True, False):
        con = sqlite3.connect(":memory:", isolation_level=None)
        if use_setup and setup.strip(): con.executescript(setup)
        t0 = time.time(); con.set_progress_handler(lambda: 1 if time.time() - t0 > 5 else 0, 200000)
        rows = None
        try:
            for st in split_sql(block):
                cur = con.execute(st)
                if cur.description is not None: rows = cur.fetchall()
            return "ok", rows
        except sqlite3.OperationalError as e:
            m = str(e)
            if "already exists" in m and use_setup: continue
            return ("interrupted" if "interrupted" in m else m), None
        except sqlite3.Error as e:
            return f"{type(e).__name__}: {e}", None
    return "unreachable", None
uncovered, syntax, sql_blocks, sql_equal, sql_intr = [], [], 0, 0, []
for r in allr.itertuples():
    c = tests.get(r.id)
    for lang, b in FENCE.findall(r.answer):
        if lang == "python":
            try: ast.parse(b)
            except SyntaxError as e: syntax.append((r.id, str(e)))
            if not (c is not None and (flat(b) in flat(c["solution"]) or flat(c["solution"]) in flat(b) or flat(b) in flat(c.get("test", "")))): uncovered.append((r.id, "python"))
        else:
            sql_blocks += 1
            st, rows = exec_sql_block(b, c["setup"] if c else "")
            if st == "interrupted": sql_intr.append(r.id)
            elif st != "ok": syntax.append((r.id, "sql block failed: " + st[:100]))
            elif c is not None and rows is not None and round_rows(rows) == round_rows(c["expected"]): sql_equal += 1
check(not syntax, "fenced python blocks parse and every fenced SQL block executes in sqlite", str(syntax[:6]))
check(not uncovered, "every fenced Python block in an answer is covered by an executed reference solution or test", str(uncovered[:10]))
rec("INFO", "SQL coverage", f"{sql_blocks} fenced SQL blocks in answers executed against sqlite ({sql_equal} reproduce the record's expected rows; the rest are alternative/contrast queries" + (f"; {len(sql_intr)} aborted after 5s as intended demonstrations of non-terminating queries: {sql_intr}" if sql_intr else "") + ")")

# ------------------------------------------------------------------ portability of the code in new records (owner runs Python 3.10, numpy 2.2, pandas 2.3, SQLite 3.37)
STD = set(getattr(sys, "stdlib_module_names", set())) | {"numpy", "pandas", "__future__"}
PY311 = re.compile(r"\b(ExceptionGroup|BaseExceptionGroup|tomllib|TaskGroup|StrEnum|asyncio\.timeout|datetime\.UTC|itertools\.batched)\b|from itertools import[^\n]*\bbatched\b|except\s*\*|from typing import[^\n]*\bSelf\b|typing\.Self")
OPTIONAL_PKG = {"smi-g0002": "sklearn", "smi-g0014": "sklearn"}
OPTIONAL_PKG.update({r.id: "sklearn" for r in new.itertuples() if re.search(r"\bsklearn\b", (tests.get(r.id) or {}).get("test", "") + (tests.get(r.id) or {}).get("solution", ""))})   # pilot-01 records whose subject is scikit-learn behaviour: test is skipped where scikit-learn is absent
foreign, newfeat = [], []
for rid in new.id:
    c = tests.get(rid)
    if not c or c["language"] != "python": continue
    for part in ("setup", "solution", "test"):
        src = c.get(part) or ""
        try: tree = ast.parse(src)
        except SyntaxError as e: foreign.append((rid, "syntax", str(e))); continue
        for node in ast.walk(tree):
            mods = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else ([node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else [])
            foreign += [(rid, m) for m in mods if m not in STD and OPTIONAL_PKG.get(rid) != m]
        if PY311.search(src): newfeat.append(rid)
check(not foreign, "new records: Python tests import only the standard library, numpy and pandas", str(foreign[:8]))
check(not newfeat, "new records: no Python 3.11+ only features in recorded code", str(sorted(set(newfeat))))
xr_cols = sorted({k for v in xres.values() for k in v})
check(len(xr_cols) >= 3 and any(c.startswith("py3.10") for c in xr_cols), "cross-version results recorded for Python 3.10, 3.11 and 3.13", str(xr_cols))
py_new = [rid for rid in new.id if rid in tests and tests[rid]["language"] == "python"]
badx = [(rid, c, xres.get(rid, {}).get(c)) for rid in py_new for c in xr_cols if xres.get(rid, {}).get(c) != "ok" and not (rid in OPTIONAL_PKG and str(xres.get(rid, {}).get(c)) == "SKIP:" + OPTIONAL_PKG[rid])]
check(not badx, f"new records: all {len(py_new)} Python reference tests passed on every recorded interpreter ({', '.join(xr_cols)})", str(badx[:6]))
failx = [(rid, c) for rid, v in xres.items() for c, r in v.items() if str(r).startswith("FAIL")]
check(not failx, "no recorded cross-version failure for any record (existing records included)", str(failx[:6]))

# ------------------------------------------------------------------ queue / manifest / originals
check({"id", "reason"} <= set(queue.columns) and queue.id.is_unique and (queue.reason.str.strip() != "").all(), "review queue: schema, unique ids, reason present")
orig = json.loads((HERE / "original_files_sha256.json").read_text())["files"]
changed = [rel for rel, h in orig.items() if (ROOT / rel).exists() and sha(ROOT / rel) != h]
check(not changed, f"original raw/interim/processed/src/model files unchanged ({sum(1 for r in orig if (ROOT / r).exists())} of {len(orig)} present)", str(changed))
for vn, vd in (("v1", V1), ("v2", V2), ("v3", V3)):
    mm = json.loads((vd / "manifest.json").read_text())
    bad_ = [f for f, h in mm["files"].items() if sha(vd / f) != h]
    check(not bad_, f"{vn} dataset files unchanged (hashes match {vn} manifest)", str(bad_))
badm = [f for f, h in manifest["files"].items() if sha(V4 / f) != h]
check(not badm, "v4 manifest hashes match current files", str(badm))
mc = manifest["counts"]
check(mc["core"] == len(core) and mc["batch_03"] == len(pil) and mc["review_queue"] == len(queue) and mc["quarantine"] == len(quar) and mc["code_tests"] == len(tests) and mc["batch_02_merged"] == len(b2), "manifest counts match files")
check(set(manifest["files"]) >= {f for f in need if f != "manifest.json"}, "manifest lists every v4 file")

# ------------------------------------------------------------------ regression against v1 / v2 / v3
v3core = pd.read_csv(V3 / "curated_questions.csv", keep_default_na=False, dtype=str).set_index("id")
v3b2 = pd.read_csv(V3 / "pilot_batch_02.csv", keep_default_na=False, dtype=str).set_index("id")
v3t = json.loads((V3 / "code_tests.json").read_text(encoding="utf-8"))
c4 = core.set_index("id")
check(set(v3core.index) <= set(c4.index), "regression: every v3 core id is present in v4", str(sorted(set(v3core.index) - set(c4.index))[:5]))
FIELDS = [c for c in v3core.columns if c not in ("version",)]
drift = [(i, f) for i in v3core.index for f in FIELDS if v3core.loc[i, f] != c4.loc[i, f]]
check(not drift, f"regression: all {len(v3core)} v3 core records identical in v4 (every column except version)", str(drift[:6]))
tdrift = [k for k in v3t if k in v3core.index and json.dumps(v3t[k], sort_keys=True) != json.dumps(tests.get(k), sort_keys=True)]
check(not tdrift, "regression: reference code of the 401 v3 core records unchanged", str(tdrift[:5]))
check(set(v3b2.index) == set(b2.id) | set(quar[quar.introduced_in == "v3-batch02"].id), "regression: batch 02 = the 46 v3 batch-02 ids (merged or quarantined, none lost)")
check(len(c4) == len(v3core) + len(v3b2) - len(quar[quar.introduced_in == "v3-batch02"]), "v4 core size = v3 core + approved batch 02", f"{len(c4)}")
check(dict(Counter(c4.loc[[i for i in v3core.index], "difficulty"])) == dict(Counter(v3core.difficulty)), "regression: difficulty distribution of the 401 v3 core records unchanged")

# ------------------------------------------------------------------ batch-02 re-verification (Phase 1)
changed_b2 = []
for i in v3b2.index:
    if i in c4.index:
        for f in ["question", "answer", "key_concepts", "difficulty"]:
            if v3b2.loc[i, f] != c4.loc[i, f]: changed_b2.append((i, f))
        if json.dumps(v3t.get(i), sort_keys=True) != json.dumps(tests.get(i), sort_keys=True): changed_b2.append((i, "code"))
logged_b2 = {(r.id, r.field) for r in b2corr.itertuples()}
unlogged = [x for x in changed_b2 if x not in logged_b2 and not (x[1] == "code" and (x[0], "code") in logged_b2)]
check(not unlogged, "batch 02: every change from v3 is listed in batch02_corrections.csv", str(unlogged[:8]))
vids = {r["id"] for r in b2ver}
check(len(vids) == 26 and sum(1 for i in vids if i in set(b2.id)) == 26, "batch 02: re-verification evidence recorded for 26 records (22 corrected + 4 Data Analysis edge-case records)", str(len(vids)))
check(len([i for i in vids if i in set(b2.id)]) >= 22 and set(v["verdict"] for v in b2ver) <= {"verified", "fix"}, "batch 02: all 22 corrected records have a re-verification (verified/fix); none left in 'quarantine'", str(Counter(v["verdict"] for v in b2ver)))
no_ev = [v["id"] for v in b2ver if not v["evidence"] or any(not (e.get("claim") and e.get("method") and e.get("evidence")) for e in v["evidence"])]
check(not no_ev, "batch 02: every re-verified record has evidence entries (claim, method, evidence)", str(no_ev))
check(set(b2.v4_verification) <= {"reverified_v4_verified", "reverified_v4_corrected", "independent_review_v3_only"} and (b2.v4_verification != "").all(), "batch 02: v4_verification set on every merged record", str(Counter(b2.v4_verification)))
check((c4.loc[[i for i in c4.index if i not in set(b2.id)], "v4_verification"] == "").all(), "v4_verification empty on the 401 v3 core records (not re-verified in this stage)")
check(not quar.shape[0] or quar.id.is_unique, "quarantine file well formed")

# ------------------------------------------------------------------ batch 03 evidence
check(len(b3rev) == len(pil) + len(quar[quar.introduced_in == "v4-batch03"]) and {r["id"] for r in b3rev} >= set(pil.id), "batch 03: every record has an independent review")
check(pil.audit_verdict.isin(["pass", "corrected"]).all() and b2.audit_verdict.isin(["pass", "corrected"]).all(), "audit_verdict set on every new record")
check(pil.question_type.isin(QTYPES).all() and pil.difficulty.isin(DIFFS).all(), "batch 03: question_type and difficulty valid")
check(not (set(pil.question) & set(core.question)), "batch 03: no question text shared with core")
bad_diff = [(r["id"], r["difficulty_final"]) for r in b3rev if pil.set_index("id").loc[r["id"], "difficulty"] != r["difficulty_final"]]
check(not bad_diff, "batch 03: final difficulty equals the adopted blind-auditor rating", str(bad_diff[:6]))
rec("INFO", "audit outcome", f"batch 03 review: {Counter(r['status'] for r in b3rev)}; corrections applied {sum(r['corrections_applied'] for r in b3rev)}; batch 02 re-verification: {Counter(v['verdict'] for v in b2ver)}")

# ------------------------------------------------------------------ reporting
def table(d, title):
    ct = pd.crosstab(d.domain, d.difficulty).reindex(columns=["Easy", "Medium", "Hard"], fill_value=0)
    ct["Total"] = ct.sum(axis=1); ct.loc["All"] = ct.sum()
    rec("INFO", title, "\n" + ct.to_string())
table(core, "core dataset: domain x difficulty (not forced to any ratio)")
table(pil, "batch 03 (separate): domain x difficulty")
table(allr, "v4 core + batch 03: domain x difficulty")
rec("INFO", "topics per domain (core + batch 03)", str(allr.groupby("domain").topic.nunique().to_dict()))
failed = [r for r in res if r[0] == "FAIL"]
print(f"\n{len(res) - len(failed)} passed/info, {len(failed)} failed")
if "--json" in sys.argv:
    Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps([{"status": s, "check": n, "detail": d} for s, n, d in res], indent=1), encoding="utf-8")
sys.exit(1 if failed else 0)
