"""
Harness + model detection for Terragraf.

Detects which AI harness is driving terra (Claude Code, Cursor, Windsurf,
Continue, the terra Qt app, or a bare CLI invocation), what provider/model
that harness is using, and persists the live answer to .scaffold/llm/CURRENT.json.

Universality: every terra subsystem that needs to know "who is calling and
what model is in play" goes through `detect()`. This is the single source of
truth — no scattered env-var lookups elsewhere in the codebase.

Public API:
    detect() -> HarnessInfo
    write_current(info) -> None
    read_current() -> HarnessInfo | None
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .capabilities import lookup as lookup_caps

_LLM_DIR = Path(__file__).resolve().parent
_CURRENT_FILE = _LLM_DIR / "CURRENT.json"


@dataclass
class HarnessInfo:
    name: str           # claude_code | cursor | windsurf | continue
                        # | terra_native | terra_cli | unknown
    provider: str       # anthropic | openai | huggingface | ollama | unknown
    model: str          # active model id
    source: str         # how detected, e.g. "env:CLAUDECODE"
    capabilities: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HarnessInfo":
        return cls(
            name=data.get("name", "unknown"),
            provider=data.get("provider", "unknown"),
            model=data.get("model", "unknown"),
            source=data.get("source", ""),
            capabilities=data.get("capabilities", {}) or {},
        )


# ── Env-var fingerprints ────────────────────────────────────────────

_CLAUDE_CODE_VARS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")
_CURSOR_VARS = ("CURSOR_TRACE_ID", "CURSOR_AGENT", "CURSOR_SESSION_ID")
_WINDSURF_VARS = ("WINDSURF_SESSION_ID", "CODEIUM_API_KEY", "WINDSURF_IDE")
_CONTINUE_VARS = ("CONTINUE_SESSION_ID", "CONTINUE_GLOBAL_DIR", "CONTINUE_API_KEY")


def _any_env(names: tuple[str, ...]) -> str | None:
    """Return the first env var name from `names` that is set, else None."""
    for n in names:
        if os.environ.get(n):
            return n
    return None


# ── Model fingerprinting per harness ────────────────────────────────

def _claude_code_model() -> tuple[str, str]:
    """Return (provider, model) for Claude Code. Always anthropic."""
    model = (
        os.environ.get("CLAUDE_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or "claude-opus-4-6"
    )
    return "anthropic", model


def _cursor_model() -> tuple[str, str]:
    """Cursor exposes the model via CURSOR_MODEL when set."""
    model = os.environ.get("CURSOR_MODEL") or "unknown"
    # Cursor can drive Anthropic or OpenAI under the hood
    if "claude" in model.lower():
        return "anthropic", model
    if "gpt" in model.lower():
        return "openai", model
    return "unknown", model


def _windsurf_model() -> tuple[str, str]:
    model = os.environ.get("WINDSURF_MODEL") or "unknown"
    if "claude" in model.lower():
        return "anthropic", model
    if "gpt" in model.lower():
        return "openai", model
    return "unknown", model


def _continue_model() -> tuple[str, str]:
    model = os.environ.get("CONTINUE_MODEL") or "unknown"
    if "claude" in model.lower():
        return "anthropic", model
    if "gpt" in model.lower():
        return "openai", model
    return "unknown", model


def _terra_settings_model() -> tuple[str, str]:
    """
    Read .terragraf_settings.json [llm] and env-var fallback chain.
    Returns (provider, model). Falls back to ('unknown', 'unknown').
    """
    try:
        from .config import load_llm_config
        cfg = load_llm_config()
        if cfg is not None and cfg.provider:
            return cfg.provider, cfg.model or "unknown"
    except Exception:
        pass

    # Env-var auto-detect for local-model setups (HF / Ollama)
    if os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_API_BASE"):
        return "ollama", os.environ.get("OLLAMA_MODEL", "unknown")
    if os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE"):
        return "huggingface", os.environ.get("HF_MODEL", "unknown")

    return "unknown", "unknown"


def _qt_app_running() -> bool:
    """
    Heuristic: in the Qt app process, QApplication.instance() returns non-None.
    Cheap check that does NOT import PySide6 if not already loaded.
    """
    qt_mod = sys.modules.get("PySide6.QtWidgets")
    if qt_mod is None:
        return False
    try:
        return qt_mod.QApplication.instance() is not None
    except Exception:
        return False


# ── Public detection ────────────────────────────────────────────────

def detect() -> HarnessInfo:
    """
    Detect the active harness and model. First match wins.
    Always returns a HarnessInfo (never None) — falls back to 'unknown'.
    """
    # 0. Explicit override
    override = os.environ.get("TERRAGRAF_HARNESS")
    if override:
        provider, model = _terra_settings_model()
        info = HarnessInfo(
            name=override,
            provider=provider,
            model=model,
            source="env:TERRAGRAF_HARNESS",
        )
        info.capabilities = lookup_caps(provider, model)
        return info

    # 1. Claude Code
    hit = _any_env(_CLAUDE_CODE_VARS)
    if hit:
        provider, model = _claude_code_model()
        info = HarnessInfo(
            name="claude_code", provider=provider, model=model,
            source=f"env:{hit}",
        )
        info.capabilities = lookup_caps(provider, model)
        return info

    # 2. Cursor
    hit = _any_env(_CURSOR_VARS)
    if hit:
        provider, model = _cursor_model()
        info = HarnessInfo(
            name="cursor", provider=provider, model=model,
            source=f"env:{hit}",
        )
        info.capabilities = lookup_caps(provider, model)
        return info

    # 3. Windsurf
    hit = _any_env(_WINDSURF_VARS)
    if hit:
        provider, model = _windsurf_model()
        info = HarnessInfo(
            name="windsurf", provider=provider, model=model,
            source=f"env:{hit}",
        )
        info.capabilities = lookup_caps(provider, model)
        return info

    # 4. Continue
    hit = _any_env(_CONTINUE_VARS)
    if hit:
        provider, model = _continue_model()
        info = HarnessInfo(
            name="continue", provider=provider, model=model,
            source=f"env:{hit}",
        )
        info.capabilities = lookup_caps(provider, model)
        return info

    # 5. Terra Qt app running in this process
    if _qt_app_running():
        provider, model = _terra_settings_model()
        info = HarnessInfo(
            name="terra_native", provider=provider, model=model,
            source="qt_application_instance",
        )
        info.capabilities = lookup_caps(provider, model)
        return info

    # 6. Bare terra CLI invocation
    provider, model = _terra_settings_model()
    if provider != "unknown":
        info = HarnessInfo(
            name="terra_cli", provider=provider, model=model,
            source="settings_or_env",
        )
        info.capabilities = lookup_caps(provider, model)
        return info

    # 7. Unknown
    info = HarnessInfo(
        name="unknown", provider="unknown", model="unknown",
        source="no_signal",
    )
    info.capabilities = lookup_caps("unknown", "unknown")
    return info


def write_current(info: HarnessInfo) -> None:
    """Persist the latest detection result to CURRENT.json."""
    try:
        _CURRENT_FILE.write_text(
            json.dumps(info.to_dict(), indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # never fail terra startup on a missing dir


def read_current() -> HarnessInfo | None:
    """Read the cached detection result. Returns None if missing/corrupt."""
    if not _CURRENT_FILE.exists():
        return None
    try:
        data = json.loads(_CURRENT_FILE.read_text(encoding="utf-8"))
        return HarnessInfo.from_dict(data)
    except (OSError, json.JSONDecodeError):
        return None


def detect_and_persist() -> HarnessInfo:
    """Convenience: detect() then write_current()."""
    info = detect()
    write_current(info)
    return info
