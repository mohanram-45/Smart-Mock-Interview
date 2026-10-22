# Reproducing the retrieval pipeline, and what DVC is (and is not) used for

## What already protects the data (reused, not duplicated)

| Control | Where | Protects |
|---|---|---|
| Frozen v5 fingerprint hard-coded in the loader + per-batch fingerprints in the registry | `src/retrieval/corpus.py` (`load_corpus(strict=True)`) | the 666-record corpus (487 v5 + 4 batches) and its order |
| Component sha256 values + corpus fingerprint | `data/retrieval/corpus_manifest.json` | the five source CSVs |
| Stage 3C-2 freeze manifest v2 | `data/evaluation/stage3c2/freeze_manifest_v2.json`, `scripts/stage3c2_freeze_v2.py` | prompts, gate, rubric, sample, model config |
| bench_v2 manifest | `data/evaluation/bench_v2/manifest.json` | the 120-answer benchmark files |
| Index metadata (`corpus_sha256`, embedder identity, `index.faiss` sha256) | `data/retrieval/index/*/index_meta.json` | each built index |

`python scripts/check_integrity.py` runs all of them in one read-only command (it is also a CI job and the first step of the DVC stage). Question ids (`smi-0001` ...) are
stable and unique (666 unique ids); nothing in the MLOps work changes any of these files (a test asserts the importer leaves every source file's mtime untouched).

## DVC: scope decision

| Artifact | Decision | Reason |
|---|---|---|
| Corpus CSVs, manifests, curated v1-v5, expansion batches, frozen Stage 3C data (all < 4 MB each, about 50 MB in the published tree; the 28 MB of browser-journey screenshots under `data/evaluation/*/screenshots/` are regenerable and not published) | **stay in Git** | small, text, already fingerprinted; moving them to DVC would add a second source of truth for the same guarantee and risk changing frozen data |
| FAISS indexes and embedding cache (`data/retrieval/index`, `data/retrieval/cache`) | **DVC stage `build_index`** | derived binary artifacts, git-ignored today, rebuilt only with the embedding model present; DVC records the exact inputs and gives you cache/restore |
| Model checkpoint (`results/siamese_bilstm.pt`, 3.8 MB) | **stays in Git for now** | already committed in the project's first commit, so it is in history either way; `dvc add` refuses a Git-tracked file (verified in Stage 7B), and moving it would need `git rm --cached` plus a remote to hold it. Optional later step, needs your approval (see below) |
| Embedding model weights | **not tracked**; pin by local directory + revision (below) | owned by Hugging Face; never copied into Git or an image |
| Session files (`results/demo_sessions`) | **never** | candidate answers |
| MLflow store | **not tracked**; rebuilt with `scripts/mlflow_import_history.py` | derived from files in Git |

## Line endings are part of the integrity story

The corpus CSVs, manifests, the frozen Stage 3C data and a few frozen source files are pinned by the sha256 of their **exact bytes**. Git for Windows defaults to
`core.autocrlf=true`, which checks text files out with CRLF; a fresh Windows clone (and the `windows-latest` CI job) would then fail every hash. `.gitattributes`
(`* text=auto eol=lf`; `*.bat`/`*.ps1` stay CRLF; binaries untouched) makes the working-tree bytes identical on every OS. Evidence (Stage 7A, Linux): the integrity check passes
on a copy where every text file is LF, and **fails** on a copy where every text file is CRLF; `scripts/check_integrity.py` now says so and prints the fix instead of only listing
hash mismatches. Never edit a manifest to make a CRLF clone pass.

**The exception (found in Stage 7B by committing the publishable tree to a scratch repository and cloning it with `core.autocrlf=true`).** Thirteen hash-pinned files are stored with
Windows (CRLF) line endings, because Python on Windows wrote them that way and their checksums were computed over those bytes: `retrieval_benchmark_minilm.json/.md` (in `reports/` and in
`data/retrieval/eval/immutable_pre_pooling_stage2b/`), the three `data/expansion/batch_0*/corrections.csv`, `data/raw/*`, `data/processed/*`, `data/interim/transformed.json` and
`src/model/Pretrained_NEURALN.py`. The blanket LF rule would have rewritten them on commit and made `test_originals_are_byte_identical_to_checksums` fail on GitHub. They are marked `-text`
in `.gitattributes` (Git then never converts them, in either direction, on any OS), and `tests/mlops/test_publication_safety.py` fails if another CRLF file whose sha256 is recorded elsewhere is
missing from that list. Rule of thumb: LF for everything you author, `-text` for anything a checksum already covers.

## Reproducing the environment

- Application (Docker): `requirements-docker.lock` (exact versions) on `python:3.13-slim-bookworm`; pin the base by digest via `SMART_PYTHON_IMAGE` for bit-for-bit rebuilds.
- Tests / CI: `requirements-ci.lock` and `requirements-ci-mlops.lock` (exact versions **and** sha256 hashes, universal across Linux/Windows/macOS and Python 3.12/3.13).
  `pip install --require-hashes -r requirements-ci.lock` reproduces the CI environment on your machine.
- Day-to-day development keeps the looser `requirements*.txt` files (what the project always used); the locks are what CI and Docker trust.

## Reproduce the retrieval pipeline from a clean environment

```
git clone <your repository> SMART-MOCK-INTERVIEW && cd SMART-MOCK-INTERVIEW
python -m venv .bot && .bot\Scripts\activate                  (Windows)      # python 3.12 recommended; faiss-cpu wheels may lag newest Python
pip install -r requirements-rag.txt
python scripts\check_integrity.py                              # must print INTEGRITY OK
python -m src.retrieval.cli build --backend minilm --local-files-only        # builds the format the application serves (qk_concise); add --doc-mode qka for the older Stage 2A format
python scripts\check_versions.py                                               # corpus, params.yaml, index and frozen files must agree
python scripts\verify_real_index.py                                           # Stage 8D: model cache, revision, existing and served-format indexes (read-only, no model load)
python scripts\verify_real_index.py --build                                   # builds ONLY the missing qk_concise index offline (about 15 s), never overwrites, then verifies retrieval against the recorded Stage 2C rankings
python -m pytest tests\retrieval -q
```
`--local-files-only` means nothing is downloaded: the MiniLM model must already be in your Hugging Face cache. Getting it is a one-time **download (~90 MB) that needs your
approval**: `python -c "from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2')"`. The build embeds 666 records and writes
`data/retrieval/index/<backend>_<config id>_<doc mode>/{index.faiss,index_meta.json}`. Compare `index_meta.json["files"]["index.faiss"]` with your build; `python
scripts\mlflow_log_provenance.py` records recorded vs freshly computed hashes.

**Known gap:** the Stage 2C result file does not record the Hugging Face model *revision*, and `index_meta.json` stores `revision: null`. Dense vectors can differ across
model revisions and library versions. To pin: download once with `huggingface-cli download sentence-transformers/all-MiniLM-L6-v2 --revision <commit sha> --local-dir models\minilm`
(a download, with your approval), pass `--model models\minilm`, and note the commit sha next to the run. Bit-for-bit equality of `index.faiss` across machines is **not**
claimed for the MiniLM backend; it was observed only for the dev-LSA backend (below).

## Using DVC (optional)

`dvc.yaml` and `params.yaml` are in the repository; the DVC *repository* (`.dvc/`) is not, until you run `dvc init`. Stage 7B checked what that does, in a clean scratch Git repository:
`dvc init` creates exactly one file, an empty `.dvc/config` (the root `.gitignore` already covers `.dvc/cache`, `.dvc/tmp` and `.dvc/config.local`, so DVC adds no ignore file). It reads
no data, uploads nothing and changes no frozen file.

```
pip install "dvc>=3,<4"
dvc init                                  # once, inside the Git repository; commit .dvc/config
python scripts\check_integrity.py          # must print INTEGRITY OK before and after
dvc repro                                 # integrity check, then rebuild index + cache (needs the MiniLM model already in the HF cache; never downloads)
git add dvc.lock                          # commit dvc.lock ONLY after a real MiniLM run on your machine (see the warning below)
```
To see the whole cycle work without touching your repository (a temporary copy, the offline `dev-lsa` stand-in embedder, no download, nothing uploaded):
`python scripts\verify_dvc.py`. It runs `dvc init`, `dvc repro`, `dvc status`, deletes the outputs, runs `dvc checkout`, and checks that the restored `index.faiss` is byte-identical
and matches the hash recorded beside it. Passed on Linux in Stage 7B (about 11 s); **not yet run on Windows**.

Edit `params.yaml` to change backend / doc mode / model: `dvc repro` then reruns only when inputs or params changed. The stage's first command is the integrity check, so a drifted
frozen file stops the pipeline before anything is rebuilt. Without `sentence-transformers` or the cached model, the default (`minilm`) stage stops with an `ImportError` / "not in cache"
message after the integrity check and writes nothing.

**Remote storage (not configured, nothing uploaded).** `dvc push` / `dvc pull` need a remote, and the project has none. For a purely local setup use a folder **outside** the repository
(`dvc remote add -d local ..\smart-dvc-store`), or the git-ignored `dvc_storage/` inside it. Credentials for any cloud remote belong in `.dvc/config.local`, which is git-ignored; never
put them in `.dvc/config`. Pushing the index, the embedding cache or a checkpoint to a cloud service is a deliberate step that needs your approval.

**Do not commit a `dvc.lock` produced with a different backend.** A lock file records the params and hashes of the run that made it. One made with `embedding.backend: dev-lsa` does not
describe the committed `params.yaml` (`minilm`), so `dvc status` would report it as changed on every machine.

**Optional, later, needs approval: moving the checkpoint to DVC.** `git rm --cached results\siamese_bilstm.pt`, commit, `dvc add results\siamese_bilstm.pt`, commit the `.dvc` pointer, `dvc push`.
The bytes stay in Git history; only future versions would be kept out of Git.

**Evidence (sandbox, DVC 3.67):** with `embedding.backend: dev-lsa` (the dev-only offline embedder), `dvc repro` ran the integrity check and the build (666 x 192 vectors),
`dvc status` reported "up to date", deleting `data/retrieval/index` and `cache` and running `dvc checkout` restored them from the DVC cache, and the rebuilt `index.faiss`
sha256 (`ba1100af...b3b28`) equalled the one recorded in the repository. A 1 MB stand-in checkpoint (not tracked by Git) survived `dvc add` -> `dvc push` -> delete -> `dvc pull` with an identical
hash. **Stage 7B repeated the repro / status / checkout cycle in a fresh scratch repository after `dvc init`: same index hash (`ba1100af...`), `dvc status` up to date, outputs restored byte-identical,
and `dvc add` on a Git-tracked file refused.** **Not run:** the stage with the real MiniLM backend.
