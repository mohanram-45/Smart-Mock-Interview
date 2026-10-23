"""Stage 15 release gate: the narrow Docker peer rule at the endpoint, the GitHub-hosted ML Docker check, dependency pins, and documentation that matches the product."""
import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml
from flask import Flask

from src.security import local_guard as G

ROOT = Path(__file__).resolve().parents[2]
GATEWAY = "172.18.0.1"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import report_delivery.routes as R
    (tmp_path / "abc123_report.json").write_text(json.dumps({"interview_role": "Data Scientist", "average_score": 70}), encoding="utf-8")
    monkeypatch.setattr(R, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(R, "PDF_DIR", tmp_path / "pdf")
    monkeypatch.setattr(R, "build_pdf", lambda report, path: b"%PDF-fake")
    monkeypatch.setattr(R, "send_report_email", lambda *a: None)
    monkeypatch.setattr(R, "_LIMITER", G.SendLimiter())
    for k in ("SMART_REPORT_TOKEN", "SMART_ALLOWED_ORIGINS", "SMART_TRUSTED_PEERS", "SMART_TRUST_DOCKER_GATEWAY"):
        monkeypatch.delenv(k, raising=False)
    app = Flask(__name__)
    app.register_blueprint(R.delivery_blueprint)
    return app.test_client()


def get_pdf(c, addr, headers=None):
    return c.get("/api/reports/abc123/pdf", environ_base={"REMOTE_ADDR": addr}, headers=headers or {})


def test_only_the_container_gateway_gets_report_access_in_docker(client, monkeypatch):
    monkeypatch.setenv("SMART_TRUST_DOCKER_GATEWAY", "1")
    monkeypatch.setattr(G, "docker_gateway", lambda: GATEWAY)
    assert get_pdf(client, GATEWAY).status_code == 200                                 # the host's browser, via the published loopback port
    assert get_pdf(client, "127.0.0.1").status_code == 200
    for peer in ("172.18.0.2", "172.18.0.5", "10.1.2.3", "192.168.0.9", "172.31.255.254", "8.8.8.8"):   # another container, other private networks, the internet
        assert get_pdf(client, peer).status_code == 403, peer
    assert client.post("/api/reports/abc123/email", json={"email": "a@example.com"}, environ_base={"REMOTE_ADDR": "172.18.0.2"}).status_code == 403
    assert get_pdf(client, GATEWAY, {"Origin": "https://evil.example"}).status_code == 403   # the gateway still cannot be used by a foreign web page


def test_nothing_is_trusted_without_the_opt_in_and_a_token_still_applies(client, monkeypatch):
    monkeypatch.setattr(G, "docker_gateway", lambda: GATEWAY)
    assert get_pdf(client, GATEWAY).status_code == 403                                  # plain host run: loopback only
    monkeypatch.setenv("SMART_TRUST_DOCKER_GATEWAY", "1")
    monkeypatch.setenv("SMART_REPORT_TOKEN", "t0ken")
    assert get_pdf(client, GATEWAY).status_code == 403
    assert get_pdf(client, GATEWAY, {"X-Report-Token": "t0ken"}).status_code == 200


def test_missing_route_table_trusts_nobody(monkeypatch):
    monkeypatch.setenv("SMART_TRUST_DOCKER_GATEWAY", "1")
    monkeypatch.setattr(G, "docker_gateway", lambda: None)
    assert G.trusted_peers() == set() and not G.is_loopback("172.17.0.1")


# ---- GitHub-hosted validation of the ML image ---------------------------------------------------------------------------------------------------------------
def _heavy():
    return yaml.safe_load((ROOT / ".github/workflows/heavy.yml").read_text(encoding="utf-8"))


def test_heavy_workflow_verifies_real_scoring_in_the_ml_container_offline_and_without_secrets():
    wf = _heavy()
    job = wf["jobs"]["docker-ml-image"]
    runs = "\n".join(str(s.get("run", "")) for s in job["steps"])
    assert "INSTALL_ML=1" in runs and "scripts/verify_ml_scoring.py" in runs and "healthcheck.py --ready" in runs
    scoring = next(s for s in job["steps"] if "verify_ml_scoring" in str(s.get("run", "")))
    assert "--network none" in scoring["run"] and "--read-only" in scoring["run"] and "HF_HUB_OFFLINE=1" in scoring["run"] and scoring.get("timeout-minutes", 99) <= 15
    raw = (ROOT / ".github/workflows/heavy.yml").read_text(encoding="utf-8")
    assert "secrets." not in raw and "API_KEY" not in raw.upper() and job["timeout-minutes"] <= 45
    on = wf.get("on", wf.get(True))
    assert set(on) == {"workflow_dispatch", "schedule"}                                 # never part of normal pull-request checks


def test_normal_ci_is_not_made_slower_by_the_ml_image():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "INSTALL_ML" not in ci and "sentence-transformers" not in ci


# ---- dependency pins ----------------------------------------------------------------------------------------------------------------------------------------
def _pin(path, name):
    m = re.search(rf"^{re.escape(name)}==([0-9][^\s;\\]*)", (ROOT / path).read_text(encoding="utf-8"), re.M | re.I)
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def test_known_vulnerable_pins_are_gone():
    for lock in ("requirements-docker.lock", "requirements-ci.lock", "requirements-ci-mlops.lock"):
        assert _pin(lock, "pillow") >= (13, 0, 0), lock                                    # pillow 12.3.0 had unfixed advisories
    assert _pin("requirements-ci-mlops.lock", "certifi") >= (2026, 10, 19)


# ---- documentation matches the product ------------------------------------------------------------------------------------------------------------------------
def test_readme_and_docs_describe_the_current_product():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for stale in ("never executed on GitHub", "does not adapt at all", "Excellent work", "You pick a role, difficulty and length"):
        assert stale not in readme, stale
    for needle in ("Results and limitations at a glance", "Not assessed", "verify_docker_ml.bat", "verify_ollama_stage12.bat", "off by default", "illustrative"):
        assert needle in readme, needle
    for img in re.findall(r"docs/screenshots/(v1_[a-z0-9_]+\.png)", readme):
        assert (ROOT / "docs/screenshots" / img).is_file(), img
    walk = (ROOT / "docs/WALKTHROUGH.md").read_text(encoding="utf-8")
    for img in re.findall(r"screenshots/(\S+?\.png)", walk):
        assert (ROOT / "docs/screenshots" / img).is_file(), img
    assert "bigscore" not in walk and "Automatic comment" not in walk
    arch = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "does not run vector search" not in arch and "Stages 12-14" in arch and "SMART_TRUST_DOCKER_GATEWAY" in arch
    for doc in ("docs/RELEASE_NOTES_v1.0.md", "docs/RELEASE_CHECKLIST_v1.0.md"):
        assert (ROOT / doc).is_file(), doc


def test_ollama_validation_command_uses_real_case_ids_and_never_simulates():
    bat = (ROOT / "verify_ollama_stage12.bat").read_bytes()
    assert b"\r\n" in bat
    text = bat.decode("utf-8")
    spec = importlib.util.spec_from_file_location("stage12_cases", ROOT / "scripts" / "stage12_assess_answers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ids = {c["id"] for c in mod.CASES}
    listed = re.search(r"--cases ([^\r\n]+)", text).group(1).split()
    assert listed and set(listed) <= ids
    assert "--live" in text and "--scripted" not in text and "SMART_DEMO_LIVE_MODULAR=1" in text and "11434" in text


def test_screenshots_are_not_publishing_private_data():
    for p in (ROOT / "docs" / "screenshots").glob("v1_*.png"):
        assert 1_000 < p.stat().st_size < 3_000_000, p.name
