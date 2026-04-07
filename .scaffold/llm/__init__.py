"""LLM provider package — Anthropic, OpenAI-compatible, HuggingFace, plus
harness/model detection."""

from .base import LLMConfig, LLMContext, LLMProvider, LLM_FALLBACK_THRESHOLD
from .config import load_llm_config
from .factory import make_provider
from .harness import HarnessInfo, detect, detect_and_persist, read_current, write_current
from .capabilities import lookup as lookup_capabilities

__all__ = [
    "LLMConfig",
    "LLMContext",
    "LLMProvider",
    "LLM_FALLBACK_THRESHOLD",
    "load_llm_config",
    "make_provider",
    "HarnessInfo",
    "detect",
    "detect_and_persist",
    "read_current",
    "write_current",
    "lookup_capabilities",
]
