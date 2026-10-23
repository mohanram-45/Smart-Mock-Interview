"""Environment configuration. Nothing is read at import time; nothing is configured by default; the legacy backend is the default.

  SMART_EVALUATION_BACKEND   legacy (default) | llm
  SMART_LLM_PROVIDER         none (default) | ollama | anthropic | openai_compatible | mock
  SMART_LLM_MODEL            model name (required for every real provider; no default is assumed)
  SMART_LLM_BASE_URL         override base URL (ollama defaults to OLLAMA_HOST or http://127.0.0.1:11434)
  SMART_LLM_API_KEY          key for hosted providers (ANTHROPIC_API_KEY / OPENAI_API_KEY are also read for their own provider)
  SMART_LLM_ALLOW_PAID       must be '1' to build a hosted (paid) provider
  SMART_LLM_TIMEOUT_S        per-call timeout, default 60, allowed 1..300
  SMART_LLM_MAX_RETRIES      bounded retries for transient errors, default 2, allowed 0..5
  SMART_LLM_NUM_CTX          Ollama context window in tokens, default 8192, allowed 2048..131072
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .errors import ProviderNotConfigured
from .providers.base import LLMProvider

BACKENDS = ("legacy", "llm")
PROVIDERS = ("none", "ollama", "anthropic", "openai_compatible", "mock")


@dataclass(frozen=True)
class EvaluationConfig:
    backend: str = "legacy"
    provider: str = "none"
    model: str = ""
    base_url: str = ""
    timeout_s: float = 60.0
    max_retries: int = 2
    allow_paid: bool = False
    num_ctx: int = 8192

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "EvaluationConfig":
        e = os.environ if env is None else env
        backend = (e.get("SMART_EVALUATION_BACKEND") or "legacy").strip().lower()
        if backend not in BACKENDS:
            raise ValueError(f"SMART_EVALUATION_BACKEND must be one of {BACKENDS}, got {backend!r}")
        provider = (e.get("SMART_LLM_PROVIDER") or "none").strip().lower()
        if provider not in PROVIDERS:
            raise ValueError(f"SMART_LLM_PROVIDER must be one of {PROVIDERS}, got {provider!r}")
        try:
            timeout = float(e.get("SMART_LLM_TIMEOUT_S") or 60)
            retries = int(e.get("SMART_LLM_MAX_RETRIES") or 2)
            num_ctx = int(e.get("SMART_LLM_NUM_CTX") or 8192)
        except ValueError as exc:
            raise ValueError(f"SMART_LLM_TIMEOUT_S / SMART_LLM_MAX_RETRIES must be numbers: {exc}") from exc
        if not 1 <= timeout <= 300:
            raise ValueError("SMART_LLM_TIMEOUT_S must be within 1..300")
        if not 0 <= retries <= 5:
            raise ValueError("SMART_LLM_MAX_RETRIES must be within 0..5")
        if not 2048 <= num_ctx <= 131072:
            raise ValueError("SMART_LLM_NUM_CTX must be within 2048..131072")
        return cls(backend=backend, provider=provider, model=(e.get("SMART_LLM_MODEL") or "").strip(),
                   base_url=(e.get("SMART_LLM_BASE_URL") or "").strip(), timeout_s=timeout, max_retries=retries,
                   allow_paid=(e.get("SMART_LLM_ALLOW_PAID") or "").strip() == "1", num_ctx=num_ctx)

    @property
    def llm_enabled(self) -> bool:
        return self.backend == "llm"


def build_provider(cfg: EvaluationConfig, env: Optional[Mapping[str, str]] = None) -> LLMProvider:
    """Raises ProviderNotConfigured with an actionable message; never guesses a model, key or endpoint."""
    from .providers.http import AnthropicProvider, OllamaProvider, OpenAICompatibleProvider
    from .providers.mock import MockProvider
    e = os.environ if env is None else env
    p = cfg.provider
    if p == "none":
        raise ProviderNotConfigured("no LLM provider configured (set SMART_LLM_PROVIDER and SMART_LLM_MODEL)")
    if p == "mock":
        raise ProviderNotConfigured("the mock provider is test-only and needs a script; construct MockProvider(...) in code")
    if not cfg.model:
        raise ProviderNotConfigured(f"SMART_LLM_MODEL is required for provider {p!r} (no default model is assumed)")
    if p == "ollama":
        base = cfg.base_url or (e.get("OLLAMA_HOST") or "http://127.0.0.1:11434")
        return OllamaProvider(cfg.model, base, cfg.timeout_s, num_ctx=cfg.num_ctx)
    if not cfg.allow_paid:
        raise ProviderNotConfigured(f"provider {p!r} is a hosted, paid API: set SMART_LLM_ALLOW_PAID=1 to approve calls")
    if p == "anthropic":
        key = e.get("SMART_LLM_API_KEY") or e.get("ANTHROPIC_API_KEY") or ""
        if not key:
            raise ProviderNotConfigured("no API key: set SMART_LLM_API_KEY (or ANTHROPIC_API_KEY)")
        return AnthropicProvider(cfg.model, cfg.base_url or "https://api.anthropic.com", cfg.timeout_s, key)
    key = e.get("SMART_LLM_API_KEY") or e.get("OPENAI_API_KEY") or ""
    if not cfg.base_url and not key:
        raise ProviderNotConfigured("no API key: set SMART_LLM_API_KEY (or OPENAI_API_KEY) and optionally SMART_LLM_BASE_URL")
    return OpenAICompatibleProvider(cfg.model, cfg.base_url or "https://api.openai.com", cfg.timeout_s, key)
