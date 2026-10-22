"""Command line: build / search / demo / benchmark / manifest.   python -m src.retrieval.cli --help"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from .corpus import load_corpus
from .embeddings import DEFAULT_MODEL
from .factory import BACKENDS, CACHE_DIR, ModelLoadError, ROOT, index_dir, make_embedder
from .index import ensure_index
from .lexical import tokenize
from .retriever import LexicalRetriever, SemanticRetriever
from .service import DOC_MODE

DEMO_QUERIES = [
    ("Why does my model get worse in production even though offline metrics were fine?", None),
    ("how do I stop a SQL query from scanning the whole table", "SQL"),
    ("what is the difference between precision and recall", None),
    ("my RAG assistant makes up facts that are not in the retrieved documents", None),
]


def _args():
    p = argparse.ArgumentParser(prog="python -m src.retrieval.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("build", "search", "demo", "benchmark", "manifest"):
        s = sub.add_parser(name)
        s.add_argument("--backend", choices=BACKENDS, default="minilm")
        s.add_argument("--doc-mode", choices=("q", "qk", "qka", "qk_concise"), default=DOC_MODE,
                       help="embedded text format; the default is the format the application serves (service.DOC_MODE)")
        s.add_argument("--model", default=DEFAULT_MODEL, help="SentenceTransformer model name or local directory (backend minilm)")
        s.add_argument("--local-files-only", action="store_true", help="never contact the model hub (use the local HF cache)")
        if name == "build":
            s.add_argument("--force", action="store_true")
        if name in ("search", "demo"):
            s.add_argument("-k", type=int, default=3)
            s.add_argument("--method", choices=("semantic", "bm25", "both"), default="both")
        if name == "search":
            s.add_argument("query")
            s.add_argument("--domain")
        if name == "benchmark":
            s.add_argument("--out", default=str(ROOT / "reports" / "retrieval_benchmark"))
            s.add_argument("--no-cache", action="store_true")
        if name == "manifest":
            s.add_argument("--out", default=str(ROOT / "data" / "retrieval" / "corpus_manifest.json"))
    return p.parse_args()


def _print(hits, width=100):
    for h in hits:
        r = h["record"]
        print(f"  {h['rank']}. [{h['score']:.3f}] {h['question_id']} | {r['domain']} | {r['difficulty']} | {r['topic'][:50]}")
        print(textwrap.indent(textwrap.fill("Q: " + r["question"], width - 6), "       "))
        print(textwrap.indent(textwrap.fill("A: " + r["canonical_answer"][:300] + ("..." if len(r["canonical_answer"]) > 300 else ""), width - 6), "       "))
        v = r["verification"]
        print(f"       verification: {v['verification']}; human_reviewed={v['human_reviewed']}; time_sensitive={v['time_sensitive']}")


def main() -> int:
    a = _args()
    corpus = load_corpus()
    R, man = corpus["records"], corpus["manifest"]
    if a.cmd == "manifest":
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(man, indent=1), encoding="utf-8")
        print(f"corpus manifest written: {a.out}\n{man['record_count']} records, sha256 {man['corpus_sha256']}")
        return 0
    if a.cmd == "benchmark":
        from .benchmark import run, to_markdown
        res = run(a.backend, model_name=a.model, use_cache=not a.no_cache, local_files_only=a.local_files_only,
                  union_path=ROOT / "data/retrieval/eval/eval_set_union_labels.jsonl")
        Path(a.out + f"_{a.backend}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        Path(a.out + f"_{a.backend}.md").write_text(to_markdown(res), encoding="utf-8")
        print(to_markdown(res).split("### ")[0])
        return 0
    emb = make_embedder(a.backend, R, a.doc_mode, a.model, local_files_only=a.local_files_only)
    vi, rebuilt = ensure_index(R, emb, index_dir(a.backend, a.doc_mode, emb.config()), a.doc_mode, CACHE_DIR, force=getattr(a, "force", False))
    if a.cmd == "build":
        b = vi.meta["build_stats"]
        print(f"{'rebuilt' if rebuilt else 'up to date'}: {vi.index.ntotal} vectors x {vi.index.d}, backend={a.backend}, doc_mode={a.doc_mode}, "
              f"embedded {b['embedded']} / cache hits {b['cache_hits']}, {b['total_build_seconds']}s -> {index_dir(a.backend, a.doc_mode, emb.config())}")
        return 0
    sem, lex = SemanticRetriever(R, vi, emb), LexicalRetriever(R, "qka" if a.doc_mode == "qk_concise" else a.doc_mode)   # BM25 reads the full text (as in the service); qk_concise needs a tokenizer
    queries = [(a.query, a.domain)] if a.cmd == "search" else DEMO_QUERIES
    for q, dom in queries:
        print(f"\nQUERY: {q}" + (f"   [domain={dom}]" if dom else ""))
        if a.method in ("semantic", "both"):
            print(f" semantic ({a.backend} + FAISS IndexFlatIP):")
            _print(sem.search(q, a.k, dom))
        if a.method in ("bm25", "both"):
            print(" lexical (BM25):")
            _print(lex.search(q, a.k, dom))
    print("\nNote: results are reference knowledge only (AI-reviewed, not human-verified).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ModelLoadError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
