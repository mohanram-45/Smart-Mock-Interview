# Stage 2A - RAG retrieval foundation

Additive package: `src/retrieval/`. It does not import or change the Flask app (`main/app.py`), the model registry
or any scorer. The app still reads `data/processed/questions_cleaned.json` exactly as before.

## What it does

```
data/curated/v5 (487, frozen)  ──┐
data/expansion/batch_01..04      ├─> corpus.load_corpus()  ──> 666 knowledge records + manifest/fingerprint
 (179, approved_batches.json)  ──┘        (validated against registry, manifests, fingerprints; quarantined excluded)
                                              │
                                    documents.build_documents(doc_mode)   searchable text  |  response metadata
                                         │                                         │
                       embeddings.embed_texts (SentenceTransformer, batched, cached, L2-normalised)
                                         │                                         │
                           index.VectorIndex (FAISS IndexFlatIP, persisted)      lexical.BM25
                                         └───────────── retriever.Semantic/LexicalRetriever ─────────────┐
                                                                                                          ▼
                                                       search(query, k, domain) -> hits with score + full record metadata
```

| Module | Responsibility |
|---|---|
| `corpus.py` | Read-only loader. Verifies v5 fingerprint, registry hashes, per-batch manifests/fingerprints, counts, ids, required fields; excludes quarantined ids; builds the corpus manifest and `corpus_sha256`. |
| `documents.py` | One document per record. `search_text` (embedded) is separate from `metadata` (the full record, returned with hits). Refuses anything that is not a reference-corpus record. |
| `embeddings.py` | `SentenceTransformerEmbedder` (default `sentence-transformers/all-MiniLM-L6-v2`, CPU), batching, dimension + unit-norm validation, content-addressed cache. |
| `embeddings_dev.py` | DEV-ONLY TF-IDF+SVD stand-in used where the model hub is unreachable. Never a substitute for MiniLM results. |
| `index.py` | `VectorIndex`: exact `IndexFlatIP`, stable id<->row mapping, domain filter (FAISS ID selector), atomic save, verified load, `ensure_index` (rebuild only when needed). |
| `lexical.py` | Okapi BM25 (no dependency), deterministic ties. |
| `retriever.py` | `SemanticRetriever`, `LexicalRetriever`; input validation. |
| `evaluate.py`, `benchmark.py` | Metrics (Success/Recall@k, MRR@10, nDCG@5), per-category/domain, no-answer analysis, latency, build time, index size; JSON + Markdown output. |
| `cli.py` | `build`, `search`, `demo`, `benchmark`, `manifest`. |

## What is embedded, and why

Embedded text per record (`doc_mode=qka`, the default): `topic`, `question`, `Key concepts: ...`, then the canonical answer.
* Question + concepts carry the topical signal for paraphrased questions; the answer adds vocabulary for concept-style queries.
* MiniLM truncates at its `max_seq_length` (256 word pieces), so the answer goes last: truncation drops the least informative tail.
* Alternative answers (`concise`, `practical`) are NOT embedded: they restate the canonical answer, and extra vectors would duplicate the same question. They stay in the returned metadata.
* Modes `q` and `qk` exist for ablation (see the Stage 2A report). The default was fixed before benchmarking.
* **Candidate answers are never reference knowledge.** `search_text` rejects any record whose provenance is not v5 or an approved batch; nothing in this package accepts user answers into the index.

## Setup

```
python -m venv .venv
.venv\Scripts\activate                      # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-rag.txt
python -m pytest tests/retrieval -q          # 81 tests (+ integration tests when SMART_RAG_TEST_MODEL is set)
```

The first use of `all-MiniLM-L6-v2` downloads about 90 MB from the Hugging Face hub into the local cache (`~/.cache/huggingface`);
the existing Sentence-BERT scorer already uses the same model, so it may already be cached on your machine (no duplicate install).
Use `--local-files-only` to forbid network access, or `--model <folder>` for a model downloaded elsewhere.

## Commands (run from the project root)

```
python -m src.retrieval.cli manifest                       # writes data/retrieval/corpus_manifest.json
python -m src.retrieval.cli build                          # embeds (cached) + builds/persists the FAISS index
python -m src.retrieval.cli demo                           # sample queries: semantic vs BM25, with answers
python -m src.retrieval.cli search "why is my model worse in production" -k 5 --domain "MLOps & Model Deployment"
python -m src.retrieval.cli benchmark                      # lexical vs semantic on the independent eval set
SMART_RAG_TEST_MODEL=sentence-transformers/all-MiniLM-L6-v2 SMART_RAG_TEST_SEMANTIC=1 python -m pytest tests/retrieval/test_st_integration.py
```

Index and cache live in `data/retrieval/index/` and `data/retrieval/cache/` (git-ignored, rebuildable). Index directories are
named by backend/model configuration and doc mode, so different models never overwrite each other.
`--backend dev-lsa` runs everything with the dev-only embedder (no model download).

## Rebuild rules

`ensure_index` loads the saved index only if ALL of these match, else rebuilds (atomically):
corpus fingerprint, record id order, embedder config (backend, model, dim, max_seq_length), doc_mode, and the
sha256 of `index.faiss`. The embedding cache is keyed by (embedder config, sha256 of text), so adding an approved batch
embeds only the new records, and any text or config change invalidates exactly the affected vectors.

## Result object

```
{"rank": 1, "score": 0.73, "question_id": "smi-m0038", "domain": "...",
 "record": {question_id, domain, topic, difficulty, question_type, question, canonical_answer, alternative_answers{},
            key_concepts[], common_mistakes[], rubric_points, tags[], verification{verification, v6_verification,
            human_reviewed(False), has_code_test, source_opened, code_executed, time_sensitive, review_by, remaining_limitations},
            sources[], provenance{origin, batch, batch_revision, dataset_fingerprint, plan_id, source_type, introduced_in}}}
```
Scores: cosine similarity in [-1, 1] for semantic; unbounded BM25 score for lexical (not comparable across queries).

## Limits to respect

* All reference answers are AI-generated and AI-reviewed. `human_reviewed` is always `False`. Do not treat retrieved answers as verified ground truth.
* 17 records are `time_sensitive` with a `review_by` date.
* Domain labels: eight, including `Generative AI & RAG` and `MLOps & Model Deployment` (not in the app's current role mapping `ROLE_MAPPING`). Stage 2B must decide how roles map to these domains.

## Stage 2B additions
- `hybrid.py` — experimental Reciprocal Rank Fusion of BM25 + semantic (`HybridRetriever`, `rrf_fuse`). Rank-based: the fused score is not a relevance confidence and cannot detect no-answer queries; use the `components` fields.
- `legacy_guard.py` — read-only proof that the approved corpus is disjoint from the 3,618 legacy boilerplate rows.
- Real MiniLM: `python -m src.retrieval.cli benchmark --backend minilm --model <local dir> --local-files-only` (reports `bm25_*`, `minilm_*`, `hybrid_minilm_*`).

## Stage 2C - feature-flagged Flask integration (`curated` question source)

Default is unchanged: `SMART_QUESTION_SOURCE=legacy` (or unset) runs the original code path and never imports faiss / torch.

```
POST /api/start-interview {"question_source": "curated"}   (or env SMART_QUESTION_SOURCE=curated; request value wins; locked per session)
        │
 flask_api.resolve_source / make_provider ──legacy──> None  ──> AdaptiveInterviewSession reads questions_cleaned.json (as before)
        │ curated
        ▼
 CuratedQuestionProvider(RetrievalService)  -> legacy-shaped dicts {id:"smi-0001", domain, difficulty, question, reference_answer, topic}
        │  (role codes ML/DL/DATA_ANALYSIS -> canonical domains, curated only)
        ▼
 AdaptiveInterviewSession (unchanged scoring / rounds / feedback / report)

GET  /api/retrieval/session-context?session_id=…&k=5   related knowledge for the current question (curated sessions only)
POST /api/retrieval/search {query,k,domain,difficulty,min_score}
GET  /api/retrieval/status                              (the last two are 404 unless curated mode or SMART_RETRIEVAL_ENABLED=1)
```

`service.RetrievalService` loads the corpus once (strict integrity check) and the model + FAISS index once, lazily (or at start-up with
`SMART_RETRIEVAL_WARMUP=1`), under a lock. Failure handling: corpus fails -> HTTP 503 (never falls back to legacy); model/faiss/index
unusable -> BM25 over the same curated records, flagged `mode: bm25_fallback` + `degraded_reason`; stale/corrupt index -> one rebuild.
No default no-answer threshold exists; an explicit `min_score` is applied to cosine scores only. Reference answers are redacted from HTTP
retrieval responses unless `SMART_RETRIEVAL_EXPOSE_REFERENCE=1`.

Env: `SMART_QUESTION_SOURCE`, `SMART_RETRIEVAL_ENABLED`, `SMART_RETRIEVAL_WARMUP`, `SMART_RETRIEVAL_EXPOSE_REFERENCE`,
`SMART_RETRIEVAL_BACKEND` (`minilm` default | `dev-lsa` tests/demo only), `SMART_RETRIEVAL_MODEL`, `SMART_RETRIEVAL_LOCAL_ONLY` (default `1`: never download on a request).
Tests: `python -m pytest tests/app tests/retrieval`.

## Stage 2C-final - selected document format: `qk_concise`

The service now embeds `qk_concise` by default: `topic`, `question`, `Key concepts: ...`, then **whole leading sentences of the existing
canonical answer** packed to a 254-token budget (real tokenizer; re-measured and trimmed, never silently truncated by the model).
No text is generated. Only the *embedded* text is shortened; the full canonical answer and all metadata stay in the corpus and come back
by `question_id`. Flags per record: `head_over_budget` (31 long scenario/code records: no answer sentence added, text still > 256 tokens),
`answer_cut` (15: first sentence cut at a word boundary), 36 records embed no answer sentence (31 + 5 with < 12 tokens left).

* Switch back: `SMART_RETRIEVAL_DOC_FORMAT=qka` (or `qk`). Allowed: `qk_concise`, `qka`, `qk`. Anything else raises at start-up.
* Index directories are keyed by doc mode; a mismatching index is never reused.
* The BM25 fallback always uses full `qka` text (no tokenizer needed). `/api/retrieval/status` reports `doc_mode` and `bm25_fallback_doc_mode`.
* Quality is **tied** with `qka` within noise (see `reports/stage2c_final_report.md`); the choice is engineering-driven, not a proven gain.
* Verify on a machine with the real model: `python scripts/stage2c_verify_flask.py` and `python -m pytest tests/app/test_real_minilm_flask.py -v`.
