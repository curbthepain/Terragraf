"""
Provider factory — single entry point to construct an LLM provider from config.
"""

from .base import LLMConfig, LLMProvider
from .config import load_llm_config


def make_provider(config: LLMConfig | None = None) -> LLMProvider | None:
    """
    Build the appropriate provider from config.
    Returns None if config is None or provider is unrecognized.
    """
    if config is None:
        config = load_llm_config()
    if config is None:
        return None

    if config.provider == "anthropic":
        from .providers import AnthropicProvider
        return AnthropicProvider(config)

    if config.provider in ("openai", "openai_compatible", "ollama"):
        from .providers import OpenAICompatibleProvider
        return OpenAICompatibleProvider(config)

    if config.provider in ("huggingface", "hf"):
        from .providers import HuggingFaceProvider
        return HuggingFaceProvider(config)

    return None
