"""
Static provider:model capability table.

Used by `llm.harness.detect()` and by terra commands that need to size their
prompts, decide whether to enable streaming, vision, or tool calling.
"""

from __future__ import annotations

# Wildcards: "provider:*" matches any model under that provider.
# Specific entries: "provider:model_id" override the wildcard.
CAPABILITIES: dict[str, dict] = {
    # ── Anthropic ──────────────────────────────────────────────────
    "anthropic:*": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 200_000, "output_tokens": 8_192,
    },
    "anthropic:claude-opus-4-6": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 1_000_000, "output_tokens": 32_000,
    },
    "anthropic:claude-sonnet-4-6": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 1_000_000, "output_tokens": 32_000,
    },
    "anthropic:claude-haiku-4-5-20251001": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 200_000, "output_tokens": 8_192,
    },
    "anthropic:claude-3-5-haiku-20241022": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 200_000, "output_tokens": 8_192,
    },

    # ── OpenAI ─────────────────────────────────────────────────────
    "openai:*": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 128_000, "output_tokens": 4_096,
    },
    "openai:gpt-4o": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 128_000, "output_tokens": 16_384,
    },
    "openai:gpt-4o-mini": {
        "streaming": True, "tools": True, "vision": True,
        "context_tokens": 128_000, "output_tokens": 16_384,
    },

    # ── Ollama / OpenAI-compatible local servers ───────────────────
    "ollama:*": {
        "streaming": True, "tools": False, "vision": False,
        "context_tokens": 32_768, "output_tokens": 4_096,
    },

    # ── HuggingFace local ──────────────────────────────────────────
    "huggingface:*": {
        "streaming": True, "tools": False, "vision": False,
        "context_tokens": 4_096, "output_tokens": 1_024,
    },
    "huggingface:meta-llama/Llama-3-8B-Instruct": {
        "streaming": True, "tools": False, "vision": False,
        "context_tokens": 8_192, "output_tokens": 2_048,
    },
    "huggingface:Qwen/Qwen2.5-7B-Instruct": {
        "streaming": True, "tools": False, "vision": False,
        "context_tokens": 32_768, "output_tokens": 4_096,
    },

    # ── Unknown fallback ───────────────────────────────────────────
    "unknown:*": {
        "streaming": False, "tools": False, "vision": False,
        "context_tokens": 4_096, "output_tokens": 1_024,
    },
}


def lookup(provider: str, model: str) -> dict:
    """
    Return the capability dict for `provider:model`. Falls back to
    `provider:*` then `unknown:*`. Always returns a non-None dict.
    """
    key = f"{provider}:{model}"
    if key in CAPABILITIES:
        return dict(CAPABILITIES[key])
    wildcard = f"{provider}:*"
    if wildcard in CAPABILITIES:
        return dict(CAPABILITIES[wildcard])
    return dict(CAPABILITIES["unknown:*"])
