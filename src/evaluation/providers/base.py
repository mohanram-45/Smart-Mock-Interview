from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ProviderResponse:
    text: str
    model: str = ""
    latency_ms: float = 0.0
    usage: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Provider-independent contract: one blocking call, text in -> text out. Implementations raise `errors.ProviderError`
    subclasses and must never return fabricated text on failure. No provider decides scoring; they only transport text."""
    name: str = "base"
    model: str = ""
    is_mock: bool = False
    paid: bool = False

    @abstractmethod
    def generate(self, system: str, user: str) -> ProviderResponse: ...
