"""Data / model / pipeline version-consistency checks (Stage 8A). Read-only: no model is loaded, nothing is downloaded or written.

`check_all()` answers one question: do the things that are supposed to describe the same retrieval system actually agree?
  * the committed corpus manifest vs the corpus the code loads (strict fingerprint)
  * `params.yaml` (what `dvc repro` builds) vs the format and model the application serves (src/retrieval/service.py)
  * every built index vs the current corpus, its own recorded file hash, and (for the served index) the served model
  * the frozen challenge query file vs its recorded sha256
  * the stored Stage 2C MiniLM rankings vs the current corpus (so the recorded metrics describe THIS corpus)
Each finding is {id, status, detail} with status pass | fail | skip. `skip` means the thing does not exist here (for example no index built yet), never "ok".
A `fail` is a real disagreement. This was added after a review found `params.yaml` building the `qka` format while the application serves `qk_concise`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from . import version

ROOT = version.ROOT


def _f(id_: str, status: str, detail: str) -> Dict[str, Any]:
    return {"id": id_, "status": status, "detail": detail}


def _read_params(root: Path) -> Dict[str, Any]:
    import yaml

    return yaml.safe_load((root / "params.yaml").read_text(encoding="utf-8"))


def check_all(root: Path = ROOT, *, verify_hashes: bool = True) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    # 1. corpus manifest vs loaded corpus
    corpus_sha = None
    try:
        from src.retrieval.corpus import load_corpus

        c = load_corpus(root, strict=True)
        corpus_sha = c["manifest"]["corpus_sha256"]
        man = json.loads((root / "data/retrieval/corpus_manifest.json").read_text(encoding="utf-8"))
        ok = man.get("corpus_sha256") == corpus_sha and man.get("record_count") == len(c["records"])
        out.append(
            _f(
                "corpus.manifest_matches_loaded_corpus",
                "pass" if ok else "fail",
                f"{len(c['records'])} records, sha256 {corpus_sha[:16]}" if ok else "committed manifest differs from the corpus the code loads",
            )
        )
    except Exception as e:
        out.append(_f("corpus.manifest_matches_loaded_corpus", "fail", f"corpus did not load strictly: {type(e).__name__}: {str(e)[:160]}"))
    # 2. params.yaml vs the served configuration
    served_mode = served_model = None
    try:
        from src.retrieval.service import DOC_MODE, MODEL_NAME

        served_mode, served_model = DOC_MODE, MODEL_NAME
        p = _read_params(root)["embedding"]
        out.append(
            _f(
                "dvc.params_doc_mode_is_the_served_format",
                "pass" if p.get("doc_mode") == DOC_MODE else "fail",
                f"params.yaml doc_mode={p.get('doc_mode')!r}, application serves {DOC_MODE!r}"
                + ("" if p.get("doc_mode") == DOC_MODE else ": `dvc repro` would rebuild an index the application does not use"),
            )
        )
        out.append(
            _f(
                "dvc.params_model_is_the_served_model",
                "pass" if p.get("model") == MODEL_NAME and p.get("backend") == "minilm" else "fail",
                f"params.yaml backend={p.get('backend')!r}, model={p.get('model')!r}; application default model {MODEL_NAME!r}",
            )
        )
    except Exception as e:
        out.append(_f("dvc.params_vs_application", "fail", f"{type(e).__name__}: {str(e)[:160]}"))
    # 3. built indexes
    rows = version.index_fingerprints(root)
    if not rows:
        out.append(
            _f(
                "index.built",
                "skip",
                "no index is built here (the application builds one on its first search; `dvc repro` or `python -m src.retrieval.cli build` builds it earlier)",
            )
        )
    served_found = False
    for r in rows:
        tag = f"index.{r['dir']}"
        if corpus_sha and r.get("corpus_sha256"):
            out.append(
                _f(
                    f"{tag}.built_from_current_corpus",
                    "pass" if r["corpus_sha256"] == corpus_sha else "fail",
                    "corpus fingerprint matches" if r["corpus_sha256"] == corpus_sha else "STALE: built from a different corpus version; rebuild it",
                )
            )
        if verify_hashes:
            f = root / "data/retrieval/index" / r["dir"] / "index.faiss"
            rec = r.get("index_faiss_sha256_recorded")
            if not f.is_file() or not rec:
                out.append(_f(f"{tag}.file_hash", "skip", "index.faiss or its recorded hash is not present"))
            else:
                actual = hashlib.sha256(f.read_bytes()).hexdigest()
                out.append(
                    _f(
                        f"{tag}.file_hash",
                        "pass" if actual == rec else "fail",
                        "index.faiss matches its recorded sha256" if actual == rec else "index.faiss differs from the hash recorded when it was built",
                    )
                )
        if r.get("backend") == "sentence-transformers":
            if served_mode and r.get("doc_mode") == served_mode and r.get("model") == served_model:
                served_found = True
    if rows and served_mode and not served_found and any(r.get("backend") == "sentence-transformers" for r in rows):
        out.append(
            _f(
                "index.served_index_present",
                "skip",
                f"MiniLM indexes exist, none for the served format {served_mode!r}: the application will build it on first search",
            )
        )
    # 4. frozen challenge query file
    fz = root / "data/retrieval/eval/challenge_v1/FROZEN.json"
    qf = root / "data/retrieval/eval/challenge_v1/queries.jsonl"
    if fz.is_file() and qf.is_file():
        want = json.loads(fz.read_text(encoding="utf-8")).get("sha256")
        got = hashlib.sha256(qf.read_bytes()).hexdigest()
        out.append(
            _f(
                "frozen.challenge_queries_unchanged",
                "pass" if got == want else "fail",
                "queries.jsonl matches FROZEN.json" if got == want else "queries.jsonl differs from the sha256 recorded when it was frozen",
            )
        )
    else:
        out.append(_f("frozen.challenge_queries_unchanged", "skip", "challenge_v1 files not present"))
    # 5. stored MiniLM rankings describe this corpus
    rk = root / "data/retrieval/stage2c/rankings_minilm.json"
    if rk.is_file() and corpus_sha:
        stored = json.loads(rk.read_text(encoding="utf-8")).get("corpus_sha256")
        out.append(
            _f(
                "stored_results.stage2c_rankings_match_corpus",
                "pass" if stored == corpus_sha else "fail",
                "recorded rankings were produced on this corpus" if stored == corpus_sha else "recorded rankings were produced on a different corpus version",
            )
        )
    return out


def summarise(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    s = {"pass": 0, "fail": 0, "skip": 0}
    for f in findings:
        s[f["status"]] += 1
    return s
