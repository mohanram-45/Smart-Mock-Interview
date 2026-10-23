"""Record ONE live provenance run: corpus manifest + component fingerprints, each built FAISS index (recorded AND freshly computed sha256), the
Stage 3C-2 freeze manifest and evaluator versions. Also re-checks the corpus with the project's own loader (strict fingerprints). Runs nothing heavy.

    python scripts/mlflow_log_provenance.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.mlops import tracking, version  # noqa: E402


def main() -> int:
    if not tracking.available():
        print("MLflow is not installed. Run:  pip install -r requirements-mlops.txt")
        return 2
    corpus_ok, detail = 1.0, ""
    try:
        from src.retrieval.corpus import load_corpus

        load_corpus(strict=True)
    except Exception as e:  # the project's own integrity control; a failure is recorded, never hidden
        corpus_ok, detail = 0.0, f"{type(e).__name__}: {str(e)[:200]}"
    idx_ok = 1.0
    for row in version.index_fingerprints():
        f = version.ROOT / "data/retrieval/index" / row["dir"] / "index.faiss"
        if not f.is_file() or version.sha256_file(f) != row.get("index_faiss_sha256_recorded"):
            idx_ok = 0.0
    with tracking.live_run(
        "smart-provenance", "provenance snapshot", params={"corpus_loader_error": detail or None}, tags={"smart.kind": "integrity_snapshot"}
    ) as run:
        run.log_params(tracking.provenance_params(verify_indexes=True))
        run.log_metrics(
            {"corpus_loader_strict_ok": corpus_ok, "index_hashes_match_recorded": idx_ok, "corpus_records": version.corpus_info().get("record_count") or 0}
        )
        print(json.dumps({"run_id": run.run_id, "corpus_loader_strict_ok": corpus_ok, "index_hashes_match_recorded": idx_ok}))
    return 0 if corpus_ok and idx_ok else 1


if __name__ == "__main__":
    sys.exit(main())
