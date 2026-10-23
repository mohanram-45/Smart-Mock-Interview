# Stage 10N: memory provenance failure (test C on Windows)

**Direct Windows access:** none. The sandbox has no `D:` drive and no shared folder, so the fix is delivered as a project-relative ZIP. Windows verification: **not done**; please re-run the focused tests there.

## Confirmed root cause
**A test-fixture assumption, not contamination, not a wrong turn.** The cited sentence "The main general-purpose deep learning frameworks today are PyTorch, TensorFlow (usually used through its Keras API) and JAX." is the opening of the **reference answer of bank question smi-0034** (`data/curated/v5`). The test's scripted candidate answers every technical question with the first third of that question's reference answer, so when the candidate-question order (Sentence-BERT ranking on Windows) reaches that question, the scripted candidate really *says* that sentence. Memory extraction stores it as a candidate statement (kind `explanation`) at the turn where it was said; the scripted model cited it; the test then required every cited quote to be inside the introduction at turn 1, which only held when the first citation happened to be the introduction.

Evidence:
- Direct reproduction: running the memory extractor on the scripted candidate's answer to smi-0034 stores one item, kind `explanation`, **turn = the answer's own turn (not 1)**, quote = that sentence, verbatim in the answer at that turn.
- The same mechanism already occurs in the sandbox with the default ranking: the second citation is a later statement (turn 6, "Split it into a model and an optimiser.", also a first-third-of-reference answer). The old assertion looked only at the first citation (the introduction), so it passed here and failed on Windows. Applying the old assertion to that sandbox citation fails; the new one passes.
- Memory is only ever written from `answers` of the current session (`M.update` in the submit path); reference text is never an input. A test confirms that when the candidate does not say the reference text, none of it is stored, and that nothing crosses sessions.

## What changed (production code: none)
No production change was needed: attribution, turn numbers and session isolation were already correct, and the meaningful-connection checks, 10N question-quality rules and semantic retrieval are untouched.
- `tests/app/test_stage10c_policy.py`: replaced `item["quote"] in INTRO and item["turn"] == 1` with a check against the **session history**, for **every** cited memory: the quote is verbatim in the candidate's answer at the recorded turn, it was said before the follow-up that cites it, and when the turn is 1 it is in INTRO. This is stricter about provenance than before, not looser.
- `tests/app/test_stage10n_memory_provenance.py` (11 tests, new): provenance of every stored and cited memory under four question orders (BM25, reversed, a front-loaded order, another seed) and across seeds and two roles; the Windows citation reproduced as a genuine later statement with its real turn; reference text the candidate did not say is never stored; no cross-session leakage.
- `reports/stage10n_memory_provenance_fix.md` (this file).

## Results (sandbox, Linux, no Sentence-BERT)
Full `pytest tests`: 1448 passed, 8 skipped, 0 failed. Ruff clean; integrity OK; versions 11 passed; mlops nothing failed. Frozen fixture untouched.

## Limitations
- Not run on Windows. I could not force the exact Windows question order (it depends on Sentence-BERT ranking), so the sandbox covers it with several orders and the direct extractor reproduction.
- A candidate who pastes reference text verbatim *is* recorded as having said it; that is correct attribution, and it stays labelled "candidate claim (not verified)".
