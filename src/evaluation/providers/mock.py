"""Deterministic MOCK provider for contract tests. Its outputs are whatever the test scripted: they say NOTHING about real LLM
quality, and every result produced through it carries provenance.is_mock=True."""
from __future__ import annotations

import json
from typing import Any, Callable, List, Union

from .base import LLMProvider, ProviderResponse

ScriptItem = Union[str, dict, BaseException, Callable[[str, str], Any]]


class MockProvider(LLMProvider):
    name = "mock"
    is_mock = True

    def __init__(self, script: List[ScriptItem] | ScriptItem, model: str = "mock-deterministic", repeat_last: bool = True):
        self.script = list(script) if isinstance(script, list) else [script]
        self.model = model
        self.repeat_last = repeat_last
        self.calls: list[dict] = []

    def generate(self, system: str, user: str) -> ProviderResponse:
        idx = len(self.calls)
        self.calls.append({"system": system, "user": user})
        if idx >= len(self.script):
            if not (self.repeat_last and self.script):
                raise AssertionError("MockProvider script exhausted")
            item = self.script[-1]
        else:
            item = self.script[idx]
        if callable(item):
            item = item(system, user)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, ProviderResponse):
            return item
        text = item if isinstance(item, str) else json.dumps(item)
        return ProviderResponse(text=text, model=self.model, latency_ms=0.0, usage={"mock": True})
