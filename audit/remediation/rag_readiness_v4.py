#!/usr/bin/env python3
"""RAG-readiness measurements for data/curated/v4 (core set). Measures only; the verdict is written by a human-readable report.
Writes data/curated/v4/rag_readiness.json and rag_readiness.md. Usage: python audit/remediation/rag_readiness_v4.py [project_root]
Needs pandas, numpy, scikit-learn (lexical retrieval baseline and semantic-duplicate scan)."""
import sys, re, json, math, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
from collections import Counter
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "audit/triage"))
from kb_common import weak_concepts
from gap_concepts import C as CHECK
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

V4 = ROOT / "data/curated/v4"
d = pd.read_csv(V4 / "curated_questions.csv", keep_default_na=False, dtype=str)
b3 = pd.read_csv(V4 / "pilot_batch_03.csv", keep_default_na=False, dtype=str)
R = {"records": len(d)}
words = lambda s: len(re.findall(r"\S+", s))
d["aw"] = d.answer.map(words); d["qw"] = d.question.map(words)
d["kc"] = d.key_concepts.map(lambda s: [x for x in s.split("; ") if x])

# 1. coverage
cov = {}
for dom, g in d.groupby("domain"):
    t = g.groupby("topic").size()
    concepts = CHECK[dom]
    hits = [int(g.question.str.lower().str.contains(rx, regex=True).sum()) for _, rx in concepts]
    cov[dom] = dict(records=len(g), topics=int(len(t)), topics_lt3=int((t < 3).sum()), min_topic=int(t.min()), max_topic=int(t.max()),
                    checklist=len(concepts), checklist_ge2=int(sum(h >= 2 for h in hits)), checklist_le1=int(sum(h <= 1 for h in hits)))
R["coverage"] = cov
R["topic_sizes"] = {dom: g.groupby("topic").size().sort_values().to_dict() for dom, g in d.groupby("domain")}

# 2. reference-answer completeness
comp = {}
for dom, g in d.groupby("domain"):
    comp[dom] = dict(median_words=int(g.aw.median()), p10=int(g.aw.quantile(.1)), p90=int(g.aw.quantile(.9)), lt30=int((g.aw < 30).sum()), lt50=int((g.aw < 50).sum()),
                     with_code_block=int(g.answer.str.contains("```").sum()), flagged_open_ended=int(g.known_limitations.str.contains("OPEN_ENDED").sum()),
                     flagged_time_sensitive=int(g.known_limitations.str.contains("TIME_SENSITIVE").sum()), flagged_unsourced_textbook=int(g.known_limitations.str.contains("TEXTBOOK").sum()))
R["completeness"] = comp
R["answers_unchanged_from_raw_seed_wording"] = int(d.modification.isin(["none", "prefix_stripped"]).sum())
R["short_answers_lt40_words_list"] = list(d[d.aw < 40].id)

# 3. retrieval metadata
meta = {}
for col in ["domain", "topic", "difficulty", "key_concepts", "source_type", "verification", "question_type", "plan_id", "sources"]:
    empty = d[col].map(lambda s: s.strip() in ("", "[]")).sum()
    meta[col] = dict(missing=int(empty), pct_present=round(100 * (1 - empty / len(d)), 1))
R["metadata_fields"] = meta
R["records_without_question_type"] = int((d.question_type == "").sum())
R["records_with_any_source"] = int((d.sources != "[]").sum())
R["records_with_executed_code"] = int((d.has_code_test == "yes").sum())
retr = (d.question + " " + d.answer + " " + d.key_concepts.str.replace(";", " "))
tok = retr.map(lambda s: int(len(s.split()) * 1.35))
R["chunk_size_tokens_est"] = dict(median=int(tok.median()), p90=int(tok.quantile(.9)), max=int(tok.max()), gt512=int((tok > 512).sum()), gt1024=int((tok > 1024).sum()))
R["difficulty"] = d.difficulty.value_counts().to_dict()
R["verification_labels"] = d.verification.value_counts().to_dict()

# 4. key-concept quality
kc_ok = d.kc.map(lambda l: 3 <= len(l) <= 8 and len({x.lower() for x in l}) == len(l))
weak = [(i, k) for i, l, q, a in zip(d.id, d.kc, d.question, d.answer) for k in weak_concepts(l, q + " " + a)]
allk = Counter(k.lower() for l in d.kc for k in l)
R["key_concepts"] = dict(all_in_3_8_distinct=bool(kc_ok.all()), total=int(sum(allk.values())), distinct=len(allk), singletons=int(sum(1 for v in allk.values() if v == 1)),
                         token_grounding_warnings=len(weak), pct_grounded=round(100 * (1 - len(weak) / sum(allk.values())), 1), most_common=allk.most_common(8))

# 5. duplication
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
R["exact_dup_questions"] = int(d.question.map(norm).duplicated().sum()); R["exact_dup_answers"] = int(d.answer.map(norm).duplicated().sum())
Q = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform(d.question); SQ = cosine_similarity(Q); np.fill_diagonal(SQ, 0)
A = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(d.answer); SA = cosine_similarity(A); np.fill_diagonal(SA, 0)
CH = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit_transform(d.question); SC = cosine_similarity(CH); np.fill_diagonal(SC, 0)
pairs = lambda S, th: [(d.id[i], d.id[j], round(float(S[i, j]), 2)) for i, j in zip(*np.where(np.triu(S) >= th))]
R["near_dup"] = dict(q_ge_085=pairs(SQ, .85), a_ge_090=pairs(SA, .90), q_char_ge_090=pairs(SC, .90), q_070_085=pairs(SQ, .70)[: 20], n_q_060_085=len([p for p in pairs(SQ, .60) if p[2] < .85]))
# new batch vs core
Bq = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit(pd.concat([d.question, b3.question]))
Sx = cosine_similarity(Bq.transform(b3.question), Bq.transform(d.question))
R["batch03_vs_core_max_cos_q"] = dict(max=round(float(Sx.max()), 2), pairs_ge_050=[(b3.id[i], d.id[j], round(float(Sx[i, j]), 2)) for i, j in zip(*np.where(Sx >= .5))])

# 6. question diversity
opener = d.question.map(lambda s: " ".join(re.findall(r"[a-z']+", s.lower())[:3]))
DEF = re.compile(r"^(what is|what are|what does|define|explain|describe|difference between|what's|how does|how do)\b", re.I)
R["diversity"] = dict(definitional_openers=int(d.question.map(lambda s: bool(DEF.match(s.strip()))).sum()), top_openers=opener.value_counts().head(8).to_dict(),
                      question_type_counts=d.question_type.replace("", "(seed record - not typed)").value_counts().to_dict(),
                      question_words_median=int(d.qw.median()), scenario_style=int(d.question.str.contains(r"\byou (are|have|run|inherit)|\bYour (team|model)|\bA (model|team|company|teammate)", regex=True).sum()))
tc = d.groupby(["domain", "topic"]).size(); p = tc / tc.sum()
R["diversity"]["topic_entropy_bits"] = round(float(-(p * np.log2(p)).sum()), 2); R["diversity"]["topics_total"] = int(len(tc))

# lexical retrieval baseline: can a record's own question retrieve its own answer record (top-1/top-5) among all records?
docs = (d.answer + " " + d.key_concepts.str.replace(";", " ")); V = TfidfVectorizer(stop_words="english", sublinear_tf=True, ngram_range=(1, 2)).fit(pd.concat([docs, d.question]))
S = cosine_similarity(V.transform(d.question), V.transform(docs)); rank = (S > S.diagonal()[:, None]).sum(axis=1)
d["rank"] = rank
R["self_retrieval_lexical_baseline"] = dict(top1=round(float((rank == 0).mean()), 3), top5=round(float((rank < 5).mean()), 3), mrr=round(float((1 / (rank + 1)).mean()), 3),
                                              by_domain={dom: round(float((g["rank"] < 5).mean()), 3) for dom, g in d.groupby("domain")}, worst=list(d.sort_values("rank", ascending=False).id.head(8)))

# 7. verification risks
R["verification_risk"] = dict(
    human_reviewed=0,
    independent_ai_review_batches=int(((d.introduced_in == "v3-pilot01") | (d.introduced_in == "v3-batch02")).sum()),
    seed_records_unchanged_from_v1=int(((d.introduced_in == "v1") & ~d.modification.isin(["answer_strengthened_v2"])).sum()),
    seed_records_rewritten_stage1b=int(d.modification.isin(["answer_strengthened_v2", "queue_resolved_stage1b"]).sum()),
    records_reverified_v4=int(d.v4_verification.str.startswith("reverified").sum()),
    records_with_remaining_limitations=int((d.remaining_limitations != "").sum()),
    records_with_code_executed=int(d.verification.str.contains("code_executed").sum()),
    records_with_source_opened=int(d.verification.str.contains("source_opened").sum()),
    background_only_claims_noted=int(sum(1 for v in json.loads((V4 / "batch02_verification.json").read_text(encoding="utf-8")) for e in v["evidence"] if e.get("method") == "background_only")),
    batch02_claims_by_method=dict(Counter(e.get("method", "?") for v in json.loads((V4 / "batch02_verification.json").read_text(encoding="utf-8")) for e in v["evidence"])))

(V4 / "rag_readiness.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
L = ["# RAG-readiness measurements - v4 core", "", f"Records measured: {len(d)}. Measurements only; the verdict and its reasoning are in `reports/stage1b_final_report.md`.", "",
     "| Domain | Records | Topics | Topics < 3 records | Checklist concepts >= 2 questions | median answer words | answers < 30 words |", "|---|---:|---:|---:|---:|---:|---:|"]
for dom in cov: L.append(f"| {dom} | {cov[dom]['records']} | {cov[dom]['topics']} | {cov[dom]['topics_lt3']} | {cov[dom]['checklist_ge2']}/{cov[dom]['checklist']} | {comp[dom]['median_words']} | {comp[dom]['lt30']} |")
L += ["", f"* Metadata present: " + ", ".join(f"{k} {v['pct_present']}%" for k, v in meta.items()), f"* Estimated chunk size (question+answer+concepts): median {R['chunk_size_tokens_est']['median']} tokens, p90 {R['chunk_size_tokens_est']['p90']}, max {R['chunk_size_tokens_est']['max']}",
      f"* Key concepts: {R['key_concepts']['distinct']} distinct, {R['key_concepts']['pct_grounded']}% pass the token-grounding heuristic",
      f"* Duplicates: exact questions {R['exact_dup_questions']}, exact answers {R['exact_dup_answers']}; question pairs >= 0.85: {len(R['near_dup']['q_ge_085'])}; answer pairs >= 0.90: {len(R['near_dup']['a_ge_090'])}",
      f"* Lexical self-retrieval baseline (question -> own answer): top-1 {R['self_retrieval_lexical_baseline']['top1']}, top-5 {R['self_retrieval_lexical_baseline']['top5']}, MRR {R['self_retrieval_lexical_baseline']['mrr']}",
      f"* Verification: human-reviewed {R['verification_risk']['human_reviewed']}; code executed on {R['verification_risk']['records_with_code_executed']}; source opened on {R['verification_risk']['records_with_source_opened']}"]
(V4 / "rag_readiness.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("wrote rag_readiness")
