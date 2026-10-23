# Stage 10N: the final two Windows failures

**Direct Windows access: none** (no `D:` drive, no shared folder, no transfer mechanism in this sandbox), so this is a patch ZIP. **Windows verification: not done.**

## Failure 1: `test_the_suite_ranks_candidate_questions_with_bm25_only` (mode was "semantic")
**Root cause (reproduced):** test-order dependence in my autouse fixture, made worse by a side effect in `sim.bm25_search`. The fixture delegated to the real service whenever `retrieval.service._service is not None`, meaning "a test installed a stand-in". But `_service` is also filled lazily by any call to `get_service()`, and `sim.bm25_search` itself called `get_service()`, creating and caching the real default service (Sentence-BERT + FAISS where installed). After any earlier BM25 use, the fixture therefore sent ranking to the semantic service. On Linux the real service falls back to BM25 (no Sentence-BERT), which hid it. Reproduced by leaving a semantic-mode service in the singleton without `set_service`.
**Fix (test infrastructure only):**
- `tests/app/conftest.py`: the fixture records what a test installs through `set_service` and delegates only to that (explicit injection), never to whatever the singleton holds.
- `src/demo/sim.py`: `bm25_search` uses its own lexical-only service and no longer creates or touches the singleton. `sim` is used by the offline simulator and tests only.
Production retrieval is unchanged: `engine._service_search` still goes through the process-wide, semantic-capable service (a clean-process test pins that). Semantic search is not disabled anywhere; deliberately installed stand-ins still work (tested).

## Failure 2: `test_the_default_engine_loads_the_semantic_stack_lazily_and_only_through_retrieval`
1. **When the test expects loading:** never at import, engine build or static pages; at the first session creation only, and only from the retrieval layer.
2. **Imports before first retrieval?** The earlier diagnostic and the code say no: nothing is attempted before the first session.
3. **Did the test record correctly on Windows?** No, **a bug in my recorder.** It attributed an import to the last four stack frames whose path contained "SMART" or "src". On Windows the `.bot` venv is inside the project folder, so third-party frames (sentence_transformers importing `sparse_encoder` and its own submodules, then torch) counted as project code; a deep library chain pushed `src/retrieval` frames out of the last four and a legitimate lazy import was classed "outside retrieval".
4. **Genuine eager imports in production?** None found. A deliberately injected eager import in `engine._hints` still fails both tests (mutation-checked).
5. **Subprocess environment?** The child inherits the environment (`PYTHONPATH`, `SMART_*`); the cause here was path attribution, not inheritance.
**Fix (test-only):** new `tests/helpers/import_recorder.py` attributes by application packages only (`<root>/src`, `<root>/main`), uses all of their frames, and allows an attempt only when a `src/retrieval` frame (or `_service_search`) is on the stack; an attempt with no application frame is prohibited. The two 5b tests use it. Reproduced with a fake deep `sentence_transformers` chain inside a "SMART" path: old test failed, new passes.

## Files changed
`src/demo/sim.py`, `tests/app/conftest.py`, `tests/app/test_stage5b_e2e.py`, `tests/helpers/import_recorder.py` (new), `tests/app/test_stage10n_windows_repair.py` (4 new tests), `tests/app/test_stage10n_import_recorder.py` (new, 5 tests on a Windows-like layout with the venv under the project), this report.

## Results (Linux sandbox)
- The two target tests: pass, also with the fake in-project ML package on `PYTHONPATH`; both fail when an eager import is injected.
- New tests: 22 + 5 pass. Adjacent (`tests/app/test_stage10*`, curated integration, 9x, 4a, 5b): 608 passed. `tests/stage10` and `tests/retrieval`: 161 passed, 1 skipped. Ruff clean, integrity OK. Full suite not re-run, as requested.

## Limitations
Real Sentence-BERT/FAISS imports were not observed (not installed here); the Windows layout is emulated. Unchanged: follow-up quality rules, memory provenance, time budget, Ollama errors, frozen fixtures.
