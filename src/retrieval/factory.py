"""Backend selection shared by the CLI and benchmark."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .documents import build_documents
from .embeddings import DEFAULT_MODEL

ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_DIR = ROOT / "data" / "retrieval"
INDEX_DIR = RETRIEVAL_DIR / "index"
CACHE_DIR = RETRIEVAL_DIR / "cache"
EVAL_PATH = RETRIEVAL_DIR / "eval" / "eval_set.jsonl"
BACKENDS = ("minilm", "dev-lsa")


class ModelLoadError(RuntimeError):
    """The embedding model could not be loaded (not cached and no network, bad path, ...)."""


def make_embedder(backend: str, records: List[Dict[str, Any]], doc_mode: str, model_name: str = DEFAULT_MODEL,
                  local_files_only: bool = False):
    if backend == "minilm":
        from .embeddings import SentenceTransformerEmbedder
        try:
            return SentenceTransformerEmbedder(model_name, local_files_only=local_files_only)
        except ImportError:
            raise
        except Exception as exc:
            raise ModelLoadError(
                f"Could not load SentenceTransformer model {model_name!r}: {type(exc).__name__}: {str(exc)[:200]}\n"
                "The model is downloaded from the Hugging Face hub on first use and then cached locally. If this machine has no access "
                "to the hub, download the model elsewhere and pass its folder with --model <dir> (add --local-files-only to forbid network).") from exc
    if backend == "dev-lsa":
        from .embeddings_dev import DevLsaEmbedder
        from .embeddings_dev import approx_count_tokens
        return DevLsaEmbedder([d["text"] for d in build_documents(records, doc_mode, approx_count_tokens if doc_mode == "qk_concise" else None)])
    raise ValueError(f"backend must be one of {BACKENDS}")


def index_dir(backend: str, doc_mode: str, config: Dict[str, Any] | None = None) -> Path:
    """One index directory per (backend/model config, doc_mode); different models never overwrite each other."""
    from .embeddings import config_id
    tag = f"{backend}_{config_id(config)[:8]}" if config else backend
    return INDEX_DIR / f"{tag}_{doc_mode}"
