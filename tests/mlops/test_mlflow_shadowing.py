"""Stage 7B: the project keeps its local MLflow store in a folder named `mlflow/` in the repository root. Python can import a folder without __init__.py as an empty
namespace package, so on a machine where MLflow is NOT installed `find_spec("mlflow")` still succeeds. `tracking.available()` must not be fooled by that."""

import importlib.machinery
import importlib.util

from src.mlops import tracking


def test_a_folder_named_mlflow_is_not_mistaken_for_the_package(monkeypatch, tmp_path):
    namespace_spec = importlib.machinery.ModuleSpec("mlflow", None, is_package=True)  # what Python returns for ./mlflow/ with no __init__.py
    namespace_spec.submodule_search_locations = [str(tmp_path / "mlflow")]
    assert namespace_spec.origin is None
    real_find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a, **k: namespace_spec if name == "mlflow" else real_find_spec(name, *a, **k))
    assert tracking.available() is False
