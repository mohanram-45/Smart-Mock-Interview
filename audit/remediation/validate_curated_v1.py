#!/usr/bin/env python3
"""Integrity validation for data/curated/v1 (Stage 1 remediation).

Usage:  python audit/remediation/validate_curated_v1.py [project_root] [--json out.json]
Exit code 0 = all hard checks passed, 1 = at least one failed. WARN items are informational.
Requires pandas; scikit-learn is optional (semantic-duplicate check is skipped without it).
Nothing is modified; code snippets run in subprocesses with a timeout.
"""
import sys, re, json, hashlib, subprocess, tempfile, os, sqlite3, ast
from pathlib import Path
from collections import Counter
import pandas as pd

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = Path(args[0]).resolve() if args and not args[0].endswith(".json") else Path(__file__).resolve().parents[2]
V1 = ROOT / "data" / "curated" / "v1"
res = []            # (status, name, detail)
def rec(status, name, detail=""):
    res.append((status, name, detail)); print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))
def check(cond, name, detail=""): rec("PASS" if cond else "FAIL", name, "" if cond else detail)
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

DOMAINS = {"Machine Learning", "Deep Learning", "NLP", "Python", "SQL", "Data Analysis"}
DIFFS = {"Easy", "Medium", "Hard"}
REQ = ["id","domain","topic","difficulty","question","answer","key_concepts","source_file","source_record_id","source_processed_id",
       "source_domain","source_difficulty","triage_status","modification","verification","version"]

# ---------------------------------------------------------------- files
need = ["curated_questions.csv","curated_questions.json","review_queue.csv","lineage.csv","removed_duplicates.csv","code_checks.json","manifest.json"]
missing = [f for f in need if not (V1 / f).exists()]
check(not missing, "v1 files present", f"missing {missing}")
if missing:
    sys.exit(1)
cur = pd.read_csv(V1/"curated_questions.csv", keep_default_na=False, dtype=str)
js = json.loads((V1/"curated_questions.json").read_text(encoding="utf-8"))
queue = pd.read_csv(V1/"review_queue.csv", keep_default_na=False, dtype=str)
lin = pd.read_csv(V1/"lineage.csv", keep_default_na=False, dtype=str)
rem = pd.read_csv(V1/"removed_duplicates.csv", keep_default_na=False, dtype=str)
checks = json.loads((V1/"code_checks.json").read_text(encoding="utf-8"))
manifest = json.loads((V1/"manifest.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- schema
check(all(c in cur.columns for c in REQ), "schema: required columns", f"missing {[c for c in REQ if c not in cur.columns]}")
empty = {c: int((cur[c].str.strip() == "").sum()) for c in ["id","domain","topic","difficulty","question","answer","key_concepts","source_file","source_record_id","source_processed_id"]}
check(not any(empty.values()), "schema: no empty required fields", str({k: v for k, v in empty.items() if v}))
check(not cur.apply(lambda r: any(str(v).lower() == "nan" for v in r), axis=1).any(), "schema: no literal 'nan' values")
check(len(js) == len(cur) and [r["id"] for r in js] == list(cur.id) and all(" ".join(r["key_concepts"]) .replace("; "," ") == " ".join(c.split("; ")) for r, c in zip(js, cur.key_concepts)),
      "json mirrors csv (ids, order, key_concepts)")
check(all(r["question"] == q and r["answer"] == a for r, q, a in zip(js, cur.question, cur.answer)), "json mirrors csv (question, answer text)")

# ---------------------------------------------------------------- ids / enums
check(cur.id.is_unique, "ids unique")
check(cur.id.str.fullmatch(r"smi-\d{4}").all(), "id format smi-NNNN")
check((cur.id == cur.source_record_id.astype(int).map(lambda n: f"smi-{n:04d}")).all(), "id derives from source_record_id (stable)")
check(set(cur.domain) <= DOMAINS, "domain in allowed set", str(set(cur.domain) - DOMAINS))
check(set(cur.difficulty) <= DIFFS, "difficulty only Easy/Medium/Hard", str(set(cur.difficulty) - DIFFS))
tdom = cur.groupby("topic").domain.nunique()
check((tdom == 1).all(), "each topic belongs to exactly one domain", str(list(tdom[tdom > 1].index)))
check(cur.version.eq("v1").all(), "version == v1")

# ---------------------------------------------------------------- provenance
raw = pd.read_csv(ROOT/"data/raw/questions_seed.csv", keep_default_na=False).set_index("id")
proc = pd.read_csv(ROOT/"data/processed/questions.csv", keep_default_na=False).set_index("id")
check(cur.source_file.eq("data/raw/questions_seed.csv").all() and (ROOT/"data/raw/questions_seed.csv").exists(), "provenance: source_file is the raw seed CSV")
bad = []
PFX = re.compile(r"^(Ans\.\s*|Solution:\s*|-\s+)")
for r in cur.itertuples():
    rid, pid = int(r.source_record_id), int(r.source_processed_id)
    if rid not in raw.index: bad.append((r.id, "raw id not found")); continue
    rr = raw.loc[rid]
    if rr.domain != r.source_domain or rr.difficulty != r.source_difficulty: bad.append((r.id, "source domain/difficulty differ from raw"))
    if pid not in proc.index or norm(proc.loc[pid].question) != norm(rr.question): bad.append((r.id, "processed record does not match raw question"))
    if r.modification in ("none", "prefix_stripped"):
        if norm(r.question) != norm(rr.question): bad.append((r.id, "question changed but modification says none"))
        exp = PFX.sub("", norm(rr.answer)).strip()
        if norm(r.answer)[1:] != norm(exp)[1:] or norm(r.answer)[:1].lower() != norm(exp)[:1].lower(): bad.append((r.id, "answer differs from raw but modification says none/prefix_stripped"))
check(not bad, "provenance: every record traces to raw seed + processed record; unmodified text equals source", str(bad[:5]))
check(set(cur.modification) <= {"none","prefix_stripped","answer_corrected","question_corrected","answer_and_question_corrected","metadata_only"}, "modification values valid")

# ---------------------------------------------------------------- lineage & exclusions
check(len(lin) == 4085 and lin.source_processed_id.is_unique, "lineage covers all 4,085 original records once")
dc = Counter(lin.disposition)
check(dc["INCLUDED"] == len(cur) and dc["REVIEW_QUEUE"] == len(queue) and dc["REMOVED_DUPLICATE"] == len(rem), "lineage counts match files", str(dict(dc)))
check(dc["EXCLUDED_TEMPLATE"] == 3618, "all 3,618 template records excluded", str(dc["EXCLUDED_TEMPLATE"]))
check(set(cur.source_processed_id) == set(lin[lin.disposition == "INCLUDED"].source_processed_id), "included ids == lineage INCLUDED")
check(not (set(cur.id) & set(queue.id)), "no record is in both dataset and review queue")
check(not cur.source_record_id.astype(str).str.contains("gen", case=False).any() and (cur.source_processed_id.astype(int) >= 3619).all(), "no generated/template records in dataset")
excl = set(lin[lin.disposition.isin(["EXCLUDED","EXCLUDED_TEMPLATE","REMOVED_DUPLICATE"])].source_processed_id)
check(not (set(cur.source_processed_id) & excl), "no EXCLUDE/duplicate record in dataset")
check(not (set(rem.removed_id) & set(cur.id)) and set(rem.kept_id) <= set(cur.id), "removed duplicates absent; their kept counterparts present")

# ---------------------------------------------------------------- text hygiene
BLEED = re.compile(r"(?:^|\s)\d{1,2}[.)]\s+(?:[A-Z][^.?]{15,}\?|Describe|Explain|True/false|Differentiate)")
PLACE = re.compile(r"This question covers|below table|following table|refer to the below|Let us look at|Look at the below|\[mean, mode|\]\(http|https?://|www\.", re.I)
probs = []
for r in cur.itertuples():
    a, q = r.answer, r.question
    if PFX.match(a): probs.append((r.id, "answer prefix"))
    if BLEED.search(a): probs.append((r.id, "possible next-question bleed"))
    if PLACE.search(a) or PLACE.search(q): probs.append((r.id, "placeholder/link text"))
    if len(a) < 25: probs.append((r.id, "answer < 25 chars"))
    if len(q) < 10: probs.append((r.id, "question < 10 chars"))
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f​﻿]", a + q): probs.append((r.id, "control/zero-width char"))
    if a != a.strip() or q != q.strip(): probs.append((r.id, "untrimmed text"))
check(not probs, "text hygiene (prefix, bleed, placeholders, links, length, control chars)", str(probs[:8]))
# lowercase starts allowed only for notation/identifiers (p > n, k-means) and authored code-identifier answers
def _ok(r):
    a = r.answer; f = a.split(" ", 1)[0]
    return a[:1].isupper() or a[:1].isdigit() or a[:1] in "\"'(" or not f.isalpha() or len(f) == 1 or r.modification == "answer_corrected"
_bad = [r.id for r in cur.itertuples() if not _ok(r)]
check(not _bad, "answers start as sentences (no mid-sentence fragments)", str(_bad[:8]))
check(not cur.answer.str.match(r"^[-*\u2022]\s").any(), "no leading bullet markers in answers")

# ---------------------------------------------------------------- duplicates
qn = cur.question.map(lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip())
an = cur.answer.map(lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip())
check(qn.is_unique, "no exact duplicate questions", str(list(cur[qn.duplicated(keep=False)].id)))
check(an.is_unique, "no exact duplicate answers", str(list(cur[an.duplicated(keep=False)].id)))
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    S = cosine_similarity(TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform(cur.question)); np.fill_diagonal(S, 0)
    hi = [(cur.id[i], cur.id[j], round(float(S[i, j]), 2)) for i, j in zip(*np.where(np.triu(S) >= 0.85))]
    check(not hi, "no near-duplicate questions (TF-IDF cosine >= 0.85)", str(hi))
    SA = cosine_similarity(TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(cur.answer)); np.fill_diagonal(SA, 0)
    ha = [(cur.id[i], cur.id[j], round(float(SA[i, j]), 2)) for i, j in zip(*np.where(np.triu(SA) >= 0.90))]
    check(not ha, "no near-duplicate answers (TF-IDF cosine >= 0.90)", str(ha))
    warn = [(cur.id[i], cur.id[j], round(float(S[i, j]), 2)) for i, j in zip(*np.where(np.triu(S) >= 0.60)) if S[i, j] < 0.85]
    rec("WARN" if warn else "PASS", "related-question pairs 0.60-0.85 (reviewed manually; distinct intents)", f"{len(warn)} pairs: {warn[:12]}")
except ImportError:
    rec("WARN", "semantic duplicate check skipped", "scikit-learn not installed")

# ---------------------------------------------------------------- key concepts
kc = cur.key_concepts.map(lambda s: [x for x in s.split("; ") if x])
check(kc.map(lambda l: 2 <= len(l) <= 5 and len(set(map(str.lower, l))) == len(l)).all(), "key_concepts: 2-5 unique items each")
STOP = {"the","and","of","for","in","to","a","an","vs","with","on","data","model"}
ACR = {"rnn","nlp","knn","svm","ner","svd","cnn","gan","lstm","pca","roc","auc","sql","bert","tf","idf","mlm","cte","acid"}
weak = []
for r, l in zip(cur.itertuples(), kc):
    words = set(re.findall(r"[a-z0-9]+", (r.question + " " + r.answer).lower()))
    for k in l:
        ts = [t for t in re.findall(r"[a-z0-9]+", k.lower()) if t not in STOP]
        if not ts or all(t in ACR for t in ts): continue
        miss = [t for t in ts if not any(w.startswith(t[:5]) or (len(w) >= 4 and t.startswith(w[:5])) for w in words)]
        if miss and len(miss) >= max(1, len(ts) // 2 + (len(ts) % 2)): weak.append((r.id, k))
rec("WARN" if weak else "PASS", "key_concepts grounded in record text", f"{len(weak)} weakly grounded: {weak[:10]}")

# ---------------------------------------------------------------- executable code & SQL
FENCE = re.compile(r"```python\n(.*?)\n```", re.S)
flat = lambda s: re.sub(r"\s+", " ", s)
fails = []
n_blocks = 0
env = dict(os.environ, MPLBACKEND="Agg")
for r in cur.itertuples():
    blocks = FENCE.findall(r.answer)
    n_blocks += len(blocks)
    for b in blocks:
        try: ast.parse(b)
        except SyntaxError as e: fails.append((r.id, f"syntax error in answer snippet: {e}"))
    if blocks and r.id not in checks: fails.append((r.id, "python snippet without a code check"))
    if r.id in checks:
        code = checks[r.id]["code"]
        for b in blocks:
            if flat(b) not in flat(code): fails.append((r.id, "answer snippet is not part of the executed check"))
for cid, c in checks.items():
    if cid not in set(cur.id): fails.append((cid, "code check for an id not in dataset")); continue
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "snippet.py"; p.write_text(c["code"], encoding="utf-8")
        try:
            out = subprocess.run([sys.executable, "-c", f"import runpy;runpy.run_path(r'{p}', run_name='snippet')"], capture_output=True, text=True, timeout=60, env=env, cwd=td)
            if out.returncode: fails.append((cid, "check failed: " + (out.stderr.strip().splitlines() or ["?"])[-1][:140]))
        except subprocess.TimeoutExpired:
            fails.append((cid, "timeout"))
check(not fails, f"executable examples: {len(checks)} checks run ({n_blocks} fenced python blocks parsed)", str(fails[:6]))

SQL_STMT = re.compile(r"\b(SELECT\b[^;]{0,400}?\bFROM|INSERT INTO|UPDATE\s+\w+\s+SET|DELETE FROM|CREATE TABLE)\b[^;]*;?", re.S)
sql_found, sql_bad = 0, []
for r in cur.itertuples():
    for m in re.findall(r"```sql\n(.*?)\n```", r.answer, re.S) + [x.group(0) for x in SQL_STMT.finditer(r.answer)]:
        sql_found += 1
        try:
            c = sqlite3.connect(":memory:"); c.execute("EXPLAIN " + m.rstrip(";"))
        except sqlite3.OperationalError as e:
            if "syntax error" in str(e) or "incomplete input" in str(e): sql_bad.append((r.id, str(e)))
check(not sql_bad, f"SQL syntax ({sql_found} snippets found in answers; sqlite parser)", str(sql_bad[:5]))
if sql_found == 0:
    rec("INFO", "SQL syntax check not applicable", "no SQL statements appear in any approved answer (answers are prose definitions); nothing was invented to test")

# ---------------------------------------------------------------- review queue
QR = ["id","source_processed_id","review_state","reason","required_to_resolve","queue_origin"]
check(all(c in queue.columns for c in QR) and queue.id.is_unique and (queue.reason.str.strip() != "").all(), "review queue: schema, unique ids, reason present")
check(set(queue.review_state) <= {"needs_review","needs_code_test","needs_source"}, "review queue: valid review_state")

# ---------------------------------------------------------------- originals & version integrity
orig = json.loads((Path(__file__).resolve().parent / "original_files_sha256.json").read_text())["files"]
changed = []
for rel, h in orig.items():
    p = ROOT / rel
    if p.exists() and sha(p) != h: changed.append(rel)
absent = [rel for rel in orig if not (ROOT / rel).exists()]
check(not changed, f"original raw/interim/processed/src/model files unchanged ({len(orig) - len(absent)} of {len(orig)} present and compared)", str(changed))
if absent: rec("WARN", "baseline files not present in this checkout", str(absent[:6]))
bad_h = [f for f, h in manifest["files"].items() if sha(V1 / f) != h]
check(not bad_h, "v1 manifest hashes match current files", str(bad_h))
check(manifest["counts"]["included"] == len(cur) and manifest["counts"]["review_queue"] == len(queue), "manifest counts match files")

# ---------------------------------------------------------------- distribution (informational)
ct = pd.crosstab(cur.domain, cur.difficulty).reindex(columns=["Easy", "Medium", "Hard"], fill_value=0)
ct["Total"] = ct.sum(axis=1); ct.loc["All"] = ct.sum()
rec("INFO", "final distribution (not forced to any target ratio)", "\n" + ct.to_string())
shares = (ct.loc["All", ["Easy", "Medium", "Hard"]] / ct.loc["All", "Total"]).round(3).to_dict()
rec("INFO", "difficulty shares", str(shares))

failed = [r for r in res if r[0] == "FAIL"]
print(f"\n{len(res) - len(failed)} passed/info, {len(failed)} failed")
for a in sys.argv:
    if a == "--json":
        out = sys.argv[sys.argv.index("--json") + 1]
        Path(out).write_text(json.dumps([{"status": s, "check": n, "detail": d} for s, n, d in res], indent=1), encoding="utf-8")
sys.exit(1 if failed else 0)
