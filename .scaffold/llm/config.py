"""
LLM configuration loader — reads from settings JSON or environment variables.
"""

import json
import os
from pathlib import Path

from .base import LLMConfig


_SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / ".terragraf_settings.json"


def load_llm_config() -> LLMConfig | None:
    """
    Load LLM config from settings JSON or environment variables.
    Returns None if no provider is configured.

    Priority: settings JSON "llm" section > environment variables.
    """
    config = _load_from_settings()
    if not config:
        config = _load_from_env()
    if not config:
        return None

    return LLMConfig(
        provider=config.get("provider", ""),
        api_key=config.get("api_key", ""),
        model=config.get("model", ""),
        base_url=config.get("base_url", ""),
        max_tokens=int(config.get("max_tokens", 2048)),
        temperature=float(config.get("temperature", 0.7)),
    )


def _load_from_settings() -> dict | None:
    """Read llm section from .terragraf_settings.json."""
    try:
        data = json.loads(_SETTINGS_FILE.read_text())
        llm = data.get("llm", {})
        if llm.get("provider") and llm.get("api_key"):
            return llm
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _load_from_env() -> dict | None:
    """
    Check environment variables for LLM configuration.

    Checks: ANTHROPIC_API_KEY, OPENAI_API_KEY,
            TERRAGRAF_LLM_PROVIDER, TERRAGRAF_LLM_MODEL,
            TERRAGRAF_LLM_BASE_URL, TERRAGRAF_LLM_MAX_TOKENS.
    """
    provider = os.environ.get("TERRAGRAF_LLM_PROVIDER", "")
    api_key = ""

    if not provider:
        # Auto-detect from API key env vars (cloud first, then local)
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
            api_key = os.environ["ANTHROPIC_API_KEY"]
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
            api_key = os.environ["OPENAI_API_KEY"]
        elif os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_API_BASE"):
            provider = "ollama"
            api_key = "ollama"  # placeholder; ollama ignores it
        elif os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE"):
            provider = "huggingface"
            api_key = "local"  # placeholder; HF local ignores it
        else:
            return None
    else:
        # Explicit provider — look for the matching key
        if provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        elif provider in ("huggingface", "hf"):
            api_key = "local"
        elif provider == "ollama":
            api_key = "ollama"
        else:
            api_key = os.environ.get("OPENAI_API_KEY", "")

    if not api_key:
        return None

    # Per-provider model defaults from env
    model = os.environ.get("TERRAGRAF_LLM_MODEL", "")
    if not model:
        if provider == "ollama":
            model = os.environ.get("OLLAMA_MODEL", "")
        elif provider in ("huggingface", "hf"):
            model = os.environ.get("HF_MODEL", "")

    base_url = os.environ.get("TERRAGRAF_LLM_BASE_URL", "")
    if not base_url and provider == "ollama":
        base_url = os.environ.get("OLLAMA_API_BASE") or "http://localhost:11434/v1"

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
        "max_tokens": os.environ.get("TERRAGRAF_LLM_MAX_TOKENS", "2048"),
        "temperature": os.environ.get("TERRAGRAF_LLM_TEMPERATURE", "0.7"),
    }
