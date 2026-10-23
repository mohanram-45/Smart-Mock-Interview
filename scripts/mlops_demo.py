"""Stage 7A: a short, reproducible walk through the MLOps tooling. Cross-platform, read-only for the repository, uses a THROWAWAY MLflow store and a
throwaway session directory (nothing is written to ./mlflow, ./results or Git). Trains nothing, downloads nothing, calls no LLM, runs no candidate code.

    python scripts\\mlops_demo.py                      # run the demo
    python scripts\\mlops_demo.py --transcript docs\\MLOPS_DEMO_TRANSCRIPT.md   # also save what it printed (no candidate text is involved)

Every step ends with a status line:
    DEMONSTRATED       it ran here, on this machine, just now
    NOT RUN HERE       its prerequisite is not installed on this machine; the exact command to run it is printed
Steps that depend on GitHub (a real Actions run) can never be demonstrated by a local script and are listed at the end as NOT TESTED."""

import argparse
import importlib.util
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STATUS = []


def say(msg=""):
    print(msg, flush=True)


def step(n, title):
    say(f"\n=== {n}. {title}")


def done(kind, detail=""):
    STATUS.append(kind)
    say(f"-> {kind}" + (f": {detail}" if detail else ""))


def run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)


def demo_mlflow(tmp):
    os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
    os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///" + (Path(tmp) / "mlflow.db").as_posix()
    os.environ["SMART_MLFLOW_ARTIFACTS"] = str(Path(tmp) / "artifacts")
    from src.mlops import tracking

    step(1, "How an MLflow experiment is tracked (live run, throwaway store)")
    if not tracking.available():
        say("MLflow (full package) is not installed.")
        say("   install:  pip install -r requirements-mlops.txt")
        done("NOT RUN HERE", "steps 1 and 2 need MLflow")
        step(2, "How a historical benchmark is imported")
        done("NOT RUN HERE", "needs MLflow: python scripts\\mlflow_import_history.py")
        return
    with tracking.live_run(
        "smart-demo",
        "demo: tiny tracked run",
        params={"purpose": "demonstration only", "model_run": "none - no model is executed"},
        tags={"smart.kind": "demo"},
    ) as run_:
        run_.log_metrics({"demo_metric": 1.0})
        rid = run_.run_id
    _, client = tracking._client()
    r = client.get_run(rid)
    for k in ("smart.provenance", "smart.human_validated", "smart.evaluator_versions", "smart.code_version"):
        if k in r.data.tags:
            say(f"   tag {k} = {str(r.data.tags[k])[:90]}")
    keys = sorted(k for k in r.data.params if k.startswith(("corpus.", "index.", "freeze.")))
    say(f"   {len(r.data.params)} params recorded automatically, including {len(keys)} corpus/index/freeze fingerprints, e.g.:")
    for k in keys[:4]:
        say(f"     {k} = {str(r.data.params[k])[:70]}")
    done("DEMONSTRATED", f"run {rid[:8]} recorded provenance=live, human_validated=false")

    step(2, "How a historical benchmark is imported (no model is rerun) and checked against its source files")
    from src.mlops import historical, verify

    first = historical.import_all()
    again = historical.import_all()
    v = verify.verify_history()
    say(f"   first import : {first['created']} created, {first['exists']} already present")
    say(f"   second import: {again['created']} created, {again['exists']} already present  (idempotent)")
    say(
        f"   verification : {v['runs_checked']} runs, {v['metrics_checked']} metrics compared with the source files -> {'ALL MATCH' if v['ok'] else v['problems'][:3]}"
    )
    sample = next(s for s in historical.all_specs() if s.key.startswith("stage3c2"))
    imp = tracking.find_run(tracking.ensure_experiment(sample.experiment), sample.key)
    say(
        f"   frozen Stage 3C-2 run: provenance={imp.data.tags.get('smart.provenance')}, decision={imp.data.tags.get('smart.decision')}, "
        f"human_validated={imp.data.tags.get('smart.human_validated')}"
    )
    done("DEMONSTRATED" if v["ok"] else "FAILED", "imported runs are labelled imported_historical; the DO NOT ADVANCE decision is preserved")


def demo_versioning():
    from src.mlops import version

    step(3, "How the corpus and retrieval index are versioned (reusing the project's own integrity controls)")
    c = version.corpus_info()
    say(f"   corpus: {c.get('record_count')} records, manifest sha256 {str(c.get('manifest_sha256'))[:16]}...")
    for name, comp in list((c.get("components") or {}).items())[:3]:
        say(f"     component {name}: fingerprint {str(comp.get('fingerprint'))[:16]}...")
    rows = version.index_fingerprints()
    if rows:
        for row in rows[:2]:
            say(
                f"   index {row['dir']}: {row.get('backend')}/{row.get('model')} recorded index.faiss sha256 {str(row.get('index_faiss_sha256_recorded'))[:16]}..."
            )
    else:
        say("   no built FAISS index on this machine (the index is rebuilt, not stored in Git: see docs/REPRODUCIBILITY.md)")
    p = run([sys.executable, "scripts/check_integrity.py"])
    for line in (p.stdout.strip().splitlines() or [""])[-5:]:
        say("   " + line)
    done("DEMONSTRATED" if p.returncode == 0 else "FAILED", "scripts/check_integrity.py (corpus loader strict, corpus manifest, freeze v2, bench_v2)")


def demo_dvc():
    step(4, "How a DVC pipeline is reproduced")
    say("   dvc.yaml has ONE stage, build_index: verify integrity, then rebuild the FAISS index + embedding cache from the Git-tracked corpus.")
    say("   (Needs the embedding model in the local Hugging Face cache; the stage never downloads one.)")
    exe = shutil.which("dvc")
    if not exe:
        say('   DVC is not installed.   install: pip install "dvc>=3,<4"')
    elif not (ROOT / ".dvc").is_dir():
        say("   DVC is installed but this repository has not been `dvc init`-ed yet.   run: dvc init   (then commit .dvc/ and dvc.yaml)")
    else:
        p = run([exe, "status"], timeout=120)
        say("   dvc status -> " + (p.stdout.strip() or p.stderr.strip())[:160].replace("\n", " | "))
        done("DEMONSTRATED", "dvc status ran (dvc repro is not run by the demo because it rebuilds the index)")
        return
    say("   to reproduce:   dvc repro        and then   dvc status   (should report: Data and pipelines are up to date)")
    done("NOT RUN HERE", "DVC is optional; see docs/REPRODUCIBILITY.md for the sandbox-verified reproduction")


def demo_ci():
    step(5, "How CI validates a code change (the same checks, run locally)")
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml:
        wf = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
        say("   .github/workflows/ci.yml jobs: " + ", ".join(wf["jobs"]))
    ruff = importlib.util.find_spec("ruff") is not None
    if ruff:
        p = run([sys.executable, "-m", "ruff", "check", "src", "main", "scripts", "tests", "report_delivery"])
        say("   ruff check (correctness rules) -> " + ("clean" if p.returncode == 0 else (p.stdout.strip().splitlines() or ["problems"])[-1]))
    else:
        say("   ruff is not installed (pip install --require-hashes -r requirements-ci.lock)")
    p = run([sys.executable, "-m", "pytest", "tests/mlops/test_ci_and_packaging.py", "-q", "-p", "no:cacheprovider"])
    say("   workflow/packaging safety tests -> " + (p.stdout.strip().splitlines() or ["?"])[-1])
    say("   A real Actions run on GitHub has NOT been executed: it needs the repository to be pushed (see docs/GITHUB_FIRST_PUSH.md).")
    done("DEMONSTRATED" if p.returncode == 0 else "FAILED", "local equivalents of the lint, integrity and workflow-safety jobs")


def demo_app(tmp):
    step(6, "How the application starts (in-process here; Docker below)")
    os.environ["SMART_DEMO_DATA_DIR"] = str(Path(tmp) / "sessions")
    os.environ["SMART_ACCESS_LOG"] = "0"
    os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
    for k in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC", "SMART_RETRIEVAL_ENABLED"):
        os.environ.pop(k, None)
    os.environ["SMART_FORBID_MODEL_TRAINING"] = "1"
    spec = importlib.util.spec_from_file_location("smart_app_demo", ROOT / "main" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    t0 = time.time()
    spec.loader.exec_module(mod)
    say(f"   app imported in {time.time() - t0:.1f}s with SMART_FORBID_MODEL_TRAINING=1 (no training, no download)")
    try:
        import waitress

        srv = waitress.create_server(mod.app, host="127.0.0.1", port=0)
        threading.Thread(target=srv.run, daemon=True).start()
        base = f"http://127.0.0.1:{srv.effective_port}"
        say(f"   serving on {base} (loopback only), same WSGI server as the Docker image")

        def get(path):
            with urllib.request.urlopen(base + path, timeout=10) as r:
                return r.status, r.read().decode()

        def post(path, body):
            req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode() or "{}")
    except ImportError:
        say("   waitress is not installed; using the in-process Flask test client instead (pip install waitress for a real server)")
        c = mod.app.test_client()

        def get(path):
            r = c.get(path)
            return r.status_code, r.get_data(as_text=True)

        def post(path, body):
            r = c.post(path, json=body)
            return r.status_code, r.get_json() or {}

    say("\n   Docker (step 6, containerised start):")
    if shutil.which("docker") and run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=60).returncode == 0:
        say("   Docker is available. Full build + run + persistence check:   python scripts\\verify_compose.py")
        done("NOT RUN HERE", "the demo does not build the image (minutes); run scripts\\verify_compose.py")
    else:
        say("   Docker is not available on this machine. Start Docker Desktop, then run:   python scripts\\verify_compose.py")
        done("NOT RUN HERE", "Docker unavailable")

    step(7, "How health, readiness and operational metrics are inspected")
    code, body = get("/healthz")
    say(f"   GET /healthz -> {code} {json.dumps({k: json.loads(body).get(k) for k in ('status', 'app_version')})}")
    code, body = get("/readyz")
    checks = json.loads(body).get("checks", {})
    say(f"   GET /readyz  -> {code} {json.dumps({k: v.get('ok') for k, v in checks.items()})}")
    secret = "DEMO-CANDIDATE-ANSWER-should-never-appear-in-metrics"
    code, created = post("/demo/api/sessions", {"role": "Data Scientist", "size": 5})
    sid = created.get("session_id")
    post(f"/demo/api/sessions/{sid}/answer", {"n": 1, "answer": secret})
    code, text = get("/metrics?format=prometheus")
    lines = [ln for ln in text.splitlines() if ln.startswith(("smart_http_requests_total", "smart_interviews_", "smart_answers_", "smart_build_info"))]
    say(f"   GET /metrics?format=prometheus -> {code}, {len(text.splitlines())} lines. A few:")
    for ln in lines[:6]:
        say("     " + ln[:110])
    leaked = secret in text
    say(f"   candidate answer text present in /metrics: {leaked}")
    post(f"/demo/api/sessions/{sid}/delete", {})
    done("DEMONSTRATED" if not leaked else "FAILED", "health, readiness and counters; no candidate text in the metrics; throwaway session deleted")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--transcript", help="also write what is printed to this Markdown file")
    a = ap.parse_args(argv)
    buf = io.StringIO()

    class Tee:
        def write(self, s):
            sys.__stdout__.write(s)
            buf.write(s)

        def flush(self):
            sys.__stdout__.flush()

    tmp = tempfile.mkdtemp(prefix="smart-mlops-demo-")
    try:
        with redirect_stdout(Tee()):
            say(f"SMART Mock Interview - MLOps demonstration ({platform.system()} {platform.release()}, Python {platform.python_version()})")
            say(f"throwaway workspace: {tmp}   (nothing is written to ./mlflow, ./results or Git)")
            demo_mlflow(tmp)
            demo_versioning()
            demo_dvc()
            demo_ci()
            demo_app(tmp)
            say("\n=== NOT TESTED (cannot be shown by a local script)")
            say("   - a real GitHub Actions run (the repository has never been pushed with these workflows)")
            say("   - Docker Desktop on Windows (use scripts\\verify_compose.py there)")
            say("   - the real python:3.13-slim-bookworm base image and the optional INSTALL_ML=1 image")
            say(f"\n== summary: {STATUS.count('DEMONSTRATED')} DEMONSTRATED, {STATUS.count('NOT RUN HERE')} NOT RUN HERE, {STATUS.count('FAILED')} FAILED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if a.transcript:
        out = Path(a.transcript)
        out.write_text(
            "# MLOps demonstration transcript\n\nGenerated by `python scripts/mlops_demo.py`. Environment line first; step status at the end of each section.\n\n```text\n"
            + buf.getvalue().replace(str(Path(tmp)), "<tmp>")
            + "```\n",
            encoding="utf-8",
            newline="\n",
        )
    return 1 if "FAILED" in STATUS else 0


if __name__ == "__main__":
    sys.exit(main())
