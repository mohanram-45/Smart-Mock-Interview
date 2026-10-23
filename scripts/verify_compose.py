"""Stage 6C: end-to-end Docker Compose verification on a developer machine (Windows Docker Desktop or Linux). Cross-platform, standard library only.

    python scripts\\verify_compose.py                 # build, start on 127.0.0.1:5099, health, readiness, persistence, privacy, clean up
    python scripts\\verify_compose.py --port 5100     # pick another loopback port if 5099 is taken
    python scripts\\verify_compose.py --no-build      # reuse an already built image
    python scripts\\verify_compose.py --keep          # leave the stack running afterwards (and keep its volume)

Safety: uses its OWN Compose project name (`smartverify`), so it never touches your normal `docker compose up` containers or the `smart-results` volume.
Publishes only on 127.0.0.1 (never 0.0.0.0). Trains nothing, downloads no model, pulls no Ollama model, runs no candidate code. The Ollama profile is not started.
Exit code 0 = every check passed; 2 = Docker unavailable (nothing was verified); 1 = a check failed."""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "smartverify"
RESULTS = []


def report(status, name, detail=""):
    RESULTS.append(status)
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""), flush=True)


def docker(*args, timeout=120, env=None):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env)


def compose(*args, timeout=1800, env=None):
    return docker("compose", "-p", PROJECT, *args, timeout=timeout, env=env)


def http(method, url, body=None, timeout=10):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"} if data is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ConnectionError) as e:
        return 0, str(e)


def as_json(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def port_is_free(port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) != 0


def wait_healthy(base, tries=45):
    last = (0, "")
    for _ in range(tries):
        last = http("GET", base + "/healthz")
        if last[0] == 200:
            return True, last
        time.sleep(2)
    return False, last


def container_id():
    p = compose("ps", "-q", "app", timeout=60)
    return p.stdout.strip().splitlines()[0] if p.stdout.strip() else ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=5099)
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)

    if not shutil.which("docker"):
        report("SKIP", "docker not found on PATH", "install Docker Desktop (WSL2 backend), start it, then re-run this script")
        return 2
    p = docker("version", "--format", "{{.Server.Os}}/{{.Server.Version}}", timeout=60)
    if p.returncode != 0:
        report("SKIP", "Docker daemon not reachable", "start Docker Desktop and wait for 'Engine running', then re-run; " + p.stderr.strip()[-200:])
        return 2
    report("PASS", "docker daemon", p.stdout.strip())
    p = docker("compose", "version", "--short", timeout=60)
    report("PASS" if p.returncode == 0 else "FAIL", "docker compose plugin", p.stdout.strip() or p.stderr.strip()[-200:])
    if p.returncode != 0:
        return 1
    if not port_is_free(a.port):
        report(
            "FAIL",
            f"127.0.0.1:{a.port} is already in use",
            "choose another with --port, or stop the process holding it (Windows: netstat -ano | findstr :%d)" % a.port,
        )
        return 1
    report("PASS", f"loopback port {a.port} is free")

    env = dict(os.environ, SMART_PUBLISH_PORT=str(a.port), COMPOSE_PROJECT_NAME=PROJECT)
    for k in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_RETRIEVAL_ENABLED", "SMART_CODEEVAL_EXEC", "SMART_INSTALL_ML"):
        env.pop(k, None)  # verify the DEFAULT (safe) configuration, whatever the developer has exported
    base = f"http://127.0.0.1:{a.port}"
    sid = None
    try:
        p = compose("config", "--quiet", env=env, timeout=60)
        report("PASS" if p.returncode == 0 else "FAIL", "compose file is valid", p.stderr.strip()[-300:])
        if p.returncode != 0:
            return 1

        t0 = time.time()
        p = compose("up", "-d", "--no-build" if a.no_build else "--build", env=env)
        if p.returncode != 0:
            report("FAIL", "compose up (build + start)", (p.stderr or p.stdout).strip()[-600:])
            return 1
        report("PASS", "compose up (build + start)", f"{time.time() - t0:.0f}s")

        ok, last = wait_healthy(base)
        report("PASS" if ok else "FAIL", "GET /healthz", as_json(last[1]).get("status", "") if ok else f"{last[0]} {last[1][:200]}")
        if not ok:
            print(compose("logs", "--tail", "40", "app", env=env).stdout)
            return 1
        code, raw = http("GET", base + "/readyz")
        checks = as_json(raw).get("checks", {})
        report("PASS" if code == 200 else "FAIL", "GET /readyz", json.dumps(checks)[:240])
        code, raw = http("GET", base + "/health")
        report("PASS" if code == 200 else "FAIL", "legacy GET /health unchanged", f"{code}")
        code, raw = http("GET", base + "/demo/")
        report("PASS" if code == 200 else "FAIL", "GET /demo/ renders", f"{code}")

        cid = container_id()
        h = docker("inspect", "-f", "{{.State.Health.Status}}", cid, timeout=30).stdout.strip() if cid else ""
        for _ in range(20):
            if h == "healthy":
                break
            time.sleep(3)
            h = docker("inspect", "-f", "{{.State.Health.Status}}", cid, timeout=30).stdout.strip()
        report("PASS" if h == "healthy" else "FAIL", "Docker HEALTHCHECK status", h)
        u = docker("exec", cid, "id", "-u", timeout=30).stdout.strip()
        report("PASS" if u and u != "0" else "FAIL", "application runs as a non-root user", f"uid {u}")
        port = docker("port", cid, timeout=30).stdout
        report(
            "PASS" if port.strip() and "0.0.0.0" not in port and "::" not in port else "FAIL",
            "published port is loopback-only",
            port.strip().replace("\n", "; "),
        )
        env_dump = docker("exec", cid, "env", timeout=30).stdout
        flags = dict(line.split("=", 1) for line in env_dump.splitlines() if line.startswith("SMART_"))
        report(
            "PASS" if flags.get("SMART_FORBID_MODEL_TRAINING") == "1" and "SMART_CODEEVAL_EXEC" not in flags else "FAIL",
            "training forbidden and no code-execution backend inside the container",
            f"FORBID_MODEL_TRAINING={flags.get('SMART_FORBID_MODEL_TRAINING')} CODEEVAL_EXEC={'set' if 'SMART_CODEEVAL_EXEC' in flags else 'unset'}",
        )
        for dangerous in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_RETRIEVAL_ENABLED"):
            report("PASS" if flags.get(dangerous, "0") in ("0", "") else "FAIL", f"{dangerous} is off by default", flags.get(dangerous, "unset"))
        w = docker("exec", cid, "sh", "-c", "test -w /hf-cache && test -w /app/results && echo writable", timeout=30).stdout.strip()
        report("PASS" if w == "writable" else "FAIL", "the two volumes (/app/results, /hf-cache) are writable by the non-root user", w)
        offline = docker("exec", cid, "env", timeout=30).stdout
        report("PASS" if "HF_HUB_OFFLINE=1" in offline else "FAIL", "model downloads are disabled by default (HF_HUB_OFFLINE=1)")
        ls = docker(
            "exec", cid, "sh", "-c", "find /app /home -name '*.pt' -o -name '*.safetensors' -o -name '*.gguf' 2>/dev/null | head -3", timeout=60
        ).stdout.strip()
        report("PASS" if not ls else "FAIL", "no model weights exist inside the container (nothing trained or downloaded at startup)", ls)
        logs = compose("logs", "app", env=env).stdout.lower()
        bad = [w for w in ("downloading", "epoch ", "training model", "pulling") if w in logs]
        report("PASS" if not bad else "FAIL", "startup log shows no training or download activity", ", ".join(bad))

        # persistence: a session created before the container is removed must still exist afterwards (named volume smart-results)
        code, raw = http("POST", base + "/demo/api/sessions", {"role": "Data Scientist", "size": 5})
        sid = as_json(raw).get("session_id")
        report("PASS" if code == 201 and sid else "FAIL", "create an interview session", f"HTTP {code}")
        if sid:
            code, _ = http("POST", f"{base}/demo/api/sessions/{sid}/answer", {"n": 1, "answer": "verify-compose placeholder answer"})
            report("PASS" if code in (200, 201) else "FAIL", "submit one answer", f"HTTP {code}")
            p = compose("down", env=env)  # no -v: the volume must survive
            report("PASS" if p.returncode == 0 else "FAIL", "compose down (volume kept)", "" if p.returncode == 0 else p.stderr.strip()[-200:])
            p = compose("up", "-d", env=env)
            ok, last = wait_healthy(base)
            report("PASS" if p.returncode == 0 and ok else "FAIL", "compose up again (new container)", f"{last[0]}")
            code, raw = http("GET", f"{base}/demo/api/sessions/{sid}")
            body = as_json(raw)
            report("PASS" if code == 200 and body.get("session_id") == sid else "FAIL", "the session survived the container being recreated", f"HTTP {code}")

        # operational metrics exist and carry no candidate text
        code, metrics = http("GET", base + "/metrics")
        report("PASS" if code == 200 and "smart_http_requests_total" in metrics else "FAIL", "GET /metrics exposes request counters", f"HTTP {code}")
        report("PASS" if "verify-compose placeholder answer" not in metrics else "FAIL", "metrics contain no candidate answer text")
        logs = compose("logs", "app", env=env).stdout
        report("PASS" if "verify-compose placeholder answer" not in logs else "FAIL", "container logs contain no candidate answer text")
    finally:
        if sid:
            http("POST", f"{base}/demo/api/sessions/{sid}/delete", {})
        if not a.keep:
            p = compose("down", "-v", "--rmi", "local", "--remove-orphans", env=env, timeout=180)  # safe: only this project's own volume and image
            report(
                "PASS" if p.returncode == 0 else "WARN",
                "cleaned up (containers, this project's volume and its built image)",
                "" if p.returncode == 0 else p.stderr.strip()[-200:],
            )
    n_fail = RESULTS.count("FAIL")
    print(f"\n== summary: {RESULTS.count('PASS')} PASS, {n_fail} FAIL, {RESULTS.count('WARN')} WARN")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
