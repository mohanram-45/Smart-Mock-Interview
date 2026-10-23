"""Prove that the DVC pipeline reproduces its declared outputs, WITHOUT touching your repository (Stage 7B).

    python scripts/verify_dvc.py            (needs: pip install "dvc>=3,<4" and the retrieval requirements: numpy, scikit-learn, faiss-cpu, pyyaml; git on PATH)

What it does, in a temporary copy of the project (your repository, `.dvc`, `dvc.lock` and `params.yaml` are never modified):
  1. copies the files Git would publish, `git init`s the copy and runs `dvc init`;
  2. switches `params.yaml` to the offline stand-in embedder (`dev-lsa`: no model, no download), because the real MiniLM model is not assumed to be present;
  3. `dvc repro`: the integrity check, then the index build; checks that the built `index.faiss` matches the sha256 recorded next to it;
  4. `dvc status` must say everything is up to date; a second `dvc repro` changes nothing; `dvc status` must notice a real change to a dependency and go quiet when it is undone;
     `dvc repro --force` must rebuild a byte-identical `index.faiss`; the dataset dependencies must be byte-identical throughout;
  5. deletes the outputs and restores them with `dvc checkout`; the restored `index.faiss` must be byte-identical.
It does not upload anything (no remote exists) and does not prove anything about the real MiniLM index. Exit 0 = all checks passed, 1 = a check failed, 2 = cannot run."""

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results = []
PROBE_DIR = "minilm_frozen_probe_q"


def report(ok, name, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def set_backend(params_text, backend="dev-lsa"):
    """Return params.yaml text with `embedding.backend` replaced; raises if the key is missing."""
    out, hit = [], False
    for line in params_text.splitlines():
        if line.strip().startswith("backend:") and not hit:
            out.append(line[: len(line) - len(line.lstrip())] + f"backend: {backend}")
            hit = True
        else:
            out.append(line)
    if not hit:
        raise ValueError("params.yaml has no `backend:` entry")
    return "\n".join(out) + "\n"


def declared_doc_mode(params_text):
    """The `embedding.doc_mode` value declared in params.yaml text."""
    for line in params_text.splitlines():
        if line.strip().startswith("doc_mode:"):
            return line.split(":", 1)[1].split("#")[0].strip()
    return None


DEP_GLOBS = ("data/retrieval/corpus_manifest.json", "data/curated/v5/*.csv", "data/curated/v5/code_tests.json", "data/expansion/batch_0*/batch_0*_accepted.csv")


def dep_hashes(work):
    """sha256 of the dataset files the pipeline reads; they must never change."""
    out = {}
    for pat in DEP_GLOBS:
        for p in sorted(Path(work).glob(pat)):
            out[p.relative_to(work).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, cwd, env, timeout=900):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def _writable(func, path, _exc):  # Windows: Git object files are read-only
    os.chmod(path, stat.S_IWRITE)
    func(path)


def index_files(work):
    return sorted(
        p for p in (work / "data" / "retrieval" / "index").glob("*/index.faiss") if p.parent.name != PROBE_DIR
    )  # the stand-in for a frozen index is not a build output


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--keep", action="store_true", help="keep the temporary copy and print its path")
    args = ap.parse_args(argv)
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1", "SMART_LLM_PROVIDER": "none"}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")  # `python` inside dvc.yaml must be THIS interpreter
    dvc = [sys.executable, "-m", "dvc"]
    try:
        v = run(dvc + ["--version"], ROOT, env, 60)
        g = run(["git", "--version"], ROOT, env, 60)
        files = run(["git", "ls-files", "-z", "-c", "-o", "--exclude-standard"], ROOT, env, 120)
        assert v.returncode == 0 and g.returncode == 0 and files.returncode == 0
    except (OSError, AssertionError, subprocess.SubprocessError):
        print('cannot run: needs DVC ("pip install dvc>=3,<4"), Git, and this folder must be a Git repository')
        return 2
    print(f"DVC {v.stdout.strip()}; working in a temporary copy, your repository is not touched")
    work = Path(tempfile.mkdtemp(prefix="smart-dvc-"))
    try:
        names = [n for n in files.stdout.split("\0") if n and (ROOT / n).is_file()]
        for n in names:
            dest = work / n
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / n, dest)
        report(True, "copied the publishable files", f"{len(names)} files")
        for cmd in (
            ["git", "init", "-q", "-b", "main"],
            ["git", "config", "user.email", "verify@example.invalid"],
            ["git", "config", "user.name", "verify"],
            ["git", "config", "core.autocrlf", "false"],
            ["git", "add", "-A"],
        ):
            run(cmd, work, env)
        run(["git", "commit", "-q", "-m", "copy"], work, env)
        init = run(dvc + ["init"], work, env, 120)
        report(
            init.returncode == 0 and (work / ".dvc" / "config").is_file(),
            "dvc init",
            "creates .dvc/config only" if init.returncode == 0 else init.stderr[-300:],
        )
        params = work / "params.yaml"
        want_mode = declared_doc_mode(params.read_text(encoding="utf-8"))
        deps_before = dep_hashes(work)
        report(want_mode == "qk_concise", "params.yaml declares the served format", f"doc_mode={want_mode}")
        # stand-in for the real, frozen historical indexes that already sit in data/retrieval/index on a developer machine
        probe = work / "data" / "retrieval" / "index" / PROBE_DIR / "index.faiss"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"frozen historical index bytes")
        probe_sha = sha256(probe)
        params.write_text(set_backend(params.read_text(encoding="utf-8")), encoding="utf-8")
        r = run(dvc + ["repro"], work, env)
        built = index_files(work)
        report(
            r.returncode == 0 and len(built) == 1,
            "dvc repro: integrity check, then index build (offline dev-lsa stand-in)",
            "" if r.returncode == 0 else (r.stdout + r.stderr)[-600:],
        )
        if not built:
            return 1
        meta = json.loads((built[0].parent / "index_meta.json").read_text(encoding="utf-8"))
        recorded = (meta.get("files") or {}).get("index.faiss") or meta.get("index_faiss_sha256")
        first = sha256(built[0])
        report(bool(recorded) and recorded == first, "built index.faiss matches the sha256 recorded beside it", first[:16])
        report(
            meta.get("doc_mode") == want_mode,
            "the pipeline built the declared document format",
            f"index doc_mode={meta.get('doc_mode')}, params doc_mode={want_mode}",
        )
        st = run(dvc + ["status"], work, env, 120)
        report("up to date" in (st.stdout + st.stderr).lower(), "dvc status: data and pipelines are up to date")
        lock1 = sha256(work / "dvc.lock")
        again_run = run(dvc + ["repro"], work, env)
        report(again_run.returncode == 0 and sha256(work / "dvc.lock") == lock1, "a second dvc repro changes nothing (dvc.lock identical)", lock1[:16])
        # dvc status must notice a REAL change to a dependency, and go quiet again when it is undone
        dep = work / "src" / "retrieval" / "__init__.py"
        original = dep.read_bytes()
        dep.write_bytes(original + b"\n# verify_dvc: deliberate change\n")
        changed = run(dvc + ["status"], work, env, 120)
        report(
            "up to date" not in (changed.stdout + changed.stderr).lower() and "build_index" in (changed.stdout + changed.stderr),
            "dvc status reports a changed dependency",
        )
        dep.write_bytes(original)
        restored = run(dvc + ["status"], work, env, 120)
        report("up to date" in (restored.stdout + restored.stderr).lower(), "dvc status is quiet again after the change is undone")
        forced = run(dvc + ["repro", "--force"], work, env)
        rebuilt = index_files(work)
        report(
            forced.returncode == 0 and len(rebuilt) == 1 and sha256(rebuilt[0]) == first,
            "dvc repro --force rebuilds a byte-identical index.faiss (reproducible)",
            "" if forced.returncode == 0 else (forced.stdout + forced.stderr)[-300:],
        )
        report(probe.is_file() and sha256(probe) == probe_sha, "a pre-existing (frozen) index directory survives repro and repro --force untouched")
        report(dep_hashes(work) == deps_before, "dataset and source dependencies are byte-identical after every run", f"{len(deps_before)} files")
        shutil.rmtree(work / "data" / "retrieval" / "index", onerror=_writable)
        shutil.rmtree(work / "data" / "retrieval" / "cache", ignore_errors=True)
        co = run(dvc + ["checkout"], work, env, 300)
        again = index_files(work)
        report(
            co.returncode == 0 and len(again) == 1 and sha256(again[0]) == first,
            "outputs deleted, dvc checkout restores a byte-identical index.faiss",
            (co.stderr or "")[-200:] if co.returncode else "",
        )
        report(probe.is_file() and sha256(probe) == probe_sha, "the pre-existing index directory is also restored byte-identical by dvc checkout")
        print(
            "\nNot verified here: the real MiniLM index (needs the model in the Hugging Face cache), any remote (none is configured), Windows DVC behaviour unless you ran this on Windows."
        )
    finally:
        if args.keep:
            print(f"kept: {work}")
        else:
            shutil.rmtree(work, onerror=_writable)
    ok = all(results)
    print("\nDVC REPRODUCIBILITY: ALL PASSED" if ok else "\nDVC REPRODUCIBILITY: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
