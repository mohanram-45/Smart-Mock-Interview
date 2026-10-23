"""Stage 7B: properties that must hold before this repository is published. Static, read-only checks of the working tree.

They exist because the first public update was audited by hand and several gaps were found (virtualenvs, DVC local config, generated indexes and a Windows user name
inside two provenance files were not protected). These tests keep them from coming back.
"""

import fnmatch
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# directories that are git-ignored (and docker-ignored) on purpose: never part of a clone, so never inspected here
_PRUNE = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".bot",
    "__pycache__",
    "mlflow",
    "mlruns",
    "tmp",
    "Temp",
    "output",
    ".ruff_cache",
    ".pytest_cache",
    ".dvc",
    "dvc_storage",
}
_BINARY_MODEL_SUFFIXES = {".pt", ".pth", ".safetensors", ".gguf", ".faiss", ".ckpt", ".onnx", ".db", ".sqlite", ".sqlite3"}
_ALLOWED_TRACKED_BINARIES = {"results/siamese_bilstm.pt"}  # committed in the project's first commit (3.8 MB); an ignore rule cannot untrack it
_TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".csv", ".txt", ".py", ".yml", ".yaml", ".toml", ".ps1", ".bat", ".html", ".js", ".css", ".cfg", ".lock", ".in"}
GITHUB_WARN_BYTES = 50 * 1000 * 1000  # GitHub warns above 50 MB and rejects above 100 MB per file; stay well under


def _walk():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if any(x in _PRUNE or x.endswith("_venv") for x in parts[:-1]) or (p.is_dir() and (p.name in _PRUNE or p.name.endswith("_venv"))):
            continue
        if parts[:2] == ("results", "demo_sessions") or (len(parts) > 3 and parts[:2] == ("data", "evaluation") and "screenshots" in parts):
            continue
        if parts[:3] in {("data", "retrieval", "index"), ("data", "retrieval", "cache")}:
            continue
        if p.is_file():
            yield rel.as_posix(), p


def _rules(name):
    return {ln.strip() for ln in (ROOT / name).read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}


def test_gitignore_protects_environments_dvc_local_config_and_generated_artifacts():
    required = {
        "*_venv/",
        ".dvc/config.local",
        "dvc_storage/",
        "*.faiss",
        "*.safetensors",
        "*.gguf",
        "*.pt",
        "*.pth",
        "*.db",
        "*.sqlite",
        "data/evaluation/**/screenshots/",
        "mlflow/",
        "results/demo_sessions/",
        ".env",
    }
    assert required <= _rules(".gitignore"), required - _rules(".gitignore")


def test_dockerignore_keeps_local_and_generated_material_out_of_the_build_context():
    required = {"*_venv", "tmp", ".dvc/config.local", "**/*.zip", "**/*.faiss", "**/*.db", "**/*.sqlite", "frontend/node_modules", "results", "mlflow"}
    assert required <= _rules(".dockerignore"), required - _rules(".dockerignore")


def test_no_model_weights_databases_or_oversized_files_outside_the_known_checkpoint():
    bad = []
    for rel, p in _walk():
        if p.suffix.lower() in _BINARY_MODEL_SUFFIXES and rel not in _ALLOWED_TRACKED_BINARIES:
            bad.append(f"{rel}: binary model/database artefact")
        elif p.stat().st_size > GITHUB_WARN_BYTES:
            bad.append(f"{rel}: {p.stat().st_size / 1e6:.0f} MB exceeds the GitHub warning size")
    assert not bad, bad


_USER_PATH = re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}([^\\\s\"'<>|*?%{}]+)")
_PLACEHOLDER = {"public", "default", "you", "yourname", "username", "user", "name", "<user>", "all users"}


def test_no_real_windows_user_name_in_publishable_text():
    """Regression: model_provenance.json and ollama_probe.json recorded C:\\Users\\<real name>\\... (now written as ~ by their producers)."""
    leaks = []
    for rel, p in _walk():
        if p.suffix.lower() not in _TEXT_SUFFIXES or p.stat().st_size > 8_000_000:
            continue
        for m in _USER_PATH.finditer(p.read_text(encoding="utf-8", errors="replace")):
            if m.group(1).lower() not in _PLACEHOLDER:
                leaks.append(f"{rel}: {m.group(0)[:40]}")
                break
    assert not leaks, leaks


def test_producers_of_the_two_provenance_files_redact_the_home_directory():
    for rel in ("audit/retrieval/model_provenance.py", "scripts/stage3b_probe_ollama.py"):
        assert "Path.home()" in (ROOT / rel).read_text(encoding="utf-8"), rel


_SECRET_SHAPES = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]{10,}|sk-[A-Za-z0-9]{32,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,}"
    r"|hf_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


def test_no_credential_shaped_strings_anywhere_in_publishable_text():
    hits = []
    for rel, p in _walk():
        if p.suffix.lower() in _TEXT_SUFFIXES and p.stat().st_size < 8_000_000 and _SECRET_SHAPES.search(p.read_text(encoding="utf-8", errors="replace")):
            hits.append(rel)
    assert not hits, hits


def test_dvc_local_only_files_cannot_be_committed_and_dvc_ignore_covers_screenshots():
    assert ".dvc/config.local" in _rules(".gitignore")
    assert "data/evaluation/**/screenshots" in _rules(".dvcignore")


def _text_attribute_is_unset(rel):
    """True if .gitattributes ends up with `-text` / `binary` for this path (the last matching line wins, like Git)."""
    state = None
    for raw in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pat, *attrs = line.split()
        target = rel if "/" in pat else rel.rsplit("/", 1)[-1]
        if not fnmatch.fnmatch(target, pat):
            continue
        for a in attrs:
            if a in ("-text", "binary"):
                state = "unset"
            elif a == "text" or a.startswith("text="):
                state = "set"
    return state == "unset"


def test_hash_pinned_files_stored_with_crlf_are_exempt_from_line_ending_conversion():
    """Regression (found by a fresh-clone simulation): retrieval_benchmark_minilm.* are pinned by sha256 over CRLF bytes; `* text=auto eol=lf` rewrote them on
    commit, so the published repository failed its own checksum test. Any CRLF text file whose sha256 is recorded in another file must be `-text`."""
    pin_files = [
        (r, p)
        for r, p in _walk()
        if p.suffix.lower() in {".json", ".txt", ".md", ".py"}
        and p.stat().st_size < 2_000_000
        and (re.search(r"sha256|manifest|freeze|checksum|hashes", p.name, re.I) or r.startswith(("tests/", "scripts/", "src/")))
    ]
    pin_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for _, p in pin_files)
    missing = []
    for rel, p in _walk():
        if p.suffix.lower() in {".bat", ".ps1", ".png", ".pt", ".lock"} or p.stat().st_size > 8_000_000:
            continue
        b = p.read_bytes()
        if b"\r\n" in b and b"\0" not in b and hashlib.sha256(b).hexdigest() in pin_text and not _text_attribute_is_unset(rel):
            missing.append(rel)
    assert not missing, f"add `-text` to .gitattributes for: {missing}"
