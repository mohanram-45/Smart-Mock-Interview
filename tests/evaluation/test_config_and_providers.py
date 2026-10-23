"""Config gating and HTTP adapters. Adapters are exercised ONLY against a local fake server: no real service is contacted and none
of them is verified against a live API in Stage 3A."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.evaluation.config import EvaluationConfig, build_provider
from src.evaluation.errors import (ProviderAuthError, ProviderNotConfigured, ProviderRateLimited, ProviderRequestError, ProviderResponseError,
                                   ProviderTimeout, ProviderUnavailable)
from src.evaluation.evaluator import AnswerEvaluator
from src.evaluation.providers.http import AnthropicProvider, OllamaProvider, OpenAICompatibleProvider
from src.evaluation.schema import EvaluationStatus as S
from tests.evaluation.conftest import BUBBLE, llm_json


# ---------------------------------------------------------------- config
def test_defaults_are_legacy_and_unconfigured():
    c = EvaluationConfig.from_env({})
    assert (c.backend, c.provider, c.llm_enabled, c.allow_paid) == ("legacy", "none", False, False)
    with pytest.raises(ProviderNotConfigured):
        build_provider(c, {})


@pytest.mark.parametrize("env", [{"SMART_LLM_NUM_CTX": "512"}, {"SMART_EVALUATION_BACKEND": "gpt"}, {"SMART_LLM_PROVIDER": "bard"}, {"SMART_LLM_TIMEOUT_S": "0"}, {"SMART_LLM_TIMEOUT_S": "999"},
                                 {"SMART_LLM_MAX_RETRIES": "9"}, {"SMART_LLM_MAX_RETRIES": "-1"}, {"SMART_LLM_TIMEOUT_S": "fast"}])
def test_invalid_config_fails_loudly(env):
    with pytest.raises(ValueError):
        EvaluationConfig.from_env(env)


def test_backend_flag_parsing_is_case_insensitive():
    assert EvaluationConfig.from_env({"SMART_EVALUATION_BACKEND": " LLM "}).llm_enabled is True


def test_provider_building_rules():
    ok = lambda **k: EvaluationConfig.from_env({"SMART_EVALUATION_BACKEND": "llm", **k})
    with pytest.raises(ProviderNotConfigured, match="SMART_LLM_MODEL"):
        build_provider(ok(SMART_LLM_PROVIDER="ollama"), {})
    p = build_provider(ok(SMART_LLM_PROVIDER="ollama", SMART_LLM_MODEL="m"), {"OLLAMA_HOST": "http://h:1"})
    assert isinstance(p, OllamaProvider) and p.base_url == "http://h:1" and not p.paid and p.num_ctx == 8192
    assert build_provider(ok(SMART_LLM_PROVIDER="ollama", SMART_LLM_MODEL="m", SMART_LLM_NUM_CTX="16384"), {}).num_ctx == 16384
    with pytest.raises(ProviderNotConfigured, match="SMART_LLM_ALLOW_PAID"):                    # hosted providers need explicit approval
        build_provider(ok(SMART_LLM_PROVIDER="anthropic", SMART_LLM_MODEL="m"), {"SMART_LLM_API_KEY": "k"})
    with pytest.raises(ProviderNotConfigured, match="API key"):
        build_provider(ok(SMART_LLM_PROVIDER="anthropic", SMART_LLM_MODEL="m", SMART_LLM_ALLOW_PAID="1"), {})
    a = build_provider(ok(SMART_LLM_PROVIDER="anthropic", SMART_LLM_MODEL="m", SMART_LLM_ALLOW_PAID="1"), {"ANTHROPIC_API_KEY": "sk-secret"})
    assert isinstance(a, AnthropicProvider) and a.paid and "sk-secret" not in repr(a)
    with pytest.raises(ProviderNotConfigured, match="test-only"):
        build_provider(ok(SMART_LLM_PROVIDER="mock", SMART_LLM_MODEL="m"), {})
    o = build_provider(ok(SMART_LLM_PROVIDER="openai_compatible", SMART_LLM_MODEL="m", SMART_LLM_ALLOW_PAID="1", SMART_LLM_BASE_URL="http://x"), {})
    assert isinstance(o, OpenAICompatibleProvider)


def test_no_secret_or_provider_default_is_hardcoded_in_the_package():
    import pathlib, re
    for f in pathlib.Path("src/evaluation").rglob("*.py"):
        t = f.read_text(encoding="utf-8")
        assert not re.search(r"sk-[A-Za-z0-9]{8,}|api[_-]?key\s*=\s*['\"][A-Za-z0-9]{8,}", t), f


# ---------------------------------------------------------------- fake server
class _H(BaseHTTPRequestHandler):
    script = []          # list of (status, headers, body | callable)
    seen = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        type(self).seen.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        status, headers, payload = type(self).script.pop(0) if type(self).script else (200, {}, {})
        if callable(payload):
            payload = payload()
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


@pytest.fixture()
def server(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost"); monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(k, raising=False)
    h = type("H", (_H,), {"script": [], "seen": []})
    s = HTTPServer(("127.0.0.1", 0), h)
    t = threading.Thread(target=s.serve_forever, daemon=True); t.start()
    h.url = f"http://127.0.0.1:{s.server_address[1]}"
    yield h
    s.shutdown(); s.server_close()


GOOD = json.dumps(llm_json((4, 4, 4, 4), correct_concepts=[{"concept": "bubble sort", "candidate_quote": "compares adjacent elements"}]))


def test_ollama_request_shape_and_parse(server):
    server.script.append((200, {}, {"message": {"content": GOOD}, "eval_count": 5}))
    r = OllamaProvider("qwen-test", server.url, 5).generate("SYS", "USR")
    b = server.seen[0]["body"]
    assert server.seen[0]["path"] == "/api/chat" and b["model"] == "qwen-test" and b["stream"] is False and b["format"] == "json"
    assert b["options"]["num_ctx"] == 8192 and r.usage["num_ctx"] == 8192 and r.usage["eval_count"] == 5
    assert b["options"]["temperature"] == 0 and b["messages"][0] == {"role": "system", "content": "SYS"} and r.text == GOOD


def test_anthropic_request_shape_headers_and_parse(server):
    server.script.append((200, {}, {"model": "m-x", "content": [{"type": "text", "text": GOOD}], "usage": {"input_tokens": 3}}))
    r = AnthropicProvider("m", server.url, 5, "KEY123").generate("SYS", "USR")
    s = server.seen[0]
    assert s["path"] == "/v1/messages" and s["headers"]["x-api-key"] == "KEY123" and s["headers"]["anthropic-version"] == "2023-06-01"
    assert s["body"]["system"] == "SYS" and s["body"]["temperature"] == 0 and s["body"]["messages"] == [{"role": "user", "content": "USR"}] and r.text == GOOD


def test_openai_compatible_request_shape_headers_and_parse(server):
    server.script.append((200, {}, {"choices": [{"message": {"content": GOOD}}]}))
    r = OpenAICompatibleProvider("m", server.url, 5, "KEY").generate("SYS", "USR")
    s = server.seen[0]
    assert s["path"] == "/v1/chat/completions" and s["headers"]["authorization"] == "Bearer KEY" and s["body"]["response_format"] == {"type": "json_object"} and r.text == GOOD


@pytest.mark.parametrize("status,headers,exc", [(401, {}, ProviderAuthError), (403, {}, ProviderAuthError), (429, {"Retry-After": "3"}, ProviderRateLimited),
                                                (500, {}, ProviderUnavailable), (503, {}, ProviderUnavailable), (400, {}, ProviderRequestError),
                                                (404, {}, ProviderRequestError)])
def test_http_errors_map_to_clear_provider_errors(server, status, headers, exc):
    server.script.append((status, headers, {"error": "x"}))
    with pytest.raises(exc) as ei:
        OpenAICompatibleProvider("m", server.url, 5, "KEY").generate("s", "u")
    if status == 429:
        assert ei.value.retry_after == 3.0


@pytest.mark.parametrize("payload", [{"unexpected": 1}, {"choices": []}, {"choices": [{"message": {"content": ""}}]}, b"<html>oops</html>"])
def test_bad_envelopes_are_provider_response_errors(server, payload):
    server.script.append((200, {}, payload))
    with pytest.raises(ProviderResponseError):
        OpenAICompatibleProvider("m", server.url, 5, "KEY").generate("s", "u")


def test_slow_server_times_out(server):
    import time
    server.script.append((200, {}, lambda: (time.sleep(1.6), {"choices": [{"message": {"content": "x"}}]})[1]))
    with pytest.raises(ProviderTimeout):
        OllamaProvider("m", server.url, 1).generate("s", "u")


def test_unreachable_server_is_a_retryable_provider_error():
    """A closed local port is refused on Linux/macOS (-> Unavailable) but some Windows setups time the connect out (-> Timeout).
    Either way it must be a RETRYABLE ProviderError, never a raw socket exception."""
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()          # a port that was just closed
    with pytest.raises((ProviderUnavailable, ProviderTimeout)) as ei:
        OllamaProvider("m", f"http://127.0.0.1:{port}", 2).generate("s", "u")
    assert ei.value.retryable


def test_end_to_end_evaluator_over_http_with_a_retry(server, make_req):
    server.script += [(503, {}, {"error": "busy"}), (200, {}, {"message": {"content": GOOD}})]
    ev = AnswerEvaluator(OllamaProvider("m", server.url, 5), max_retries=2, sleep=lambda s: None)
    r = ev.evaluate(make_req(BUBBLE, "Bubble sort compares adjacent elements and swaps them. O(n²)."))
    assert r.evaluation_status == S.GRADED and r.provenance.attempts == 2 and r.provenance.provider == "ollama" and r.provenance.is_mock is False
