"""Stage 7B: the helper parts of scripts/verify_dvc.py that do not need DVC installed (the full run is `python scripts/verify_dvc.py`)."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_dvc.py"
spec = importlib.util.spec_from_file_location("verify_dvc", SCRIPT)
verify_dvc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_dvc)


def test_set_backend_changes_only_the_backend_line():
    text = "embedding:\n  backend: minilm\n  doc_mode: qka\n  model: sentence-transformers/all-MiniLM-L6-v2\n"
    out = verify_dvc.set_backend(text)
    assert "  backend: dev-lsa\n" in out and "doc_mode: qka" in out and "all-MiniLM-L6-v2" in out and "minilm\n" not in out.split("model:")[0]


def test_set_backend_refuses_a_params_file_without_a_backend():
    with pytest.raises(ValueError):
        verify_dvc.set_backend("embedding:\n  doc_mode: qka\n")


def test_without_dvc_or_git_it_reports_instead_of_crashing(monkeypatch, capsys):
    def boom(*a, **k):
        raise FileNotFoundError("no such executable")

    monkeypatch.setattr(subprocess, "run", boom)
    assert verify_dvc.main([]) == 2
    assert "cannot run" in capsys.readouterr().out
