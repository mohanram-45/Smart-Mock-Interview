"""Execution interface for behaviour tests. Candidate code is UNTRUSTED. Rules:

  * Candidate code is never executed in the Flask process, never with eval/exec in this project's processes, and never through a bare subprocess or a timeout alone
    (neither is a sandbox: a child process can still read your files, use the network and use your credentials).
  * The default is `DisabledRunner`: nothing runs, behaviour tests report "not run", and the assessment says so.
  * The only real backend is `DockerRunner`, enabled ONLY when SMART_CODEEVAL_EXEC=docker, and only after a pre-flight (daemon reachable, the image already present
    locally: nothing is ever pulled; an isolation self-test inside the container passes). If any step fails the runner reports itself disabled, with the reason.
  * The container gets: no network, a read-only root filesystem, a small noexec tmpfs, no host mounts, no environment from the host, all capabilities dropped,
    no-new-privileges, an unprivileged user, and hard limits on memory (no swap), CPU, processes, open files and file size. The code and the tests arrive on stdin.
    The host side bounds wall-clock time and output size, and force-removes the container on timeout.
  * A static policy gate runs first (static.py): submissions with forbidden imports or constructs are refused and never sent to any backend.

What this is NOT: a container shares the host kernel. It is a sensible barrier for a single user practising on their own machine; it is not sufficient for hosting
strangers' code. For that, use a stronger boundary (gVisor, Firecracker/microVMs, or a dedicated throw-away host) and a separate process for the tests.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_IMAGE = "smart-codeeval:numpy"          # built locally by the user; see docs in the report. Never pulled automatically.
LIMITS = {"memory": "256m", "cpus": "1", "pids": 64, "nofile": 64, "fsize_bytes": 1_000_000, "cpu_seconds": 15, "wall_seconds": 25, "max_output_bytes": 1_000_000, "tmpfs": "16m"}

_BOOTSTRAP = r"""
import sys, json
try:
    import resource
    for k, v in ((resource.RLIMIT_CPU, %(cpu)d), (resource.RLIMIT_FSIZE, %(fsize)d), (resource.RLIMIT_NOFILE, %(nofile)d), (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(k, (v, v))
except Exception:
    pass
p = json.loads(sys.stdin.read())
g = {"__name__": "harness"}
exec(compile(p["harness"], "<harness>", "exec"), g)
r = g["run"](p["harness_id"], p["source"], p.get("cases"))
sys.stdout.write("\n" + p["nonce"] + json.dumps(r) + "\n")
sys.stdout.flush()
"""

_SELFTEST = r"""
import json, os, socket
out = {}
try:
    socket.create_connection(("1.1.1.1", 53), timeout=2).close(); out["network_blocked"] = False
except Exception:
    out["network_blocked"] = True
try:
    open("/selftest_write", "w").close(); out["root_readonly"] = False
except Exception:
    out["root_readonly"] = True
out["no_host_env"] = not any(k.upper().endswith(("TOKEN", "SECRET", "KEY", "PASSWORD")) or k in ("HOME_HOST", "USERPROFILE") for k in os.environ)
out["not_root"] = (os.getuid() != 0) if hasattr(os, "getuid") else False
out["no_host_paths"] = not any(os.path.exists(p) for p in ("/host", "/Users", "/mnt/c", "/home/host"))
print("SELFTEST" + json.dumps(out))
"""


@dataclass
class ExecResult:
    status: str                       # "not_run" | "ok" | "refused" | "timeout" | "sandbox_error"
    reason: str = ""
    tests: List[Dict[str, Any]] = field(default_factory=list)
    load_error: Optional[str] = None
    backend: str = "none"
    limits: Dict[str, Any] = field(default_factory=dict)
    seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "reason": self.reason, "tests": self.tests, "load_error": self.load_error, "backend": self.backend, "limits": self.limits, "seconds": round(self.seconds, 2)}


class Runner:
    name = "none"
    sandboxed = False

    def available(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def run(self, harness_id: str, source: str, cases: Optional[List[Dict[str, Any]]] = None) -> ExecResult:
        raise NotImplementedError


class DisabledRunner(Runner):
    """The default. Never executes anything."""
    name = "disabled"

    def __init__(self, reason: str = "Code execution is disabled (the default). Behaviour tests were not run."):
        self.reason = reason

    def available(self) -> Tuple[bool, str]:
        return False, self.reason

    def run(self, harness_id: str, source: str, cases: Optional[List[Dict[str, Any]]] = None) -> ExecResult:
        return ExecResult("not_run", self.reason, backend=self.name)


def _oneliner(code: str) -> str:
    """Wrap a program as a single-line, quote-free `python -c` argument (base64). Windows command lines mangle newlines and double quotes in arguments; this form
    passes through docker.exe untouched. The decoded program is still only ever run inside the container."""
    import base64
    return "import base64;exec(base64.b64decode('" + base64.b64encode(code.encode("utf-8")).decode("ascii") + "'))"


def _harness_source() -> str:
    return (Path(__file__).with_name("harness.py")).read_text(encoding="utf-8")


def build_docker_command(image: str, name: str, limits: Optional[Dict[str, Any]] = None, *, code: str = _BOOTSTRAP) -> List[str]:
    """The exact `docker run` argument list. Pure function so the isolation flags can be inspected and tested without Docker."""
    L = {**LIMITS, **(limits or {})}
    return ["docker", "run", "--rm", "-i", "--name", name,
            "--network", "none", "--ipc", "none",
            "--read-only", "--tmpfs", f"/tmp:rw,noexec,nosuid,nodev,size={L['tmpfs']}",
            "--memory", L["memory"], "--memory-swap", L["memory"], "--cpus", str(L["cpus"]), "--pids-limit", str(L["pids"]),
            "--ulimit", f"nofile={L['nofile']}:{L['nofile']}", "--ulimit", f"fsize={L['fsize_bytes']}:{L['fsize_bytes']}", "--ulimit", "core=0",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65534:65534",
            "--workdir", "/tmp", "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "HOME=/tmp", "--label", "smart-codeeval=1",
            image, "timeout", "-s", "KILL", str(L["wall_seconds"]),       # in-container wall-clock guard: a sleeping program is still ended even if the host side vanishes
            "python", "-I", "-c",
            _oneliner(code % {"cpu": L["cpu_seconds"], "fsize": L["fsize_bytes"], "nofile": L["nofile"]})]


def _bounded_run(cmd: Sequence[str], stdin_bytes: bytes, wall: float, max_out: int, kill_cmd: Optional[Sequence[str]]) -> Tuple[Optional[bytes], str]:
    """Run `cmd`, feed stdin, read at most max_out bytes of stdout, stop after `wall` seconds. stderr is discarded (it cannot block the child or fill our memory)."""
    p = subprocess.Popen(list(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    state = {"timeout": False}

    def kill():
        state["timeout"] = True
        if kill_cmd:
            try:
                subprocess.run(list(kill_cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            except Exception:
                pass
        try:
            p.kill()
        except Exception:
            pass

    timer = threading.Timer(wall, kill)
    timer.start()
    try:
        try:
            p.stdin.write(stdin_bytes); p.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        out = p.stdout.read(max_out + 1)
        if len(out) > max_out:
            kill()
            return None, "output_too_large"
        p.wait(timeout=5)
    except Exception:
        kill()
    finally:
        timer.cancel()
        try:
            p.kill()
        except Exception:
            pass
    if state["timeout"]:
        return None, "timeout"
    return out, "ok"


class DockerRunner(Runner):
    name = "docker"
    sandboxed = True

    def __init__(self, image: str = DEFAULT_IMAGE, limits: Optional[Dict[str, Any]] = None):
        self.image, self.limits = image, {**LIMITS, **(limits or {})}
        self._checked: Optional[Tuple[bool, str]] = None

    def _docker(self, args: Sequence[str], timeout: float = 15) -> subprocess.CompletedProcess:
        return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)

    def available(self) -> Tuple[bool, str]:
        """Pre-flight, cached. Reaches the daemon, requires the image locally (no pull), and runs the isolation self-test INSIDE a container built with the real flags."""
        if self._checked is not None:
            return self._checked
        try:
            if self._docker(["info", "--format", "{{.ServerVersion}}"], 10).returncode != 0:
                return self._set(False, "Docker is installed but its daemon is not reachable (is Docker Desktop running?).")
            osr = self._docker(["info", "--format", "{{.OSType}}"], 10)
            if osr.returncode != 0 or osr.stdout.strip().lower() != "linux":
                return self._set(False, "Docker is not in Linux-container mode (on Windows: Docker Desktop must use the WSL 2 / Linux containers engine). Execution stays disabled.")
            if self._docker(["image", "inspect", self.image], 10).returncode != 0:
                return self._set(False, f"The Docker image '{self.image}' is not present locally. It is never pulled automatically; build it once yourself (see the Stage 5A report).")
            name = "smart-selftest-" + secrets.token_hex(4)
            cmd = build_docker_command(self.image, name, self.limits, code=_SELFTEST.replace("%", "%%"))
            out, how = _bounded_run(cmd, b"", 30, 10_000, ["docker", "rm", "-f", name])
            line = next((l for l in (out or b"").decode("utf-8", "replace").splitlines() if l.startswith("SELFTEST")), "")
            res = json.loads(line[len("SELFTEST"):]) if line else {}
            failed = [k for k in ("network_blocked", "root_readonly", "not_root", "no_host_paths") if not res.get(k)]
            if how != "ok" or failed or not res:
                return self._set(False, "The isolation self-test did not pass (" + (", ".join(failed) or how) + "), so execution stays disabled.")
            return self._set(True, "Docker sandbox ready (self-test passed: no network, read-only filesystem, unprivileged user, no host paths).")
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            return self._set(False, f"Docker could not be used ({type(e).__name__}).")

    def _set(self, ok: bool, why: str) -> Tuple[bool, str]:
        self._checked = (ok, why)
        return self._checked

    def run(self, harness_id: str, source: str, cases: Optional[List[Dict[str, Any]]] = None) -> ExecResult:
        ok, why = self.available()
        if not ok:
            return ExecResult("not_run", why, backend=self.name)
        nonce = "SMARTRESULT" + secrets.token_hex(8) + ":"
        payload = json.dumps({"harness": _harness_source(), "harness_id": harness_id, "source": source, "cases": cases, "nonce": nonce}).encode("utf-8")
        name = "smart-codeeval-" + secrets.token_hex(6)
        cmd = build_docker_command(self.image, name, self.limits)
        t0 = time.time()
        out, how = _bounded_run(cmd, payload, self.limits["wall_seconds"], self.limits["max_output_bytes"], ["docker", "rm", "-f", name])
        secs = time.time() - t0
        lim = {k: self.limits[k] for k in ("memory", "cpus", "pids", "wall_seconds")}
        if how == "timeout":
            return ExecResult("timeout", f"The code ran longer than {self.limits['wall_seconds']} seconds and was stopped.", backend=self.name, limits=lim, seconds=secs)
        if how == "output_too_large":
            return ExecResult("sandbox_error", "The code produced too much output and was stopped.", backend=self.name, limits=lim, seconds=secs)
        text = (out or b"").decode("utf-8", "replace")
        line = next((l for l in reversed(text.splitlines()) if l.startswith(nonce)), None)
        if line is None:
            return ExecResult("sandbox_error", "No test result came back (the code may have crashed the interpreter, run out of memory or exited early).", backend=self.name, limits=lim, seconds=secs)
        try:
            data = json.loads(line[len(nonce):])
            tests = [t for t in data.get("tests", []) if isinstance(t, dict) and t.get("status") in ("passed", "failed", "error")]
            return ExecResult("ok", "", tests, data.get("load_error"), self.name, lim, secs)
        except ValueError:
            return ExecResult("sandbox_error", "The test result could not be read.", backend=self.name, limits=lim, seconds=secs)


def get_runner(env: Optional[Dict[str, str]] = None) -> Runner:
    """DisabledRunner unless SMART_CODEEVAL_EXEC=docker; the image comes from SMART_CODEEVAL_IMAGE. The returned runner may still report itself unavailable."""
    env = os.environ if env is None else env
    mode = (env.get("SMART_CODEEVAL_EXEC") or "").strip().lower()
    if mode == "docker":
        return DockerRunner(env.get("SMART_CODEEVAL_IMAGE") or DEFAULT_IMAGE)
    if mode:
        return DisabledRunner(f"Unknown SMART_CODEEVAL_EXEC value '{mode}': execution stays disabled.")
    return DisabledRunner()


_runner_cache: Dict[str, Runner] = {}


def shared_runner() -> Runner:
    """One runner per configuration, so the Docker pre-flight is not repeated for every answer."""
    key = f"{os.environ.get('SMART_CODEEVAL_EXEC', '')}|{os.environ.get('SMART_CODEEVAL_IMAGE', '')}"
    if key not in _runner_cache:
        _runner_cache.clear(); _runner_cache[key] = get_runner()
    return _runner_cache[key]
