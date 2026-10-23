"""Run provenance: which code, evaluator versions, corpus and index are running. Read-only; never imports torch; every part is best-effort."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
APP_VERSION = "2.0.0"  # matches GET / on the legacy API
FREEZE_MANIFEST = "data/evaluation/stage3c2/freeze_manifest_v2.json"


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def git_commit(root: Path = ROOT) -> str:
    """SMART_GIT_COMMIT (set at image build) > .git/HEAD > 'unknown'. Pure file reads: no git binary, no subprocess."""
    env = os.environ.get("SMART_GIT_COMMIT", "").strip()
    if env:
        return env[:40]
    try:
        head = (root / ".git" / "HEAD").read_text().strip()
        if head.startswith("ref:"):
            ref = root / ".git" / head.split(" ", 1)[1].strip()
            if ref.exists():
                return ref.read_text().strip()[:40]
            packed = root / ".git" / "packed-refs"
            if packed.exists():
                for line in packed.read_text().splitlines():
                    if line.endswith(head.split(" ", 1)[1].strip()):
                        return line.split()[0][:40]
            return "unknown"
        return head[:40]
    except Exception:
        return "unknown"


_CONST_RE = re.compile(r'^\s*([A-Z_]*VERSION)\s*=\s*["\']([^"\']+)["\']', re.M)


@lru_cache(maxsize=1)
def evaluator_versions() -> Dict[str, str]:
    """Version constants of the experimental evaluator, read from source text (NOT imported: importing the evaluator pulls pydantic and patches nothing,
    but reading text keeps /healthz cheap and side-effect free)."""
    out: Dict[str, str] = {}
    files = {
        "pipeline": "src/evaluation/modular/pipeline.py",
        "rubric_engine": "src/evaluation/modular/rubric_engine.py",
        "verifier_prompt": "src/evaluation/modular/llm_verifier.py",
        "qwen_prompt": "src/evaluation/modular/qwen_verifier.py",
    }
    for name, rel in files.items():
        try:
            m = _CONST_RE.search((ROOT / rel).read_text(encoding="utf-8"))
            if m:
                out[name] = m.group(2)
        except Exception:
            pass
    try:
        txt = (ROOT / "src/evaluation/modular/variant_3c4.py").read_text(encoding="utf-8")
        m = re.search(r'VARIANT\w*\s*=\s*["\']([^"\']+)["\']', txt)
        out["opt_in_variant"] = m.group(1) if m else "3c4.0"
    except Exception:
        pass
    return out


def corpus_info(root: Path = ROOT) -> Dict[str, Any]:
    p = root / "data/retrieval/corpus_manifest.json"
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
        return {
            "record_count": m.get("record_count"),
            "manifest_sha256": sha256_file(p),
            "components": {c["name"]: {"records": c.get("records"), "fingerprint": c.get("fingerprint")} for c in m.get("components", [])},
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


def index_fingerprints(root: Path = ROOT) -> List[Dict[str, Any]]:
    """One row per built FAISS index under data/retrieval/index: embedder identity + the recorded index.faiss sha256 (from index_meta.json; the
    index file itself is hashed on demand with verify=True in the tracker)."""
    rows: List[Dict[str, Any]] = []
    base = root / "data/retrieval/index"
    if not base.is_dir():
        return rows
    for d in sorted(base.iterdir()):
        mp = d / "index_meta.json"
        if not mp.is_file():
            continue
        try:
            m = json.loads(mp.read_text(encoding="utf-8"))
            emb = m.get("embedder", {})
            rows.append(
                {
                    "dir": d.name,
                    "doc_mode": m.get("doc_mode"),
                    "n": m.get("n"),
                    "dim": m.get("dim"),
                    "backend": emb.get("backend"),
                    "model": emb.get("model"),
                    "revision": emb.get("revision"),
                    "embedder_config_id": m.get("embedder_config_id"),
                    "corpus_sha256": m.get("corpus_sha256"),
                    "faiss_version": m.get("faiss_version"),
                    "index_faiss_sha256_recorded": (m.get("files") or {}).get("index.faiss"),
                }
            )
        except Exception:
            continue
    return rows


def freeze_info(root: Path = ROOT) -> Dict[str, Any]:
    p = root / FREEZE_MANIFEST
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
        return {"version": m.get("version"), "status": m.get("status"), "manifest_sha256": sha256_file(p)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


_FLAG_DEFAULTS = {
    "SMART_QUESTION_SOURCE": "legacy",
    "SMART_RETRIEVAL_ENABLED": "off",
    "SMART_DEMO_CODE_EVAL": "off",
    "SMART_CODEEVAL_EXEC": "disabled",
    "SMART_DEMO_LIVE_MODULAR": "off",
    "SMART_DEMO_ALLOW_SCORER_SETUP": "off",
    "SMART_EVALUATION_BACKEND": "legacy",
    "SMART_LLM_PROVIDER": "none",
    "SMART_LLM_ALLOW_PAID": "off",
    "SMART_RETRIEVAL_EXPOSE_REFERENCE": "off",
}


def flags_state() -> Dict[str, Any]:
    """Which opt-in features are set in THIS process (value shown, or the default). Never includes secrets (SMART_LLM_API_KEY is deliberately absent)."""
    return {k: os.environ.get(k, d) for k, d in _FLAG_DEFAULTS.items()}


def build_info(light: bool = False) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "app_version": APP_VERSION,
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "evaluator_versions": evaluator_versions(),
    }
    if not light:
        info.update(corpus=corpus_info(), frozen_experiment=freeze_info(), flags=flags_state())
    return info
