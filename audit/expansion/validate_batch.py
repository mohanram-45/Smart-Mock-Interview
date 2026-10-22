#!/usr/bin/env python3
"""Validate a staged expansion batch. Usage: python audit/expansion/validate_batch.py data/expansion/batch_NN [out.json]
Stdlib+pandas; scikit-learn optional (duplicate scans are skipped, and reported as skipped, without it)."""
import sys, json, re, hashlib, subprocess, tempfile, os, itertools, platform
from pathlib import Path
from collections import Counter
import pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
B = (ROOT / sys.argv[1]).resolve() if not Path(sys.argv[1]).is_absolute() else Path(sys.argv[1])
res = []
def rec(s, n, d=""): res.append((s, n, d)); print(("PASS " if s == "PASS" else s + " ") + n + ("" if s == "PASS" else " :: " + d))
def check(c, n, d=""): rec("PASS" if c else "FAIL", n, "" if c else d)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
d = pd.read_csv(B / f"{B.name}_accepted.csv", keep_default_na=False, dtype=str); man = json.loads((B / "manifest.json").read_text(encoding="utf-8"))
v5 = pd.read_csv(ROOT / "data/curated/v5/curated_questions.csv", keep_default_na=False, dtype=str)
# prior = v5 plus every lower-numbered staged batch (duplicate checks run against all of them)
_pr = [v5[["id", "question", "answer"]]]
for _p in sorted((ROOT / "data/expansion").glob("batch_*")):
    if _p.name < B.name and (_p / f"{_p.name}_accepted.csv").exists(): _pr.append(pd.read_csv(_p / f"{_p.name}_accepted.csv", keep_default_na=False, dtype=str)[["id", "question", "answer"]])
prior = pd.concat(_pr, ignore_index=True); PRIOR_BATCHES = [_p.name for _p in sorted((ROOT / "data/expansion").glob("batch_*")) if _p.name < B.name and (_p / f"{_p.name}_accepted.csv").exists()]
tests = json.loads((B / "code_tests.json").read_text(encoding="utf-8"))
words = lambda s: len(re.findall(r"\S+", s))
# schema
v5cols = list(v5.columns); NEW = ["concise_answer", "detailed_answer", "practical_answer", "answer_set", "rubric_points", "related_domains", "tags", "time_sensitive", "review_by", "v6_verification"]
check(list(d.columns) == v5cols + NEW, "schema: v5 columns in order, new columns appended")
check(len(d) == man["record_count"] and d.id.is_unique and d.id.str.match(r"^smi-[a-z]\d{4}$").all(), "ids unique, pattern smi-<letter>NNNN, count equals manifest")
check(not set(d.id) & set(v5.id), "no id collides with v1-v5")
TYPES = {"concept", "scenario", "debugging", "coding", "design", "evaluation", "business_case", "sql_exercise"}
check(d.question_type.isin(TYPES).all() and d.difficulty.isin(["Easy", "Medium", "Hard"]).all(), "enums: question_type, difficulty")
check((d.domain.nunique() >= 1) and d.groupby("topic").domain.nunique().max() == 1, "one domain per topic")
for c in ["domain", "topic", "question", "answer", "key_concepts", "common_mistakes", "interview_style_note", "verification", "plan_id", "answer_set", "v6_verification"]:
    check((d[c].str.strip() != "").all(), f"no empty {c}")
check(d.answer_set.isin(["single", "concise+detailed", "detailed+practical", "concise+detailed+practical"]).all(), "answer_set enum")
# answer sets
bad = []
for r in d.itertuples():
    s = r.answer_set; has = {"concise": r.concise_answer != "", "detailed": r.detailed_answer != "", "practical": r.practical_answer != ""}
    want = {"single": (0, 0, 0), "concise+detailed": (1, 1, 0), "detailed+practical": (0, 1, 1), "concise+detailed+practical": (1, 1, 1)}[s]
    if tuple(int(has[k]) for k in ("concise", "detailed", "practical")) != want: bad.append((r.id, "fields"))
    if s != "single" and r.answer != r.detailed_answer: bad.append((r.id, "answer!=detailed"))
    if has["concise"] and words(r.concise_answer) > 80: bad.append((r.id, "concise>80"))
    if has["detailed"] and not 120 <= words(r.detailed_answer) <= 450: bad.append((r.id, "detailed words"))
    if s == "single" and not 80 <= words(r.answer) <= 450: bad.append((r.id, "single words"))
check(not bad, "answer-set rules: fields match set, answer==detailed for multi-field, concise<=80, detailed 120-450, single 80-450", str(bad))
kc = d.key_concepts.map(lambda s: [x for x in s.split("; ") if x])
check(kc.map(lambda l: 3 <= len(l) <= 8 and len({x.lower() for x in l}) == len(l)).all(), "key_concepts 3-8 and distinct")
mist = d.common_mistakes.map(json.loads); check(mist.map(lambda l: 1 <= len(l) <= 3).all(), "common_mistakes 1-3")
design = d[d.question_type == "design"]; check(all(json.loads(x) for x in design.rubric_points if x) and (design.rubric_points != "").all(), "design questions carry rubric_points")
labels = {"ai_generated+ai_reviewed", "ai_generated+ai_reviewed+code_executed", "ai_generated+ai_reviewed+source_opened", "ai_generated+ai_reviewed+code_executed+source_opened"}
check(d.verification.isin(labels).all() and not d.verification.str.contains("human").any() and not d.v6_verification.str.contains("human_reviewed").any(), "verification labels from vocabulary; no human-verification claim")
check(((d.has_code_test == "yes") == d.id.isin(list(tests))).all() and d.verification.str.contains("code_executed").eq(d.has_code_test == "yes").all(), "has_code_test / code_executed label / code_tests.json agree")
ok_src = True
for r in d.itertuples():
    s = json.loads(r.sources)
    for x in s: ok_src &= bool(x["url"].startswith("https://") and x["title"] and x["supports"] and x["status"] in ("lead_opened_supported", "lead_opened_partially", "independent_reviewer_supported", "independent_reviewer_partially", "opened_by_author_agent_only"))
    ok_src &= (("source_opened" in r.verification) == bool(s))
check(ok_src, "sources: valid fields/status; source_opened label iff the record cites a source")
check(not d.question.str.contains(r"real interview|asked (at|by|in)\b.*(Google|Amazon|Meta|Microsoft)", case=False, regex=True).any() and not d.interview_style_note.str.contains("real interview", case=False).any(), "no claim of a real interview")
# prices/limits in time-sensitive guard (conceptual only)
check(not d.answer.str.contains(r"\$\s?\d|USD|per month", regex=True).any(), "no prices in answers")
# duplicates & templates
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
check(d.question.map(norm).is_unique and not (set(d.question.map(norm)) & set(prior.question.map(norm))), "0 exact duplicate questions (batch, v5 and earlier batches)")
check(d.answer.map(norm).is_unique and not (set(d.answer.map(norm)) & set(prior.answer.map(norm))), "0 exact duplicate answers (batch, v5 and earlier batches)")
op = d.question.map(lambda s: " ".join(re.findall(r"[a-z']+", s.lower())[:4])); mo = op.value_counts().max()
check(mo <= 3, "no 4-word opener more than 3 times", str(op.value_counts().head(3).to_dict()))
DEF = re.compile(r"^(what is|what are|what does|define|explain|describe|difference between|what's|how does|how do)\b", re.I)
share = d.question.map(lambda s: bool(DEF.match(s.strip()))).mean(); check(share <= .35, f"definitional openers {share:.0%} <= 35%")
def sh(s, n=5): w = re.findall(r"[a-z0-9']+", s.lower()); return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}
S = [sh(a) for a in d.answer]; jm = 0
for i, j in itertools.combinations(range(len(S)), 2):
    if S[i] and S[j]: jm = max(jm, len(S[i] & S[j]) / len(S[i] | S[j]))
V = [sh(a) for a in prior.answer]; jv = max((len(a & b) / len(a | b) for a in S for b in V if a and b), default=0)
check(jm < .25 and jv < .25, f"template check: max 5-gram Jaccard of answers within batch {jm:.2f}, vs prior {jv:.2f} (< .25)")
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    allq = pd.concat([d.question, prior.question]).tolist(); T = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit(allq)
    Qb, Qv = T.transform(d.question), T.transform(prior.question); Sx = cosine_similarity(Qb, Qv); Sw = cosine_similarity(Qb); np.fill_diagonal(Sw, 0)
    ch = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit(allq); Sc = cosine_similarity(ch.transform(d.question), ch.transform(prior.question))
    Ta = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit(pd.concat([d.answer, prior.answer])); SA = cosine_similarity(Ta.transform(d.answer), Ta.transform(prior.answer)); SAw = cosine_similarity(Ta.transform(d.answer)); np.fill_diagonal(SAw, 0)
    check(max(Sx.max(), Sw.max(), Sc.max()) < .85, f"no near-duplicate questions >= 0.85 (max word {max(Sx.max(), Sw.max()):.2f}, char {Sc.max():.2f})")
    check(max(SA.max(), SAw.max()) < .90, f"no near-duplicate answers >= 0.90 (max {max(SA.max(), SAw.max()):.2f})")
    nn = np.maximum(Sx.max(1), Sw.max(1)); rec("INFO", "similarity", f"median nearest-neighbour cosine {np.median(nn):.2f}; pairs in 0.70-0.85: {int(((Sx >= .7) & (Sx < .85)).sum() + ((np.triu(Sw) >= .7) & (np.triu(Sw) < .85)).sum())}; max to prior {Sx.max():.2f}")
    check(np.median(nn) <= .50, "median nearest-neighbour similarity <= 0.50")
except ImportError:
    rec("SKIP", "semantic duplicate scan (needs scikit-learn)", "skipped in this environment; exact-duplicate and 5-gram checks above still ran")
# code execution
def run_py(sol, test):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.py"; p.write_text(sol.rstrip() + "\n\n" + test.rstrip() + "\n", encoding="utf-8")
        try: r = subprocess.run([sys.executable, "-I", str(p)], capture_output=True, text=True, timeout=120, cwd=td); return r.returncode == 0, r.stderr[-300:]
        except subprocess.TimeoutExpired: return False, "timeout"
fails = []; imps = set()
for i, c in tests.items():
    ok, err = run_py(c["solution"], c["test"]); 
    if not ok: fails.append((i, err))
    imps |= set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z0-9_]+)", c["solution"] + "\n" + c["test"], re.M))
check(not fails, f"{len(tests)} code tests executed on Python {platform.python_version()}", str(fails))
allowed = {"numpy", "math", "collections", "fractions", "itertools", "random", "re", "heapq", "functools", "statistics", "typing", "dataclasses", "bisect", "json", "warnings", "operator", "string", "decimal", "sqlite3", "hashlib", "hmac", "tempfile", "os"}
check(imps <= allowed, "code imports only stdlib + numpy", str(imps - allowed))
check(not any(re.search(r"\bmatch\s+\w+:|except\*|tomllib|ExceptionGroup|time\.(time|perf_counter)|urllib|import requests|requests\.(get|post)", c["solution"] + c["test"]) for c in tests.values()), "no 3.11+ features, wall-clock timing or network in recorded code")
CFG = json.loads((B / "configs.json").read_text(encoding="utf-8")) if (B / "configs.json").exists() else {}
fence = []
for r in d.itertuples():
    if r.id in tests:
        fs = []
        for f in (r.answer, r.detailed_answer, r.practical_answer): fs += re.findall(r"```(?:python)?\n(.*?)```", f, re.S)
        sqlf = [x.strip() for f in (r.answer, r.detailed_answer, r.practical_answer) for x in re.findall(r"```sql\n(.*?)```", f, re.S)]
        cfg_sql = [c["content"].strip() for c in CFG.get(r.id, []) if c["lang"] == "sql"]
        if not (any(x.strip() == tests[r.id]["solution"].strip() for x in fs) or (sqlf and all(x in cfg_sql and re.sub(r"\s+", " ", x) in re.sub(r"\s+", " ", tests[r.id]["solution"]) for x in sqlf))): fence.append(r.id)
    elif any(l not in ("yaml", "yml", "dockerfile", "bash", "sh", "text") for l in re.findall(r"```(\w*)\n.*?```", r.answer + r.detailed_answer + r.practical_answer, re.S)) and r.id not in tests: fence.append(r.id + ":untested fence")  # yaml/dockerfile/shell config snippets are not executed (reported in the batch report)
check(not fence, "every fenced code block equals a tested solution; fenced code only where tested", str(fence))
# fingerprint & regression
FP = ["id", "domain", "topic", "difficulty", "question_type", "question", "answer", "key_concepts", "common_mistakes"]
fa = hashlib.sha256(json.dumps([[str(r[f]) for f in FP] for r in sorted(d.to_dict("records"), key=lambda r: r["id"])], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
fb = hashlib.sha256(json.dumps(tests, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(); fc = hashlib.sha256((fa + fb).encode()).hexdigest()
f = man["fingerprint"]; check((f["content_sha256"], f["code_tests_sha256"], f["combined_sha256"]) == (fa, fb, fc), "fingerprint recomputed from files equals manifest", fc)
rec("INFO", "fingerprint (combined sha256)", fc)
check({p: sha(B / p) for p in man["files"]} == man["files"], "manifest file hashes match")
check(man.get("configs_sha256") is None or hashlib.sha256(json.dumps(CFG, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == man["configs_sha256"], "configs.json hash equals manifest (when present)")
check(man["predecessor_manifest_sha256"] == {v: sha(ROOT / f"data/curated/{v}/manifest.json") for v in ("v1", "v2", "v3", "v4", "v5")}, "regression: v1-v5 manifests unchanged")
v5m = json.loads((ROOT / "data/curated/v5/manifest.json").read_text())["fingerprint"]["combined_sha256"]
check(v5m == "9eb94d8fe8bc83486dd401c5651878ebef0c4d0bd2c359d6e58fe12ba4637123" and sha(ROOT / "data/curated/v5/curated_questions.csv") == json.loads((ROOT / "data/curated/v5/manifest.json").read_text())["files"]["curated_questions.csv"], "regression: v5 fingerprint and dataset file unchanged")
orig = json.loads((ROOT / "audit/remediation/original_files_sha256.json").read_text())["files"]
check(all(sha(ROOT / k) == v for k, v in orig.items() if (ROOT / k).exists()), f"regression: original files unchanged ({sum((ROOT / k).exists() for k in orig)} present)")
q = pd.read_csv(B / "quarantine.csv"); check(len(q) == man["quarantined"], "quarantine.csv count equals manifest")
rec("INFO", "counts", json.dumps({k: man[k] for k in ("record_count", "quarantined", "difficulty_counts", "question_type_counts", "answer_set_counts", "records_with_code_test", "records_with_lead_opened_source", "records_with_any_source", "records_with_fully_supporting_source", "distinct_source_urls", "unverified_claim_count")}))
out = sys.argv[2] if len(sys.argv) > 2 else None
sm = Counter(s for s, _, _ in res); print(dict(sm))
if out: Path(out).write_text(json.dumps({"python": platform.python_version(), "summary": dict(sm), "checks": res}, indent=1), encoding="utf-8")
sys.exit(1 if sm["FAIL"] else 0)
