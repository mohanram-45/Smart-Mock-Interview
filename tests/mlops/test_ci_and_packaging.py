"""Stage 6B: static checks of the CI workflows, Dockerfile, Compose file, env example and DVC pipeline (they cannot be executed in every environment,
so their safety properties are asserted from the files themselves)."""

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
CI = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
HEAVY = yaml.safe_load((ROOT / ".github/workflows/heavy.yml").read_text(encoding="utf-8"))
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def _steps(wf):
    return [s for j in wf["jobs"].values() for s in j.get("steps", [])]


def _runs(wf):
    return "\n".join(s.get("run", "") for s in _steps(wf))


def _on(wf):
    return wf.get("on", wf.get(True))  # YAML 1.1 parses the bare key `on` as True


def test_ci_runs_every_required_check():
    r = _runs(CI)
    for needle in (
        "pytest tests/retrieval",
        "pytest tests/evaluation",
        "pytest tests/app",
        "pytest tests/codeeval",
        "scripts/check_integrity.py",
        "ruff check",
        "ruff format --check",
        "docker build",
        "docker compose config",
    ):
        assert needle in r, f"CI is missing: {needle}"


def test_normal_ci_has_no_gpu_ollama_paid_keys_or_secrets():
    raw = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "secrets." not in raw and "API_KEY" not in raw.upper().replace("SMART_LLM_ALLOW_PAID", "")
    assert "gpu" not in raw.lower().replace("no gpu", "")
    assert CI["env"]["HF_HUB_OFFLINE"] == "1" and CI["env"]["TRANSFORMERS_OFFLINE"] == "1"
    assert CI["env"]["SMART_LLM_ALLOW_PAID"] == "0" and CI["env"]["SMART_LLM_PROVIDER"] == "none"
    assert ":9" in CI["env"]["OLLAMA_HOST"], "Ollama must point at an unreachable address in normal CI"
    assert CI["env"]["SMART_CODEEVAL_EXEC"] == ""
    assert CI["permissions"] == {"contents": "read"}
    for j in CI["jobs"].values():
        assert j["runs-on"] in ("ubuntu-latest", "windows-latest") and "timeout-minutes" in j
    assert not re.search(r"torch|sentence-transformers|ollama pull|playwright install", _runs(CI)), (
        "normal CI must not install heavyweight packages or pull models"
    )


def test_normal_ci_triggers_on_pull_requests_and_heavy_does_not():
    assert "pull_request" in _on(CI)
    assert "pull_request" not in _on(HEAVY) and "push" not in _on(HEAVY)
    assert "workflow_dispatch" in _on(HEAVY)
    assert re.search(r"torch", _runs(HEAVY))  # heavyweight work lives here


def test_no_workflow_runs_a_qwen_benchmark_or_candidate_code():
    for wf in (CI, HEAVY):
        r = _runs(wf)
        assert "stage3c2_run" not in r and "stage3b_run" not in r and "ollama pull" not in r
        assert "SMART_CODEEVAL_EXEC=docker" not in r


def test_ci_requirements_are_lean():
    reqs = (ROOT / "requirements-ci.txt").read_text(encoding="utf-8").lower()
    for bad in ("torch", "sentence-transformers", "transformers", "ollama", "openai", "anthropic"):
        assert not re.search(rf"^{bad}\b", reqs, re.M), f"{bad} must not be in requirements-ci.txt"


def test_dockerfile_is_non_root_with_healthcheck_and_no_weights_or_secrets():
    assert re.search(r"^USER\s+smart", DOCKERFILE, re.M) and "10001" in DOCKERFILE
    assert "HEALTHCHECK" in DOCKERFILE and "healthcheck.py" in DOCKERFILE
    assert re.search(r"^FROM\s+\$\{PYTHON_IMAGE\}", DOCKERFILE, re.M) and "python:3.13-slim-bookworm" in DOCKERFILE
    assert "SMART_FORBID_MODEL_TRAINING=1" in DOCKERFILE
    assert "pip install -r requirements-docker.lock" in DOCKERFILE  # pinned set
    for bad in (
        ".pt",
        ".pth",
        ".safetensors",
        ".gguf",
        "COPY . ",
        "ADD http",
        "API_KEY",
        "TOKEN",
        "PASSWORD",
        "docker.sock",
        "docker-ce",
        "apt-get install docker",
    ):
        assert bad not in DOCKERFILE, f"Dockerfile must not contain {bad!r}"
    assert "torch" not in DOCKERFILE.replace("torch/sentence-transformers", "")  # torch only via the optional INSTALL_ML build arg file
    assert 'if [ "$INSTALL_ML" = "1" ]' in DOCKERFILE


def test_lock_file_is_pinned_and_lean():
    lines = [ln for ln in (ROOT / "requirements-docker.lock").read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
    assert lines and all(re.match(r"^[A-Za-z0-9_.\-]+==[0-9][^=\s]*$", ln) for ln in lines)
    names = {ln.split("==")[0].lower() for ln in lines}
    assert {"flask", "waitress", "numpy", "scikit-learn", "reportlab", "pydantic"} <= names
    assert not names & {"torch", "sentence-transformers", "faiss-cpu", "transformers", "ollama"}


def test_compose_is_loopback_only_least_privilege_and_has_no_code_execution():
    app = COMPOSE["services"]["app"]
    assert all(p.startswith("127.0.0.1:") for p in app["ports"]), "published ports must be loopback-only"
    assert "ports" not in COMPOSE["services"]["ollama"], "Ollama must not be published"
    assert app.get("privileged") is not True and app["read_only"] is True
    assert app["cap_drop"] == ["ALL"] and "no-new-privileges:true" in app["security_opt"]
    assert "healthcheck" in app and any(v.startswith("smart-results:") for v in app["volumes"])
    for v in app["volumes"]:
        assert "docker.sock" not in v and not v.startswith(("/", ".", "~")), "no host bind mounts"
    env = app["environment"]
    assert "SMART_CODEEVAL_EXEC" not in env, "Docker execution must not be passed into the Flask container"
    assert env["SMART_FORBID_MODEL_TRAINING"] == "1" and env["SMART_LLM_ALLOW_PAID"] == "0" and env["SMART_DEMO_ALLOW_SCORER_SETUP"] == "0"
    for flag in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_RETRIEVAL_ENABLED"):
        assert env[flag].endswith(":-0}"), f"{flag} must default to off"
    assert env["SMART_QUESTION_SOURCE"].endswith(":-legacy}")
    assert COMPOSE["services"]["ollama"]["profiles"] == ["ollama"], "Ollama is optional (profile)"
    assert app["build"]["args"]["INSTALL_ML"].endswith(":-0}")
    raw = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert not re.search(r"(?i)(password|secret|token|api_key)\s*[:=]\s*\S", raw)


def test_env_example_only_sets_known_flags_with_safe_defaults():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    kv = dict(re.findall(r"^([A-Z_]+)=([^\s#]*)", text, re.M))
    for name in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_RETRIEVAL_ENABLED", "SMART_INSTALL_ML", "SMART_OBS_PROBE_OLLAMA"):
        assert kv[name] == "0"
    assert kv["SMART_QUESTION_SOURCE"] == "legacy"
    assert not any(re.search(r"KEY|TOKEN|SECRET|PASSWORD", k) for k in kv), "no credentials belong in the env example"
    # every variable the compose file interpolates is documented in the example
    interp = set(re.findall(r"\$\{([A-Z_]+):-", (ROOT / "docker-compose.yml").read_text(encoding="utf-8")))
    assert interp <= set(re.findall(r"^#?\s*([A-Z_]+)=", text, re.M)), interp - set(re.findall(r"^#?\s*([A-Z_]+)=", text, re.M))


def test_dockerignore_keeps_secrets_candidate_data_and_weights_out():
    di = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for needle in (".env", "results", "mlflow", ".git", "**/*.pt", "**/*.safetensors", "data/retrieval/index"):
        assert needle in di


def test_dvc_pipeline_is_minimal_and_does_not_touch_frozen_data():
    d = yaml.safe_load((ROOT / "dvc.yaml").read_text(encoding="utf-8"))
    assert list(d["stages"]) == ["build_index"]
    st = d["stages"]["build_index"]
    outs = [next(iter(o)) if isinstance(o, dict) else o for o in st["outs"]]
    assert outs == ["data/retrieval/index", "data/retrieval/cache"]
    assert "--local-files-only" in st["cmd"] and "check_integrity.py" in st["cmd"]
    assert not any("evaluation" in o or "curated" in o for o in outs), "frozen datasets are never DVC outputs"
    p = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))
    assert {"backend", "doc_mode", "model"} <= set(p["embedding"])


def test_healthcheck_script_reports_unhealthy_when_nothing_listens(capsys):
    import importlib.util

    spec = importlib.util.spec_from_file_location("hc", ROOT / "scripts/healthcheck.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["x", "http://127.0.0.1:9"]) == 1
    assert "UNHEALTHY" in capsys.readouterr().out


# ---------------------------------------------------------------- Stage 7A: workflow supply-chain and repository hygiene
WORKFLOWS = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / ".github/workflows").glob("*.yml")}


def test_every_action_is_pinned_to_a_full_commit_sha():
    uses = [m for raw in WORKFLOWS.values() for m in re.findall(r"^\s*-?\s*uses:\s*(\S+)", raw, re.M)]
    assert uses
    for u in uses:
        assert re.fullmatch(r"[\w.\-]+/[\w.\-]+@[0-9a-f]{40}", u), f"action not pinned to a commit SHA: {u}"
    assert all(re.search(r"uses:\s*\S+@[0-9a-f]{40} # v\d", raw) for raw in WORKFLOWS.values()), "keep the human-readable version as a comment"


def test_checkout_does_not_persist_credentials_and_workflows_are_least_privilege():
    for name, raw in WORKFLOWS.items():
        wf = yaml.safe_load(raw)
        assert wf["permissions"] == {"contents": "read"}, name
        for j in wf["jobs"].values():
            for st in j.get("steps", []):
                if str(st.get("uses", "")).startswith("actions/checkout@"):
                    assert st["with"]["persist-credentials"] is False, name
            assert "permissions" not in j or j["permissions"] == {"contents": "read"}, "jobs must not widen permissions"


def test_workflows_cannot_leak_candidate_data_or_run_untrusted_code():
    for name, raw in WORKFLOWS.items():
        wf = yaml.safe_load(raw)
        assert "pull_request_target" not in _on(wf) and "workflow_run" not in _on(wf), name
        assert "upload-artifact" not in raw and "actions/cache" not in raw.replace("setup-python", ""), (
            f"{name}: no artifacts (candidate data) and no hand-rolled caches"
        )
        assert "secrets." not in raw and "GITHUB_TOKEN" not in raw, name
        runs = _runs(wf)
        for untrusted in ("github.event", "github.head_ref", "github.ref_name", "inputs."):
            assert untrusted not in runs, f"{name}: untrusted context interpolated into a shell script: {untrusted}"
        assert "demo_sessions" not in raw


def test_python_dependencies_install_from_hash_checked_locks():
    for name, raw in WORKFLOWS.items():
        for line in re.findall(r"pip install[^\n]*", raw):
            if "-r " in line:
                assert "--require-hashes" in line and ".lock" in line, f"{name}: {line}"
    for lock in ("requirements-ci.lock", "requirements-ci-mlops.lock"):
        text = (ROOT / lock).read_text(encoding="utf-8")
        pins = re.findall(r"^([A-Za-z0-9_.\-]+)==\S+", text, re.M)
        assert pins and text.count("--hash=sha256:") >= len(pins), f"{lock}: every pin needs a hash"
    ci = (ROOT / "requirements-ci.lock").read_text(encoding="utf-8").lower()
    for bad in ("\ntorch==", "\nsentence-transformers==", "\ntransformers==", "\nollama==", "\nopenai==", "\nanthropic=="):
        assert bad not in ci
    assert "\nruff==" in ci and "\npytest==" in ci and "\nfaiss-cpu==" in ci
    assert "\nmlflow==" in (ROOT / "requirements-ci-mlops.lock").read_text(encoding="utf-8").lower()


def test_ci_has_a_windows_job_and_a_single_gate_job():
    assert CI["jobs"]["windows"]["runs-on"] == "windows-latest"
    gate = CI["jobs"]["ci-ok"]
    assert set(gate["needs"]) == set(CI["jobs"]) - {"ci-ok"} and gate["if"] == "always()"


def test_gitignore_keeps_secret_cache_and_artifact_rules():
    """Regression: an earlier stage replaced .gitignore and silently dropped the original secret/cache rules."""
    rules = {ln.strip() for ln in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}
    required = {
        ".env",
        "report_delivery/.env",
        ".venv/",
        "venv/",
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
        "frontend/node_modules/",
        "output/",
        "results/reports/",
        "results/evaluation/",
        "Temp/",
        "tmp/",
        ".agents/",
        ".codex/",
        ".bot/",
        "dataset_upgrade_prompt.md",
        "data/retrieval/index/",
        "data/retrieval/cache/",
        "results/demo_sessions/",
        "mlflow/",
        "mlruns/",
        ".dvc/cache",
        ".dvc/tmp",
        "*.zip",
    }
    assert required <= rules, required - rules


def test_no_machine_specific_paths_or_credentials_in_source():
    pat = re.compile(r"D:[\\/]+Projects|/home/claude|C:[\\/]+Users|/Users/[A-Za-z]|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}")
    offenders = []
    for base in ("src", "main", "scripts", ".github", "docker-compose.yml", "Dockerfile", "pyproject.toml", "dvc.yaml", "params.yaml"):
        p = ROOT / base
        for f in [p] if p.is_file() else [x for x in p.rglob("*") if x.is_file() and x.suffix in (".py", ".yml", ".yaml", ".bat", ".ps1", ".toml", ".txt")]:
            if "__pycache__" in f.parts or f.name == "test_ci_and_packaging.py":
                continue
            if pat.search(f.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(f.relative_to(ROOT)))
    assert not offenders, offenders


def test_gitattributes_forces_lf_for_hash_pinned_files_and_crlf_for_windows_launchers():
    """Regression: without this, Git for Windows (autocrlf=true) checks pinned CSV/JSON out with CRLF and every sha256 check fails."""
    ga = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert re.search(r"^\* text=auto eol=lf$", ga, re.M)
    for pat in ("*.bat", "*.ps1"):
        assert re.search(rf"^{re.escape(pat)} text eol=crlf$", ga, re.M)
    for pat in ("*.pt", "*.faiss", "*.png"):
        assert re.search(rf"^{re.escape(pat)} binary$", ga, re.M)
    for bat in ROOT.glob("*.bat"):
        assert b"\r\n" in bat.read_bytes(), (
            f"{bat.name} must be CRLF in the working tree. A checkout made before .gitattributes existed keeps LF; convert this launcher to CRLF "
            "(it is not hash-pinned) or re-checkout it: git checkout-index --force --all would also rewrite other files, so prefer converting just this file"
        )


def test_documentation_links_and_referenced_commands_exist():
    """Outdated-documentation guard: every relative Markdown link resolves, and every scripts\\\\*.py / scripts/*.py named in the Stage 6-7 docs exists."""
    link = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
    broken = []
    for md in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        for target in link.findall(md.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (md.parent / target).exists():
                broken.append(f"{md.relative_to(ROOT)} -> {target}")
    assert not broken, broken
    missing = []
    for name in ("MLOPS.md", "REPRODUCIBILITY.md", "TROUBLESHOOTING.md", "GITHUB_FIRST_PUSH.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        for rel in set(re.findall(r"scripts[\\\\/]+([A-Za-z0-9_]+\.(?:py|ps1))", text)):
            if not (ROOT / "scripts" / rel).is_file():
                missing.append(f"{name}: scripts/{rel}")
    assert not missing, missing


def test_compose_has_a_model_cache_volume_and_never_downloads_by_default():
    """Regression: with a read-only root filesystem an INSTALL_ML=1 build had nowhere to keep the embedding model, and nothing stopped a silent download."""
    app = COMPOSE["services"]["app"]
    assert any(v.startswith("smart-hf-cache:/hf-cache") for v in app["volumes"]) and "smart-hf-cache" in COMPOSE["volumes"]
    assert app["environment"]["HF_HUB_OFFLINE"].endswith(":-1}") and app["environment"]["TRANSFORMERS_OFFLINE"].endswith(":-1}")
    assert "HF_HOME=/hf-cache" in DOCKERFILE and "/hf-cache" in DOCKERFILE.split("RUN mkdir")[1].split("\n")[0]


def test_ruff_import_classification_does_not_depend_on_the_local_mlflow_store():
    """Stage 8C regression: `mlflow/` (the local tracking store) made ruff classify `import mlflow` as first-party only on machines that had run MLflow, so the strict
    lint step passed locally and would have failed on a fresh GitHub checkout."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.ruff.lint.isort]" in text and re.search(r'known-third-party\s*=\s*\[[^\]]*"mlflow"', text)
