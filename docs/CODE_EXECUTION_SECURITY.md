# Code-execution security assessment

**Bottom line.** The default and recommended mode is **static-only**: submitted code is parsed, never run. An optional Docker interface can run behaviour tests, but **a normal Docker container is not a production-grade secure sandbox**, and isolation has **not been demonstrated on a real Docker daemon by this project's author** (the development environment had none). Use it only for your own practice on your own machine. No public code-execution endpoint exists, and none should be built on this design.

## 1. Threat model

- **In scope:** a single user practising locally who pastes their own code, possibly copied from elsewhere, possibly containing mistakes (infinite loops, huge allocations) or accidental harm.
- **Out of scope:** hostile strangers submitting code to a hosted service. Nothing here is designed or sufficient for that.

## 2. What runs where

| Step | Process | Executes candidate code? |
|---|---|---|
| Split code from prose (`extract.py`) | Flask | No (text processing) |
| Static analysis and policy gate (`static.py`) | Flask | No (`ast.parse` only) |
| Requirement assessment (`evaluate.py`) | Flask | No |
| Behaviour tests (`harness.py`) | **Inside a container only** | Yes, only if `SMART_CODEEVAL_EXEC=docker` **and** the pre-flight passed **and** the policy gate passed |

Calls to `exec`/`eval`/`compile` exist only in `harness.py` (plus the bootstrap text in `runner.py`, which is a string that runs inside the container); only `runner.py` starts processes, never through a shell; and no web-facing module imports the harness. An AST-based test (`tests/codeeval/test_no_exec_in_web_layers.py`) enforces all three, another asserts the default flow does not import the runner/harness at all, and another that a submission with a top-level file write and `os.system` creates no file.

## 3. Review of the Docker interface

Command built by `build_docker_command` (a pure function; flags asserted in `tests/codeeval/test_runner.py`).

| Area | Control | Evidence | Residual risk / limits |
|---|---|---|---|
| **Network** | `--network none`, `--ipc none`; pre-flight self-test inside a container with the real flags tries to open a socket and must fail | Flags unit-tested; self-test runs on your machine at first use | Self-test is cached per server process. Isolation depends on Docker honouring the flag |
| **Resource limits** | `--memory 256m` with equal `--memory-swap`; `--cpus 1`; `--pids-limit 64`; `--ulimit nofile=64`, `fsize=1000000`, `core=0`; in-container `RLIMIT_CPU` 15 s; tmpfs 16 MB | Flags unit-tested | Limits bound the damage of a runaway program; they are not a security boundary. A pids limit of 64 stops fork bombs but not slow resource exhaustion by many sequential runs |
| **Filesystem** | `--read-only` root; `/tmp` is a `noexec,nosuid,nodev` tmpfs; working directory `/tmp`; `PYTHONDONTWRITEBYTECODE=1`; no volumes | Flags unit-tested; self-test checks root is read-only | The image's own files are readable (it is a generic Python image, no project data) |
| **Container privileges** | `--cap-drop ALL`, `--security-opt no-new-privileges`, `--user 65534:65534`, Docker's default seccomp profile, no `--privileged`, no devices, no `--pid host`, no `--userns host` | Flags unit-tested (forbidden flags asserted absent); self-test checks non-root | **Shares the host (or Docker Desktop VM) Linux kernel.** A kernel or runtime vulnerability could allow escape. This is the central limit of any container |
| **Timeouts and termination** | Host: wall-clock timer (25 s) kills the client and runs `docker rm -f <name>`. Container: `timeout -s KILL 25 python ...` guards the run even if the host side vanishes | Timer/kill logic unit-tested with fakes; `--docker-sample` hangs a sample on purpose on your machine | A hostile program can kill the in-container `timeout` (same user); the host timer still applies. If the whole app is killed mid-run, the in-container guard ends the container; containers are labelled `smart-codeeval=1` for manual cleanup |
| **Temporary files** | None on the host: source and harness travel on stdin; nothing is written to a mounted folder | Code inspection; no mounts in the command | tmpfs inside the container disappears with it (`--rm`) |
| **Host mounts and secrets** | No `-v/--mount`, no `--env-file`; only `PYTHONDONTWRITEBYTECODE` and `HOME=/tmp` are passed; the Docker socket is never mounted; the container has no network to reach host services | Flags unit-tested (only two `--env` entries) | Anyone who can run `docker` on a Linux host is effectively root there; on Windows, Docker Desktop's VM is the boundary |
| **Output limits** | Host reads at most 1 MB of stdout then kills; stderr is discarded (cannot block or fill memory); the result is read only from a nonce-prefixed line | Unit-tested (flood, forged line ignored) | A hostile program can read the nonce (see below) |
| **Image provenance** | The image must already exist locally; it is never pulled or built by the app (`docker image inspect` only) | Unit-tested | You build it from `docker/codeeval/Dockerfile` (`python:3.12-slim` + NumPy). Pin a digest if you want reproducibility |
| **Windows / Docker Desktop** | Command line passed to `docker.exe` is a single-line, quote-free base64 program (Windows mangles newlines/quotes); Linux-container mode is required (checked via `docker info`); `docker` must be on PATH | Argument shape unit-tested; the decoded program is compiled and run with a trivial harness on Linux | **Not run on Windows by the author.** `verify_windows.bat --check-docker --docker-sample` does it on your machine |

### Known weaknesses (not fixed, by design of the prototype)

1. **Shared kernel.** See above. Stronger boundaries (gVisor, Firecracker/microVMs, a throw-away VM) are required before any untrusted use.
2. **Harness and candidate share one interpreter.** A hostile submission can read the result nonce or monkeypatch the harness and report that its own code "passed". Consequently, under Docker, "verified correct" means *the harness reported a pass*; it is trustworthy for honest practice, not against an adversary. A hosted design needs the tests in a separate process/container that the candidate cannot influence.
3. **Behaviour tests are narrow.** They test a handful of inputs (listed in `harness.py`); passing them does not prove the code is correct for all inputs.
4. **Pre-flight is per process.** Docker's state can change after the check.
5. **Resource exhaustion by repetition.** There is no rate limiting; one worker thread serialises runs.
6. **Static policy gate is a filter, not proof.** It refuses obvious forbidden imports/names/attributes; it is not a complete analyser.

## 4. Verdict and operating rules

- Keep **static-only** as the default (it is). Do not set `SMART_CODEEVAL_EXEC=docker` unless you accept the limits above.
- The app binds to `127.0.0.1`. **Never expose it** (`SMART_HOST=0.0.0.0`) while the code check or Docker execution is enabled.
- Do not paste code you do not trust, even with Docker.
- Before any public deployment: separate untrusted-execution service, stronger isolation, authentication, quotas/rate limits, per-run ephemeral workspaces, independent security review.

## 5. What was and was not verified

| Claim | Status |
|---|---|
| Flask never executes candidate code; default path does not import the runner/harness/static modules | Verified by automated tests |
| Top-level side effects in a submission (file write, `os.system`) do not occur | Verified by automated test |
| `DockerRunner` refuses to start containers unless daemon, Linux mode, local image and self-test all pass; never pulls | Verified with fakes |
| Command carries every isolation flag and none of the forbidden ones | Verified by automated tests |
| Containers actually enforce the limits and network block | **Not verified here** (no Docker daemon in the development environment) |
| Works on Windows with Docker Desktop | **Not verified**; use the verification script |

## 6. Stage 9C addendum: integration status (no new execution capability)

- **Default is unchanged: static read only.** Without `SMART_DEMO_CODE_EVAL=1` there is no code panel; with it, candidate code is parsed, never run. `SMART_CODEEVAL_EXEC=docker` is the only way to run code, it is never set by default, and the Flask process never executes candidate code (a Docker run is a separate container process).
- **Specs are per question.** Only questions with a declared spec (`CA.spec_ids()`, 2 today) are assessed. Every other practical question returns `no_spec` and the UI says "No code check for this question"; nothing is guessed from similar questions.
- **Verified vs advisory** are different buckets in the UI: "verified correct / incorrect" appear only when behaviour tests actually ran in the sandbox; "found in the code", "mentioned" and similar are text-reading observations and are labelled "not verified". Similarity scores are never used for code.
- **Docker boundary review (repeated for 9C, nothing new verified):** the isolation flags in section 3 are asserted by unit tests against the command line only; no Docker daemon was available to test enforcement, so network blocking, memory/CPU/PID limits and read-only filesystem remain **unverified in practice**. The weaknesses in section 3 still apply: shared kernel; harness and candidate share one interpreter (a hostile submission can claim a pass); narrow tests; no rate limiting; the static gate is a filter, not proof.
- **Decision:** do not enable experimental local execution beyond the existing opt-in flag, and do not widen the spec set until (a) `verify_windows.bat --check-docker --docker-sample` passes on a real Docker Desktop and (b) harness and candidate are separated into different processes. Honest-practice use on localhost only.
