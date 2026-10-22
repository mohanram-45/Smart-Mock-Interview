"""Stage 5A safety tests: execution is off by default, the isolation flags are what they should be, the Docker backend refuses to run unless its pre-flight passes, and
the application never calls the behaviour harness directly. Docker itself is exercised only if a daemon and the image exist (skipped otherwise); the sandbox this was
developed in has neither, so the container path is verified by construction (flags, pre-flight logic), not by a real run."""
import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.codeeval import runner as R
from src.codeeval.evaluate import assess
from tests.codeeval import fixtures as F

ROOT = Path(__file__).resolve().parents[2]


def test_default_runner_is_disabled_and_nothing_is_spawned(monkeypatch):
    for k in ("SMART_CODEEVAL_EXEC", "SMART_CODEEVAL_IMAGE"):
        monkeypatch.delenv(k, raising=False)
    def boom(*a, **k): raise AssertionError("a process was started")
    monkeypatch.setattr(subprocess, "Popen", boom); monkeypatch.setattr(subprocess, "run", boom)
    r = R.get_runner()
    assert isinstance(r, R.DisabledRunner) and r.available()[0] is False
    out = assess("smi-h0029", F.NP_GOOD, r)
    assert out["executed"] is False and out["execution"]["status"] == "not_run"
    assert R.shared_runner().available()[0] is False
    assert isinstance(R.get_runner({"SMART_CODEEVAL_EXEC": "subprocess"}), R.DisabledRunner)       # unknown modes never enable anything
    assert isinstance(R.get_runner({"SMART_CODEEVAL_EXEC": "local"}), R.DisabledRunner)


def test_docker_only_when_explicitly_enabled():
    r = R.get_runner({"SMART_CODEEVAL_EXEC": "docker", "SMART_CODEEVAL_IMAGE": "my-image"})
    assert isinstance(r, R.DockerRunner) and r.image == "my-image"


def test_docker_command_carries_every_isolation_flag_and_no_host_access():
    cmd = R.build_docker_command("img:tag", "smart-x")
    s = " ".join(cmd[:cmd.index("img:tag")])
    for flag in ("--network none", "--ipc none", "--read-only", "--cap-drop ALL", "--security-opt no-new-privileges", "--user 65534:65534", "--pids-limit 64", "--memory 256m", "--memory-swap 256m", "--cpus 1",
                 "--ulimit nofile=64:64", "--ulimit core=0"):
        assert flag in s, flag
    assert "--tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m" in s
    for bad in ("-v", "--volume", "--mount", "--privileged", "--env-file", "--network host", "--pid host", "--cap-add", "--device", "-p", "--publish", "--userns host", "--add-host"):
        assert bad not in cmd, bad
    envs = [cmd[i + 1] for i, c in enumerate(cmd) if c == "--env"]
    assert sorted(envs) == ["HOME=/tmp", "PYTHONDONTWRITEBYTECODE=1"], "no environment from the host may be forwarded"
    assert cmd[cmd.index("img:tag") + 1:cmd.index("img:tag") + 7] == ["timeout", "-s", "KILL", "25", "python", "-I"] and cmd[0:3] == ["docker", "run", "--rm"]
    assert "--label" in cmd and "smart-codeeval=1" in cmd
    assert cmd.index("--memory") + 1 == cmd.index("256m") and R.LIMITS["memory"] == "256m"


def test_candidate_source_travels_on_stdin_never_on_the_command_line():
    payload_marker = "SECRET_CANDIDATE_TEXT_123"
    seen = {}
    class FakeP:
        stdin = type("S", (), {"write": lambda s, b: seen.setdefault("stdin", b), "close": lambda s: None})()
        stdout = type("O", (), {"read": lambda s, n: b""})()
        def wait(self, timeout=None): return 0
        def kill(self): pass
    import unittest.mock as m
    with m.patch.object(R.subprocess, "Popen", lambda cmd_, **k: seen.update(cmd=cmd_, kw=k) or FakeP()):
        R._bounded_run(["docker", "x"], payload_marker.encode(), 5, 100, None)
    assert payload_marker.encode() in seen["stdin"] and payload_marker not in " ".join(seen["cmd"])
    assert seen["kw"]["stderr"] == subprocess.DEVNULL


class _Fake:
    """Programmable replacement for subprocess.run used by DockerRunner pre-flight."""
    def __init__(self, info=0, image=0, ostype="linux"): self.info, self.image, self.ostype, self.calls = info, image, ostype, []
    def __call__(self, args, **k):
        self.calls.append(list(args))
        rc = self.info if args[1] == "info" else self.image if args[1:3] == ["image", "inspect"] else 0
        return subprocess.CompletedProcess(args, rc, self.ostype if args[1] == "info" else "", "")


def test_docker_unavailable_means_not_run_and_no_container_is_started(monkeypatch):
    fake = _Fake(info=1)
    monkeypatch.setattr(R.subprocess, "run", fake)
    started = []
    monkeypatch.setattr(R.subprocess, "Popen", lambda *a, **k: started.append(a) or (_ for _ in ()).throw(AssertionError("must not start")))
    d = R.DockerRunner("img")
    ok, why = d.available()
    assert ok is False and "daemon is not reachable" in why
    res = d.run("numpy_pairwise_sq_dists", F.NP_GOOD)
    assert res.status == "not_run" and started == []
    assert d.available() == (False, why) and len([c for c in fake.calls if c[1] == "info"]) == 1      # cached


def test_missing_image_is_never_pulled(monkeypatch):
    fake = _Fake(info=0, image=1)
    monkeypatch.setattr(R.subprocess, "run", fake)
    ok, why = R.DockerRunner("img").available()
    assert ok is False and "never pulled" in why
    assert not any(c[1] in ("pull", "build") or c[1:3] == ["image", "pull"] for c in fake.calls)


@pytest.mark.parametrize("selftest,failed", [({"network_blocked": False, "root_readonly": True, "not_root": True, "no_host_paths": True}, "network_blocked"),
                                             ({"network_blocked": True, "root_readonly": False, "not_root": True, "no_host_paths": True}, "root_readonly"),
                                             ({"network_blocked": True, "root_readonly": True, "not_root": False, "no_host_paths": True}, "not_root"), ({}, "ok")])
def test_failed_isolation_self_test_keeps_execution_disabled(monkeypatch, selftest, failed):
    monkeypatch.setattr(R.subprocess, "run", _Fake())
    monkeypatch.setattr(R, "_bounded_run", lambda *a, **k: (("SELFTEST" + json.dumps(selftest)).encode() if selftest else b"", "ok"))
    ok, why = R.DockerRunner("img").available()
    assert ok is False and "self-test did not pass" in why


def test_passing_self_test_enables_and_run_parses_only_the_nonce_line(monkeypatch):
    monkeypatch.setattr(R.subprocess, "run", _Fake())
    good = {"network_blocked": True, "root_readonly": True, "not_root": True, "no_host_paths": True}
    calls = []
    def fake_bounded(cmd, stdin, wall, maxo, kill):
        calls.append(cmd)
        if stdin == b"":
            return ("SELFTEST" + json.dumps(good)).encode(), "ok"
        nonce = json.loads(stdin)["nonce"]
        forged = "SMARTRESULTforged:" + json.dumps({"tests": [{"id": "x", "status": "passed", "detail": ""}]})
        real = nonce + json.dumps({"tests": [{"id": "expansion_example", "status": "failed", "detail": "d"}, {"id": "bogus", "status": "weird"}], "load_error": None})
        return (forged + "\n" + real + "\n").encode(), "ok"
    monkeypatch.setattr(R, "_bounded_run", fake_bounded)
    d = R.DockerRunner("img")
    assert d.available()[0] is True
    res = d.run("numpy_pairwise_sq_dists", "x = 1")
    assert res.status == "ok" and [t["id"] for t in res.tests] == ["expansion_example"] and res.tests[0]["status"] == "failed"    # forged line ignored, junk status dropped
    assert "--network" in calls[0] and "none" in calls[0]


def test_timeout_output_flood_and_missing_result_are_reported(monkeypatch):
    monkeypatch.setattr(R.subprocess, "run", _Fake())
    d = R.DockerRunner("img"); d._checked = (True, "ok")
    for how, status in (("timeout", "timeout"), ("output_too_large", "sandbox_error")):
        monkeypatch.setattr(R, "_bounded_run", lambda *a, _h=how, **k: (None, _h))
        assert d.run("numpy_pairwise_sq_dists", "x=1").status == status
    monkeypatch.setattr(R, "_bounded_run", lambda *a, **k: (b"nothing useful", "ok"))
    assert d.run("numpy_pairwise_sq_dists", "x=1").status == "sandbox_error"


def test_bounded_run_enforces_wall_clock_and_output_limits_on_harmless_commands():
    out, how = R._bounded_run([sys.executable, "-c", "import time; time.sleep(30)"], b"", 1.0, 1000, None)
    assert how == "timeout" and out is None
    out, how = R._bounded_run([sys.executable, "-c", "print('x' * 5_000_000)"], b"", 20, 1000, None)
    assert how == "output_too_large"
    out, how = R._bounded_run([sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"], b"abc", 20, 1000, None)
    assert how == "ok" and out.strip() == b"ABC"


@pytest.mark.skipif(not (shutil.which("docker") and os.environ.get("SMART_CODEEVAL_EXEC") == "docker"), reason="needs Docker, the local image and SMART_CODEEVAL_EXEC=docker")
def test_real_docker_sandbox_end_to_end():
    r = R.get_runner()
    ok, why = r.available()
    assert ok, why
    out = assess("smi-h0029", F.NP_GOOD, r)
    assert out["executed"] and out["summary"]["functional"].startswith("5 of 5")
    hostile = F.NP_GOOD.replace("import numpy as np", "import numpy as np\nwhile True:\n    pass")
    assert assess("smi-h0029", hostile, r)["execution"]["status"] == "timeout"


# ------------------------------------------------------------------------------------------------ the application never runs candidate code
def _calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


def test_only_the_harness_may_exec_and_nothing_in_the_app_imports_it():
    for p in (ROOT / "src" / "codeeval").glob("*.py"):
        found = _calls(p) & {"exec", "eval", "compile", "__import__", "open"}
        if p.name == "harness.py":
            assert found == {"exec", "compile"}, found                     # the harness is the one place, and it is only ever shipped into a container
        else:
            assert not found, (p.name, found)
    for p in list((ROOT / "src" / "demo").glob("*.py")) + [ROOT / "main" / "app.py"]:
        text = p.read_text(encoding="utf-8")
        assert "codeeval.harness" not in text and "from .harness" not in text and "import harness" not in text, p.name
        assert "_BOOTSTRAP" not in text and "TrustedLocalRunner" not in text, p.name
    for p in (ROOT / "src").rglob("*.py"):
        assert "TrustedLocalRunner" not in p.read_text(encoding="utf-8")


def test_importing_the_package_and_assessing_statically_never_imports_numpy_or_the_harness():
    code = ("import sys\nfrom src.codeeval.evaluate import assess\n"
            "r = assess('smi-h0029', 'import numpy as np\\ndef pairwise_sq_dists(A, B):\\n    return A @ B.T\\n')\n"
            "assert r['status'] == 'assessed' and not r['executed']\n"
            "bad = [m for m in ('numpy', 'src.codeeval.harness') if m in sys.modules]\nassert not bad, bad\n")
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env={**os.environ, "SMART_CODEEVAL_EXEC": ""})
    assert p.returncode == 0, p.stderr


def test_program_argument_is_one_line_and_quote_free_so_windows_cannot_mangle_it():
    cmd = R.build_docker_command("img:tag", "smart-x")
    arg = cmd[-1]
    assert "\n" not in arg and '"' not in arg and "\r" not in arg and len(arg) < 8000
    import base64, re
    inner = re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)", arg).group(1)
    prog = base64.b64decode(inner).decode()
    assert "RLIMIT_CPU" in prog and "exec(compile(" in prog and "15" in prog          # the same bootstrap, unchanged by the wrapping
    compile(prog, "<bootstrap>", "exec")                                                 # and it is valid Python


def test_non_linux_container_mode_keeps_execution_disabled(monkeypatch):
    monkeypatch.setattr(R.subprocess, "run", _Fake(ostype="windows"))
    ok, why = R.DockerRunner("img").available()
    assert ok is False and "Linux-container" in why
