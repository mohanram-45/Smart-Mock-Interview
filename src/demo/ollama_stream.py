"""Stage 9D: a small STREAMING Ollama chat client for the follow-up feature (stdlib only; localhost).

Why it exists (see docs/STAGE9D_PERFORMANCE.md): the Stage 9C path used the evaluator's blocking provider. That gives (a) no cancellation: when the deadline passed, the HTTP call was only
abandoned, the local model kept generating and the NEXT request queued behind it; (b) no timings when a call fails (the metrics arrive only in the final reply); (c) no keep_alive, so the
model could be unloaded between turns and cold-loaded inside an interview.

This client:
  * streams, so a deadline CLOSES THE CONNECTION (Ollama then stops generating) and the partial timings are still reported;
  * enforces ONE absolute deadline over connect + prompt processing + generation;
  * sends keep_alive, a small num_ctx and a hard num_predict;
  * returns Ollama's own metrics (load_duration, prompt_eval_count/duration, eval_count/duration, total_duration) exactly as reported, plus the client-side time to first token.
It never fabricates text on failure and never raises anything but `src.evaluation.errors.ProviderError` subclasses.
"""
from __future__ import annotations

import http.client
import json
import socket
import time
import urllib.parse
from typing import Any, Dict, Optional

from ..evaluation.errors import ProviderRequestError, ProviderResponseError, ProviderTimeout, ProviderUnavailable
from ..evaluation.providers.base import LLMProvider, ProviderResponse

METRIC_KEYS = ("total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration", "done_reason")


class DeadlineExceeded(ProviderTimeout):
    code = "deadline_exceeded"

    def __init__(self, message: str = "", metrics: Optional[Dict[str, Any]] = None):
        super().__init__(message or "deadline exceeded")
        self.metrics = metrics or {}


def derived(m: Dict[str, Any]) -> Dict[str, Any]:
    """Human-readable rates from Ollama's nanosecond counters. Only what the server reported; None where it did not."""
    def ms(k):
        v = m.get(k)
        return round(v / 1e6, 1) if isinstance(v, (int, float)) else None

    def rate(n, d):
        return round(m[n] / (m[d] / 1e9), 1) if isinstance(m.get(n), (int, float)) and isinstance(m.get(d), (int, float)) and m[d] > 0 else None
    return {"load_ms": ms("load_duration"), "prompt_tokens": m.get("prompt_eval_count"), "prompt_eval_ms": ms("prompt_eval_duration"), "prompt_tok_per_s": rate("prompt_eval_count", "prompt_eval_duration"),
            "generated_tokens": m.get("eval_count"), "generate_ms": ms("eval_duration"), "generate_tok_per_s": rate("eval_count", "eval_duration"), "server_total_ms": ms("total_duration"),
            "done_reason": m.get("done_reason")}


class StreamingOllama(LLMProvider):
    name = "ollama-stream"
    paid = False

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434", *, num_predict: int = 160, num_ctx: int = 2048, keep_alive: str = "30m", temperature: float = 0.0, seed: int = 7,
                 response_schema: Optional[dict] = None, connect_timeout: float = 3.0):
        if not model:
            raise ValueError("model is required")
        u = urllib.parse.urlparse(base_url if "://" in base_url else "http://" + base_url)
        if u.scheme != "http" or not u.hostname:
            raise ValueError("base_url must be a plain http URL (the local Ollama server)")
        self.model, self.host, self.port = model, u.hostname, u.port or 11434
        self.num_predict, self.num_ctx, self.keep_alive, self.temperature, self.seed = int(num_predict), int(num_ctx), keep_alive, float(temperature), int(seed)
        self.response_schema, self.connect_timeout = response_schema, float(connect_timeout)
        self.last_metrics: Dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"StreamingOllama(model={self.model!r}, host={self.host!r}, port={self.port})"

    # --------------------------------------------------------------------------------------------- plumbing
    def _connect(self, remaining: float) -> http.client.HTTPConnection:
        try:
            return http.client.HTTPConnection(self.host, self.port, timeout=max(0.2, min(self.connect_timeout, remaining)))
        except Exception as e:                                                      # pragma: no cover - constructor does not connect
            raise ProviderUnavailable(f"cannot reach Ollama: {e}") from e

    def _post_stream(self, path: str, body: Dict[str, Any], deadline_abs: float, t0: float):
        """Yield decoded NDJSON objects. Closes the connection (=> Ollama cancels) on any exit, including the deadline."""
        remaining = deadline_abs - time.monotonic()
        if remaining <= 0:
            raise DeadlineExceeded("no time left")
        conn = self._connect(remaining)
        sock = resp = None
        try:
            try:                                  # PHASE 1, connecting. A refusal or a connect timeout both mean "no server answered": ProviderUnavailable, never DeadlineExceeded. Windows does not refuse
                conn.connect()                    # a closed local port at once (it retries the SYN for about two seconds), so the same unreachable endpoint that Linux refuses
            except (socket.timeout, TimeoutError) as e:      # immediately ran into the connect timeout there and used to be reported as a response deadline (Stage 10N Windows run).
                raise ProviderUnavailable(f"cannot reach Ollama at {self.host}:{self.port}: connect timed out") from e
            except (ConnectionError, OSError) as e:
                raise ProviderUnavailable(f"cannot reach Ollama at {self.host}:{self.port}: {type(e).__name__}") from e
            try:                                  # PHASE 2, connected: now a timeout really is the model being slow, so it stays DeadlineExceeded (with partial metrics)
                sock = conn.sock                  # http.client drops conn.sock for close-delimited replies; keep our own handle
                sock.settimeout(max(0.2, deadline_abs - time.monotonic()))
                conn.request("POST", path, json.dumps(body).encode("utf-8"), {"Content-Type": "application/json"})
                resp = conn.getresponse()
            except (socket.timeout, TimeoutError) as e:
                raise DeadlineExceeded("no response within the deadline") from e
            except (ConnectionError, OSError) as e:
                raise ProviderUnavailable(f"cannot reach Ollama at {self.host}:{self.port}: {type(e).__name__}") from e
            if resp.status != 200:
                detail = resp.read(300).decode("utf-8", "replace")
                if resp.status == 404:
                    raise ProviderUnavailable(f"model {self.model!r} not found in Ollama (ollama list): {detail[:120]}")
                raise (ProviderUnavailable if resp.status >= 500 else ProviderRequestError)(f"HTTP {resp.status}: {detail[:160]}")
            while True:
                left = deadline_abs - time.monotonic()
                if left <= 0:
                    raise DeadlineExceeded("deadline exceeded while generating")
                sock.settimeout(left)
                try:
                    line = resp.readline()
                except (socket.timeout, TimeoutError) as e:
                    raise DeadlineExceeded("deadline exceeded while generating") from e
                except (ConnectionError, OSError, http.client.HTTPException) as e:
                    raise ProviderUnavailable(f"connection lost: {type(e).__name__}") from e
                if not line:
                    return
                try:
                    yield json.loads(line)
                except ValueError as e:
                    raise ProviderResponseError("stream line is not JSON") from e
        finally:                                                      # closing the socket is what makes Ollama stop generating
            for closer in (lambda: resp and resp.close(), lambda: sock and sock.shutdown(socket.SHUT_RDWR), lambda: sock and sock.close(), conn.close):
                try:
                    closer()
                except Exception:
                    pass

    # --------------------------------------------------------------------------------------------- API
    def generate_bounded(self, system: str, user: str, deadline_s: float) -> ProviderResponse:
        """One chat turn that is guaranteed to return or raise within ~deadline_s seconds. On DeadlineExceeded the exception carries the partial metrics."""
        t0 = time.monotonic()
        deadline_abs = t0 + float(deadline_s)
        body = {"model": self.model, "stream": True, "format": self.response_schema or "json", "keep_alive": self.keep_alive,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": self.temperature, "seed": self.seed, "num_predict": self.num_predict, "num_ctx": self.num_ctx}}
        parts, first_ms, metrics, chunks = [], None, {}, 0
        try:
            for obj in self._post_stream("/api/chat", body, deadline_abs, t0):
                if obj.get("error"):
                    raise ProviderUnavailable(f"Ollama error: {str(obj['error'])[:160]}")
                piece = (obj.get("message") or {}).get("content")
                if isinstance(piece, str) and piece:
                    if first_ms is None:
                        first_ms = (time.monotonic() - t0) * 1000
                    parts.append(piece)
                    chunks += 1
                if obj.get("done"):
                    metrics = {k: obj.get(k) for k in METRIC_KEYS}
        except DeadlineExceeded as e:
            e.metrics = {"first_token_ms": round(first_ms, 1) if first_ms else None, "chunks_received": chunks, "client_elapsed_ms": round((time.monotonic() - t0) * 1000, 1)}
            self.last_metrics = e.metrics
            raise
        text = "".join(parts)
        if not metrics:
            raise ProviderResponseError("stream ended without a final message (connection cut)")
        usage = {**metrics, "first_token_ms": round(first_ms, 1) if first_ms is not None else None, "client_elapsed_ms": round((time.monotonic() - t0) * 1000, 1), "num_ctx": self.num_ctx,
                 "num_predict": self.num_predict, "keep_alive": self.keep_alive}
        self.last_metrics = usage
        return ProviderResponse(text, self.model, usage["client_elapsed_ms"], usage)

    def generate(self, system: str, user: str) -> ProviderResponse:                # LLMProvider contract
        return self.generate_bounded(system, user, 60.0)

    def warm(self, deadline_s: float) -> Dict[str, Any]:
        """Load the model into memory and keep it there: a one-token chat. Returns Ollama's metrics (load_duration is the cold-load cost). Raises ProviderError."""
        t0 = time.monotonic()
        body = {"model": self.model, "stream": True, "keep_alive": self.keep_alive, "messages": [{"role": "user", "content": "Reply with the single word ok."}],
                "options": {"temperature": 0.0, "num_predict": 2, "num_ctx": self.num_ctx}}
        metrics: Dict[str, Any] = {}
        for obj in self._post_stream("/api/chat", body, t0 + float(deadline_s), t0):
            if obj.get("error"):
                raise ProviderUnavailable(f"Ollama error: {str(obj['error'])[:160]}")
            if obj.get("done"):
                metrics = {k: obj.get(k) for k in METRIC_KEYS}
        if not metrics:
            raise ProviderResponseError("warm-up stream ended without a final message")
        metrics["client_elapsed_ms"] = round((time.monotonic() - t0) * 1000, 1)
        return metrics

    def unload(self, deadline_s: float = 10.0) -> None:
        """Ask Ollama to drop the model from memory (used by the benchmark to measure a true cold start)."""
        t0 = time.monotonic()
        for _ in self._post_stream("/api/chat", {"model": self.model, "stream": False, "keep_alive": 0, "messages": []}, t0 + deadline_s, t0):
            pass
