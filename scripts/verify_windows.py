"""Local verification of SMART Mock Interview on YOUR machine (written for Windows, works anywhere). Run from the project folder:

    .bot\\Scripts\\python.exe scripts\\verify_windows.py                    # environment, data, readiness, flags, in-process app smoke test
    .bot\\Scripts\\python.exe scripts\\verify_windows.py --url http://127.0.0.1:5000   # ...and probe a RUNNING server
    .bot\\Scripts\\python.exe scripts\\verify_windows.py --check-docker     # ...and the Docker pre-flight (starts only our own self-test container)
    .bot\\Scripts\\python.exe scripts\\verify_windows.py --docker-sample    # ...and run our OWN known-good NumPy sample inside the container
    .bot\\Scripts\\python.exe scripts\\verify_windows.py --check-ollama     # ...and check Ollama is reachable and qwen2.5:7b is installed (no generation)
    .bot\\Scripts\\python.exe scripts\\verify_windows.py --run-tests        # ...and the full pytest suites

It never trains a model, downloads anything, pulls or builds a Docker image, or runs candidate code. The Docker steps run only code written in this repository.
Each line is PASS / WARN (works, but a feature is unavailable) / FAIL (something is broken). Exit code 1 if any FAIL. Paste the output back if anything fails."""
import argparse
import importlib
import importlib.util
import importlib.metadata as md
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "components"))
sys.path.insert(0, str(ROOT / "src" / "model"))
try:                                           # a Windows console in cp1252 must never crash a report line
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ap = argparse.ArgumentParser()
ap.add_argument("--url", help="base URL of a running server, e.g. http://127.0.0.1:5000")
ap.add_argument("--check-docker", action="store_true")
ap.add_argument("--docker-sample", action="store_true")
ap.add_argument("--check-ollama", action="store_true")
ap.add_argument("--run-tests", action="store_true")
args = ap.parse_args()
counts = {"PASS": 0, "WARN": 0, "FAIL": 0}


def say(level, name, detail=""):
    counts[level] += 1
    print(f"{level:4}  {name}" + (f"  -> {detail}" if detail else ""), flush=True)


def check(name, ok, detail="", warn=False):
    say("PASS" if ok else ("WARN" if warn else "FAIL"), name, "" if ok else detail)


def section(t):
    print(f"\n== {t}", flush=True)


# ---------------------------------------------------------------------------------------------------------------------------------------------- environment
section("Environment")
print(f"      {platform.platform()} | Python {sys.version.split()[0]} | {sys.executable}")
check("Python 3.10 or newer", sys.version_info >= (3, 10), f"found {sys.version.split()[0]}")
in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
check("running inside a virtual environment", in_venv, "not in a venv (use .bot\\Scripts\\python.exe); packages may come from the wrong place", warn=True)
needed = {"flask": "Flask", "flask_cors": "flask-cors"}
for mod, pipname in needed.items():
    try:
        importlib.import_module(mod)
        try:
            ver = md.version(pipname)
        except Exception:
            ver = ""
        say("PASS", f"package {pipname}", ver)
    except Exception as e:
        say("FAIL", f"package {pipname}", f"missing ({type(e).__name__}): pip install {pipname}")
optional = {"torch": ("Bi-LSTM and Sentence-BERT scorers", "torch"), "sentence_transformers": ("Sentence-BERT scorer", "sentence-transformers"),
            "sklearn": ("TF-IDF scorer", "scikit-learn"), "language_tool_python": ("TF-IDF grammar checker", "language-tool-python"),
            "faiss": ("semantic search API", "faiss-cpu"), "numpy": ("semantic search / code tests", "numpy"), "pydantic": ("experimental evaluator", "pydantic")}
for mod, (why, pipname) in optional.items():
    ok = importlib.util.find_spec(mod) is not None
    check(f"optional package {pipname} ({why})", ok, f"not installed: pip install {pipname}", warn=True)

# ---------------------------------------------------------------------------------------------------------------------------------------------- data
section("Project data and frozen experiment")
try:
    from src.retrieval.service import get_service
    n = len(get_service().records()); check("curated question bank loads (expects 666 records)", n == 666, f"loaded {n}")
except Exception as e:
    say("FAIL", "curated question bank loads", f"{type(e).__name__}: {str(e)[:200]}")
ck = ROOT / "results" / "siamese_bilstm.pt"
check("trained Bi-LSTM checkpoint present", ck.exists(), "results\\siamese_bilstm.pt missing: the Bi-LSTM scorer will report 'needs setup' (train once: python src\\model\\SiameseBiLSTM.py)", warn=True)
fz = ROOT / "scripts" / "stage3c2_freeze_v2.py"
if fz.exists():
    r = subprocess.run([sys.executable, str(fz), "verify"], capture_output=True, text=True, cwd=ROOT)
    check("frozen Stage 3C-2 experiment unchanged (DO NOT ADVANCE decision preserved)", r.returncode == 0 and "no drift" in (r.stdout + r.stderr), (r.stdout + r.stderr)[-300:])

# ---------------------------------------------------------------------------------------------------------------------------------------------- readiness + flags
section("Scorer readiness (no training, no downloads) and feature flags")
try:
    import model_registry as MR
    for key in MR.MODEL_CHOICES:
        r = MR.readiness(key)
        check(f"scorer '{key}' ready", r["ready"], f"{r['reason']}  Fix: {r['hint']}", warn=True)
    check("default scorer is ready (the first interview will be scored)", MR.readiness(MR.DEFAULT_MODEL)["ready"], f"default '{MR.DEFAULT_MODEL}' is not ready; pick a ready scorer on the setup page", warn=True)
except Exception as e:
    say("FAIL", "model registry", f"{type(e).__name__}: {e}")
for var in ("SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC", "SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_ALLOW_SCORER_SETUP", "SMART_RETRIEVAL_EXPOSE_REFERENCE", "SMART_HOST", "SMART_DEBUG"):
    v = os.environ.get(var)
    check(f"{var} is unset (default: off)", v is None or v == "", f"currently '{v}' (fine if you set it on purpose)", warn=True)

# ---------------------------------------------------------------------------------------------------------------------------------------------- in-process app
section("Application smoke test (in-process, temporary session folder, real scorer if ready)")
tmp = tempfile.mkdtemp(prefix="smart_verify_")
os.environ["SMART_DEMO_DATA_DIR"] = tmp
try:
    import importlib.util as iu
    spec = iu.spec_from_file_location("smart_app", ROOT / "main" / "app.py")
    mod = iu.module_from_spec(spec); sys.modules["smart_app"] = mod; spec.loader.exec_module(mod)
    c = mod.app.test_client()
    for url in ("/demo/", "/demo/about", "/demo/guide", "/demo/api/status", "/demo/api/catalog", "/demo/recorded"):
        check(f"GET {url}", c.get(url).status_code == 200, f"status {c.get(url).status_code}")
    cat = c.get("/demo/api/catalog").json
    check("code check is OFF by default", cat["code_eval"]["enabled"] is False)
    check("live modular evaluation is OFF by default", "live" not in cat["modular_modes"])
    ready_keys = [m["key"] for m in cat["legacy_models"] if m["ready"]]
    lm = next((m["key"] for m in cat["legacy_models"] if m["default"]), None)
    r = c.post("/demo/api/sessions", json={"role": "Python Developer", "difficulty": "Mixed", "size": 3, "legacy_model": lm})
    check("start a 3-question interview", r.status_code == 201, str(r.json))
    if r.status_code == 201:
        sid = r.json["session_id"]
        t0 = time.time()
        a = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "A short answer in my own words:\n    indented line\n\tand a tab."})
        dt = time.time() - t0
        check("submit an answer", a.status_code == 200, str(a.json)[:200])
        ex = c.get(f"/demo/s/{sid}/export.json").json
        legacy = ex["answers"][0]["legacy"]
        check(f"answer scored by '{lm}' in {dt:.1f}s" if legacy["status"] == "scored" else f"scorer '{lm}' unavailable: interview still works", legacy["status"] == "scored",
              str(legacy.get("reason")), warn=True)
        check("indentation and tabs survive storage and export", "    indented line\n\tand a tab." in ex["answers"][0]["answer"])
        f = Path(tmp) / f"{sid}.json"
        check("session file written atomically (Windows os.replace)", f.exists() and json.loads(f.read_text(encoding="utf-8"))["id"] == sid)
        c.post(f"/demo/api/sessions/{sid}/finish")
        check("summary page renders after finishing", c.get(f"/demo/s/{sid}/summary").status_code == 200)
        c.post(f"/demo/api/sessions/{sid}/delete")
        check("deleting the interview removes its file", not f.exists())
    check("unknown session id gives a friendly 404", c.get("/demo/s/demo_" + "0" * 20).status_code == 404)
    code_sample = c.post("/demo/api/sessions", json={"role": "Data Scientist", "code_eval": True})
    check("code_eval request without the flag is refused (400)", code_sample.status_code == 400)
except Exception as e:
    import traceback
    say("FAIL", "application smoke test", f"{type(e).__name__}: {e}")
    traceback.print_exc()
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------------------------------------------------------------------------- host
section("Host checks")
s = socket.socket()
port = int(os.environ.get("SMART_PORT", "5000"))
try:
    s.bind(("127.0.0.1", port)); check(f"port {port} is free to start the app", True)
except OSError:
    check(f"port {port} is free to start the app", False, "something is already listening (is the app already running? or set SMART_PORT=5001)", warn=True)
finally:
    s.close()
sess = ROOT / "results" / "demo_sessions"
try:
    sess.mkdir(parents=True, exist_ok=True); t = sess / ".write_test"; t.write_text("x"); t.unlink(); check("results\\demo_sessions is writable", True)
except OSError as e:
    check("results\\demo_sessions is writable", False, str(e))
check("project path has no problematic characters", all(ord(ch) < 128 for ch in str(ROOT)), "non-ASCII characters in the path can break some Python libraries on Windows", warn=True)

# ---------------------------------------------------------------------------------------------------------------------------------------------- running server
if args.url:
    section(f"Running server at {args.url}")
    import urllib.request
    base = args.url.rstrip("/")
    for path in ("/demo/", "/demo/api/status", "/demo/about"):
        try:
            with urllib.request.urlopen(base + path, timeout=10) as resp:
                check(f"GET {path}", resp.status == 200, f"status {resp.status}")
                if path == "/demo/api/status":
                    j = json.loads(resp.read()); check("server reports 666 questions", j.get("questions") == 666, str(j.get("questions")))
        except Exception as e:
            say("FAIL", f"GET {path}", f"{type(e).__name__}: {e}")
    try:
        with urllib.request.urlopen(base + "/demo/", timeout=10) as resp:
            h = {k.lower(): v for k, v in resp.headers.items()}
        check("security headers present (CSP, nosniff, no-store)", "content-security-policy" in h and h.get("x-content-type-options") == "nosniff" and "no-store" in h.get("cache-control", ""))
    except Exception:
        pass

# ---------------------------------------------------------------------------------------------------------------------------------------------- docker (opt-in)
if args.check_docker or args.docker_sample:
    section("Docker pre-flight (opt-in; nothing is pulled or built; candidate code is never run)")
    if shutil.which("docker") is None:
        say("WARN", "docker command found", "Docker Desktop is not installed or not on PATH: code check stays read-only (this is fine)")
    else:
        from src.codeeval.runner import DockerRunner, DEFAULT_IMAGE
        image = os.environ.get("SMART_CODEEVAL_IMAGE") or DEFAULT_IMAGE
        d = DockerRunner(image)
        ok, why = d.available()
        check(f"Docker sandbox pre-flight passes for image '{image}'", ok, why + "  (build once: docker build -t smart-codeeval:numpy docker\\codeeval)", warn=True)
        print(f"      {why}")
        if ok and args.docker_sample:
            from tests.codeeval import fixtures as F
            res = d.run("numpy_pairwise_sq_dists", F.NP_GOOD)           # OUR OWN known-good sample, not a candidate answer
            passed = [t for t in res.tests if t["status"] == "passed"]
            check(f"our own NumPy sample ran in the container ({res.status}, {res.seconds:.1f}s)", res.status == "ok" and len(passed) == len(res.tests) and len(res.tests) > 0,
                  f"{res.status}: {res.reason}; tests={[(t['id'], t['status']) for t in res.tests]}")
            res2 = d.run("numpy_pairwise_sq_dists", "import time\ntime.sleep(60)\n")  # our own 'hangs forever' sample: must be stopped by the wall-clock limit
            check("a hanging sample is stopped by the time limit", res2.status in ("timeout", "ok") and res2.seconds < 40, f"{res2.status} after {res2.seconds:.1f}s")
            left = subprocess.run(["docker", "ps", "-aq", "--filter", "label=smart-codeeval=1"], capture_output=True, text=True).stdout.split()
            check("no leftover containers", not left, f"remove with: docker rm -f {' '.join(left)}")

# ---------------------------------------------------------------------------------------------------------------------------------------------- ollama (opt-in)
if args.check_ollama:
    section("Ollama (optional; only for the experimental live evaluator)")
    import urllib.request
    host = os.environ.get("SMART_DEMO_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
    if not host.startswith("http"):
        host = "http://" + host
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=5) as resp:
            names = [m["name"] for m in json.loads(resp.read()).get("models", [])]
        check("Ollama is reachable", True)
        check("model qwen2.5:7b is installed", any(n.startswith("qwen2.5:7b") for n in names), f"installed: {names}. Not installed: ollama pull qwen2.5:7b (a multi-GB download; only needed for the experimental live mode)", warn=True)
    except Exception as e:
        check("Ollama is reachable", False, f"{type(e).__name__}: start it with 'ollama serve' (only needed for the experimental live mode)", warn=True)

# ---------------------------------------------------------------------------------------------------------------------------------------------- tests
if args.run_tests:
    section("Automated test suites")
    for d in ("tests/evaluation", "tests/retrieval", "tests/app", "tests/codeeval"):
        r = subprocess.run([sys.executable, "-m", "pytest", d, "-q", "-p", "no:warnings"], capture_output=True, text=True, cwd=ROOT)
        last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        check(f"{d}: {last}", r.returncode == 0, (r.stdout + r.stderr)[-400:])

print(f"\nSummary: {counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL")
if counts["FAIL"]:
    print("Something is broken: paste this whole output back.")
elif counts["WARN"]:
    print("Works, with the warnings above (each names the feature that is unavailable and how to enable it).")
else:
    print("Everything checked is fine.")
sys.exit(1 if counts["FAIL"] else 0)
