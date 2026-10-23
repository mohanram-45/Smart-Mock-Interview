"""Verify (and, only when asked, build) the REAL MiniLM `qk_concise` index the application serves (Stage 8D).

    python scripts\\verify_real_index.py                 read-only: corpus, model cache, existing indexes; if the index exists also its metadata and checksum. Loads no model.
    python scripts\\verify_real_index.py --retrieval     also loads the model OFFLINE and searches the built index (compares with the recorded Stage 2C rankings)
    python scripts\\verify_real_index.py --build         builds the missing index with the project's own CLI (offline), then runs every check including retrieval

Guarantees: HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE are forced on, so nothing is downloaded; an existing index directory is never overwritten or rebuilt; every other index
under data/retrieval/index and the recorded Stage 2C results are hashed before and after and must be byte-identical; the model cache listing must not change.
Exit 0 = every check passed (skips are listed), 1 = a check failed, 2 = cannot run (for example the model is not in the local cache and --build/--retrieval was requested)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ["HF_HUB_OFFLINE"] = "1"  # before any import that could reach the network
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPO = "sentence-transformers/all-MiniLM-L6-v2"
DOC_MODE = "qk_concise"
SCORE_TOLERANCE = 2e-3  # float32 / library-version noise; the recorded rankings were produced on CPU with the same model
MIN_TOP1_AGREEMENT = 0.99

results: List[Dict[str, str]] = []


def report(status: str, name: str, detail: str = "") -> None:
    results.append({"status": status, "name": name, "detail": detail})
    print(f"[{status.upper():4}] {name}" + (f" - {detail}" if detail else ""))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree_hashes(base: Path, exclude_dirs: tuple = ()) -> Dict[str, str]:
    """{relative posix path: sha256} for every file under base (skipping the named top-level directories)."""
    out: Dict[str, str] = {}
    if not base.is_dir():
        return out
    for p in sorted(base.rglob("*")):
        if p.is_file():
            rel = p.relative_to(base)
            if rel.parts and rel.parts[0] in exclude_dirs:
                continue
            out[rel.as_posix()] = sha256_file(p)
    return out


def expected_index_dir_name(model: str, doc_mode: str = DOC_MODE) -> str:
    """The directory the application and the CLI use for the real model: minilm_<config id[:8]>_<doc mode>. Computed without loading the model."""
    from src.retrieval.embeddings import config_id

    cfg = {"backend": "sentence-transformers", "model": model, "dim": 384, "max_seq_length": 256, "normalised": True}
    return f"minilm_{config_id(cfg)[:8]}_{doc_mode}"


def verify_index_dir(d: Path, corpus: Dict[str, Any], model: str = REPO, doc_mode: str = DOC_MODE, dim: int = 384) -> List[Dict[str, str]]:
    """Static checks of a built index directory against the current corpus. Returns findings; loads no model."""
    out: List[Dict[str, str]] = []

    def f(ok: Optional[bool], name: str, detail: str = "") -> None:
        out.append({"status": "pass" if ok else ("skip" if ok is None else "fail"), "name": name, "detail": detail})

    meta_p, idx_p = d / "index_meta.json", d / "index.faiss"
    if not (meta_p.is_file() and idx_p.is_file()):
        f(False, "index.files_present", "index.faiss and index_meta.json are required")
        return out
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    ids = [r["question_id"] for r in corpus["records"]]
    corpus_sha = corpus["manifest"]["corpus_sha256"]
    f(meta.get("corpus_sha256") == corpus_sha, "index.corpus_fingerprint", f"index {str(meta.get('corpus_sha256'))[:16]} vs corpus {corpus_sha[:16]}")
    f(meta.get("doc_mode") == doc_mode, "index.document_format", f"index doc_mode={meta.get('doc_mode')!r}, expected {doc_mode!r}")
    emb = meta.get("embedder") or {}
    f(
        emb.get("model") == model and emb.get("dim") == dim and emb.get("max_seq_length") == 256 and emb.get("normalised") is True,
        "index.embedder_configuration",
        f"model={emb.get('model')}, dim={emb.get('dim')}, max_seq_length={emb.get('max_seq_length')}, normalised={emb.get('normalised')}",
    )
    f(meta.get("ids") == ids and meta.get("n") == len(ids), "index.row_order_matches_corpus", f"{len(ids)} records, same order")
    rec = (meta.get("files") or {}).get("index.faiss")
    actual = sha256_file(idx_p)
    f(bool(rec) and rec == actual, "index.checksum_matches_manifest", f"index.faiss sha256 {actual[:16]} (recorded {str(rec)[:16]})")
    try:
        import faiss

        ix = faiss.read_index(str(idx_p))
        f(ix.ntotal == len(ids) and ix.d == dim, "index.faiss_shape", f"{ix.ntotal} vectors x {ix.d}")
    except ImportError:
        f(None, "index.faiss_shape", "faiss is not installed in this environment")
    return out


def compare_with_stored(live: Dict[str, List[str]], live_top_score: Dict[str, float], stored: Dict[str, List[list]]) -> Dict[str, Any]:
    """Compare live top-k ids/scores with the recorded Stage 2C `dense_qk_concise` rankings (same query ids)."""
    common = [q for q in stored if q in live]
    same_top1 = [q for q in common if stored[q] and live[q] and stored[q][0][0] == live[q][0]]
    max_delta = max((abs(stored[q][0][1] - live_top_score[q]) for q in common if stored[q]), default=0.0)
    top10 = [len(set(x[0] for x in stored[q][:10]) & set(live[q][:10])) / 10 for q in common if stored[q]]
    return {
        "queries_compared": len(common),
        "top1_agreement": round(len(same_top1) / len(common), 4) if common else 0.0,
        "max_abs_top1_score_delta": round(max_delta, 6),
        "mean_top10_overlap": round(sum(top10) / len(top10), 4) if top10 else 0.0,
        "disagreeing_query_ids": sorted(set(common) - set(same_top1))[:20],
    }


def hf_snapshot() -> Optional[Path]:
    try:
        from huggingface_hub import snapshot_download

        return Path(snapshot_download(REPO, local_files_only=True))
    except Exception:
        return None


def cache_listing(snap: Optional[Path]) -> Dict[str, int]:
    """Relative path -> size of the model's cache directory, to prove that nothing was added or changed."""
    if snap is None:
        return {}
    base = snap.parents[1]  # models--org--name
    return {p.relative_to(base).as_posix(): p.stat().st_size for p in sorted(base.rglob("*")) if p.is_file() or p.is_symlink()}


def read_queries() -> Dict[str, str]:
    q: Dict[str, str] = {}
    for rel in ("data/retrieval/eval/stage2c_dev_v2plus.jsonl", "data/retrieval/eval/challenge_v1/queries.jsonl"):
        for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                q[r["query_id"]] = r["query"]
    return q


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", action="store_true", help="build the missing index (offline; refuses to touch an existing one)")
    ap.add_argument("--retrieval", action="store_true", help="load the model offline and search the built index")
    ap.add_argument("--write-report", metavar="PATH", help="write the findings as JSON to PATH")
    a = ap.parse_args(argv)
    need_model = a.build or a.retrieval

    from src.retrieval.corpus import corpus_fingerprint, load_corpus

    corpus = load_corpus(strict=True)
    sha = corpus_fingerprint(corpus["records"])
    stored_rk = json.loads((ROOT / "data/retrieval/stage2c/rankings_minilm.json").read_text(encoding="utf-8"))
    report(
        "pass" if sha == corpus["manifest"]["corpus_sha256"] == stored_rk["corpus_sha256"] else "fail",
        "corpus fingerprint",
        f"{len(corpus['records'])} records, sha256 {sha[:16]}; manifest and recorded Stage 2C rankings agree"
        if sha == stored_rk["corpus_sha256"]
        else "corpus differs from the manifest or from the recorded rankings",
    )

    prov_p = ROOT / "data/retrieval/model_provenance.json"
    if not prov_p.is_file():
        report("fail", "model provenance record", "data/retrieval/model_provenance.json is missing (it records the model revision and file hashes)")
        return 1
    prov = json.loads(prov_p.read_text(encoding="utf-8"))
    revision = prov["snapshot_dir_name_(revision)"]
    snap = hf_snapshot()
    before_cache = cache_listing(snap)
    if snap is None:
        report(
            "fail" if need_model else "skip",
            "model in the local Hugging Face cache",
            f"{REPO} is not cached; nothing is downloaded. Recorded revision: {revision}",
        )
    else:
        report("pass" if snap.name == revision else "fail", "embedding model revision", f"cached snapshot {snap.name} vs recorded {revision}")
        bad = [n for n, meta in prov["files"].items() if not (snap / n).is_file() or sha256_file(snap / n) != meta["sha256"]]
        report(
            "pass" if not bad else "fail",
            "model files match the recorded sha256",
            f"{len(prov['files'])} files checked" if not bad else f"differ or missing: {bad[:5]}",
        )

    idx_root = ROOT / "data/retrieval/index"
    name = expected_index_dir_name(REPO)
    target = idx_root / name
    frozen_before = tree_hashes(idx_root, exclude_dirs=(name,))
    stage2c_before = tree_hashes(ROOT / "data/retrieval/stage2c")
    report("pass", "frozen artifacts snapshotted", f"{len(frozen_before)} index files + {len(stage2c_before)} recorded Stage 2C files hashed")

    if a.build:
        if target.exists():
            report("fail", "build refused", f"{name} already exists; it is never overwritten (delete it yourself if you really want a rebuild)")
            return 1
        if snap is None:
            return 2
        cmd = [sys.executable, "-m", "src.retrieval.cli", "build", "--backend", "minilm", "--doc-mode", DOC_MODE, "--model", REPO, "--local-files-only"]
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        last = (r.stdout.strip().splitlines() or [""])[-1][:200]
        report(
            "pass" if r.returncode == 0 else "fail",
            "index build (project CLI, offline)",
            f"{time.perf_counter() - t0:.1f}s; {last}" if r.returncode == 0 else (r.stderr or r.stdout)[-400:],
        )
        if r.returncode != 0:
            return 1

    if not target.is_dir():
        report("skip", "served-format index", f"{name} does not exist yet. Build it with: python scripts\\verify_real_index.py --build")
    else:
        for fd in verify_index_dir(target, corpus):
            report(fd["status"], fd["name"], fd["detail"])
        if need_model:
            from src.retrieval.service import RetrievalService

            svc = RetrievalService(backend="minilm", model_name=REPO, local_files_only=True, doc_mode=DOC_MODE)
            queries = read_queries()
            live: Dict[str, List[str]] = {}
            top: Dict[str, float] = {}
            degraded = None
            for qid, text in queries.items():
                res = svc.search(text, k=10)
                if res["mode"] != "semantic":
                    degraded = res.get("degraded_reason")
                    break
                live[qid] = [x["question_id"] for x in res["results"]]
                top[qid] = res["results"][0]["score"] if res["results"] else 0.0
            if degraded:
                report("fail", "retrieval from the built index", f"semantic mode unavailable, BM25 fallback used: {degraded}")
            else:
                report(
                    "pass" if not svc.index_rebuilt else "fail", "service loaded the existing index without rebuilding it", f"index_rebuilt={svc.index_rebuilt}"
                )
                stored_all: Dict[str, List[list]] = {}
                for sname in ("dev", "challenge"):
                    stored_all.update(stored_rk["sets"][sname]["rankings"]["dense_qk_concise"])
                cmp = compare_with_stored(live, top, stored_all)
                ok = cmp["queries_compared"] > 0 and cmp["top1_agreement"] >= MIN_TOP1_AGREEMENT and cmp["max_abs_top1_score_delta"] <= SCORE_TOLERANCE
                report("pass" if ok else "fail", "retrieval reproduces the recorded Stage 2C dense_qk_concise rankings", json.dumps(cmp))
                # each corpus question retrieves itself
                import random

                rnd = random.Random(0)
                recs = rnd.sample(corpus["records"], 40)
                hit = sum(1 for r in recs if (svc.search(r["question"], k=1)["results"] or [{}])[0].get("question_id") == r["question_id"])
                report("pass" if hit >= 38 else "fail", "self-retrieval of 40 sampled corpus questions", f"{hit}/40 ranked first")
            report("pass" if svc.status().get("mode") == "semantic" else "fail", "service mode", str(svc.status().get("mode")))

    if snap is None:
        report(
            "skip", "no model download / no change to the model cache", "the model is not cached here; offline mode was forced, so nothing could be downloaded"
        )
    else:
        after_cache = cache_listing(snap)
        report(
            "pass" if after_cache == before_cache else "fail",
            "no model download / no change to the model cache",
            f"{len(after_cache)} cache files, listing identical" if after_cache == before_cache else "cache listing changed",
        )
    frozen_after = tree_hashes(idx_root, exclude_dirs=(name,))
    stage2c_after = tree_hashes(ROOT / "data/retrieval/stage2c")
    report(
        "pass" if frozen_after == frozen_before and stage2c_after == stage2c_before else "fail",
        "frozen historical index artifacts and Stage 2C results unchanged",
        "byte-identical",
    )

    bad = [x for x in results if x["status"] == "fail"]
    print(
        f"\n{'REAL INDEX VERIFICATION: ALL PASSED' if not bad else 'REAL INDEX VERIFICATION: FAILED'} ({sum(x['status'] == 'pass' for x in results)} pass, {len(bad)} fail, {sum(x['status'] == 'skip' for x in results)} skip)"
    )
    if a.write_report:
        Path(a.write_report).write_text(json.dumps({"findings": results}, indent=1), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
