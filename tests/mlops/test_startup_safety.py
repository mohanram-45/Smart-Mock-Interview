"""Stage 6B: start-up and health probing must never train, download or load a model, and the new MLOps modules must never execute code."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_startup_and_probes_do_not_load_or_train_any_model(tmp_path):
    code = r"""
import importlib.util, sys, os
os.environ["SMART_DEMO_DATA_DIR"] = sys.argv[1]
os.environ["SMART_ACCESS_LOG"] = "0"
spec = importlib.util.spec_from_file_location("smart_app_probe", "main/app.py")
m = importlib.util.module_from_spec(spec); sys.modules["smart_app_probe"] = m; spec.loader.exec_module(m)
import model_registry as MR
def boom(*a, **k): raise AssertionError("a scorer was requested during start-up / probing")
MR.get_scorer = boom
for k in list(MR._ADAPTER_CLASSES): MR._ADAPTER_CLASSES[k] = boom
c = m.app.test_client()
for path in ("/", "/health", "/healthz", "/readyz", "/metrics", "/api/models", "/api/roles", "/demo/", "/demo/about", "/demo/guide"):
    r = c.get(path)
    assert r.status_code == 200, (path, r.status_code)
heavy = [x for x in ("torch", "transformers", "sentence_transformers", "faiss", "mlflow", "language_tool_python", "ollama") if x in sys.modules]
print("HEAVY", heavy)
"""
    p = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True, cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT)}
    )
    assert p.returncode == 0, p.stdout + p.stderr
    heavy = [ln for ln in p.stdout.splitlines() if ln.startswith("HEAVY")][0]
    assert heavy == "HEAVY []", f"start-up imported heavyweight packages: {heavy}"


@pytest.mark.parametrize("name", ["metrics.py", "obs.py", "version.py"])
def test_runtime_mlops_modules_never_execute_code_or_spawn_processes(name):
    tree = ast.parse((ROOT / "src/mlops" / name).read_text(encoding="utf-8"))
    banned_calls = {"exec", "eval", "compile", "__import__"}
    banned_modules = {"subprocess", "multiprocessing", "ctypes", "pickle", "marshal"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls, f"{name}: {node.func.id}()"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen", "spawn", "run", "Popen"}:
            owner = getattr(node.func.value, "id", "")
            assert owner not in {"os", "subprocess"}, f"{name}: {owner}.{node.func.attr}()"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            assert not any(m.split(".")[0] in banned_modules for m in mods), f"{name} imports a banned module"


def test_no_workflow_or_script_enables_docker_execution_automatically():
    for f in [*ROOT.glob(".github/workflows/*.yml"), ROOT / "docker-compose.yml", ROOT / "Dockerfile", ROOT / ".env.example", ROOT / "scripts/verify_mlops.py"]:
        text = f.read_text(encoding="utf-8")
        assert "SMART_CODEEVAL_EXEC=docker" not in text and 'SMART_CODEEVAL_EXEC: "docker"' not in text, f"{f.name} enables Docker code execution"


def test_integrity_check_explains_crlf_checkouts(tmp_path, monkeypatch):
    """Regression: a Windows clone with core.autocrlf=true changes the bytes of every hash-pinned file; the failure must say why."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("check_integrity", Path(__file__).resolve().parents[2] / "scripts/check_integrity.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "data/curated/v5").mkdir(parents=True)
    (tmp_path / "data/curated/v5/curated_questions.csv").write_bytes(b"a,b\r\n1,2\r\n")
    (tmp_path / "data/retrieval").mkdir(parents=True)
    (tmp_path / "data/retrieval/corpus_manifest.json").write_bytes(b'{"a": 1}\n')
    assert mod.crlf_files(tmp_path) == ["data/curated/v5/curated_questions.csv"]
    assert "core.autocrlf" in mod.CRLF_HINT and "hash-pinned" in mod.CRLF_HINT
    assert mod.crlf_files() == [], "the repository's own pinned files must be LF"
