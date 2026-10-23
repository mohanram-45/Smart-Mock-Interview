"""Regression: the retrieval package must import and run where the Unix-only `resource` module is absent (Windows)."""
import ast
import subprocess
import sys
import types
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[2] / "src" / "retrieval"
ROOT = PKG.parents[1]


def test_no_toplevel_unix_only_imports():
    for py in PKG.glob("*.py"):
        for node in ast.parse(py.read_text(encoding="utf-8")).body:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            assert not {"resource", "fcntl", "pwd", "grp", "termios"} & {n.split(".")[0] for n in names}, f"{py.name}: {names}"


def test_benchmark_imports_without_resource_module():
    """Simulates Windows: `import resource` raises ModuleNotFoundError (sys.modules entry None)."""
    code = ("import sys; sys.modules['resource'] = None\n"
            "import src.retrieval.benchmark as b\n"
            "v = b._rss_mb()\n"
            "assert v is None or v > 0, v\n"
            "print('ok', v)\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("ok")


def test_rss_falls_back_to_psutil_then_none(monkeypatch):
    from src.retrieval import benchmark as b
    monkeypatch.setitem(sys.modules, "resource", None)
    fake = types.ModuleType("psutil")

    class P:
        def memory_info(self):
            return types.SimpleNamespace(rss=200 * 1024 * 1024, peak_wset=300 * 1024 * 1024)

    fake.Process = P
    monkeypatch.setitem(sys.modules, "psutil", fake)
    assert b._rss_mb() == pytest.approx(300.0)  # Windows peak working set preferred
    monkeypatch.setitem(sys.modules, "psutil", None)
    assert b._rss_mb() is None  # neither available: metric omitted, no exception


def test_rss_uses_resource_when_present():
    pytest.importorskip("resource")
    from src.retrieval import benchmark as b
    assert b._rss_mb() > 0
