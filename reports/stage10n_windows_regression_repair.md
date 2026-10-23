# Stage 10N Windows regression repair

**Not verified on Windows.** All five failures pass in the Linux sandbox *before and after* my changes, so I reproduced the causes with stand-ins (below), fixed what could be shown to be wrong, and added a diagnostic that prints, on Windows, what that machine does for each failure. The Windows test run must be repeated. Nothing here claims Windows passes. No Stage 10O work, no new functionality, no benchmark was run, frozen fixture and labels untouched, no git operations.

Windows result reported: `tests/app` 639 passed, 5 failed. Sandbox after repair: `tests/app` 658 passed, 5 skipped; full suite 1436 passed, 8 skipped, 0 failed.

## 1. Root causes

**One shared environmental cause (A, C, D):** a `DemoEngine` built without its own ranking calls the process-wide retrieval service, which silently becomes **Sentence-BERT + FAISS wherever they are installed** (your `.bot` env) and is BM25 where they are not (the sandbox). I found and fixed the same trap in the offline simulator in 10M; the *test* helpers still had it. Consequences: (1) a different ranking picks different core questions, and the best memory to recall depends on the question; (2) the default engine imports torch/sentence_transformers/faiss at the first session. Previous-stage defect, not introduced by 10N: no 10N change touches retrieval, ranking or the memory selector.

| | Failure | Verdict | Confirmed or suspected |
|---|---|---|---|
| A | cross-turn memory: follow-up recalled "reported 91% accuracy", test wanted oral cancer / class imbalance | **Legitimate alternative grounding plus an order-dependent, over-narrow test.** | **Confirmed by reproduction:** with a cross-validation core question and an answer about accuracy, the sandbox code produces exactly your Windows text ("You mentioned a result earlier: reported 91% accuracy. How did you check that result held up…"). It quotes the candidate's own introduction sentence, hedged as "reported", attributed, hedged as a candidate claim. Which core question Windows asked I cannot see; that it was a different one is inferred from the ranking difference. |
| B | time budget: interview stayed `active` | **Real production defect (prior), exposed on Windows.** | **Confirmed by reproduction** (a short answer after the budget expired inserts a rule follow-up and the interview stays active). `_maybe_follow_up` never consulted the time budget; the wrap-up only removed *planned* questions, not the inserted follow-up. On Windows the semantic memory match produced a follow-up even for the strong answer; the sandbox's lexical match did not. |
| C | valid memory citation: `cited == []` | **Not a persistence or logging fault; the meaningful-connection rule working. The test's scripted model was non-adaptive.** | **Confirmed by reproduction:** when retrieval offers the accuracy claim or the class-imbalance challenge (not the project) and the model writes about the oral cancer project, the citation is dropped (`memory_stage: not_connected`) and no lead-in is attached. The requirement stays. |
| D | default journey imported torch, sentence_transformers, faiss | **Prior defect / outdated expectation, platform dependent.** | **Confirmed by import tracing:** the first session creation calls `_hints` → `_service_search` → `RetrievalService._load_semantic` → `make_embedder` → `import sentence_transformers`. Nothing is imported at app start, engine build or static pages. The sandbox passed only because the packages are absent. I cannot say whether it also failed on Windows before 10N (no earlier full `tests/app` Windows run is on file). |
| E | `DeadlineExceeded: no response within the deadline` for 127.0.0.1:9 | **Platform timing difference plus a real classification defect in the client.** | **Suspected cause, mechanism confirmed in code:** Windows retries the SYN to a closed local port for about two seconds before refusing, so the connect hit the 2 s connect window and the client reported it as a *response* deadline (`DeadlineExceeded`, a `ProviderTimeout`), while the test (and the API) expect `ProviderUnavailable`. I could not measure Windows' timing here. |

**Also found while reproducing C (a 10N regression, mine):** the 10N `BUILD ON` and `USE` prompt lines could push a memory prompt past its 3000-character limit for a long question (3030 characters in one case).

**ZIP audit:** the Stage 10N ZIP did not omit or replace any file changed in 10N: every file newer than the 10M ZIP was included (checked by name and content); the Windows files affected were the ones above, none missing. Stage 10N did not change policy, memory selection or retrieval.

## 2. Changed files and rationale
- `src/demo/engine.py`: `_budget_spent`; `_followup_wanted` and `_maybe_follow_up` refuse any follow-up (rule, memory, model) once the time budget is spent, and no model call is made. Within budget nothing changes (control test).
- `src/demo/ollama_stream.py`: connect and response phases separated. A refusal or a **connect timeout** is `ProviderUnavailable`; a timeout *after* connecting stays `DeadlineExceeded` (with partial metrics). No timeout is extended, no exception is swallowed; missing model (404) is unchanged.
- `src/demo/followup_llm.py`: `PROMPT_CHAR_LIMIT = 2900` with fixed-order trimming (BUILD ON, USE, previous questions, shorter question). TARGET, concepts, the answer and the EARLIER statement are never dropped. The 10N intelligence rules are untouched.
- `tests/app/conftest.py`: autouse `_hermetic_retrieval` (BM25-only ranking unless a test installs its own service or is marked `real_stack`; clears the two Sentence-BERT env switches). `pyproject.toml`: registers the `real_stack` marker.
- `scripts/stage10n_windows_repair_diag.py`, `.github/workflows/ci.yml` (smoke step), `docs/STAGE10_MODEL_AND_POLICY.md` section 15.

## 3. Tests added or updated, with reasons
**Added** `tests/app/test_stage10n_windows_repair.py` (18 tests): B (short answer, forced memory follow-up, no model call, control within budget); A (the achievement recall is grounded and attributed; never from another session); C (adaptive model is cited, an unconnected question keeps no citation, an unoffered or other-session id is never cited); prompt size (stress case, never drops the earlier statement or answer); suite ranks with BM25; no inherited SBERT env; E (connect timeout, refusal, post-connect deadline, generator falls back cleanly); the diagnostic runs. Each fix test was **mutation-checked**: reverting the fix makes it fail.

**Updated, with the contract change stated:**
- `test_stage5b_e2e`: the isolation test now builds the engine with `search_fn=bm25_search` and records every *attempt* to import torch/sentence_transformers/faiss (so a machine without them cannot hide a defect). It does not allow those imports. A new test pins the real contract: the **default** engine never touches them at import, build or static pages, and the first session may only through `src.retrieval` (lazy).
- `test_stage10a_memory` A: asserts the follow-up uses the cited statement's own words, is attributed and is a candidate claim, instead of requiring the oral-cancer words. The project is still the usual pick in the hermetic run.
- `test_stage10c_policy` C: the scripted model now builds its question from the statement it is offered (the prompt's USE line); the lead is checked against the cited item. The meaningful-connection requirement is **not** relaxed (see the new "unconnected keeps no citation" test).
- Not changed: the E test itself (the code now meets it).

## 4. Results in this environment
- The five tests directly: 5 passed (they also passed before the changes, which is why diagnosis used stand-ins).
- `pytest tests/app`: 658 passed, 5 skipped. Also with `SMART_DEMO_MEMORY_SBERT=1` exported: 658 passed.
- Stage 10 focused (`tests/app/test_stage10*.py`): 338 passed.
- Full `pytest tests`: 1436 passed, 8 skipped, 0 failed. `ruff` clean; `check_integrity` OK; `check_versions` 11 passed; `verify_mlops` 16 PASS, 3 INFO. Scripted benchmark 17/17 gates; the frozen fixture hash test passes. Validator pair rates unchanged (false acceptances 2/35, false rejections 16/32).
- With a stand-in semantic service installed (as an explicit test choice), the memory and 10N repair tests pass (54 of 55; the one failure is the new "ranks with BM25" test, which that stand-in overrides on purpose).
- Not run: Playwright browser tests (not installed here).

## 5. Windows-specific limitations
- No Sentence-BERT, FAISS, torch or Ollama here; Windows TCP timing for E and the real ranking for A/C were **not** observed. Real-ranking behaviour is now covered by diagnostics rather than by assertions.
- The hermetic fixture means unit tests no longer exercise Sentence-BERT ranking. That is intentional (unit tests must be platform-independent); real-ranking checks belong in `real_stack`-marked tests and the diagnostic.

## 6. Unresolved risks
1. If Windows still fails A or C, the diagnostic will say which statement was offered and why; I could not see that here.
2. The achievement recall wording ("a result earlier: reported 91% accuracy") is correct but slightly stiff.
3. D on Windows depends on the new subprocess import recorder behaving the same on Windows paths (it filters on file names, not separators).
4. Follow-ups are blocked only when the budget is *over*; during the "wrapping" window one more follow-up can still be added (existing contract, unchanged).
5. The 10N real-model evaluation still has not been run.

## 7. Windows procedure
1. Unzip `stage10n_windows_repair.zip` over the project root.
2. `.\.bot\Scripts\python.exe scripts\stage10n_windows_repair_diag.py` (add `--skip-real` to avoid loading Sentence-BERT). Send `tmp\stage10n_windows_repair_diag.json` if anything fails; it shows the environment, whether the two rankings agree, the first memory pick, the time-budget outcome, the citation stage, who imports the heavy packages, and how port 9 behaves.
3. `.\.bot\Scripts\python.exe -m pytest tests/app -q --tb=short`, then the five tests by name, then `python -m pytest tests -q`.
4. Only after that: the real-model evaluation.

**ZIP:** `stage10n_windows_repair.zip` holds only the changed files (listed in section 2 plus the new tests and report).
