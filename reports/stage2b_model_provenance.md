# Stage 2B — model provenance and configuration

## What the evidence shows (read from the actual Windows artifacts)
| Item | Value | Source |
|---|---|---|
| Model id | `sentence-transformers/all-MiniLM-L6-v2` | benchmark JSON `model`, `embedder.model`; index_meta.json |
| Backend | `sentence-transformers` (not the dev-lsa stand-in) | `embedder.backend` |
| Embedding dim / normalisation | 384 / L2-normalised, inner product == cosine | index_meta.json (`dim`, `metric`) |
| max_seq_length | 256 | `embedder.max_seq_length` |
| Library versions | sentence-transformers 5.6.0, torch 2.12.1+cpu, FAISS 1.15.1, Python 3.12.7 | benchmark `env`, `embedder`, index_meta |
| Device | CPU, Windows 11 (build 10.0.26300), 12 CPUs | benchmark `env` |
| Embedder config id | `d14b0073c4bfe08b` (index dirs `minilm_d14b0073_{q,qk,qka}`) | index_meta.json |
| Corpus | 666 records, `corpus_sha256 = db776e9f…c6e7ef`, identical to the manifest and to the strict loader on this machine | benchmark JSON, `corpus_manifest.json` |
| Loaded offline | Yes: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `--local-files-only`; console showed `Loading weights: 103/103` | your terminal output |
| Cold build | 666 docs embedded, 0 cache hits, 16.3 s (qka); model load 0.13 s | benchmark `index_build` |

## Is it the genuine pretrained model?
Strongly supported, not yet cryptographically pinned.
- It loaded 103 weight tensors from a local cache with all network access disabled, so it is not a random-init model built on the fly.
- Its behaviour is not random-model behaviour: MiniLM top-1 cosine separates answerable from no-answer queries with AUROC 0.99 (answerable mean 0.58 vs no-answer 0.30), and it beats BM25 on paraphrases. The random tiny test model used earlier gives cos(dog, puppy)=1.0 and cos(dog, “stock market crash”)=0.98 and cannot do this.
- **Not recorded:** the cached snapshot's revision hash and the SHA-256 of its weight file. The benchmark runner did not capture them and this session cannot read your Hugging Face cache.

## Cache details
- Document-embedding cache: `data/retrieval/cache/bench/emb_d14b0073c4bfe08b.npz` (content-addressed by embedder config id + text hash; rebuilt if the config or corpus text changes).
- Model weights: your default Hugging Face cache (outside the project). Not copied into the project.

## To close the gap (one command, offline, on the PC that has the cache)
```
$env:HF_HUB_OFFLINE="1"; $env:TRANSFORMERS_OFFLINE="1"
python audit/retrieval/model_provenance.py
```
It writes `data/retrieval/model_provenance.json` with the snapshot revision, the file list with SHA-256, config, a dog/puppy sanity check and exact token counts of the qka documents (truncation). The script was tested here only against a tiny local test model, not the real one.
