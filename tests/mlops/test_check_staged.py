"""Stage 7B: scripts/check_staged.py, the pre-commit publication safety check, tested in throw-away Git repositories."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_staged.py"


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path):
    try:
        _git(tmp_path, "init", "-q")
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git is not available")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "core.autocrlf", "false")
    return tmp_path


def _run(repo, *args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _stage(repo, name, content=b"hello\n"):
    f = repo / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    _git(repo, "add", "-f", "--", name)


def test_clean_staged_files_pass(repo):
    _stage(repo, "src/app.py", "print('ok')\n")
    _stage(repo, ".env.example", "SMART_PORT=5000\n")
    _stage(repo, "docs/guide.md", "Install into C:\\Users\\<you>\\project or C:\\Users\\Public\\x\n")
    code, out = _run(repo)
    assert code == 0 and "PUBLICATION CHECK OK" in out, out


@pytest.mark.parametrize(
    "name",
    [
        ".env",
        "report_delivery/.env",
        "mlflow/mlflow.db",
        "results/demo_sessions/s1.json",
        "data/retrieval/index/x/index.faiss",
        "weights/model.safetensors",
        "bundle.zip",
        "mlops_venv/pyvenv.cfg",
        ".dvc/config.local",
        "data/evaluation/stage6a/screenshots/a.png",
    ],
)
def test_paths_that_must_never_be_published_are_blocked(repo, name):
    _stage(repo, name)
    code, out = _run(repo)
    assert code == 1 and "BLOCKED" in out, out


def test_credential_shaped_strings_and_real_user_paths_are_blocked(repo):
    _stage(repo, "a.txt", "key = " + "sk-ant-" + "a1B2c3D4" * 4 + "\n")
    _stage(repo, "b.md", "ollama is at C:" + "\\Users\\" + "jdoe" + "\\AppData\\Local\\Ollama\n")  # assembled at run time: this file must itself pass the scan
    code, out = _run(repo)
    assert code == 1 and "credential-shaped string" in out and "real Windows user name" in out, out


def test_oversized_files_fail_and_large_files_only_warn(repo):
    _stage(repo, "big/huge.bin", b"\0" * 51_000_000)
    code, out = _run(repo)
    assert code == 1 and "TOO BIG" in out, out
    _git(repo, "rm", "-q", "--cached", "big/huge.bin")
    _stage(repo, "big/ok.bin", b"\0" * 12_000_000)
    code, out = _run(repo)
    assert code == 0 and "WARN" in out and "large" in out, out


def test_the_already_tracked_checkpoint_is_allowed(repo):
    _stage(repo, "results/siamese_bilstm.pt", b"\0" * 1000)
    code, out = _run(repo)
    assert code == 0, out


def test_worktree_mode_honours_gitignore_and_sees_untracked_files(repo):
    (repo / ".gitignore").write_text("secret.db\n", encoding="utf-8")
    (repo / "secret.db").write_bytes(b"x")
    (repo / "notes.md").write_text("fine\n", encoding="utf-8")
    code, out = _run(repo, "--worktree")
    assert code == 0 and "checked 2 files" in out, out  # .gitignore + notes.md; the ignored database is not part of `git add -A`
    (repo / "leak.txt").write_text("token ghp_" + "A" * 36 + "\n", encoding="utf-8")
    code, out = _run(repo, "--worktree")
    assert code == 1 and "leak.txt" in out, out


def test_outside_a_repository_it_reports_instead_of_crashing(tmp_path):
    code, out = _run(tmp_path)
    assert code == 2 and "cannot run" in out, out
