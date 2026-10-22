# Troubleshooting

Start with `verify_windows.bat`: it checks most of the items below and prints the fix. Paste its output if you need help.

| Symptom | Likely cause | Fix |
|---|---|---|
| `run_demo.bat` says Flask is not installed | The virtual environment is missing or not the one used | `python -m venv .bot`, `.bot\Scripts\activate`, `pip install -r requirements.txt` |
| "Port 5000 is already in use" | The app (or another program) is already running | Open http://127.0.0.1:5000/demo/, or `set SMART_PORT=5001` and start again |
| Setup page says a scorer "needs one-time setup" | By design: scorers are never trained or downloaded in a web request | Run the one-time command shown (see README, Model setup), or pick a ready scorer. The interview works without one; scores then show as unavailable |
| First start after launching is slow | The scorer model is loading (Sentence-BERT / Bi-LSTM) | Wait; the page says so. Later interviews reuse it |
| `ModuleNotFoundError: faiss` / `torch` / `sentence_transformers` | Optional package not installed. The demo itself needs only Flask and flask-cors; each scorer needs its own packages | `pip install <package>`; `faiss-cpu` may need Python 3.10-3.12 |
| TF-IDF scorer unavailable | `language-tool-python` missing, Java missing, or LanguageTool not downloaded yet | `pip install language-tool-python`, install Java, run the one-time command in the README |
| "Question bank unavailable" | The curated corpus failed its integrity checks or its files are missing | Run `python -m src.retrieval.cli manifest`; check `data\curated` and `data\expansion` are intact (they are verified by fingerprint) |
| "The question bank changed since this interview started" | The corpus was edited during a session | Start a new interview |
| Code check option is missing on the setup page | `SMART_DEMO_CODE_EVAL` is not set | `run_demo.bat --code-check` |
| Code check says "code NOT run" | Normal: read-only is the default | To run behaviour tests, see Configuration; requires Docker |
| Docker pre-flight fails | Docker Desktop not running, Windows-containers mode, image not built, or self-test failed (the message says which) | Start Docker Desktop; switch to Linux containers; `docker build -t smart-codeeval:numpy docker\codeeval`; rerun `verify_windows.bat --check-docker` |
| Leftover containers | The app was killed during a run | `docker rm -f $(docker ps -aq --filter label=smart-codeeval=1)` (PowerShell: `docker ps -aq --filter label=smart-codeeval=1 \| % { docker rm -f $_ }`) |
| "Experimental evaluation unavailable" | Ollama is not running or `qwen2.5:7b` is not installed | `ollama serve`; `ollama pull qwen2.5:7b` (large download, only for the experimental live mode); `verify_windows.bat --check-ollama` |
| Summary says "restored from a saved session" | Normal after a restart | None |
| "That interview could not be found" | Deleted, older than 14 days, or from another computer | Start a new interview |
| Unicode errors in the console | Windows code page | `chcp 65001`, or use PowerShell/Windows Terminal. The app's pages are unaffected |
| Browser tests fail to start | Playwright not installed | `pip install playwright` and `playwright install chromium` |
| Everything looks unstyled | An old cached page | Hard refresh (Ctrl+F5); the app sends `no-store` so this is rare |

If a session file looks corrupt, delete `results\demo_sessions\<id>.json`; nothing else depends on it.

## Docker, MLflow and CI (Stage 6B)

| Symptom | Cause and fix |
|---|---|
| `docker compose up` fails: "daemon not reachable" | Start Docker Desktop (WSL2 backend) and wait until it says "running" |
| Container is `unhealthy` | `docker compose logs app`; then `python scripts\healthcheck.py --ready` from the host. `/readyz` 503 means the corpus manifest or the session volume is not writable |
| Port 5000 already in use | set `SMART_PUBLISH_PORT=5001` in `.env` |
| Demo says "scorer not set up" inside Docker | expected in the lean image (no PyTorch / weights). Build with `SMART_INSTALL_ML=1` and provide a checkpoint/model volume, or run on the host with `python main\app.py` |
| Legacy `/api/start-interview` returns 400 "Failed to load questions" in Docker | the legacy default scorer needs PyTorch (same as above) |
| Live Qwen evaluation not offered | `SMART_DEMO_LIVE_MODULAR=1`, a reachable Ollama (`docker compose --profile ollama up`, or `SMART_DEMO_OLLAMA_HOST=http://host.docker.internal:11434` for Ollama on Windows) and the model pulled |
| `scripts\mlflow_import_history.py`: "MLflow is not installed" | `pip install -r requirements-mlops.txt` (the full package; `mlflow-skinny` has no SQL backend) |
| MLflow import raises `ImportDrift` | a frozen result file changed after it was imported. Do not use `--allow-drift`; find out why the file changed (`python scripts\check_integrity.py`) |
| `mlflow ui` port clash with the app | `mlflow ui --port 5001 --backend-store-uri sqlite:///mlflow/mlflow.db` |
| `check_integrity.py` reports DRIFT | a frozen file differs from its recorded hash. Restore it from Git; never regenerate a frozen manifest to make the check pass |
| `dvc repro` fails at the build step | the MiniLM model is not in the local Hugging Face cache (the stage never downloads). See docs/REPRODUCIBILITY.md |
| `check_integrity.py` fails on a **fresh Windows clone** and prints a CRLF HINT | Git converted line endings (`core.autocrlf=true`). Make sure `.gitattributes` is present, then `git config core.autocrlf false`, `git rm --cached -r -q .`, `git reset --hard` (commit or stash your work first). Never edit a manifest |
| `scripts\validate_windows.ps1` "cannot be loaded because running scripts is disabled" | run it as `powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1` (affects only that process) |
| `verify_compose.py`: "127.0.0.1:5099 is already in use" | `netstat -ano \| findstr :5099`, stop that process, or pass `--port 5100`. The script never uses the normal 5000 |
| `verify_compose.py`: "Docker daemon not reachable" | start Docker Desktop and wait for "Engine running"; with WSL2 backend run `wsl --status` if it never starts |
| `docker build` fails pulling `python:3.13-slim-bookworm` | no internet / Docker Hub rate limit / proxy: log in (`docker login`), or set `SMART_PYTHON_IMAGE` to a base you already have (must be Python 3.13) |
| `pip install --require-hashes` fails with "hashes do not match" or "no matching distribution" | you are on a Python version other than 3.12/3.13, or a platform without wheels for a pin. Use the looser `requirements*.txt`, or regenerate the lock (docs/MLOPS.md) |
| `verify_mlops.bat` window closes/blocks in automation | it ends with `pause`; set `SMART_NO_PAUSE=1` for unattended runs |
| GitHub: CI job `windows` fails on integrity | see the CRLF row above; check `git ls-files --eol data/curated` shows `w/lf` |
| `test_originals_are_byte_identical_to_checksums` fails after a commit or clone | a hash-pinned file with CRLF line endings was converted. `git check-attr text -- <file>` must say `unset`; add the file to the `-text` list at the end of `.gitattributes`, then `git add --renormalize <file>` and restore the original bytes from your backup or an earlier clone. Never edit the checksum file |
| `check_staged.py` prints `BLOCKED`, `TOO BIG` or `CONTENT` | something that must not be published is staged. `git restore --staged <path>` un-stages it without changing the file; for `CONTENT`, remove the credential or personal path first. The script only reads |
| `verify_dvc.py`: "cannot run" | needs `pip install "dvc>=3,<4"`, Git on PATH, and the project folder to be a Git repository (it copies what Git would publish) |
| `verify_dvc.py`: `dvc repro` fails at the integrity step | a frozen file differs from its pinned hash; fix that first (`python scripts\check_integrity.py` explains it). It never fails because of a missing MiniLM model: it uses the offline stand-in |
| `dvc add results\siamese_bilstm.pt` says it is already tracked by Git | expected: the checkpoint was committed in the first commit. Leave it in Git (3.8 MB); docs/REPRODUCIBILITY.md describes the optional move |

### Windows test failures seen in Stage 8C

| Symptom | Cause | Fix |
|---|---|---|
| `test_end_interview_is_async` / `test_full_curated_interview_and_report` end with HTTP 202 instead of 200 | an Ollama server was running on `127.0.0.1:11434`, so the background report job waited for the real model (up to 180 s) while the test polls for 10 s | fixed: `tests/app/conftest.py` points the report LLM at a refusing port. Tests no longer depend on a local Ollama |
| `test_heuristic_only_flag_true_in_sidecar...` / `test_human_review_flag_blocks_eligibility` raise `ScopeIntegrityError` | the test fixture wrote its sidecar with `write_text`, which turns `\n` into `\r\n` on Windows, so its sha256 no longer matched | fixed: the fixture writes exact bytes |
| `test_integrity_check_explains_crlf_checkouts` compares `data\curated\...` with `data/curated/...` | `check_integrity.crlf_files` returned OS-specific separators | fixed: `as_posix()` |
| `test_gitattributes_forces_lf...` says `run_all.bat must be CRLF` | `run_all.bat` was committed before `.gitattributes`, so this working copy kept LF (Git itself stores it as LF and would check it out as CRLF) | convert the working copy to CRLF; the file is not hash-pinned and `git diff` shows no change |
