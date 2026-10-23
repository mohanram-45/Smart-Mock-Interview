"""Test-only helpers for the code-assessment prototype.

`TrustedLocalRunner` runs the behaviour harness in an ordinary Python subprocess. That is NOT a sandbox and it must never run anything except fixtures written in this
repository (known-good and known-bad reference solutions). It lives in tests/ so application code can never import it. Real isolation is DockerRunner's job; its flags are
asserted here and it is skipped when Docker is not present."""
import json
import subprocess
import sys

import pytest

from src.codeeval.runner import ExecResult, Runner, _BOOTSTRAP, LIMITS, _harness_source


class TrustedLocalRunner(Runner):
    name = "trusted-local-fixtures-only"
    sandboxed = False

    def __init__(self):
        self.calls = []

    def available(self):
        return True, ""

    def run(self, harness_id, source, cases=None):
        self.calls.append(harness_id)
        nonce = "TESTRESULT:"
        payload = json.dumps({"harness": _harness_source(), "harness_id": harness_id, "source": source, "cases": cases, "nonce": nonce})
        code = _BOOTSTRAP % {"cpu": 15, "fsize": 1_000_000, "nofile": 256}
        try:
            p = subprocess.run([sys.executable, "-I", "-c", code], input=payload, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return ExecResult("timeout", "fixture timed out", backend=self.name)
        line = next((l for l in reversed(p.stdout.splitlines()) if l.startswith(nonce)), None)
        if line is None:
            return ExecResult("sandbox_error", "no result", backend=self.name)
        d = json.loads(line[len(nonce):])
        return ExecResult("ok", "", d["tests"], d["load_error"], self.name, {}, 0.0)


@pytest.fixture()
def trusted():
    return TrustedLocalRunner()
