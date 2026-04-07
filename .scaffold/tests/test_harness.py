"""Tests for the universal harness/model registry (.scaffold/llm/harness.py)
and capability lookup."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm.harness import (
    HarnessInfo,
    detect,
    detect_and_persist,
    read_current,
    write_current,
)
from llm.capabilities import lookup as lookup_caps, CAPABILITIES


# ── env helper ──────────────────────────────────────────────────────

_HARNESS_VARS = (
    "TERRAGRAF_HARNESS",
    "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT",
    "CLAUDE_MODEL", "ANTHROPIC_MODEL",
    "CURSOR_TRACE_ID", "CURSOR_AGENT", "CURSOR_SESSION_ID", "CURSOR_MODEL",
    "WINDSURF_SESSION_ID", "CODEIUM_API_KEY", "WINDSURF_IDE", "WINDSURF_MODEL",
    "CONTINUE_SESSION_ID", "CONTINUE_GLOBAL_DIR", "CONTINUE_API_KEY",
    "CONTINUE_MODEL",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
    "OLLAMA_HOST", "OLLAMA_API_BASE", "OLLAMA_MODEL",
    "HF_HOME", "TRANSFORMERS_CACHE", "HF_MODEL",
    "TERRAGRAF_LLM_PROVIDER", "TERRAGRAF_LLM_MODEL",
)


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Strip every harness/model env var so detect() starts from zero.
    Also short-circuits the QApplication detection so leftover Qt instances
    from other tests don't pollute these tests with terra_native results."""
    for v in _HARNESS_VARS:
        monkeypatch.delenv(v, raising=False)
    # Force settings file to a non-existent tmp path so detection
    # never accidentally picks up the user's real .terragraf_settings.json
    fake_settings = tmp_path / "no_such_settings.json"
    monkeypatch.setattr(
        "llm.config._SETTINGS_FILE", fake_settings, raising=True,
    )
    # Other tests in the suite construct QApplication instances that linger
    # in sys.modules['PySide6.QtWidgets']. Force detection to ignore Qt.
    monkeypatch.setattr("llm.harness._qt_app_running", lambda: False)
    yield


# ── Detection ───────────────────────────────────────────────────────

class TestDetectHarness:
    def test_unknown_when_no_signal(self, clean_env):
        info = detect()
        assert info.name == "unknown"
        assert info.provider == "unknown"
        assert info.source == "no_signal"

    def test_detect_claude_code_via_claudecode_env(self, clean_env, monkeypatch):
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("CLAUDE_MODEL", "claude-opus-4-6")
        info = detect()
        assert info.name == "claude_code"
        assert info.provider == "anthropic"
        assert info.model == "claude-opus-4-6"
        assert info.source == "env:CLAUDECODE"

    def test_detect_claude_code_default_model(self, clean_env, monkeypatch):
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
        info = detect()
        assert info.name == "claude_code"
        assert info.model == "claude-opus-4-6"  # default

    def test_detect_cursor(self, clean_env, monkeypatch):
        monkeypatch.setenv("CURSOR_TRACE_ID", "abc123")
        monkeypatch.setenv("CURSOR_MODEL", "claude-3-5-sonnet")
        info = detect()
        assert info.name == "cursor"
        assert info.provider == "anthropic"
        assert "claude-3-5-sonnet" in info.model

    def test_detect_cursor_with_gpt(self, clean_env, monkeypatch):
        monkeypatch.setenv("CURSOR_AGENT", "agent-1")
        monkeypatch.setenv("CURSOR_MODEL", "gpt-4o")
        info = detect()
        assert info.name == "cursor"
        assert info.provider == "openai"

    def test_detect_windsurf(self, clean_env, monkeypatch):
        monkeypatch.setenv("WINDSURF_SESSION_ID", "xyz")
        monkeypatch.setenv("WINDSURF_MODEL", "claude-sonnet")
        info = detect()
        assert info.name == "windsurf"
        assert info.provider == "anthropic"

    def test_detect_continue(self, clean_env, monkeypatch):
        monkeypatch.setenv("CONTINUE_SESSION_ID", "qqq")
        monkeypatch.setenv("CONTINUE_MODEL", "gpt-4o-mini")
        info = detect()
        assert info.name == "continue"
        assert info.provider == "openai"

    def test_explicit_override_wins(self, clean_env, monkeypatch):
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("TERRAGRAF_HARNESS", "cursor")
        info = detect()
        assert info.name == "cursor"
        assert info.source == "env:TERRAGRAF_HARNESS"

    def test_terra_cli_with_anthropic_key(self, clean_env, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
        info = detect()
        assert info.name == "terra_cli"
        assert info.provider == "anthropic"

    def test_terra_cli_with_hf_home(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setenv("HF_HOME", str(tmp_path))
        monkeypatch.setenv("HF_MODEL", "meta-llama/Llama-3-8B-Instruct")
        info = detect()
        assert info.name == "terra_cli"
        assert info.provider == "huggingface"
        assert info.model == "meta-llama/Llama-3-8B-Instruct"

    def test_terra_cli_with_ollama_host(self, clean_env, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "llama3")
        info = detect()
        assert info.name == "terra_cli"
        assert info.provider == "ollama"


# ── Capabilities ────────────────────────────────────────────────────

class TestCapabilities:
    def test_lookup_specific_anthropic_opus(self):
        caps = lookup_caps("anthropic", "claude-opus-4-6")
        assert caps["streaming"] is True
        assert caps["tools"] is True
        assert caps["context_tokens"] == 1_000_000

    def test_lookup_falls_back_to_provider_wildcard(self):
        caps = lookup_caps("anthropic", "claude-future-model-not-listed")
        assert caps["streaming"] is True
        assert caps["context_tokens"] == 200_000  # anthropic:* default

    def test_lookup_unknown_provider_falls_back_to_unknown(self):
        caps = lookup_caps("madeup", "fake")
        assert caps["streaming"] is False
        assert caps["context_tokens"] == 4_096

    def test_huggingface_wildcard(self):
        caps = lookup_caps("huggingface", "tiny-gpt2-no-such-entry")
        assert caps["tools"] is False
        assert caps["context_tokens"] == 4_096

    def test_lookup_returns_copy_not_reference(self):
        c1 = lookup_caps("anthropic", "claude-opus-4-6")
        c1["streaming"] = "mutated"
        c2 = lookup_caps("anthropic", "claude-opus-4-6")
        assert c2["streaming"] is True


# ── Persistence ─────────────────────────────────────────────────────

class TestPersistence:
    def test_write_and_read_current_roundtrip(self, clean_env, tmp_path,
                                              monkeypatch):
        target = tmp_path / "CURRENT.json"
        monkeypatch.setattr("llm.harness._CURRENT_FILE", target)
        info = HarnessInfo(
            name="claude_code",
            provider="anthropic",
            model="claude-opus-4-6",
            source="env:CLAUDECODE",
            capabilities={"streaming": True, "context_tokens": 1_000_000},
        )
        write_current(info)
        assert target.exists()

        loaded = read_current()
        assert loaded is not None
        assert loaded.name == "claude_code"
        assert loaded.provider == "anthropic"
        assert loaded.model == "claude-opus-4-6"
        assert loaded.capabilities["context_tokens"] == 1_000_000

    def test_read_current_missing(self, clean_env, tmp_path, monkeypatch):
        monkeypatch.setattr("llm.harness._CURRENT_FILE", tmp_path / "nope.json")
        assert read_current() is None

    def test_detect_and_persist(self, clean_env, tmp_path, monkeypatch):
        target = tmp_path / "CURRENT.json"
        monkeypatch.setattr("llm.harness._CURRENT_FILE", target)
        monkeypatch.setenv("CLAUDECODE", "1")
        info = detect_and_persist()
        assert info.name == "claude_code"
        assert target.exists()
        data = json.loads(target.read_text())
        assert data["name"] == "claude_code"


# ── HuggingFace provider lazy import ────────────────────────────────

class TestHuggingFaceProvider:
    def test_construct_does_not_import_transformers(self):
        # transformers might already be loaded by other tests; we just check
        # that constructing the provider doesn't crash and the lazy state
        # is correct
        from llm.factory import make_provider
        from llm.base import LLMConfig
        cfg = LLMConfig(
            provider="huggingface", api_key="local",
            model="sshleifer/tiny-gpt2", base_url="",
        )
        p = make_provider(cfg)
        assert type(p).__name__ == "HuggingFaceProvider"
        assert p._pipeline is None
        assert p._tokenizer is None

    def test_factory_routes_huggingface(self):
        from llm.factory import make_provider
        from llm.base import LLMConfig
        cfg = LLMConfig(
            provider="huggingface", api_key="local",
            model="anything", base_url="",
        )
        p = make_provider(cfg)
        assert p is not None
        assert type(p).__name__ == "HuggingFaceProvider"

    def test_factory_routes_hf_alias(self):
        from llm.factory import make_provider
        from llm.base import LLMConfig
        cfg = LLMConfig(
            provider="hf", api_key="local",
            model="anything", base_url="",
        )
        p = make_provider(cfg)
        assert type(p).__name__ == "HuggingFaceProvider"

    def test_factory_routes_ollama_to_openai_compat(self):
        from llm.factory import make_provider
        from llm.base import LLMConfig
        cfg = LLMConfig(
            provider="ollama", api_key="ollama",
            model="llama3", base_url="http://localhost:11434/v1",
        )
        p = make_provider(cfg)
        assert type(p).__name__ == "OpenAICompatibleProvider"

    def test_validate_returns_bool(self):
        from llm.factory import make_provider
        from llm.base import LLMConfig
        cfg = LLMConfig(
            provider="huggingface", api_key="local",
            model="sshleifer/tiny-gpt2", base_url="",
        )
        p = make_provider(cfg)
        # Whether transformers is installed or not, validate should not raise
        result = p.validate()
        assert isinstance(result, bool)
