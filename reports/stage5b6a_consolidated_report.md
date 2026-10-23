# Stage 5B + 6A: consolidated report

**Status.** Engineering work complete. Nothing in this stage is human-validated; the frozen Stage 3C-2 experiment and its **DO NOT ADVANCE** decision are untouched (`stage3c2_freeze_v2.py verify`: no drift). No existing score was changed, no model was downloaded or trained, no Qwen benchmark was run, no candidate code was executed on the host.

**What I could not verify here (needs you).** The development environment is Linux with no Docker daemon, no PyTorch/Sentence-BERT, no Java and no Ollama, and it is not Windows. So: the Windows batch launchers, the real scorers, the real Docker sandbox and the live Ollama mode were **not run**. Section 8 gives the exact commands; `verify_windows.bat` automates them.

## 1. Mission A: real-environment reliability (5B)

### Defects found by the audit and fixed
| # | Finding | Fix | Test |
|---|---|---|---|
| 1 | The TF-IDF scorer's readiness check ignored its grammar dependency: `language-tool-python` is imported at module load, and its first use **downloads LanguageTool (hundreds of MB) and needs Java**. A web request could therefore trigger a download | `readiness("tfidf")` now requires the package and the LanguageTool cache (`LTP_PATH` / `~/.cache/language_tool_python`), with a precise reason and one-time fix | `test_tfidf_readiness_requires_the_grammar_checker_and_its_cache` |
| 2 | `requirements.txt` lacked `scikit-learn` (the TF-IDF scorer needs it) | Added `scikit-learn>=1.3.0` | `verify_windows.py` import checks |
| 3 | Docker interface passed a multi-line, double-quoted program as a `-c` argument: fragile through Windows command lines | One-line, quote-free base64 program | `test_program_argument_is_one_line_and_quote_free...` (also run through a local interpreter with a trivial harness) |
| 4 | Docker pre-flight did not check Linux-container mode (Windows-containers mode would fail confusingly) | `docker info` OS type must be `linux` | `test_non_linux_container_mode_keeps_execution_disabled` |
| 5 | A container could outlive the app if it was killed mid-run | In-container `timeout -s KILL 25`, and a `smart-codeeval=1` label for cleanup | flag test |
| 6 | Atomic session save could fail on Windows when a scanner holds the target (`os.replace` PermissionError) | Bounded retry | existing concurrency tests + `verify_windows.py` write check |
| 7 | (4D, re-verified) a crashing code checker or runner lookup could break submission | contained at engine level | `test_crashing_code_checker_at_every_layer_is_contained` |
| 8 | Prose answer box had `wrap="off"` (long lines scrolled sideways) | `wrap="off"` only for code questions | browser check + `test_prose_answer_box_wraps_and_code_box_does_not` |
| 9 | Duplicate evidence snippets in the code panel | de-duplicated | visual |

### Audit results (all verified by automated tests unless marked)
Start-up never trains or downloads (readiness probes; subprocess test asserts no torch/transformers import). Invalid or crashing code assessments cannot break a session. Answers, indentation, tabs, feedback, summaries and JSON export agree (byte-exact; control characters are removed on purpose). Repeated submission is an idempotent replay; a different resubmission is 409; refresh/restart/resume/delete/expired/malformed ids behave (E2E tests, real browser). Feature flags are off by default (catalog, setup page, 400 on request, import isolation, `verify_windows.py`). Advisory/unverified findings are never presented as confirmed: reading code cannot yield "verified correct", keyword stuffing earns nothing verified, explanation matches are labelled "mentioned (not verified)", and the generic comment is labelled "Automatic comment... not a check that your answer is correct".

### Code-execution security assessment
Full review in `docs/CODE_EXECUTION_SECURITY.md` (network, resources, filesystem, privileges, timeouts, temporary files, mounts/secrets, output limits, Windows compatibility, known weaknesses). Summary: **static-only remains the default and the recommendation.** The optional Docker path uses `--network none`, read-only root, noexec tmpfs, no mounts, no host env, all capabilities dropped, no-new-privileges, unprivileged user, memory/CPU/pids/ulimit limits, host and in-container time limits, bounded output, local image only (never pulled). It is **not** described as a production-grade sandbox: it shares the host kernel, harness and candidate share one interpreter (a hostile submission could forge a pass), and **isolation has not been demonstrated on a real daemon**. No public execution endpoint exists; the app binds to `127.0.0.1`. New structural tests assert that only `harness.py` may call `exec/eval/compile`, only `runner.py` starts processes (never with a shell), and no web layer imports the harness.

## 2. Mission B: portfolio-ready application (6A)
Flask retained; legacy routes and default behaviour unchanged.
- **Landing/setup:** the three result kinds (similarity score / modular evaluation / code check) shown side by side with their status; removed the duplicate step numbering; link to About.
- **About page** (`/demo/about`): accessible SVG diagram of the data flow, the RAG architecture **as implemented** (the interview app does not use vector search to pick questions), each evaluator with its limits, and what is and is not established.
- **Interview page:** progress, difficulty mix and current difficulty; code questions get a monospace no-wrap box with Tab/Shift+Tab/auto-indent and a keyboard escape; prose boxes wrap.
- **Feedback and summary:** score explanations per scorer, code-specific note, "Automatic comment" label, always-visible three-kind legend, overview with a code-check column, per-question cards where the explanation collapses to "What does this number mean?" to keep the summary readable, explicit pending/interrupted/failed states.
- **Accessibility/responsive:** skip link first, one `h1`, landmarks, labelled controls, `aria-current`, reduced-motion, dark mode, print stylesheet, `<noscript>` notice; no horizontal scroll at 390 px or 1280 px (checked in a real browser).

## 3. Mission C: documentation
`README.md` (replaces the older README; the legacy system is kept in a short section, its historic text remains in git), `docs/ARCHITECTURE.md`, `docs/CONFIGURATION.md` (every variable and default), `docs/WALKTHROUGH.md` (with screenshots), `docs/TROUBLESHOOTING.md`, `docs/CODE_EXECUTION_SECURITY.md`, `docker/codeeval/Dockerfile`, `run_demo.bat`, `verify_windows.bat`. Every capability described exists; no accuracy, benchmark-improvement or security guarantee is claimed. `run_demo.bat` is **written but untested on Windows**; the documented fallback is `python main\app.py`.

## 4. Mission D: tests (reproducible)
| Suite | Result |
|---|---|
| `tests/evaluation` | 426 passed, 2 skipped |
| `tests/retrieval` | 137 passed, 1 skipped |
| `tests/app` | 199 passed, 5 skipped (26 new in `test_stage5b_e2e.py`; 15 from 4D) |
| `tests/codeeval` | 42 passed, 1 skipped (real-Docker test skipped without a daemon) |
| Frozen experiment | `stage3c2_freeze_v2.py verify`: no drift |
| Browser, real Chromium | `stage6a_browser_journey.py` 48/48; `stage4d_browser_journey.py` 25/25; `stage4b_browser_journey.py` 31/31 |
| `verify_windows.py` in the Linux sandbox | 0 FAIL (WARNs are the packages and checkpoint that environment lacks) |

New E2E coverage: new interview, five-question completion, code-answer submission, static check, results display, persistence/restart/resume, failing scorer, failing/crashing code checker, feature isolation (including a clean subprocess import check), deletion, repeated/conflicting submissions, hostile text (script/img tags, template syntax, NUL/control characters, RTL override, SQL, 8k characters, emoji, fenced code with closing tags), hostile code in the code panel. The browser journey drives a five-question interview through the UI with typed code, plus a server with a failing scorer. Caveat: browser screenshots use the transparent word-overlap stand-in scorer, so their percentages are not model scores.

## 5. Screenshots
`data/evaluation/stage6a/screenshots/` (18 images: landing, About, prose and code questions, code box typing, both feedback kinds, summary desktop/dark/mobile, resume card, expired session, failed scorer, mobile pages). A subset is in `docs/screenshots/`.

## 6. Launch commands
```bat
.bot\Scripts\python.exe main\app.py                      :: http://127.0.0.1:5000/demo/
run_demo.bat                                              :: same, opens the browser (untested on Windows)
run_demo.bat --code-check                                 :: + experimental read-only code check
set SMART_DEMO_CODE_EVAL=1 & set SMART_CODEEVAL_EXEC=docker & .bot\Scripts\python.exe main\app.py   :: sandboxed tests (see security doc first)
```

## 7. Remaining blockers for public deployment
1. **Not human-validated:** no score matches human marking; the modular evaluator failed its gate (abstain 0.45 > 0.40).
2. **Code execution:** needs a stronger boundary (gVisor/Firecracker/throw-away VM), tests in a separate process from candidate code, quotas/rate limits. Untested on a real daemon.
3. **No authentication, accounts, multi-user storage, rate limiting, HTTPS or CSRF design;** sessions are single-user local files.
4. **Scorer limits:** similarity is not correctness; the Bi-LSTM is trained on near-exact positives; MiniLM truncates long text at about 256 word-pieces.
5. **Windows-specific behaviour and the one-click launcher unverified by the author;** real Sentence-BERT scoring was exercised only in your own five-question run (Stage 4D brief), not re-run here.
6. **Coverage:** code checks exist for 2 questions; 666-question bank; retrieval labels are AI-generated.

## 8. Run these on your machine (in order)
```bat
cd D:\Projects\SMART-MOCK-INTERVIEW
pip install -r requirements.txt                       :: picks up scikit-learn
verify_windows.bat --run-tests                        :: environment, readiness, in-process app test, all four suites
python main\app.py                                    :: in a second window; then:
verify_windows.bat --url http://127.0.0.1:5000        :: probes the running server
docker build -t smart-codeeval:numpy docker\codeeval  :: optional, only if you want the sandbox
verify_windows.bat --check-docker --docker-sample     :: runs ONLY this repository's own sample code in the container
verify_windows.bat --check-ollama                     :: optional
```
Paste any FAIL (or surprising WARN) output back.

## 9. Recommended next milestone
**Human-validation study of the default scorer and the code check**, before any more features: have one or two people grade ~40 answers (including the 2 code questions) with a simple rubric, then compare against similarity scores and code-check buckets (agreement table, with the failure cases). That gives the project its first evidence-based claim (or an honest negative). In parallel, run `verify_windows.bat --docker-sample` and decide whether the sandbox is worth keeping. Only then decide whether to continue the modular evaluator.

## 10. Files changed or added
Changed: `src/model/model_registry.py`, `src/codeeval/runner.py`, `src/demo/{engine,routes,store,codeassess}.py`, templates (`base`, `setup`, `interview`, `summary`, `_macros`, `_answer_eval`), `demo.css`, `demo.js`, `requirements.txt`, `README.md` (new content), `scripts/stage4b_browser_journey.py` (selector update). Added: `src/demo/templates/about.html`, `scripts/verify_windows.py`, `scripts/stage6a_browser_journey.py`, `run_demo.bat`, `verify_windows.bat`, `docs/*`, `tests/app/test_stage5b_e2e.py`, `tests/codeeval/test_no_exec_in_web_layers.py`, additions to `tests/codeeval/test_runner.py`, screenshots, this report.
