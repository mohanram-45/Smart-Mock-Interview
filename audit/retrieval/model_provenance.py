"""Record provenance of the locally cached all-MiniLM-L6-v2 and measure token lengths of the qka documents.

Run on the machine that holds the model cache, offline:
    $env:HF_HUB_OFFLINE="1"; $env:TRANSFORMERS_OFFLINE="1"
    python audit/retrieval/model_provenance.py
Optional: pass a model directory as argv[1]. Writes data/retrieval/model_provenance.json. Never downloads (local_files_only=True); fails if the model is not cached.
"""
import hashlib, json, os, platform, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
REPO = "sentence-transformers/all-MiniLM-L6-v2"

def sha256(p, n=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(n), b""): h.update(b)
    return h.hexdigest()

from huggingface_hub import snapshot_download
import numpy as np, sentence_transformers, torch, transformers
snap = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(snapshot_download(REPO, local_files_only=True))  # optional explicit model dir
files = {str(p.relative_to(snap)).replace("\\", "/"): {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in sorted(snap.rglob("*")) if p.is_file()}
from sentence_transformers import SentenceTransformer
m = SentenceTransformer(str(snap), device="cpu")
from src.retrieval.corpus import load_corpus
from src.retrieval.documents import build_documents
texts = [d["text"] for d in build_documents(load_corpus()["records"], "qka")]
n_tok = [len(m.tokenizer(t, add_special_tokens=True)["input_ids"]) for t in texts]
lim = m.max_seq_length
e = m.encode(["a dog", "a puppy", "stock market crash"], normalize_embeddings=True)
out = {"repo": REPO, "snapshot_dir_name_(revision)": snap.name, "snapshot_path": str(snap).replace(str(Path.home()), "~"), "files": files,   # "~": never record the machine's user name in a file that gets committed
       "config": {"max_seq_length": lim, "embedding_dim": m.get_sentence_embedding_dimension(), "modules": [type(x).__name__ for x in m]},
       "versions": {"python": platform.python_version(), "sentence_transformers": sentence_transformers.__version__, "torch": torch.__version__, "transformers": transformers.__version__},
       "sanity": {"cos(dog,puppy)": float(e[0] @ e[1]), "cos(dog,stock market crash)": float(e[0] @ e[2]),
                  "note": "a randomly initialised model does not give dog~puppy >> dog~stock-crash"},
       "qka_doc_token_lengths": {"n": len(n_tok), "max_seq_length": lim, "share_truncated": round(sum(t > lim for t in n_tok) / len(n_tok), 3),
                                 "median": int(np.median(n_tok)), "p90": int(np.percentile(n_tok, 90)), "max": int(max(n_tok))}}
(ROOT / "data/retrieval/model_provenance.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("snapshot_dir_name_(revision)", "config", "sanity", "qka_doc_token_lengths")}, indent=1))
print("weights sha256:", {k: v["sha256"][:16] for k, v in files.items() if k.endswith((".safetensors", ".bin"))})
