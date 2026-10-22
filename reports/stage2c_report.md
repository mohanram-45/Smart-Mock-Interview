# Stage 2C report: safe retrieval integration

Date: 2026-10-14. Status: **Phases 2-5 done in the sandbox; Phase 1 blocked (needs one command on your PC). STOP for approval.**

## 1. What was built

| Piece | File |
|---|---|
| Flag + Blueprint + response metadata | `src/retrieval/flask_api.py` |
| Corpus/model/index service (lazy singleton, lock, BM25 fallback) | `src/retrieval/service.py` |
| Curated question provider (string ids, role-code aliases) | `src/retrieval/question_source.py` |
| Dependency-free provider contract + `QuestionSourceUnavailable` | `src/components/question_provider.py` |
| Edits to existing code | `main/app.py` (+22 lines), `src/components/interview_session.py` (optional `question_provider`; legacy branch untouched) |

Scoring, feedback, rounds and report code were **not touched**. The legacy path still reads `questions_cleaned.json`.

## 2. Feature flag behaviour (tested)

- Default `legacy`; env `SMART_QUESTION_SOURCE=curated` flips the default; `question_source` in the start request overrides it; the choice is locked per session (later env change does not move a running session).
- Invalid value (request or env) -> HTTP 400, never silently coerced.
- Sources are never mixed: legacy sessions have int ids, curated sessions `smi-NNNN` string ids, verified in one process alternating modes.
- Legacy responses are **byte-identical**: only curated responses gain `question_source`, `domain`, `difficulty`, `topic`.
- Legacy mode does not import faiss, torch, sentence-transformers or the service module (subprocess test).

## 3. Verification (before/after, not "files unchanged")

1. Before touching any route I wrote 24 characterisation tests against the unmodified app and recorded a golden transcript of a scripted 22-step scenario (all routes, error paths included): `tests/app/golden/legacy_baseline.json`, sha256 `87806315ec00d91a0d97a1fdc87075780fbea3614652dafb1a92df485a677212`.
2. After the integration the same transcript matches exactly.
3. Mutation check: deliberately leaking curated metadata into legacy responses made 3 characterisation tests fail; reverted, all pass. So the guard actually bites.

| Suite | Result |
|---|---|
| `tests/app` (Flask: 24 legacy characterisation + 53 curated/flag/failure) | **77 passed, 0 failed** |
| `tests/retrieval` (Stage 2A/2B) | **106 passed, 1 skipped** (skip = real-MiniLM test, needs the model) |

Covered: legacy compatibility, curated retrieval, domain + difficulty filtering, stable ids, quarantined exclusion (666 records, none quarantined), missing index (built), corrupt index (rebuilt once), unusable index and unavailable model (BM25 fallback, flagged, still curated records, interview still starts), corpus failure (503, no half-built session, legacy unaffected), repeated requests (15 searches, model/index loaded once, identical rankings), invalid inputs (11 bad bodies -> 400), no-answer semantics, flag switching, full curated interview through the report (string ids survive into the report), adaptive (tfidf) engine with curated.

## 4. Demonstration

`scripts/stage2c_demo.py` starts the real app over HTTP, shows the default legacy start (int id), then an explicit curated start, related-knowledge retrieval for the current question, the app's own answer path, next question, latency, and an invalid input. Output of the **sandbox run**: `reports/stage2c_demo_output_sandbox.txt`.

**That run used the dev-lsa stand-in embedder and a stub answer scorer (both labelled in the output). It demonstrates the integration, not MiniLM quality.** The real-MiniLM run is one command on your PC (section 8).

## 5. Latency / loading (sandbox, dev-lsa stand-in; real MiniLM numbers pending your run)

| | Value |
|---|---|
| Curated start-interview | 5.5 ms (corpus already loaded) |
| Cold first retrieval (stand-in model fit + index build) | 3.5 s |
| Warm search, engine / HTTP p50, p95 | 8.0 / 10.9 ms, 8.7 / 15.5 ms |
| Model + index loads over 50 requests | 1 |

Stage 2B real-MiniLM figures (Windows): mean 9.8 ms/query, 16.3 s cold embedding of the corpus, ~0.94 GB process memory. Expect the first curated retrieval after a cold start to take seconds, so `SMART_RETRIEVAL_WARMUP=1` is available.

## 6. Compatibility issues found

1. **Pre-existing legacy defect (not fixed, by design):** `ROLE_MAPPING` uses `ML/DL/DATA_ANALYSIS` but the legacy file uses `Machine Learning/Deep Learning/Data Analysis`. In legacy mode "Machine Learning Engineer" therefore only receives Python questions (test `test_known_defect_role_domain_codes...` documents it). Curated mode maps the codes to canonical domains, so roles behave as their names suggest. This means curated vs legacy differ materially for those roles; that is a behaviour change you opt into.
2. `POST /api/start-interview` without a JSON content-type returns 500 (415 swallowed by the blanket `except`). Pre-existing, recorded, untouched.
3. **Thin curated Hard pools**: questions per role (Easy/Medium/Hard): Data Scientist 104/284/45, ML Engineer 77/201/27, Data Analyst 28/75/17, NLP Engineer 11/35/7, Python Developer 12/27/6. Legacy has far more (e.g. NLP 170/349/130). The fixed engine wants 5/4/4; Python/NLP Hard has 6-7, and Deep Learning alone only 2 Hard (a DL-only custom interview gets a short Hard round; same existing "ask what's available" behaviour). No repeats occur within a session.
4. The tfidf scorer trains its vectorizer on the first corpus a process sees, so switching sources in one long-running process leaves it trained on the first source's answers (existing caching behaviour; scorer unchanged).

## 7. Phase 1 (truncation / provenance): not done, honestly

`audit/retrieval/model_provenance.py` has not been run on your PC (the output `data/retrieval/model_provenance.json` is absent), and this sandbox cannot load MiniLM. So **model revision, weights checksum, tokenizer config, measured token lengths and truncation impact are all still unmeasured.** The "about 60% of qka documents exceed 256 tokens" figure remains an estimate. I did not tune any no-answer threshold; the API has none by default and labels any explicit one as unvalidated. Recommendation: do not claim truncation is harmless until the measurement exists.

## 8. Remaining limitations

- Real MiniLM has not been run through Flask by me. Run on your PC (offline, from the project root):
  `python audit/retrieval/model_provenance.py` then `python scripts/stage2c_demo.py --backend minilm --model bert` (`bert` scorer = the app's existing Sentence-BERT; needs no training).
- Question *selection* in curated mode is domain/difficulty random sampling, as in legacy; MiniLM is used for knowledge retrieval, not to choose questions.
- Similarity scores from the app's scorers are not a validated measure of correctness; nothing here claims they are. No LLM grading was added.
- `/api/domains` and `/api/roles` still list the legacy codes; curated-only domains (Generative AI & RAG, MLOps) are reachable via `custom_domains` only.
- A failed model load is sticky until restart (avoids repeated slow failures); a transient failure needs a restart or `service.reset()`.
- AI-generated relevance labels (Stage 2B) still underpin the retrieval quality claims; no human review.
- In-memory sessions, single process; not a production deployment.

## 9. Verdict

Integration is safe to merge behind the flag, default off. Legacy behaviour is demonstrably unchanged. Not yet approved for enabling by default: Phase 1 measurement and a real-MiniLM run are outstanding.
