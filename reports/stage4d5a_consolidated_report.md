# Stage 4D + 5A: consolidated report

Status: both missions done. Nothing here is human-validated. The frozen 3C-2 result (abstain rate 0.45 > 0.40, DO NOT ADVANCE) is untouched; freeze v2 verifies "no drift". No existing legacy score was changed.

## 1. What your real interview showed (audit)
- Indentation was **stored intact** in your session. The defects were presentation: code and prose shared one `<pre>` style, the textarea had no Tab handling, and the legacy comment ("That's a comprehensive, accurate response") looked like a verdict.
- The 51.3% on your correct linear regression is a **text-similarity** artefact (the scorer compares your code text with a reference solution's text; MiniLM also reads only ~256 word-pieces). It is not evidence the code was wrong.
- Dogfooding (honest note): I ran your two submitted answers through the new behaviour tests in a **throwaway cloud container with a trusted local subprocess, which is not a secure sandbox** (test-only runner). Both passed 5/5 behaviour tests and 4/4 structure checks. The NumPy answer mentions neither the memory trade-off nor cancellation (0/2 explanation topics); the regression question asks for no explanation. This is a check of the tests, not a grade.

## 2. Stage 4D: fixes
- Answers render as separate **code blocks** (monospace, `tab-size:4`, line numbers, no re-wrap, scroll inside the box) and **prose blocks**; tabs, CRLF and indentation survive; everything is autoescaped (tested with `<script>`/`<img onerror>`).
- Code questions get a monospace no-wrap box: Tab = 4 spaces, Shift+Tab outdents, Enter keeps/auto-indents after `:`, Esc then Tab leaves (no keyboard trap), toggle for any question.
- Legacy card relabelled: per-scorer "what this number is", "resemblance, not correctness", a code-specific note ("does not run your code"), and the generic text is labelled **Automatic comment, chosen only from the score band**.
- Summary overview has a Code check column; pending/interrupted/failed states are explicit; polling uses a single `pending` flag.
- Bug found by tests and fixed: a crashing code check could break answer submission; it now degrades to "Code check unavailable. Nothing was verified."

## 3. Stage 5A: code-evaluation prototype (`src/codeeval`, opt-in)
Layers: extract (code vs prose) -> static (`ast` only, policy gate) -> spec (data-driven requirements, registry by question id) -> harness (behaviour tests) -> runner (Disabled by default / Docker) -> evaluate. Specs: smi-h0029 (NumPy distances, 11 requirements) and smi-0462 (linear regression, 9). New questions = new `CodeSpec`, no hard-coded scores.
Output is **five buckets, no score**: verified correct, demonstrated in code text, missing, incorrect, unverified. Static reading can never produce "verified correct". Explanation topics are matched by wording only and are always "unverified". Keyword stuffing earns nothing verified (tested). Similarity is never used. Kept entirely separate from adaptive difficulty.

## 4. Safety and isolation assessment
- Flask never executes candidate code. Only `harness.py` calls `exec`, and it runs only inside a container. The default runner is **disabled**; the default web path performs static analysis only (tested: default flow does not even import the runner/harness).
- Static policy gate refuses execution for forbidden imports/names/attributes/file IO.
- Optional Docker runner (`SMART_CODEEVAL_EXEC=docker`): `--network none --ipc none --read-only` + noexec tmpfs, no mounts, no host env, `--cap-drop ALL`, no-new-privileges, user 65534, memory (= memory-swap), cpus, pids, ulimits, bounded wall-clock and output, `docker rm -f` on timeout, source via stdin. Pre-flight: daemon reachable, image present locally (never pulled), in-container isolation self-test; otherwise it falls back to disabled.
- **Not verified against a real daemon**: this environment has no Docker. Correct by construction and unit-tested (command flags, pre-flight, parsing), not proven. One integration test is skipped without Docker.
- Limits: a container shares the host kernel (a local single-user barrier, not multi-tenant); harness and candidate share one interpreter, so a hostile submission could tamper with its own results. An ordinary subprocess or timeout is not claimed to be a sandbox.

## 5. Tests
evaluation 426 passed/2 skipped; retrieval 137/1; app 173/5 (15 new in `test_stage4d_code.py`); codeeval 37/1; freeze v2 no drift. Browser: `stage4b_browser_journey.py` 31/31 (default server, regression); `stage4d_browser_journey.py` 25/25 (real keystrokes, escaping, indentation, refresh stability, export, mobile). Screenshots: `data/evaluation/stage4d/screenshots/` (screenshots use the word-overlap stand-in scorer, so the percentages in them are not real model scores).

## 6. Launch
Normal (unchanged, code check off):
`python main\app.py` then http://127.0.0.1:5000/demo/
Code check, read-only:
`set SMART_DEMO_CODE_EVAL=1` then `python main\app.py`; on the setup page tick "Experimental code check".
Sandboxed behaviour tests (optional): `docker build -t smart-codeeval:numpy docker\codeeval`, then also `set SMART_CODEEVAL_EXEC=docker` (`SMART_CODEEVAL_IMAGE` to rename). Without a passing pre-flight it stays read-only and says so.
Browser journey: `pip install playwright`, `playwright install chromium`, start `scripts/stage4a_demo_server.py --port 5056` with the flag, run `scripts/stage4d_browser_journey.py`.

## 7. Remaining deployment blockers
1. Docker path untested on a real daemon (do this on your Windows machine first).
2. For any hosted use: gVisor/Firecracker, harness in a separate process from candidate code, per-run workspaces, rate limits, auth.
3. Nothing is human-validated; code specs cover only 2 questions; explanation checks are wording-only.
4. Legacy scores are similarity, not grades; bilstm is weak on rephrased answers.
5. Single-user local persistence only.

## 8. Recommended next milestone
Run the Docker image on your machine and execute the real-daemon test; then have a human grade ~20 code answers for these two questions and compare against the bucket output (agreement table) before adding more specs.
