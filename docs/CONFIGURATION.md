# Configuration and feature flags

Everything is configured with environment variables; nothing needs a config file. In a Windows command prompt use `set NAME=value` before starting (it lasts for that window); in PowerShell use `$env:NAME="value"`. `run_demo.bat` sets the code-check flags for you via `--code-check` / `--docker`.

## Demo application

| Variable | Default | Effect |
|---|---|---|
| `SMART_HOST` | `127.0.0.1` | Interface to bind. Anything else (e.g. `0.0.0.0`) exposes candidate answers to your network. Do not do that casually |
| `SMART_PORT` | `5000` | Port |
| `SMART_DEBUG` | off | Werkzeug debugger/reloader. Off by default because the debugger allows code execution from the browser |
| `SMART_DEMO_DATA_DIR` | `results/demo_sessions` | Where session files are stored |
| `SMART_DEMO_HISTORY` | this computer only | The dashboard, history list and "delete all" are served only to requests from this computer. `1` allows other clients (for example a container with its port published to localhost only); `0` turns the history pages off. A single interview is always reachable from its own unguessable link |
| `SMART_DEMO_RETENTION_DAYS` | `14` | Session files older than this are deleted at start-up of the store |
| `SMART_DEMO_LEGACY_MODEL` | `bilstm` | Preferred default scorer (`bilstm`, `bert`, `tfidf`). If it is not ready, another ready scorer is preselected and the page says so |
| `SMART_DEMO_ALLOW_SCORER_SETUP` | off | `1` lets the demo train/download a missing scorer on first use. Off so a web request never starts a long job or a download |
| `SMART_RETRIEVAL_EXPOSE_REFERENCE` | off | `1` shows reference answers on the summary page |

## Experimental features (all off by default)

| Variable | Default | Effect |
|---|---|---|
| `SMART_DEMO_CODE_EVAL` | off | `1` adds the "Experimental code check" option to the setup page. Without it, a request for the code check is refused with HTTP 400, and the code-check modules are not even imported |
| `SMART_CODEEVAL_EXEC` | unset | `docker` requests sandboxed behaviour tests. Used only if the Docker pre-flight passes; otherwise the check stays read-only and says so. Any other value keeps execution disabled |
| `SMART_CODEEVAL_IMAGE` | `smart-codeeval:numpy` | Docker image to use. It must already exist locally; it is never pulled or built automatically |
| `SMART_DEMO_LIVE_MODULAR` | off | `1` offers the real-model modular evaluation (needs Ollama). The *mock verifier* mode, which tests the pipeline and says it measures nothing about answer quality, is always available |
| `SMART_DEMO_OLLAMA_HOST` / `OLLAMA_HOST` | `http://127.0.0.1:11434` | Where Ollama listens |
| `SMART_DEMO_QWEN_MODEL` | `qwen2.5:7b` | Model name for the live evaluator |
| `SMART_DEMO_RECORDED_RESULTS` | newest complete run | Path of the recorded experiment results shown at `/demo/recorded` |

### Building the optional code-check image (once, Docker Desktop in Linux-container mode)

```bat
docker build -t smart-codeeval:numpy docker\codeeval
set SMART_DEMO_CODE_EVAL=1
set SMART_CODEEVAL_EXEC=docker
.bot\Scripts\python.exe main\app.py
```

Check it first with `verify_windows.bat --check-docker`. Read [CODE_EXECUTION_SECURITY.md](CODE_EXECUTION_SECURITY.md) before using it: a container is not a production-grade sandbox.

## Retrieval and legacy application

| Variable | Default | Effect |
|---|---|---|
| `SMART_QUESTION_SOURCE` | `legacy` | `curated` makes the **legacy** API draw questions from the curated corpus |
| `SMART_RETRIEVAL_ENABLED` | off | `1` exposes `/api/retrieval/*` routes: `status`, `search`, `session-context` and (Stage 8B) `diagnostics`, which never returns reference answers even with `SMART_RETRIEVAL_EXPOSE_REFERENCE=1` |
| `SMART_RETRIEVAL_BACKEND` | `minilm` | Embedding backend |
| `SMART_RETRIEVAL_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `SMART_RETRIEVAL_LOCAL_ONLY` | on | Forbid network access when loading the embedding model |
| `SMART_RETRIEVAL_DOC_FORMAT` | `qk_concise` | Embedded text format (`qka`, `qk`, ...) |
| `SMART_RETRIEVAL_WARMUP` | off | Load the model and index in the background at start-up |

## LLM evaluator settings (experimental; used by `src/evaluation`)

| Variable | Default | Notes |
|---|---|---|
| `SMART_EVALUATION_BACKEND` | `legacy` | `llm` switches the *legacy* API's evaluation backend. Not used by the demo |
| `SMART_LLM_PROVIDER` | `none` | `ollama`, `mock`, or hosted providers |
| `SMART_LLM_MODEL` | none | Required for any real provider |
| `SMART_LLM_ALLOW_PAID` | off | A hosted (paid) provider cannot be built unless this is `1`. This project's runs use local Ollama only |
| `SMART_LLM_TIMEOUT_S`, `SMART_LLM_MAX_RETRIES`, `SMART_LLM_NUM_CTX` | 60, 2, 8192 | Bounded ranges are enforced |

## Verifying the defaults

`verify_windows.bat` reports each flag above as PASS when unset and checks, in a temporary session folder, that the code check and live evaluation are refused/hidden by default. Automated tests assert the same (`tests/app/test_stage5b_e2e.py::test_flags_are_genuinely_off_by_default` and the import-isolation test).

## Stage 6B variables (observability, packaging)

| Variable | Default | Effect |
|---|---|---|
| `SMART_FORBID_MODEL_TRAINING` | unset (set to `1` in the Docker image and compose file) | `1` makes the legacy Bi-LSTM scorer raise instead of training when no checkpoint exists. Unset keeps the legacy behaviour (trains on first use) |
| `SMART_JSON_LOGS` | `1` | JSON access-log formatter on the `smart.access` logger |
| `SMART_ACCESS_LOG` | `1` | `0` disables the per-request access-log line (metrics are still counted) |
| `SMART_METRICS_ENABLED` | `1` | `0` makes `GET /metrics` return 404 |
| `SMART_OBS_PROBE_OLLAMA` | `0` | `1` lets `/readyz` make a 1-second `GET /api/tags` call to Ollama |
| `SMART_GIT_COMMIT` | read from `.git` | Shown by `/healthz`; set by the Docker build argument |
| `MLFLOW_TRACKING_URI` | `sqlite:///<repo>/mlflow/mlflow.db` | Where `scripts/mlflow_*.py` store runs |
| `SMART_MLFLOW_ARTIFACTS` | `<repo>/mlflow/artifacts` | MLflow artifact root |
| `SMART_INSTALL_ML`, `SMART_PYTHON_IMAGE`, `SMART_PUBLISH_PORT`, `SMART_APP_MEM_LIMIT`, `OLLAMA_IMAGE` | see `.env.example` | Docker Compose only |
