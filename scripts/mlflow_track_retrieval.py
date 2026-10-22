"""Run a retrieval evaluation and record it in MLflow as a NEW experiment run (Stage 8A). Imported historical runs are never touched or mixed with these.

    python scripts/mlflow_track_retrieval.py --backend minilm --local-files-only        # real model from the local Hugging Face cache; never downloads
    python scripts/mlflow_track_retrieval.py --backend dev-lsa --dry-run                # offline stand-in; prints what WOULD be recorded and records nothing in MLflow
    options: --doc-mode (default: the format the application serves)  --eval-set PATH (repeatable; default: the dev set and the frozen challenge set)

What is recorded: the embedder configuration (model, dimension, max_seq_length, library versions), the document format, the corpus fingerprint, the index file hash,
each evaluation file's sha256, the label provenance, the aggregate metrics and latency. Labels in the shipped evaluation sets are AI-pooled, not human ground truth, and the run
says so. Like any retrieval run it builds the (git-ignored) FAISS index if none exists yet. Before anything is evaluated, the version-consistency check must pass (corpus vs params vs index vs frozen files); `--allow-mismatch` overrides it and tags the run.
Exit codes: 0 recorded / dry run printed, 1 refused (mismatch), 2 cannot run (missing dependency or model)."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_SETS = ["data/retrieval/eval/stage2c_dev_v2plus.jsonl", "data/retrieval/eval/challenge_v1/eval_set.jsonl"]
LABEL_NOTE = "AI-pooled relevance labels; NOT human ground truth; no human-validated retrieval accuracy exists"


def flat_metrics(prefix, res):
    m = {}
    for k, v in res["overall"].items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            m[f"{prefix}.{k}"] = float(v)
    for k, v in res["latency_ms"].items():
        m[f"{prefix}.latency_ms.{k}"] = float(v)
    for k in ("top1_score_auroc_answerable_vs_no_answer", "mean_top1_score_no_answer", "mean_top1_score_answerable"):
        if res["no_answer"].get(k) is not None:
            m[f"{prefix}.no_answer.{k}"] = float(res["no_answer"][k])
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--backend", choices=("minilm", "dev-lsa"), default="minilm")
    ap.add_argument("--doc-mode", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--local-files-only", action="store_true")
    ap.add_argument("--eval-set", action="append", default=None)
    ap.add_argument("--experiment", default="smart-retrieval-live")
    ap.add_argument("--run-name", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-mismatch", action="store_true")
    a = ap.parse_args(argv)

    from src.mlops import consistency

    findings = consistency.check_all(verify_hashes=False)
    bad = [f for f in findings if f["status"] == "fail"]
    for f in bad:
        print(f"[FAIL] {f['id']} - {f['detail']}")
    if bad and not a.allow_mismatch:
        print("refused: fix the mismatch first (python scripts/check_versions.py), or pass --allow-mismatch to record the run tagged as such")
        return 1

    try:
        from src.retrieval.corpus import load_corpus
        from src.retrieval.embeddings import DEFAULT_MODEL
        from src.retrieval.evaluate import evaluate_retriever, load_eval_set
        from src.retrieval.factory import CACHE_DIR, ModelLoadError, index_dir, make_embedder
        from src.retrieval.index import ensure_index
        from src.retrieval.retriever import SemanticRetriever
        from src.retrieval.service import DOC_MODE

        doc_mode = a.doc_mode or DOC_MODE
        recs = load_corpus(None, strict=True)["records"]
        emb = make_embedder(a.backend, recs, doc_mode, a.model or DEFAULT_MODEL, local_files_only=a.local_files_only)
        vi, rebuilt = ensure_index(recs, emb, index_dir(a.backend, doc_mode, emb.config()), doc_mode, CACHE_DIR)
    except (ImportError, ModelLoadError) as e:
        print(f"cannot run: {type(e).__name__}: {str(e)[:300]}")
        return 2
    sem = SemanticRetriever(recs, vi, emb)

    params = {
        "retrieval.backend": a.backend,
        "retrieval.doc_mode": doc_mode,
        "retrieval.index_rebuilt_for_this_run": rebuilt,
        "retrieval.metric": vi.meta.get("metric"),
        "index.embedder_config_id": vi.meta.get("embedder_config_id"),
        "index.faiss_sha256": hashlib.sha256((index_dir(a.backend, doc_mode, emb.config()) / "index.faiss").read_bytes()).hexdigest(),
        "index.corpus_sha256": vi.meta.get("corpus_sha256"),
        "index.faiss_version": vi.meta.get("faiss_version"),
        "labels.provenance": LABEL_NOTE,
        "consistency.mismatches_overridden": str(bool(bad)).lower(),
    }
    for k, v in emb.config().items():
        params[f"embedder.{k}"] = v
    metrics = {}
    for rel in a.eval_set or DEFAULT_SETS:
        p = ROOT / rel
        if not p.is_file():
            print(f"skip: {rel} not found")
            continue
        name = "challenge_v1" if p.parent.name == "challenge_v1" else p.stem
        params[f"eval.{name}.sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        res = evaluate_retriever(sem, load_eval_set(p), k=10)
        params[f"eval.{name}.n_queries"] = res["overall"]["n_queries"]
        metrics.update(flat_metrics(name, res))
    if not metrics:
        print("cannot run: no evaluation set found")
        return 2
    run_name = a.run_name or f"{a.backend} {doc_mode} (live evaluation)"
    if a.dry_run:
        print(json.dumps({"experiment": a.experiment, "run_name": run_name, "params": params, "metrics": metrics}, indent=1, default=str))
        print("\ndry run: nothing was recorded")
        return 0
    from src.mlops import tracking

    if not tracking.available():
        print("cannot run: MLflow is not installed (pip install -r requirements-mlops.txt). Use --dry-run to see what would be recorded.")
        return 2
    tags = {"smart.kind": "retrieval_evaluation", "smart.label_source": "ai_pooled_not_ground_truth"}
    if bad:
        tags["smart.consistency"] = "MISMATCH_OVERRIDDEN"
    with tracking.live_run(a.experiment, run_name, params=params, tags=tags) as run:
        run.log_metrics(metrics)
        print(f"recorded run {run.run_id} in experiment {a.experiment!r} ({len(metrics)} metrics, {len(params)} parameters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
