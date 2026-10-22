"""Publication safety check for what is about to be committed (read-only; changes nothing, uploads nothing).

    python scripts/check_staged.py              check the STAGED changes (run it before every `git commit`)
    python scripts/check_staged.py --worktree   check everything `git add -A` WOULD add (tracked + untracked, honouring .gitignore), before staging anything

Fails (exit 1) on: a path that must never be published (secrets, environments, databases, model weights, indexes, archives, candidate sessions, MLflow/DVC local state),
a file over 50 MB (GitHub warns at 50 MB and rejects at 100 MB), a credential-shaped string, or a real Windows user name inside a path. Warns above 10 MB.
Exit 2 if it cannot run (not a Git repository)."""

import argparse
import fnmatch
import re
import subprocess
import sys
from collections import Counter

BLOCKED_SUFFIXES = {".pt", ".pth", ".safetensors", ".gguf", ".faiss", ".ckpt", ".onnx", ".db", ".sqlite", ".sqlite3", ".zip", ".pkl", ".npy", ".npz"}
ALLOWED_PATHS = {"results/siamese_bilstm.pt"}  # committed in the project's first commit; only reaches this check if it was modified
BLOCKED_PATTERNS = [
    ".env",
    "*/.env",
    ".env.*",
    "*/.env.*",
    "mlflow/*",
    "mlruns/*",
    "tmp/*",
    "Temp/*",
    "output/*",
    "results/demo_sessions/*",
    ".dvc/cache/*",
    ".dvc/tmp/*",
    ".dvc/config.local",
    "dvc_storage/*",
    "data/retrieval/index/*",
    "data/retrieval/cache/*",
    "data/evaluation/*/screenshots/*",
    "*/node_modules/*",
    "node_modules/*",
    "*/__pycache__/*",
    "__pycache__/*",
    ".venv/*",
    "venv/*",
    ".bot/*",
    "*_venv/*",
    ".agents/*",
    ".codex/*",
]
ENV_EXAMPLE = re.compile(r"(^|/)\.env\.example$")
SECRET_SHAPES = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]{10,}|sk-[A-Za-z0-9]{32,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{30,}"
    r"|xox[baprs]-[A-Za-z0-9\-]{10,}|hf_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
USER_PATH = re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}([^\\\s\"'<>|*?%{}]+)")
PLACEHOLDER_USERS = {"public", "default", "you", "yourname", "username", "user", "name", "all users"}
HARD_LIMIT, WARN_LIMIT, SCAN_LIMIT = 50_000_000, 10_000_000, 8_000_000


def git(*args, stdin=None):
    return subprocess.run(["git", *args], input=stdin, capture_output=True, check=True).stdout


def blocked_reason(path):
    if path in ALLOWED_PATHS or ENV_EXAMPLE.search(path):
        return None
    if any(fnmatch.fnmatch(path, pat) for pat in BLOCKED_PATTERNS):
        return "path that must never be published"
    suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    if suffix in BLOCKED_SUFFIXES:
        return f"{suffix} file (model weights, index, database or archive)"
    return None


def content_problems(data):
    if b"\0" in data[:4096] or len(data) > SCAN_LIMIT:
        return []
    text = data.decode("utf-8", errors="replace")
    out = []
    if SECRET_SHAPES.search(text):
        out.append("credential-shaped string")
    for m in USER_PATH.finditer(text):
        if m.group(1).lower() not in PLACEHOLDER_USERS:
            out.append(f"real Windows user name in a path ({m.group(0)[:30]})")
            break
    return out


def staged_files():
    names = [n.decode("utf-8", "replace") for n in git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split(b"\0") if n]
    if not names:
        return []
    out = git("cat-file", "--batch", stdin="".join(f":{n}\n" for n in names).encode("utf-8"))
    files, pos = [], 0
    for n in names:
        eol = out.index(b"\n", pos)
        header = out[pos:eol].split()
        if len(header) < 3:  # "<name> missing"
            pos = eol + 1
            continue
        size = int(header[2])
        files.append((n, out[eol + 1 : eol + 1 + size]))
        pos = eol + 1 + size + 1
    return files


def worktree_files():
    names = [n.decode("utf-8", "replace") for n in git("ls-files", "-z", "-c", "-o", "--exclude-standard").split(b"\0") if n]
    files = []
    for n in names:
        try:
            with open(n, "rb") as fh:
                files.append((n, fh.read()))
        except OSError:
            continue  # deleted but still listed
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--worktree", action="store_true", help="check everything `git add -A` would add instead of the staged changes")
    args = ap.parse_args(argv)
    try:
        files = worktree_files() if args.worktree else staged_files()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"cannot run: {e}")
        return 2
    problems, warnings, top, total = [], [], Counter(), 0
    for path, data in files:
        total += len(data)
        top[path.split("/")[0]] += len(data)
        reason = blocked_reason(path)
        if reason:
            problems.append(f"BLOCKED  {path}: {reason}")
        if len(data) > HARD_LIMIT:
            problems.append(f"TOO BIG  {path}: {len(data) / 1e6:.0f} MB (GitHub rejects files over 100 MB, warns over 50 MB)")
        elif len(data) > WARN_LIMIT:
            warnings.append(f"large    {path}: {len(data) / 1e6:.1f} MB")
        for p in content_problems(data):
            problems.append(f"CONTENT  {path}: {p}")
    scope = "everything `git add -A` would add" if args.worktree else "the staged changes"
    print(f"checked {len(files)} files, {total / 1e6:.1f} MB ({scope})")
    for k, v in top.most_common(8):
        print(f"  {v / 1e6:7.2f} MB  {k}")
    for w in warnings:
        print("WARN", w)
    for p in problems:
        print("FAIL", p)
    print(
        "PUBLICATION CHECK FAILED" if problems else "PUBLICATION CHECK OK - nothing blocked, nothing oversized, no credential-shaped strings, no personal paths"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
