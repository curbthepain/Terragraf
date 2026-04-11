"""
LLM provider abstraction layer — shared types and constants.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


LLM_FALLBACK_THRESHOLD = 0.5


@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""
    provider: str = ""          # "anthropic" or "openai"
    api_key: str = ""
    model: str = ""
    base_url: str = ""          # for openai-compatible overrides (ollama, vllm, etc.)
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class LLMContext:
    """Context passed to an LLM provider for a query."""
    query: str = ""
    route_matches: list = field(default_factory=list)
    header_matches: list = field(default_factory=list)
    best_score: float = 0.0


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def stream(self, context: LLMContext) -> Iterator[str]:
        """Yield text tokens as they arrive. Raises on error."""
        ...

    @abstractmethod
    def validate(self) -> bool:
        """Return True if the provider is configured and reachable."""
        ...
