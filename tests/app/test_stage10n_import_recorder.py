"""Stage 10N final repair: the import recorder used by the lazy-loading tests attributes imports correctly when the virtual environment lives INSIDE the project (the Windows `.bot` layout), however deep a
library's own import chain is, and still flags eager imports from application code."""
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

HELPERS = Path(__file__).resolve().parents[1] / "helpers"


def w(path: Path, text: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


@pytest.fixture()
def project(tmp_path):
    """A miniature project laid out like the Windows one: the venv's site-packages is under the project root, with a deep sentence_transformers -> torch import chain."""
    root = tmp_path / "SMART-PROJECT"
    sp = root / ".bot" / "Lib" / "site-packages"
    w(sp / "torch" / "__init__.py")
    w(sp / "torch" / "nn.py")
    w(sp / "sentence_transformers" / "__init__.py", "from . import sparse_encoder\nclass SentenceTransformer: pass\n")
    chain = ["sparse_encoder"] + [f"m{i}" for i in range(1, 7)]
    for a, b in zip(chain, chain[1:]):
        w(sp / "sentence_transformers" / a / "__init__.py" if a == "sparse_encoder" else sp / "sentence_transformers" / "sparse_encoder" / f"{a}.py", f"from . import {b}\n")
    w(sp / "sentence_transformers" / "sparse_encoder" / "m6.py", "import torch.nn\n")
    w(root / "src" / "__init__.py")
    w(root / "src" / "retrieval" / "__init__.py")
    w(root / "src" / "retrieval" / "loader.py", "def load():\n    import sentence_transformers\n    return sentence_transformers\n")
    w(root / "src" / "demo" / "__init__.py")
    w(root / "src" / "demo" / "eager.py", "import sentence_transformers\n")
    w(root / "src" / "demo" / "late.py", "def sneaky():\n    import faiss\n")
    w(sp / "faiss" / "__init__.py")
    return root, sp


def run(root, sp, body):
    code = f"import sys\nsys.path.insert(0, r'{HELPERS}')\nimport import_recorder as R\nR.install(r'{root}')\nsys.path[:0] = [r'{root}', r'{sp}']\n" + textwrap.dedent(body) + \
        "\nallowed, prohibited = R.classify(R.ATTEMPTS)\nprint('ALLOWED', len(allowed), 'PROHIBITED', len(prohibited), [n for n, _ in prohibited])\n"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(root))
    assert r.returncode == 0, r.stderr[-600:]
    return r.stdout.strip().splitlines()[-1]


def test_a_lazy_import_from_the_retrieval_layer_is_allowed_even_through_a_deep_library_chain_inside_the_project(project):
    root, sp = project
    out = run(root, sp, "import src.retrieval.loader as L\nassert not R.ATTEMPTS, 'importing the module must not load the stack'\nL.load()\n")
    assert "PROHIBITED 0" in out and "ALLOWED" in out and "ALLOWED 0" not in out, out


def test_importing_the_stack_from_other_application_code_at_import_time_is_prohibited(project):
    root, sp = project
    out = run(root, sp, "import src.demo.eager\n")
    assert "PROHIBITED 0" not in out and "sentence_transformers" in out, out


def test_importing_it_from_a_non_retrieval_function_later_is_prohibited(project):
    root, sp = project
    out = run(root, sp, "import src.demo.late as m\nm.sneaky()\n")
    assert "PROHIBITED 1" in out and "faiss" in out, out


def test_an_attempt_with_no_application_frame_is_prohibited(project):
    root, sp = project
    out = run(root, sp, "import torch\n")
    assert "PROHIBITED 1" in out and "torch" in out, out


def test_third_party_frames_inside_the_project_folder_are_not_application_code(project):
    root, sp = project
    out = run(root, sp, "import src.retrieval.loader as L\nL.load()\nimport import_recorder\nassert all(rel.startswith(('src/', 'main/')) for _, fr in R.ATTEMPTS for rel, _ in fr), R.ATTEMPTS\n")
    assert "PROHIBITED 0" in out, out
