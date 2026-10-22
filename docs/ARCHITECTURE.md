# Architecture

This describes what is implemented. Where something exists but the demo does not use it, that is said explicitly.

## 1. Overview

**End-to-end workflow (demo).** Setup (role, difficulty, 3/5/8 questions) -> questions are drawn from the curated corpus by role/domain/difficulty -> the candidate answers one question at a time (code formatting is kept) -> each answer is stored in a local session file and passed to the **default similarity scorer** -> if the person opted in, also to the **modular evaluator** and/or the **code check** (separate panels, separate labels; a failure in either never interrupts the session) -> per-question feedback -> summary and JSON export -> optional deletion. Semantic retrieval (`/api/retrieval/*`) is a separate, opt-in surface over the same corpus.

```
                    curated question bank (666 records, read-only)
        data/curated/v5 (487, frozen) + data/expansion/batch_01..04 (179, approved)
                                   |
                     src/retrieval  corpus loader  (fingerprints, manifests, quarantine list)
                       |                                   |
         (opt-in /api/retrieval/*)                  records: question, reference answer,
         MiniLM embeddings -> FAISS + BM25                 key concepts, difficulty, domain
                                                           |
                                       src/demo  catalog.select_questions(role, domain, difficulty)
                                                           |
   browser  <-->  Flask blueprint /demo  <-->  DemoEngine  <-->  DemoStore (results/demo_sessions/<id>.json)
                                                           |
                              each submitted answer goes to three SEPARATE checks
          +----------------------------+-------------------------------+-----------------------------+
          | 1. similarity score        | 2. modular evaluation         | 3. code check               |
          |    (default)               |    (opt-in, experimental)     |    (opt-in, experimental)   |
          | src/model scorers          | src/evaluation + demo adapter | src/codeeval                |
          +----------------------------+-------------------------------+-----------------------------+
```

The three checks never feed each other, never feed question selection, and are shown in separate panels with separate labels.

## 2. Question retrieval ("the RAG part")

- **Corpus.** `src/retrieval/corpus.py` loads 666 records after verifying the frozen v5 fingerprint, per-batch manifests and a quarantine list. Candidate answers are never added to it.
- **Search (implemented, opt-in).** Records are embedded with `all-MiniLM-L6-v2` (text = topic, question, key concepts, then the reference answer; the model reads about 256 word-pieces, so long answers are truncated at the tail), stored in an exact FAISS `IndexFlatIP`, and compared with a pure-Python BM25 baseline. Exposed through `/api/retrieval/*` when `SMART_RETRIEVAL_ENABLED=1` or `SMART_QUESTION_SOURCE=curated`.
- **What the demo does.** It loads the records through the same loader and draws questions by **role, domain and difficulty**. It does not run vector search. The reference answer of the drawn record is what the similarity scorers compare against.
- **Measured quality.** Retrieval benchmarks (reports `stage2b_*`, `stage2c_*`) use AI-generated, pooled labels, not human ground truth, so they are indicative only.
- **Served format and truncation (Stage 8B audit).** The service embeds `qk_concise` (topic, question, key concepts, then whole leading answer sentences that fit 256 word-pieces; Stage 2C-final). Of 666 records the stored tokenizer run shows 31 whose head (topic + question + concepts) alone exceeds the limit and 15 whose first answer sentence had to be cut. The diagnostics report this per hit (`embedding_coverage`), measured with the model's own tokenizer when MiniLM is loaded and only approximated with the offline stand-in (labelled).
- **Evidence and provenance (Stage 8B).** `RetrievalService.diagnose()` / `POST /api/retrieval/diagnostics` (opt-in, same flag as search) return scores, rank, a BM25 cross-check, per-hit provenance (question id, corpus origin, corpus fingerprint, indexed format), the index/model/corpus fingerprints and whether the index matches the corpus. They never return reference answers, key concepts, question text or the query. The *evidence band* (`insufficient` < 0.40 <= `weak` < 0.45 <= `adequate` cosine) is descriptive and uncalibrated: on the stored MiniLM runs it flags 19/20 dev and 10/18 frozen-challenge no-answer queries (and 4/146, 1/40 answerable ones), so it never hides results. In BM25 fallback mode no band is computed.
- **Tested and not adopted.** Re-ranking the stored top-30 candidates by key-concept coverage did not beat plain cosine on the dev set; hybrid (RRF) fusion was already not consistently better (Stage 2C). `scripts/stage8_retrieval_probe.py` reproduces both numbers from stored rankings.

## 3. The interview app (`src/demo`)

| File | Role |
|---|---|
| `routes.py` | Flask blueprint at `/demo`: pages (setup, interview, summary, About, guide, recorded run), JSON API under `/demo/api`, export, security headers (CSP, nosniff, no-store) |
| `engine.py` | `DemoEngine`: creates sessions, validates answers, scores, replays identical resubmissions, builds summaries. One lock per session. Never trains or downloads a scorer in a request (`model_registry.readiness`) |
| `store.py` | One JSON file per session, atomic writes (with a Windows retry), 14-day retention, in-memory working set; a model or code job that was running at shutdown is shown as *interrupted* |
| `catalog.py` | Role to domain mapping and question selection |
| `present.py` | Splits an answer into code and prose blocks for display; no execution |
| `experimental.py`, `modular_adapter.py` | Lazy bridge to the modular evaluator (only imported if requested) |
| `codeassess.py` | Lazy bridge to `src/codeeval` (only imported if requested) |
| `templates/`, `static/` | Server-rendered Jinja pages (autoescaped), vanilla JS for form submission and polling, one CSS file |

Properties tested: refresh/back/forward show the right question; a stale tab cannot overwrite an answer (409); an identical resubmission replays the stored result; question id, answer and feedback stay associated; deleting removes the file; ids are validated before any file access.

## 4. Similarity scorers (`src/model`)

`model_registry` exposes three scorers with one interface, `score(reference, answer) -> 0..1`:

- **Siamese Bi-LSTM**, trained on this project's own question/answer pairs. It mostly saw near-exact positives, so it is strict with reworded answers.
- **Sentence-BERT**, cosine similarity of MiniLM embeddings. Reads only about the first 256 word-pieces of each text.
- **TF-IDF + grammar**, cosine similarity of TF-IDF vectors; the grammar check is not part of the number.

All three measure resemblance to the reference answer. `FeedbackGenerator` picks a comment from the score band; it does not read the answer.

## 5. Experimental modular evaluation (`src/evaluation`)

Opt-in. A verifier (a local qwen2.5:7b through Ollama, or a rule-based mock for pipeline tests) labels which required concepts an answer states, each with a quote. Fixed rules check the quotes against the answer and produce a rubric; a numeric score is emitted only for questions whose scope allows it and only with sufficient evidence, otherwise the result is advisory or an explicit abstention. Status: the recorded run failed its acceptance gate (abstain 0.45 > 0.40); the decision is **do not advance**, and the frozen experiment is protected by a fingerprint check (`scripts/stage3c2_freeze_v2.py verify`).

**Safeguards added around it in Stage 8B** (`modular/safeguards.py`, `demo/experimental.py`; the frozen pipeline files are untouched): invisible/format characters are stripped before segmentation (code indentation and newlines are kept); an instruction hidden with look-alike letters or split across lines, which the per-claim detector missed, withholds the numeric score (`possible_hidden_instruction`); an answer longer than the 20,000 characters the evaluator reads gets no number (`answer_truncated_not_fully_assessed`); a circuit breaker pauses the live model for 60 s after two consecutive provider failures so a stopped Ollama server does not stall every queued answer. Safeguards can only remove a number, never add or raise one. LLM scores still never feed adaptive difficulty. They fix input handling, not grading accuracy; a human validation plan is proposed in [EVALUATOR_VALIDATION_PROTOCOL.md](EVALUATOR_VALIDATION_PROTOCOL.md).

## 6. Experimental code check (`src/codeeval`)

```
answer text --extract--> code blocks + prose
code blocks --static (ast only)--> structure facts + policy gate (forbidden imports/names/IO)
spec (data-driven requirements per question) + static facts + prose --evaluate--> five buckets
(optional) policy-clean code --runner--> container --harness--> behaviour test results
```

- `extract.py` separates code from explanation (fenced blocks, whole-answer parse, line heuristics); indentation is never altered.
- `static.py` uses `ast` only. It reports what the code *contains* and refuses execution for forbidden constructs.
- `spec.py` / `specs_builtin.py`: requirements per question id (functional, structure, explanation). Two questions today: NumPy pairwise squared distances, and linear regression from scratch. Adding a question means adding a `CodeSpec`; no scores are hard-coded.
- `declarative.py` (Stage 8B): the same `CodeSpec` built from validated JSON (whitelisted structure rules, literal-only test cases, wording-only explanation topics) plus a generic `declarative_cases` harness, so a third question needs data rather than new Python. See [CODE_ASSESSMENT_SPECS.md](CODE_ASSESSMENT_SPECS.md). Cases reach the sandbox on stdin; nothing in the loader executes anything.
- `runner.py`: `DisabledRunner` by default. `DockerRunner` only with `SMART_CODEEVAL_EXEC=docker`, after a pre-flight. Candidate code is never executed in the Flask process. `harness.py` is the only file that calls `exec`, and it runs only inside the container.
- `evaluate.py` returns **five buckets** (verified correct, demonstrated in the code text, missing, incorrect, unverified) and **no score**. Reading code can never produce *verified correct*. Explanation topics are matched by wording and are always *unverified*. Keyword stuffing earns nothing verified (tested).

See [CODE_EXECUTION_SECURITY.md](CODE_EXECUTION_SECURITY.md) for the isolation review.

## 7. Persistence and privacy

Answers and the results shown are stored only in `results/demo_sessions/` on this computer (git-ignored), deleted after 14 days or on request. No reference answers are written to the session file. Nothing is sent anywhere; the only network use is by the optional pieces you enable (model downloads you run on purpose; Ollama on `127.0.0.1`).

## 8. Legacy application

`main/app.py` also serves the original adaptive API (`/api/*`), unchanged, over the 4,085-question knowledge base. The demo is mounted beside it at `/demo`. The legacy adaptive rounds use the similarity score; the demo does not adapt.

## 9. MLOps layer (Stage 6B)

```
 result files in Git (Stage 2C retrieval, 3B and 3C-2 evaluation)      corpus manifest + index metadata + freeze manifest
            |  src/mlops/historical.py  (copy verbatim, tag "imported_historical", store source sha256)
            v                                         |
   MLflow store  mlflow/mlflow.db (git-ignored)  <----+---- src/mlops/tracking.py  live_run(): standard tags + fingerprints
            ^
   scripts/mlflow_import_history.py --verify  ->  re-reads the sources, compares every metric, exit 1 on mismatch

 Flask app (main/app.py)
   src/mlops/obs.py      request hooks -> src/mlops/metrics.py (in-process counters; registered names only; sanitised labels)
                         JSON access log (route template, status, ms; never bodies / answers / ids)
                         /healthz  /readyz  /metrics        (legacy /health unchanged)
   src/demo/engine.py    counts scorer failures, abstentions, completions, code-check outcomes (outcome words only)

 packaging:  Dockerfile (lean, non-root, HEALTHCHECK)  +  docker-compose.yml (loopback only, read-only, optional ollama profile)
 CI:         .github/workflows/ci.yml (every PR, no GPU/Ollama/secrets/model downloads)  +  heavy.yml (manual / weekly)
 versioning: dvc.yaml  build_index  (index + embedding cache)   |   Git for everything else (the checkpoint stays in Git)
```

The web app never imports MLflow (a test walks the import graph); MLflow, DVC and Docker are developer-side tooling around the app, not part of a request. Counters are
per process. See [MLOPS.md](MLOPS.md) and [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

**Version consistency (Stage 8A).** `src/mlops/consistency.py` (`scripts/check_versions.py`, also run by `verify_mlops.py`, `validate_windows.ps1` and CI) checks that the committed corpus manifest, the corpus the code loads, `params.yaml` (what `dvc repro` builds) versus the format and model the application serves, every built index (corpus fingerprint and file hash), the frozen challenge queries and the stored Stage 2C rankings agree. It was added after finding `params.yaml` building `qka` while the application serves `qk_concise`. `scripts/mlflow_track_retrieval.py` records future retrieval evaluations as *live* MLflow runs (embedder config, index hash, evaluation-file hashes, label provenance) and refuses to run on a mismatch; imported historical runs keep their own tag and are never mixed in.

## Stage 11: objective follow-up engine (flag, default off)

`src/demo/intel.py` is an alternative engine for model-written follow-ups, selected by `SMART_DEMO_FOLLOWUP_ENGINE=objective` (default: the Stage 10N engine). Code decides ask or skip, the target concept and the memory attribution; the model only writes the question. It plugs into `LLMFollowUpGenerator.propose` and therefore into the same `engine._llm_followup` path, budgets, session-isolation check and provenance. See `docs/STAGE11_INTELLIGENCE_ARCHITECTURE.md` for the integration matrix, gates and how to evaluate it on Windows.
