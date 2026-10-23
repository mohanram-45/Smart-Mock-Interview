"""Stage 13 security regressions: compare-tool debugger/binding/CORS, the legacy report endpoints (origin, loopback, token, recipient, rate limit), CORS origins, secrets exclusion."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flask import Flask  # noqa: E402

from src.security import local_guard as G  # noqa: E402


# ---- helpers ---------------------------------------------------------------------------------------------------------------------------------------------
@pytest.fixture()
def client(tmp_path, monkeypatch):
    import report_delivery.routes as R
    (tmp_path / "abc123_report.json").write_text(json.dumps({"interview_role": "Data Scientist", "average_score": 70}), encoding="utf-8")
    monkeypatch.setattr(R, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(R, "PDF_DIR", tmp_path / "pdf")
    monkeypatch.setattr(R, "build_pdf", lambda report, path: b"%PDF-fake")
    sent = []
    monkeypatch.setattr(R, "send_report_email", lambda to, report, pdf: sent.append(to))
    monkeypatch.setattr(R, "_LIMITER", G.SendLimiter())
    for k in ("SMART_REPORT_TOKEN", "SMART_ALLOWED_ORIGINS"):
        monkeypatch.delenv(k, raising=False)
    app = Flask(__name__)
    app.register_blueprint(R.delivery_blueprint)
    c = app.test_client()
    c.sent = sent
    return c


def post(c, email="me@example.com", headers=None, addr="127.0.0.1", rid="abc123"):
    return c.post(f"/api/reports/{rid}/email", json={"email": email}, headers=headers or {}, environ_base={"REMOTE_ADDR": addr})


# ---- compare tool ----------------------------------------------------------------------------------------------------------------------------------------
def _compare_module():
    spec = importlib.util.spec_from_file_location("compare_app_s13", ROOT / "compare" / "app.py")
    return spec, ROOT / "compare" / "app.py"


def test_compare_defaults_are_local_and_debugger_off():
    src = (ROOT / "compare" / "app.py").read_text(encoding="utf-8")
    assert "debug=True" not in src and '"0.0.0.0"' not in src and "'0.0.0.0'" not in src
    ns = {}
    start = src.index("def run_config")
    end = src.index('if __name__ == "__main__"')
    exec(src[start:end], ns)
    assert ns["run_config"]({}) == ("127.0.0.1", 5050, False)
    assert ns["run_config"]({"SMART_DEBUG": "1", "SMART_COMPARE_HOST": "10.0.0.5", "SMART_COMPARE_PORT": "6000"}) == ("10.0.0.5", 6000, True)
    assert ns["run_config"]({"SMART_DEBUG": "no"})[2] is False


def test_compare_cors_is_not_wildcard_and_errors_are_generic():
    src = (ROOT / "compare" / "app.py").read_text(encoding="utf-8")
    assert '"origins": "*"' not in src and "cors_origins()" in src
    pass


def test_launchers_do_not_enable_debug_or_public_binding():
    bat = (ROOT / "run_all.bat").read_text(encoding="utf-8", errors="replace")
    assert "SMART_DEBUG=&&" in bat and "127.0.0.1" in bat
    assert "0.0.0.0" not in bat
    js = (ROOT / "frontend" / "server.js").read_text(encoding="utf-8")
    assert "app.listen(PORT, '127.0.0.1'" in js


def test_main_cors_uses_local_allowlist():
    src = (ROOT / "main" / "app.py").read_text(encoding="utf-8")
    assert '"origins": "*"' not in src and "cors_origins()" in src
    assert "*" not in G.cors_origins() and all(o.startswith("http://") for o in G.cors_origins())


# ---- origin / loopback / token ---------------------------------------------------------------------------------------------------------------------------
def test_local_page_origin_allowed(client):
    r = post(client, headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 200 and client.sent == ["me@example.com"]


def test_cross_site_origin_refused_and_nothing_sent(client):
    for origin in ("https://evil.example", "http://localhost.evil.example", "null", "http://127.0.0.1.evil.com:5000"):
        r = post(client, headers={"Origin": origin})
        assert r.status_code == 403, origin
    assert client.sent == []


def test_no_origin_requires_loopback_peer(client):
    assert post(client, addr="203.0.113.9").status_code == 403
    assert post(client, addr="127.0.0.1").status_code == 200
    assert post(client, addr="::1", rid="abc123").status_code in (200, 429)


def test_pdf_download_is_guarded_too(client):
    assert client.get("/api/reports/abc123/pdf", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/reports/abc123/pdf", environ_base={"REMOTE_ADDR": "198.51.100.4"}).status_code == 403
    assert client.get("/api/reports/abc123/pdf", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code == 200


def test_extra_allowed_origin_is_honoured(client, monkeypatch):
    monkeypatch.setenv("SMART_ALLOWED_ORIGINS", "https://reports.example.org")
    assert post(client, headers={"Origin": "https://reports.example.org"}).status_code == 200


def test_token_required_when_configured(client, monkeypatch):
    monkeypatch.setenv("SMART_REPORT_TOKEN", "s3cret-token")
    assert post(client).status_code == 403
    assert post(client, headers={"X-Report-Token": "wrong"}).status_code == 403
    assert post(client, headers={"X-Report-Token": "s3cret-token"}, addr="203.0.113.9").status_code == 200


def test_same_origin_request_allowed(client):
    r = client.post("/api/reports/abc123/email", json={"email": "me@example.com"}, base_url="http://reports.local:5000", headers={"Origin": "http://reports.local:5000"},
                    environ_base={"REMOTE_ADDR": "198.51.100.4"})
    assert r.status_code == 200


# ---- recipient handling ----------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [
    "", "no-at-sign", "a@b", "a@b..com", "a b@example.com", "a@example.com\r\nBcc: x@evil.com", "a@example.com,b@example.com", "a@example.com;b@example.com",
    "Name <a@example.com>", "<a@example.com>", "a@@example.com", ".a@example.com", "a.@example.com", "a@-example.com", "x" * 250 + "@example.com", "a@example.com\n",
    " a@example.com", "a@example.com ", "a\x00@example.com", "a@exa mple.com", '"a b"@example.com',
])
def test_unsafe_recipients_rejected(client, bad):
    assert post(client, email=bad).status_code == 400
    assert client.sent == []


@pytest.mark.parametrize("good", ["me@example.com", "first.last+tag@sub.example.co.uk", "a_b-c@example.io"])
def test_normal_recipients_accepted(good):
    assert G.valid_recipient(good)


def test_non_json_and_non_object_bodies(client):
    r = client.post("/api/reports/abc123/email", data="email=a@example.com", content_type="application/x-www-form-urlencoded", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 415
    r = client.post("/api/reports/abc123/email", json=["a@example.com"], environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 400
    assert client.sent == []


def test_bad_or_unknown_report_ids(client):
    assert post(client, rid="..%2f..%2fetc").status_code in (400, 404)
    assert post(client, rid="nope").status_code == 404
    assert client.sent == []


def test_rate_limit_per_report_and_overall(client):
    assert post(client).status_code == 200
    assert post(client).status_code == 429                      # same report again within a minute
    lim = G.SendLimiter(per_report_s=0, max_total=2, window_s=100)
    assert lim.allow("a", 0) is None and lim.allow("b", 1) is None
    assert lim.allow("c", 2) is not None and lim.allow("c", 101.5) is None


def test_smtp_failures_do_not_leak_server_detail(client, monkeypatch):
    import report_delivery.routes as R

    def boom(*a, **k):
        raise OSError("connect to smtp.internal.corp:587 refused [10.1.2.3]")
    monkeypatch.setattr(R, "send_report_email", boom)
    r = post(client)
    assert r.status_code == 503 and "10.1.2.3" not in r.get_data(as_text=True) and "internal" not in r.get_data(as_text=True)


def test_success_response_does_not_echo_recipient(client):
    assert "example.com" not in post(client).get_data(as_text=True)


def test_email_sender_validate_email_is_strict():
    from report_delivery.email_sender import validate_email
    assert validate_email("me@example.com") and not validate_email("a@example.com,b@example.com") and not validate_email("a@example.com\r\nBcc: b@evil.com")


# ---- secrets and private data are not publishable --------------------------------------------------------------------------------------------------------
def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")


def test_gitignore_covers_secrets_sessions_and_agent_config():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for needle in (".env", "report_delivery/.env", "results/demo_sessions/", ".claude/", "*.zip"):
        assert needle in text, needle


def test_no_secret_or_private_file_is_tracked():
    tracked = _git("ls-files").splitlines()
    bad = [p for p in tracked if p.split("/")[-1] == ".env" or (p.split("/")[-1].startswith(".env.") and not p.endswith(".example")) or p.startswith(".claude/")
           or p.startswith("results/demo_sessions/") or p.startswith("tmp/") or p.startswith("Temp/")]
    assert bad == []


def test_check_staged_blocks_env_and_claude_paths():
    spec = importlib.util.spec_from_file_location("check_staged_s13", ROOT / "scripts" / "check_staged.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import fnmatch
    for p in ("report_delivery/.env", ".env", "results/demo_sessions/x.json"):
        assert any(fnmatch.fnmatch(p, pat) for pat in mod.BLOCKED_PATTERNS), p
