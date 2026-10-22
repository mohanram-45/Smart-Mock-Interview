"""Legacy mode stays the default, Flask/app code does not import the modular package, and the legacy evaluator behaves as before."""
import os
import re
from pathlib import Path

from src.evaluation.config import BACKENDS, EvaluationConfig
from src.evaluation.evaluator import UNSUPPORTED_SCORE_CAP
from tests.evaluation.conftest import ACID, llm_json

ROOT = Path(__file__).resolve().parents[2]


def test_default_backend_is_still_legacy_and_backends_unchanged():
    assert BACKENDS == ("legacy", "llm")
    assert EvaluationConfig().backend == "legacy"


# Directories that are never active application source: scratch/backup copies, environments, generated or cached output, VCS data.
_NOT_ACTIVE = {".git", "tmp", "Temp", "output", "results", "mlflow", "mlruns", "node_modules", "__pycache__", "dvc_storage", ".dvc", ".bot", "site-packages",
               ".ruff_cache", ".pytest_cache", "build", "dist", "audit", "tests", "scripts", "backup", "backups"}
_FORBIDDEN = re.compile(r"evaluation\.modular|from \.modular|import modular")
# The ONE opt-in, lazily-importing bridge used by the /demo layer (see test_stage4a_demo.py for its isolation tests).
_ALLOWED_BRIDGE = "src/demo/experimental.py"


def _active_source_files(root: Path):
    """Python files of the active application: skips tests, scripts, audit evidence, the modular package itself, and anything that is a backup, environment,
    scratch (`tmp/`) or generated directory, however deep. Stage 8D: this used to be `ROOT.rglob("*.py")`, which also read backup copies placed under tmp/."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _NOT_ACTIVE and "venv" not in d.lower() and "backup" not in d.lower() and not d.startswith("stage8")]
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        if rel_dir == "src/evaluation/modular" or rel_dir.startswith("src/evaluation/modular/"):
            dirnames[:] = []
            continue
        for name in filenames:
            if name.endswith(".py"):
                yield (Path(dirpath) / name).relative_to(root).as_posix(), Path(dirpath) / name


def _modular_importers(root: Path):
    return [rel for rel, p in _active_source_files(root) if rel != _ALLOWED_BRIDGE and _FORBIDDEN.search(p.read_text(encoding="utf-8", errors="ignore"))]


def test_no_application_code_imports_the_modular_package():
    assert _modular_importers(ROOT) == []
    scanned = {rel for rel, _ in _active_source_files(ROOT)}
    assert "main/app.py" in scanned and "src/components/interview_session.py" in scanned   # the scan really covers the application


def test_backup_and_scratch_copies_do_not_cause_false_failures_but_real_modules_are_still_caught(tmp_path):
    """Stage 8D regression: a backup of an old file that imports the modular package, left under tmp/, failed the whole suite on a developer machine."""
    bad = "from src.evaluation.modular.pipeline import run\n"
    for rel in ("tmp/backup_7b/main/app.py", "tmp/stage8_backup/src/demo/x.py", "backups/old.py", "app_venv/Lib/site-packages/m.py", "mlops_venv/x.py", "results/gen.py",
                "scripts/tool.py", "tests/t.py", "src/evaluation/modular/inner.py"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(bad, encoding="utf-8")
    (tmp_path / "src/demo").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/demo/experimental.py").write_text(bad, encoding="utf-8")        # the allowed opt-in bridge
    assert _modular_importers(tmp_path) == []
    # a real application module that imports it is still detected, in each import spelling
    for spelling in ("from src.evaluation.modular import x", "import src.evaluation.modular.y", "from .modular import z"):
        (tmp_path / "src/components").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src/components/leak.py").write_text(spelling + "\n", encoding="utf-8")
        assert _modular_importers(tmp_path) == ["src/components/leak.py"], spelling
    (tmp_path / "src/components/leak.py").unlink()
    (tmp_path / "main").mkdir()
    (tmp_path / "main/app.py").write_text(bad, encoding="utf-8")
    assert _modular_importers(tmp_path) == ["main/app.py"]


def test_legacy_modules_do_not_depend_on_the_modular_package():
    for f in (ROOT / "src" / "evaluation").glob("*.py"):
        assert "modular" not in f.read_text(encoding="utf-8"), f.name


def test_legacy_evaluator_still_caps_when_no_concept_is_verified(evaluator_for, make_req):
    ev = evaluator_for(llm_json((4, 4, 4, 4)))
    res = ev.evaluate(make_req(ACID, "It keeps database transactions safe."))
    assert UNSUPPORTED_SCORE_CAP == 30
    assert res.provisional_score is not None and res.provisional_score <= UNSUPPORTED_SCORE_CAP
