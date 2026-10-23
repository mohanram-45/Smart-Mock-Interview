"""Stage 6B verification for a developer machine (Windows or Linux). Read-only: trains nothing, downloads nothing, pulls no model, runs no candidate code.

    python scripts\\verify_mlops.py                       # integrity + in-process health/metrics + flags + MLflow (if installed)
    python scripts\\verify_mlops.py --url http://127.0.0.1:5000        # also probe a RUNNING server (python main\\app.py or Docker)
    python scripts\\verify_mlops.py --check-docker                      # docker + compose available, compose file valid
    python scripts\\verify_mlops.py --docker-build --docker-run         # build the image, start it on 127.0.0.1:5099, check health, remove it
    python scripts\\verify_mlops.py --check-dvc --check-ollama

Exit code 0 = nothing failed (SKIP means the optional component is not installed, with the command to install it)."""

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
RESULTS = []


def report(status, name, detail=""):
    RESULTS.append((status, name, detail))
    print(f"[{status:4}] {name}" + (f" - {detail}" if detail else ""))


def run(cmd, timeout=120, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT, **kw)


def section(title):
    print(f"\n== {title}")


def check_environment():
    section("environment")
    report("PASS", "python", f"{platform.python_version()} on {platform.system()} {platform.release()}")
    for mod, hint in (("flask", "pip install -r requirements.txt"), ("pydantic", "pip install -r requirements-rag.txt  (or pip install pydantic)")):
        try:
            __import__(mod)
            report("PASS", f"import {mod}")
        except Exception:
            report("FAIL", f"import {mod}", hint)
    for mod, hint in (
        ("mlflow", "pip install -r requirements-mlops.txt"),
        ("sqlalchemy", "comes with the full mlflow package"),
        ("waitress", "pip install waitress  (only the Docker image uses it)"),
    ):
        try:
            if importlib.util.find_spec(mod) is None:
                raise ImportError(mod)
            report("PASS", f"optional: {mod}")
        except Exception:
            report("SKIP", f"optional: {mod} not installed", hint)


def check_integrity():
    section("dataset and frozen-experiment integrity (project's own controls)")
    p = run([sys.executable, "scripts/check_integrity.py"])
    for line in p.stdout.strip().splitlines():
        print("      " + line)
    report("PASS" if p.returncode == 0 else "FAIL", "scripts/check_integrity.py", "no drift" if p.returncode == 0 else "DRIFT - see output")


def check_versions():
    section("version consistency (corpus vs DVC params vs served format vs indexes vs frozen files)")
    p = run([sys.executable, "scripts/check_versions.py"])
    for line in p.stdout.strip().splitlines():
        print("      " + line)
    report("PASS" if p.returncode == 0 else "FAIL", "scripts/check_versions.py", "no disagreement" if p.returncode == 0 else "MISMATCH - see output")


def check_in_process():
    section("health, readiness, metrics and flags (in-process, temp session directory)")
    tmp = tempfile.mkdtemp(prefix="smart-verify-")
    os.environ["SMART_DEMO_DATA_DIR"] = tmp
    os.environ["SMART_ACCESS_LOG"] = "0"  # keep this report readable; the JSON access log is covered by the tests
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("smart_app_verify", ROOT / "main" / "app.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        c = mod.app.test_client()
        r = c.get("/health")
        report("PASS" if r.status_code == 200 and r.json == {"status": "ok"} else "FAIL", "legacy GET /health unchanged", str(r.json))
        r = c.get("/healthz")
        report(
            "PASS" if r.status_code == 200 and r.json.get("status") == "ok" else "FAIL",
            "GET /healthz",
            f"app {r.json.get('app_version')} pipeline {r.json.get('evaluator_versions', {}).get('pipeline')}",
        )
        r = c.get("/readyz")
        chk = r.json.get("checks", {})
        report("PASS" if r.status_code == 200 else "FAIL", "GET /readyz", json.dumps({k: v.get("ok") for k, v in chk.items()}))
        for k, v in r.json.get("optional", {}).get("scorers", {}).items():
            report("INFO", f"scorer {k}", "ready" if v["ready"] else f"not set up: {v['reason']}")
        r = c.get("/metrics")
        report("PASS" if r.status_code == 200 and "smart_http_requests_total" in r.json.get("metrics", {}) else "FAIL", "GET /metrics")
        from src.mlops import version

        f = version.flags_state()
        off = (
            f["SMART_DEMO_CODE_EVAL"] in ("off", "0", "")
            and f["SMART_CODEEVAL_EXEC"] in ("disabled", "", "0")
            and f["SMART_DEMO_LIVE_MODULAR"] in ("off", "0", "")
        )
        report(
            "PASS" if off else "WARN",
            "experimental flags off by default in this shell",
            json.dumps({k: f[k] for k in ("SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC", "SMART_DEMO_LIVE_MODULAR")}),
        )
        report("PASS" if "mlflow" not in sys.modules else "FAIL", "the Flask app does not import MLflow")
    except Exception as e:
        report("FAIL", "in-process app check", f"{type(e).__name__}: {str(e)[:200]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_mlflow():
    section("MLflow tracking (temporary store; no model is run)")
    try:
        import sqlalchemy  # noqa: F401

        import mlflow  # noqa: F401
    except Exception:
        report("SKIP", "MLflow", "pip install -r requirements-mlops.txt")
        return
    tmp = tempfile.mkdtemp(prefix="smart-mlflow-")
    env = {
        **os.environ,
        "MLFLOW_TRACKING_URI": "sqlite:///" + (Path(tmp) / "m.db").as_posix(),
        "SMART_MLFLOW_ARTIFACTS": str(Path(tmp) / "a"),
        "PYTHONPATH": str(ROOT),
        "MLFLOW_DISABLE_AGENT_HINT": "1",
    }
    try:
        p = run([sys.executable, "scripts/mlflow_import_history.py"], timeout=600, env=env)
        tail = [ln for ln in p.stdout.splitlines() if ln.startswith(("imported", "{", "MLflow records", "MISMATCH", "PROBLEM"))]
        report("PASS" if p.returncode == 0 else "FAIL", "import historical results + verify against source files", " | ".join(tail)[:300])
        p = run([sys.executable, "scripts/mlflow_log_provenance.py"], timeout=300, env=env)
        report("PASS" if p.returncode == 0 else "FAIL", "live provenance run (corpus + index fingerprints)", p.stdout.strip()[-200:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("      to browse the real store:  python scripts\\mlflow_import_history.py   then   mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db")


def http_json(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except Exception as e:
        return 0, {"error": str(e)}


def check_url(base):
    section(f"running server at {base}")
    base = base.rstrip("/")
    for path in ("/healthz", "/readyz", "/health", "/demo/"):
        try:
            with urllib.request.urlopen(base + path, timeout=8) as r:
                body = r.read(4000).decode("utf-8", "replace")
                ok = r.status == 200
        except urllib.error.HTTPError as e:
            ok, body = False, e.read(500).decode("utf-8", "replace")
        except Exception as e:
            ok, body = False, str(e)
        report("PASS" if ok else "FAIL", f"GET {path}", "" if ok else body[:160])


def check_docker(build, run_it):
    section("Docker")
    if not shutil.which("docker"):
        report("SKIP", "docker not found on PATH", "install Docker Desktop (WSL2 backend) then re-run with --check-docker")
        return
    p = run(["docker", "compose", "config", "--quiet"], timeout=60)
    report("PASS" if p.returncode == 0 else "FAIL", "docker compose config (file is valid; needs no daemon)", p.stderr.strip()[:300])
    p = run(["docker", "version", "--format", "{{.Server.Os}}/{{.Server.Version}}"], timeout=30)
    if p.returncode != 0:
        report("FAIL" if (build or run_it) else "SKIP", "docker daemon not reachable", "start Docker Desktop, then re-run with --docker-build --docker-run")
        return
    report("PASS", "docker daemon", p.stdout.strip())
    if build or run_it:
        t0 = time.time()
        p = run(["docker", "build", "-t", "smart-mock-interview:verify", "."], timeout=1500)
        report(
            "PASS" if p.returncode == 0 else "FAIL", "docker build (lean image)", f"{time.time() - t0:.0f}s" if p.returncode == 0 else p.stderr.strip()[-300:]
        )
        if p.returncode != 0:
            return
    if run_it:
        name = "smart-verify"
        run(["docker", "rm", "-f", name], timeout=30)
        p = run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-p",
                "127.0.0.1:5099:5000",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "smart-mock-interview:verify",
            ],
            timeout=60,
        )
        if p.returncode != 0:
            report("FAIL", "docker run", p.stderr.strip()[:300])
            return
        try:
            ok = False
            for _ in range(30):
                code, body = http_json("http://127.0.0.1:5099/healthz")
                if code == 200:
                    ok = True
                    break
                time.sleep(2)
            report("PASS" if ok else "FAIL", "container /healthz on 127.0.0.1:5099", body.get("git_commit", "") if ok else str(body)[:200])
            code, body = http_json("http://127.0.0.1:5099/readyz")
            report("PASS" if code == 200 else "FAIL", "container /readyz", json.dumps(body.get("checks", {}))[:200])
            u = run(["docker", "exec", name, "id", "-u"], timeout=30).stdout.strip()
            report("PASS" if u and u != "0" else "FAIL", "container user is not root", f"uid {u}")
            if not ok:
                print(run(["docker", "logs", "--tail", "30", name], timeout=30).stdout)
        finally:
            run(["docker", "rm", "-f", name], timeout=60)


def check_dvc():
    section("DVC")
    exe = shutil.which("dvc")
    if not exe:
        report("SKIP", "dvc not installed", 'pip install "dvc>=3,<4"   (then: dvc init  in the Git repository)')
        return
    p = run([exe, "--version"], timeout=30)
    report("PASS", "dvc", p.stdout.strip())
    if (ROOT / ".dvc").exists():
        p = run([exe, "dag"], timeout=60)
        report("PASS" if p.returncode == 0 else "FAIL", "dvc dag (dvc.yaml parses)", p.stdout.strip()[:200] or p.stderr.strip()[:200])
    else:
        report("SKIP", "repository is not DVC-initialised", "dvc init   (see docs/REPRODUCIBILITY.md)")


def check_ollama():
    section("Ollama (read-only: lists installed models; pulls nothing)")
    host = (os.environ.get("SMART_DEMO_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").strip()
    host = host if host.startswith("http") else "http://" + host
    code, body = http_json(host.rstrip("/") + "/api/tags", timeout=4)
    if code != 200:
        report(
            "SKIP", f"Ollama not reachable at {host}", "start it, or ignore: it is only needed for the opt-in live Qwen evaluation (SMART_DEMO_LIVE_MODULAR=1)"
        )
        return
    names = [m.get("name") for m in body.get("models", [])]
    report("PASS", "Ollama reachable", ", ".join(names)[:200])
    want = os.environ.get("SMART_DEMO_QWEN_MODEL", "qwen2.5:7b")
    report(
        "PASS" if want in names else "SKIP",
        f"model {want} installed",
        "" if want in names else f"ollama pull {want}   (needs your approval; this script never pulls)",
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url")
    ap.add_argument("--check-docker", action="store_true")
    ap.add_argument("--docker-build", action="store_true")
    ap.add_argument("--docker-run", action="store_true")
    ap.add_argument("--check-dvc", action="store_true")
    ap.add_argument("--check-ollama", action="store_true")
    ap.add_argument("--skip-mlflow", action="store_true")
    a = ap.parse_args()
    check_environment()
    check_integrity()
    check_versions()
    check_in_process()
    if not a.skip_mlflow:
        check_mlflow()
    if a.url:
        check_url(a.url)
    if a.check_docker or a.docker_build or a.docker_run:
        check_docker(a.docker_build, a.docker_run)
    if a.check_dvc:
        check_dvc()
    if a.check_ollama:
        check_ollama()
    fails = [r for r in RESULTS if r[0] == "FAIL"]
    print("\n== summary: " + ", ".join(f"{n} {s}" for s in ("PASS", "FAIL", "WARN", "SKIP", "INFO") if (n := sum(1 for r in RESULTS if r[0] == s))))
    print("NOTHING FAILED" if not fails else "FAILED: " + "; ".join(r[1] for r in fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
