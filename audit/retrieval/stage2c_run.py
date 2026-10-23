"""Stage 2C-final experiment runner (run on a machine that has the real MiniLM; works offline once cached).

  python audit/retrieval/stage2c_run.py --backend minilm --local-files-only
  python audit/retrieval/stage2c_run.py --backend dev-lsa            # smoke test only (stand-in embedder, NOT MiniLM)

Does NOT modify the corpus, the existing index, the eval sets or any app code. Writes under data/retrieval/stage2c/:
  formats_<backend>.json    exact embedded text + flags + token length for every record x format
  rankings_<backend>.json   top-30 per query per format (dense cosine, exact) + BM25 on the same text, for the dev (166) and challenge sets
  diagnosis_<backend>.json  bubble-sort investigation
"""
import argparse, json, platform, statistics, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from src.retrieval.corpus import load_corpus
from src.retrieval.doc_formats import FORMATS, build_text
from src.retrieval.embeddings import embed_texts as _embed_texts, l2_normalise
from src.retrieval.factory import make_embedder
from src.retrieval.lexical import BM25

OUT = ROOT / "data/retrieval/stage2c"
DEV = ROOT / "data/retrieval/eval/eval_set_v2.jsonl"
CH = ROOT / "data/retrieval/eval/challenge_v1/queries.jsonl"
TOPN = 30


def embed_texts(emb, texts, cache_dir=None):
    if getattr(emb, "backend", "") == "sentence-transformers":
        return _embed_texts(emb, texts, cache_dir=cache_dir)
    return l2_normalise(emb.encode_raw(list(texts))), {}      # dev stand-in only: tolerate all-zero vectors for out-of-vocabulary text


def jl(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def rank(sims, ids, n=TOPN):
    order = np.lexsort((np.arange(len(sims)), -sims))[:n]
    return [[ids[i], round(float(sims[i]), 5)] for i in order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="minilm", choices=["minilm", "dev-lsa"])
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--local-files-only", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    corpus = load_corpus(); R = corpus["records"]; ids = [r["question_id"] for r in R]
    emb = make_embedder(a.backend, R, "qka", a.model, local_files_only=a.local_files_only) if a.backend == "minilm" else make_embedder(a.backend, R, "qka")
    if a.backend == "minilm":
        tok = emb.model.tokenizer
        count = lambda t: len(tok(t, add_special_tokens=False)["input_ids"])
        tok_note = "real MiniLM tokenizer"
    else:
        import re
        count = lambda t: int(len(re.findall(r"\w+|[^\w\s]", t)) * 1.25)
        tok_note = "DEV APPROXIMATION (regex*1.25) - NOT the MiniLM tokenizer"
    msl = emb.max_seq_length if a.backend == "minilm" else 256
    cache = None if a.no_cache else ROOT / "data/retrieval/cache/stage2c"

    # ---- documents, token lengths ----
    texts, stats, full = {}, {}, {}
    for f in FORMATS:
        built = [build_text(r, f, count, msl) for r in R]
        texts[f] = [b["text"] for b in built]
        lens = [count(t) + 2 for t in texts[f]]
        stats[f] = {"n": len(lens), "max_seq_length": msl, "share_over_limit": round(sum(l > msl for l in lens) / len(lens), 4),
                    "n_over_limit": sum(l > msl for l in lens), "median": int(statistics.median(lens)),
                    "p90": int(np.percentile(lens, 90)), "max": max(lens),
                    "answer_cut": sum(b["flags"]["answer_cut"] for b in built), "head_over_budget": sum(b["flags"]["head_over_budget"] for b in built),
                    "records_with_no_answer_sentence": sum(1 for b in built if f == "qk_concise" and b["flags"]["answer_sentences"] == 0)}
        full[f] = [{"id": r["question_id"], "tokens": l, "flags": b["flags"], "text": b["text"]} for r, l, b in zip(R, lens, built)]
    # how much of the full answer does the concise format keep (words)?
    cw = [len(t.split()) for t in (r["canonical_answer"] for r in R)]
    kept = [max(0, len(t.split()) - len((r["topic"] + " " + r["question"] + " Key concepts: " + "; ".join(r["key_concepts"])).split())) for t, r in zip(texts["qk_concise"], R)]
    stats["qk_concise"]["answer_words_kept_median_share"] = round(float(np.median([k / max(1, c) for k, c in zip(kept, cw)])), 3)
    json.dump({"tokenizer": tok_note, "backend": a.backend, "stats": stats, "docs": full}, open(OUT / f"formats_{a.backend}.json", "w", encoding="utf-8"), ensure_ascii=False)

    # ---- embeddings ----
    D, emb_s = {}, {}
    for f in FORMATS:
        t0 = time.perf_counter()
        D[f], _ = embed_texts(emb, texts[f], cache_dir=cache)
        emb_s[f] = round(time.perf_counter() - t0, 2)
    bm = {f: BM25(texts[f]) for f in FORMATS}

    # ---- rankings ----
    out = {"backend": a.backend, "tokenizer": tok_note, "embedder": emb.config(), "corpus_sha256": corpus["manifest"]["corpus_sha256"],
           "env": {"python": platform.python_version(), "platform": platform.platform()}, "embed_seconds": emb_s, "sets": {}}
    lat = {}
    for name, path in (("dev", DEV), ("challenge", CH)):
        qs = jl(path)
        qv, _ = embed_texts(emb, [q["query"] for q in qs])
        S = {f: qv @ D[f].T for f in FORMATS}
        out["sets"][name] = {"n_queries": len(qs), "queries": [q["query_id"] for q in qs], "rankings": {}}
        for f in FORMATS:
            out["sets"][name]["rankings"][f"dense_{f}"] = {q["query_id"]: rank(S[f][i], ids) for i, q in enumerate(qs)}
            out["sets"][name]["rankings"][f"bm25_{f}"] = {q["query_id"]: [[ids[j], round(float(s[j]), 5)] for j in np.lexsort((np.arange(len(s)), -s))[:TOPN] if s[j] > 0]
                                                          for q, s in ((q, bm[f].scores(q["query"])) for q in qs)}
    # single-query encode latency (batch 1), same for every format (query side is format-independent)
    probe = [q["query"] for q in jl(DEV)[:40]]
    ts = []
    for q in probe:
        t0 = time.perf_counter(); emb.encode_raw([q]); ts.append((time.perf_counter() - t0) * 1000)
    out["query_encode_ms"] = {"median": round(statistics.median(ts), 2), "p95": round(float(np.percentile(ts, 95)), 2), "n": len(ts)}
    # exact numpy ranking vs FAISS IndexFlatIP (existing index machinery) for qka
    try:
        import faiss
        ix = faiss.IndexFlatIP(D["qka"].shape[1]); ix.add(D["qka"].astype(np.float32))
        dq, _ = embed_texts(emb, [q["query"] for q in jl(DEV)])
        _, I = ix.search(dq.astype(np.float32), 10)
        npy = out["sets"]["dev"]["rankings"]["dense_qka"]
        qids = out["sets"]["dev"]["queries"]
        same = sum([ids[j] for j in I[i]] == [x[0] for x in npy[qids[i]][:10]] for i in range(len(qids)))
        out["faiss_vs_numpy_top10_identical_queries"] = f"{same}/{len(qids)}"
    except Exception as e:
        out["faiss_vs_numpy_top10_identical_queries"] = f"not run: {type(e).__name__}"
    json.dump(out, open(OUT / f"rankings_{a.backend}.json", "w"))

    # ---- bubble-sort diagnosis ----
    by = {r["question_id"]: r for r in R}
    target = "smi-0453"
    cluster = ["smi-0445", "smi-0446", "smi-0447", "smi-0448", "smi-0449", "smi-0450", "smi-0451", "smi-0452", "smi-0453", "smi-h0032"]
    probes = [("exact question text of smi-0453 (what the demo sent)", by[target]["question"], True),
              ("paraphrase: how does bubble sort work and why is it slow", "Explain how bubble sort works and why it is considered slow.", False),
              ("short keyword query", "bubble sort", False),
              ("different record: quicksort question text", by["smi-0452"]["question"], False)]
    diag = {"tokenizer": tok_note, "target": target, "cluster": cluster, "records": {}, "probes": []}
    for cid in cluster:
        r = by[cid]; i = ids.index(cid)
        item = {"domain": r["domain"], "difficulty": r["difficulty"], "topic": r["topic"], "question": r["question"], "key_concepts": r["key_concepts"],
                "canonical_answer_words": len(r["canonical_answer"].split()),
                "tokens": {f: full[f][i]["tokens"] for f in FORMATS}}
        if a.backend == "minilm":
            enc = emb.model.tokenizer(texts["qka"][i], add_special_tokens=False)["input_ids"][: msl - 2]
            item["qka_visible_to_model"] = emb.model.tokenizer.decode(enc)
        else:
            item["qka_visible_to_model"] = " ".join(texts["qka"][i].split()[: int((msl - 2) / 1.25)])
        diag["records"][cid] = item
    for label, q, excl in probes:
        qv, _ = embed_texts(emb, [q])
        pr = {"label": label, "query": q, "per_format": {}}
        for f in FORMATS:
            s = (qv @ D[f].T)[0]
            full_rank = rank(s, ids, len(ids)); pos = {x[0]: (k + 1, x[1]) for k, x in enumerate(full_rank)}
            shown = [x for x in full_rank if not (excl and x[0] == target)][:10]
            pr["per_format"][f] = {
                "top10_" + ("excluding_self" if excl else "all"): [{"id": x[0], "score": x[1], "domain": by[x[0]]["domain"], "q": by[x[0]]["question"][:70]} for x in shown],
                "cluster_rank_score": {c: {"rank": pos[c][0], "score": pos[c][1]} for c in cluster}}
            if excl:
                pr["per_format"][f]["rank_of_self"] = pos[target][0]
        # domain-filtered (Python) top 5 excluding self
        py = [k for k, i in enumerate(ids) if by[i]["domain"] == "Python"]
        s = (qv @ D["qka"].T)[0]
        pr["qka_python_only_top5_excl_self"] = [[ids[k], round(float(s[k]), 5)] for k in sorted(py, key=lambda k: -s[k]) if ids[k] != target][:5]
        diag["probes"].append(pr)
    json.dump(diag, open(OUT / f"diagnosis_{a.backend}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"stats": stats, "embed_seconds": emb_s, "query_encode_ms": out["query_encode_ms"], "faiss_vs_numpy": out["faiss_vs_numpy_top10_identical_queries"], "tokenizer": tok_note}, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
