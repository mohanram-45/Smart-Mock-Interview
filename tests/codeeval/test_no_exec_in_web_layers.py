"""Structural guard: nothing in the web-facing or analysis code can execute candidate code. Only harness.py (run inside a container) may call exec/eval/compile,
and only runner.py may start processes."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = sorted(list((ROOT / "src" / "codeeval").glob("*.py")) + list((ROOT / "src" / "demo").glob("*.py")) + [ROOT / "main" / "app.py"])


def calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                yield f.id, n.lineno
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                yield f"{f.value.id}.{f.attr}", n.lineno


def test_only_the_container_harness_calls_exec_eval_or_compile():
    offenders = [(p.name, name, line) for p in FILES for name, line in calls(p) if name in ("exec", "eval", "compile", "builtins.exec", "builtins.eval") and p.name != "harness.py"]
    assert offenders == [], offenders


def test_only_the_runner_starts_processes_and_never_through_a_shell():
    bad = []
    for p in FILES:
        for name, line in calls(p):
            if name in ("os.system", "os.popen", "os.execv", "os.spawnl", "pty.spawn") or (name.startswith("subprocess.") and p.name != "runner.py"):
                bad.append((p.name, name, line))
    assert bad == [], bad
    src = (ROOT / "src" / "codeeval" / "runner.py").read_text(encoding="utf-8")
    assert "shell=True" not in src


def test_harness_is_never_imported_by_the_web_layers():
    for p in FILES:
        if p.name in ("harness.py",):
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            mod = n.module if isinstance(n, ast.ImportFrom) else None
            names = [a.name for a in n.names] if isinstance(n, (ast.Import, ast.ImportFrom)) else []
            assert "harness" not in (mod or "").split(".")[-1:] and not any(x.split(".")[-1] == "harness" for x in names) or p.name == "runner.py", p.name
