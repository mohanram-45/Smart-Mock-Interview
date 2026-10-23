"""HTTP adapters (stdlib urllib only: no new dependency). NONE of these is verified against a real service in Stage 3A;
they are exercised only against a local fake server in tests. Hosted adapters are `paid=True` and the factory refuses to build
them unless SMART_LLM_ALLOW_PAID=1 is set explicitly."""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from ..errors import (ProviderAuthError, ProviderRateLimited, ProviderRequestError, ProviderResponseError, ProviderTimeout,
                      ProviderUnavailable)
from .base import LLMProvider, ProviderResponse


def post_json(url: str, headers: Dict[str, str], body: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        ra: Optional[float] = None
        try:
            ra = float(e.headers.get("Retry-After")) if e.headers and e.headers.get("Retry-After") else None
        except ValueError:
            ra = None
        msg = f"HTTP {e.code}: {detail}"
        if e.code in (401, 403):
            raise ProviderAuthError(msg) from e
        if e.code == 429:
            raise ProviderRateLimited(msg, retry_after=ra) from e
        if e.code in (408, 409, 425) or e.code >= 500:
            raise (ProviderTimeout(msg) if e.code == 408 else ProviderUnavailable(msg, retry_after=ra)) from e
        raise ProviderRequestError(msg) from e
    except (socket.timeout, TimeoutError) as e:
        raise ProviderTimeout(f"no response within {timeout}s") from e
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
            raise ProviderTimeout(f"no response within {timeout}s") from e
        raise ProviderUnavailable(f"cannot reach provider: {e.reason}") from e
    except OSError as e:                                         # connection reset etc.
        raise ProviderUnavailable(f"network error: {e}") from e
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise ProviderResponseError("response body is not JSON") from e


class _HttpProvider(LLMProvider):
    def __init__(self, model: str, base_url: str, timeout: float, api_key: str = "", max_output_tokens: int = 2000):
        if not model:
            raise ValueError("model is required")
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), float(timeout)
        self._api_key, self.max_output_tokens = api_key, int(max_output_tokens)

    def __repr__(self) -> str:                                    # never print the key
        return f"{type(self).__name__}(model={self.model!r}, base_url={self.base_url!r})"


class OllamaProvider(_HttpProvider):
    """Local model via Ollama (the project's existing optional LLM integration uses the same host variable).

    num_ctx is set EXPLICITLY: Ollama silently truncates prompts that exceed the context window (older defaults were 2048-4096
    tokens), which would cut off the candidate answer. `usage['prompt_eval_count']` is returned so truncation can be detected."""
    name = "ollama"
    paid = False

    def __init__(self, model: str, base_url: str, timeout: float, api_key: str = "", max_output_tokens: int = 2000,
                 num_ctx: int = 8192, temperature: float = 0.0, seed: int = 7, response_schema: Optional[dict] = None):
        super().__init__(model, base_url, timeout, api_key, max_output_tokens)
        self.response_schema = response_schema            # None = plain JSON mode; a JSON schema = grammar-constrained structured output
        self.num_ctx, self.temperature, self.seed = int(num_ctx), float(temperature), int(seed)

    def generate(self, system: str, user: str) -> ProviderResponse:
        t0 = time.perf_counter()
        d = post_json(f"{self.base_url}/api/chat", {}, {
            "model": self.model, "stream": False, "format": self.response_schema or "json",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": self.temperature, "seed": self.seed, "num_predict": self.max_output_tokens, "num_ctx": self.num_ctx}}, self.timeout)
        try:
            text = d["message"]["content"]
        except Exception as e:
            raise ProviderResponseError("missing message.content in Ollama response") from e
        if not isinstance(text, str):
            raise ProviderResponseError("message.content is not text")
        usage = {k: d.get(k) for k in ("done_reason", "prompt_eval_count", "eval_count", "total_duration", "load_duration", "prompt_eval_duration", "eval_duration")}
        usage["num_ctx"] = self.num_ctx
        return ProviderResponse(text, self.model, (time.perf_counter() - t0) * 1000, usage)


class AnthropicProvider(_HttpProvider):
    name = "anthropic"
    paid = True

    def generate(self, system: str, user: str) -> ProviderResponse:
        t0 = time.perf_counter()
        d = post_json(f"{self.base_url}/v1/messages", {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"}, {
            "model": self.model, "max_tokens": self.max_output_tokens, "temperature": 0, "system": system,
            "messages": [{"role": "user", "content": user}]}, self.timeout)
        try:
            text = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
        except Exception as e:
            raise ProviderResponseError("missing content blocks in Anthropic response") from e
        if not text:
            raise ProviderResponseError("empty text content")
        return ProviderResponse(text, d.get("model", self.model), (time.perf_counter() - t0) * 1000, dict(d.get("usage") or {}))


class OpenAICompatibleProvider(_HttpProvider):
    name = "openai_compatible"
    paid = True

    def generate(self, system: str, user: str) -> ProviderResponse:
        t0 = time.perf_counter()
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        d = post_json(f"{self.base_url}/v1/chat/completions", headers, {
            "model": self.model, "temperature": 0, "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, self.timeout)
        try:
            text = d["choices"][0]["message"]["content"]
        except Exception as e:
            raise ProviderResponseError("missing choices[0].message.content") from e
        if not isinstance(text, str) or not text:
            raise ProviderResponseError("empty or non-text content")
        return ProviderResponse(text, d.get("model", self.model), (time.perf_counter() - t0) * 1000, dict(d.get("usage") or {}))
