"""Stage 2B final: leakage/design checks + error analysis on saved rankings (v2_pooled labels). Read-only."""
import json, re, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from src.retrieval.documents import build_documents, search_text
from src.retrieval.evaluate import load_eval_set
from src.retrieval.lexical import tokenize

C = load_corpus(); R = C["records"]; by = {r["question_id"]: r for r in R}
EV = ROOT / "data/retrieval/eval"; ev = load_eval_set(EV / "eval_set_v2.jsonl"); evq = {q["query_id"]: q for q in ev}
B = json.load(open(EV / "immutable_pre_pooling_stage2b/retrieval_benchmark_minilm.json"))
F = json.load(open(ROOT / "reports/stage2b_final_benchmark.json"))
out = {}
# ---- 1. leakage / design checks ------------------------------------------------------------------------------
docs = {m: build_documents(R, m) for m in ("q", "qk", "qka")}
alltext = {m: "\n".join(d["text"] for d in docs[m]).lower() for m in docs}
checks = {}
checks["n_docs_per_mode"] = {m: len(d) for m, d in docs.items()}
checks["unique_doc_ids_per_mode"] = {m: len({d["doc_id"] for d in docs[m]}) for m in docs}
checks["doc_keys"] = sorted({k for m in docs for d in docs[m] for k in d})
checks["searchable_text_equals_search_text_fn_for_every_doc"] = all(d["text"] == search_text(r, m) for m in docs for d, r in zip(docs[m], R))
checks["doc_ids_equal_corpus_ids_in_order"] = all([d["doc_id"] for d in docs[m]] == [r["question_id"] for r in R] for m in docs)
checks["eval_query_text_found_verbatim_in_any_doc"] = sum(1 for q in ev if q["query"].lower() in alltext["qka"])
checks["eval_query_ids_or_labels_in_docs"] = sum(1 for q in ev if q["query_id"].lower() in alltext["qka"])
bad_origin = [r["question_id"] for r in R if r["provenance"]["origin"] not in ("v5", "batch_01", "batch_02", "batch_03", "batch_04")]
checks["records_with_non_reference_origin"] = bad_origin  # candidate/user answers can only enter via a non-allowed origin; documents.py raises on them
checks["eval_set_label_fields_in_docs"] = "none: documents are built from corpus records only; eval files are never read by build_documents"
checks["doc_fields_used"] = "topic + question (q); + key_concepts (qk); + canonical_answer (qka). alternatives, common_mistakes, tags, sources, verification are metadata only"
alt_texts = [a for r in R for a in r["alternative_answers"].values() if a and a != r["canonical_answer"]]
checks["alt_answer_text_in_qka_docs"] = sum(1 for a in alt_texts if a.lower() in alltext["qka"])
# exact record-to-record duplicates in the doc text (no duplicate index entries)
checks["duplicate_doc_texts_qka"] = len(docs["qka"]) - len({d["text"] for d in docs["qka"]})
# authored queries vs corpus: max token-set Jaccard of each query with any question (lexical leakage of queries)
def jac(a, b): a, b = set(a), set(b); return len(a & b) / max(1, len(a | b))
qtok = {r["question_id"]: tokenize(r["question"]) for r in R}
mx = [max(jac(tokenize(q["query"]), t) for t in qtok.values()) for q in ev]
checks["max_jaccard_query_vs_any_stored_question"] = {"median": round(statistics.median(mx), 3), "p95": round(sorted(mx)[int(.95 * (len(mx) - 1))], 3), "max": round(max(mx), 3)}
# truncation risk for MiniLM max_seq_length=256 (word-count proxy: ~1.3 wordpieces/word; estimate, tokenizer not used)
wc = [len(d["text"].split()) for d in docs["qka"]]
checks["qka_docs_likely_truncated_at_256_wordpieces_(est)"] = round(sum(w * 1.3 > 256 for w in wc) / len(wc), 3)
checks["qka_doc_words"] = {"median": statistics.median(wc), "p90": sorted(wc)[int(.9 * (len(wc) - 1))]}
out["design_checks"] = checks
# ---- 2. mode comparison: does answer text help or mislead? (per-query flips at rank 1, primary queries) -----------
P = F["labels"]["v2_pooled"]; flips = {}
def rows(s): return {r["query_id"]: r for r in P[s]["rows"]}
for fam in ("bm25", "minilm", "hybrid_minilm"):
    a, b = rows(f"{fam}_q"), rows(f"{fam}_qka")
    prim = [q["query_id"] for q in ev if not q["no_answer"] and a[q["query_id"]]["has_primary"]]
    flips[fam] = {"q_ok_qka_wrong@1": [i for i in prim if a[i]["success@1"] and not b[i]["success@1"]],
                  "q_wrong_qka_ok@1": [i for i in prim if not a[i]["success@1"] and b[i]["success@1"]]}
    flips[fam] = {k: {"n": len(v), "ids": v} for k, v in flips[fam].items()}
out["answer_text_effect_rank1"] = flips
# ---- 3. no-answer behaviour (qka) ------------------------------------------------------------------------------
na = {}
for s in ("bm25_qka", "minilm_qka"):
    rw = rows(s); ans = sorted(rw[q["query_id"]]["top1_score"] for q in ev if not q["no_answer"]); no = [(rw[q["query_id"]]["top1_score"], q["query_id"]) for q in ev if q["no_answer"]]
    pts = []
    for thr in sorted({round(x, 2) for x in ([i / 100 for i in range(30, 80, 5)] if s.startswith("minilm") else [5, 10, 15, 20, 25, 30, 35, 40])}):
        pts.append({"threshold": thr, "no_answer_rejected": round(sum(x < thr for x, _ in no) / len(no), 3), "answerable_wrongly_rejected": round(sum(x < thr for x in ans) / len(ans), 3)})
    na[s] = {"operating_points (illustrative; thresholds chosen on these same queries -> optimistic)": pts,
             "highest_scoring_no_answer_queries": sorted([(round(x, 3), q, evq[q]["query"][:90]) for x, q in no], reverse=True)[:5]}
out["no_answer_operating_points"] = na
# ---- 4. hard cases: queries where the best system misses top-5 or top-1 -------------------------------------------------
hard = {}
for s in ("bm25_qka", "minilm_qka", "hybrid_minilm_qka"):
    rw = rows(s); miss5 = [q["query_id"] for q in ev if not q["no_answer"] and rw[q["query_id"]]["has_primary"] and not rw[q["query_id"]]["success@5"]]
    hard[s] = {"miss_top5": miss5, "n": len(miss5)}
allmiss = Counter(i for s in hard for i in hard[s]["miss_top5"])
hard["missed_by_all_three"] = sorted(i for i, c in allmiss.items() if c == 3); hard["missed_by_hybrid_only"] = sorted(set(hard["hybrid_minilm_qka"]["miss_top5"]) - set(hard["bm25_qka"]["miss_top5"]) - set(hard["minilm_qka"]["miss_top5"]))
out["hard_cases_top5_misses"] = hard
# detail for hybrid + minilm failures
detail = []
for qid in sorted(set(hard["minilm_qka"]["miss_top5"]) | set(hard["hybrid_minilm_qka"]["miss_top5"]) | set(hard["bm25_qka"]["miss_top5"])):
    q = evq[qid]; rel = {k: g for k, g in q["relevant"].items() if g >= 2}
    d = {"query_id": qid, "category": q["category"], "query": q["query"], "grade2": {k: by[k]["question"][:100] for k in rel}}
    for s in ("bm25_qka", "minilm_qka", "hybrid_minilm_qka"):
        rk = rows(s)[qid]["ranked"]; d[s + "_rank_of_first_grade2"] = next((i + 1 for i, x in enumerate(rk) if x in rel), None); d[s + "_top1"] = by[rk[0]]["question"][:100] if rk else None
    detail.append(d)
out["hard_case_detail"] = detail
# ---- 5. domain-confusion: top-1 in wrong domain ------------------------------------------------------------------
dc = {}
for s in ("bm25_qka", "minilm_qka", "hybrid_minilm_qka"):
    rw = rows(s); n = w = 0
    for q in ev:
        if q["no_answer"] or not q["domain"]: continue
        n += 1; rk = rw[q["query_id"]]["ranked"]; w += bool(rk) and by[rk[0]]["domain"] != q["domain"]
    dc[s] = {"n": n, "top1_in_other_domain": w, "rate": round(w / n, 3)}
out["top1_domain_mismatch"] = dc
json.dump(out, open(ROOT / "reports/stage2b_final_analysis.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ("design_checks", "answer_text_effect_rank1", "top1_domain_mismatch")}, indent=1, ensure_ascii=False)[:3500])
print(json.dumps(out["no_answer_operating_points"], indent=1, ensure_ascii=False)[:2500])
print(json.dumps({k: v for k, v in out["hard_cases_top5_misses"].items()}, indent=1)[:1500])
