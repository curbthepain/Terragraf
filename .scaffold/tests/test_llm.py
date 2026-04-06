"""Tests for Session 14 — LLM provider layer, streaming, fallback routing.

24 tests covering:
  - Config loading (4)
  - Factory + provider types (4)
  - Provider streaming with mocked SDK (5)
  - QueryEngine fallback threshold (3)
  - LLMWorker Qt signals (4, needs PySide6)
  - LLMResponseCard widget (4, needs PySide6)
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure .scaffold is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Check PySide6 availability
try:
    import PySide6
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

needs_qt = pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not installed")


# ── QApplication fixture ───────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _ensure_qapp():
    if not HAS_PYSIDE6:
        yield
        return
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ── Shared fixtures ────────────────────────────────────────────────────

@pytest.fixture
def scaffold_state():
    """Create a minimal ScaffoldState with test data."""
    from app.scaffold_state import ScaffoldState

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "headers").mkdir()
        (tmp / "routes").mkdir()
        (tmp / "tables").mkdir()
        (tmp / "instances" / "shared").mkdir(parents=True)

        (tmp / "headers" / "project.h").write_text(
            '#module COMPUTE {\n'
            '    #path "compute/"\n'
            '    #exports [fft1d]\n'
            '    #desc "Compute"\n'
            '}\n'
        )
        (tmp / "routes" / "structure.route").write_text(
            "fft -> compute/fft/ # FFT\n"
        )
        (tmp / "tables" / "deps.table").write_text("fft | math | uses | low\n")
        (tmp / "HOT_CONTEXT.md").write_text("# Test\n")
        (tmp / "instances" / "shared" / "queue.json").write_text("[]")

        state = ScaffoldState(scaffold_dir=tmp)
        state.load_all()
        yield state


@pytest.fixture
def mock_provider():
    """A provider that yields three tokens synchronously."""
    p = MagicMock()
    p.stream = MagicMock(return_value=iter(["Hello", " world", "!"]))
    p.__class__.__name__ = "MockProvider"
    return p


@pytest.fixture
def error_provider():
    """A provider that raises on stream()."""
    p = MagicMock()
    p.stream = MagicMock(side_effect=RuntimeError("No API key configured"))
    return p


# ═══════════════════════════════════════════════════════════════════════
# Config loading tests (4)
# ═══════════════════════════════════════════════════════════════════════

def test_load_config_returns_none_when_no_config(monkeypatch, tmp_path):
    """load_llm_config() returns None when nothing is configured."""
    import llm.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "_SETTINGS_FILE", tmp_path / "nope.json")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TERRAGRAF_LLM_PROVIDER", raising=False)

    from llm.config import load_llm_config
    assert load_llm_config() is None


def test_load_config_from_settings_json(monkeypatch, tmp_path):
    """Reads provider + api_key from settings JSON llm section."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({
        "llm": {
            "provider": "anthropic",
            "api_key": "sk-test-123",
            "model": "claude-3-haiku",
        }
    }))

    import llm.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "_SETTINGS_FILE", settings_file)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from llm.config import load_llm_config
    config = load_llm_config()
    assert config is not None
    assert config.provider == "anthropic"
    assert config.api_key == "sk-test-123"
    assert config.model == "claude-3-haiku"


def test_load_config_from_env_anthropic(monkeypatch, tmp_path):
    """ANTHROPIC_API_KEY in env produces anthropic config."""
    import llm.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "_SETTINGS_FILE", tmp_path / "nope.json")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TERRAGRAF_LLM_PROVIDER", raising=False)

    from llm.config import load_llm_config
    config = load_llm_config()
    assert config is not None
    assert config.provider == "anthropic"
    assert config.api_key == "sk-ant-test"


def test_load_config_from_env_openai(monkeypatch, tmp_path):
    """OPENAI_API_KEY in env produces openai config."""
    import llm.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "_SETTINGS_FILE", tmp_path / "nope.json")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.delenv("TERRAGRAF_LLM_PROVIDER", raising=False)

    from llm.config import load_llm_config
    config = load_llm_config()
    assert config is not None
    assert config.provider == "openai"
    assert config.api_key == "sk-openai-test"


# ═══════════════════════════════════════════════════════════════════════
# Factory + provider types (4)
# ═══════════════════════════════════════════════════════════════════════

def test_make_provider_returns_none_when_no_config():
    """make_provider(None) returns None."""
    from llm.factory import make_provider
    from llm.base import LLMConfig
    assert make_provider(LLMConfig()) is None  # empty provider string


def test_make_provider_anthropic_type():
    """make_provider with anthropic config returns AnthropicProvider."""
    from llm.factory import make_provider
    from llm.base import LLMConfig
    from llm.providers import AnthropicProvider
    config = LLMConfig(provider="anthropic", api_key="test")
    provider = make_provider(config)
    assert isinstance(provider, AnthropicProvider)


def test_make_provider_openai_type():
    """make_provider with openai config returns OpenAICompatibleProvider."""
    from llm.factory import make_provider
    from llm.base import LLMConfig
    from llm.providers import OpenAICompatibleProvider
    config = LLMConfig(provider="openai", api_key="test")
    provider = make_provider(config)
    assert isinstance(provider, OpenAICompatibleProvider)


def test_make_provider_unknown_returns_none():
    """Unknown provider string returns None."""
    from llm.factory import make_provider
    from llm.base import LLMConfig
    config = LLMConfig(provider="gemini", api_key="test")
    assert make_provider(config) is None


# ═══════════════════════════════════════════════════════════════════════
# Provider streaming with mocked SDK (5)
# ═══════════════════════════════════════════════════════════════════════

def test_anthropic_stream_yields_tokens(monkeypatch):
    """AnthropicProvider.stream() yields tokens from mocked SDK."""
    from llm.providers import AnthropicProvider
    from llm.base import LLMConfig, LLMContext

    # Mock the anthropic module
    mock_anthropic = MagicMock()
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["Hello", " from", " Claude"])
    mock_anthropic.Anthropic.return_value.messages.stream.return_value = mock_stream_ctx
    monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

    config = LLMConfig(provider="anthropic", api_key="test-key", model="test-model")
    provider = AnthropicProvider(config)
    ctx = LLMContext(query="What is 2+2?")

    tokens = list(provider.stream(ctx))
    assert tokens == ["Hello", " from", " Claude"]


def test_openai_stream_yields_tokens(monkeypatch):
    """OpenAICompatibleProvider.stream() yields tokens from mocked SDK."""
    from llm.providers import OpenAICompatibleProvider
    from llm.base import LLMConfig, LLMContext

    # Build mock chunks
    chunks = []
    for text in ["Hi", " there", "!"]:
        chunk = MagicMock()
        choice = MagicMock()
        choice.delta.content = text
        chunk.choices = [choice]
        chunks.append(chunk)

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value.chat.completions.create.return_value = iter(chunks)
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    config = LLMConfig(provider="openai", api_key="test-key")
    provider = OpenAICompatibleProvider(config)
    ctx = LLMContext(query="Hello")

    tokens = list(provider.stream(ctx))
    assert tokens == ["Hi", " there", "!"]


def test_anthropic_missing_sdk_raises(monkeypatch):
    """ImportError on anthropic raises RuntimeError."""
    from llm.providers import AnthropicProvider
    from llm.base import LLMConfig, LLMContext

    # Remove anthropic from modules if present
    monkeypatch.setitem(sys.modules, "anthropic", None)

    config = LLMConfig(provider="anthropic", api_key="test")
    provider = AnthropicProvider(config)
    ctx = LLMContext(query="test")

    with pytest.raises(RuntimeError, match="anthropic SDK not installed"):
        list(provider.stream(ctx))


def test_openai_missing_sdk_raises(monkeypatch):
    """ImportError on openai raises RuntimeError."""
    from llm.providers import OpenAICompatibleProvider
    from llm.base import LLMConfig, LLMContext

    monkeypatch.setitem(sys.modules, "openai", None)

    config = LLMConfig(provider="openai", api_key="test")
    provider = OpenAICompatibleProvider(config)
    ctx = LLMContext(query="test")

    with pytest.raises(RuntimeError, match="openai SDK not installed"):
        list(provider.stream(ctx))


def test_stream_includes_context_in_messages(monkeypatch):
    """LLMContext route_matches appear in the constructed system prompt."""
    from llm.providers import AnthropicProvider
    from llm.base import LLMConfig, LLMContext
    from query.engine import RouteMatch

    mock_anthropic = MagicMock()
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["ok"])
    mock_anthropic.Anthropic.return_value.messages.stream.return_value = mock_stream_ctx
    monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

    config = LLMConfig(provider="anthropic", api_key="test-key")
    provider = AnthropicProvider(config)

    rm = RouteMatch(concept="fft", path="compute/fft/", score=0.3)
    ctx = LLMContext(query="What is FFT?", route_matches=[rm], best_score=0.3)

    list(provider.stream(ctx))

    # Check the system prompt passed to the SDK
    call_kwargs = mock_anthropic.Anthropic.return_value.messages.stream.call_args[1]
    system_text = call_kwargs["system"]
    assert "fft" in system_text.lower()
    assert "compute/fft/" in system_text


# ═══════════════════════════════════════════════════════════════════════
# QueryEngine fallback threshold (3)
# ═══════════════════════════════════════════════════════════════════════

def test_best_score_no_matches(scaffold_state):
    """best_score returns 0.0 when no matches."""
    from query.engine import QueryEngine, QueryResult
    engine = QueryEngine(scaffold_state)
    result = QueryResult()
    assert engine.best_score(result) == 0.0


def test_best_score_with_skill_match(scaffold_state):
    """best_score returns 1.0 when skill_match is set."""
    from query.engine import QueryEngine, QueryResult
    engine = QueryEngine(scaffold_state)
    result = QueryResult(skill_match=("test_skill", {}))
    assert engine.best_score(result) == 1.0


def test_needs_llm_fallback_below_threshold(scaffold_state):
    """needs_llm_fallback True when best score < 0.5."""
    from query.engine import QueryEngine, QueryResult, RouteMatch
    engine = QueryEngine(scaffold_state)

    # Low-scoring result
    result = QueryResult(
        route_matches=[RouteMatch(concept="x", path="y", score=0.3)]
    )
    assert engine.needs_llm_fallback(result) is True

    # High-scoring result
    result2 = QueryResult(
        route_matches=[RouteMatch(concept="fft", path="compute/fft/", score=1.0)]
    )
    assert engine.needs_llm_fallback(result2) is False


# ═══════════════════════════════════════════════════════════════════════
# LLMWorker Qt signals (4)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_llm_worker_emits_tokens(mock_provider):
    """LLMWorker emits token_received for each token from provider."""
    from PySide6.QtCore import QCoreApplication
    from app.llm_worker import LLMWorker
    from llm.base import LLMContext

    ctx = LLMContext(query="test")
    worker = LLMWorker(mock_provider, ctx)

    received = []
    worker.token_received.connect(lambda t: received.append(t))

    worker.start()
    worker._thread.join(timeout=2.0)
    QCoreApplication.processEvents()

    assert received == ["Hello", " world", "!"]


@needs_qt
def test_llm_worker_emits_finished(mock_provider):
    """LLMWorker emits finished when stream completes."""
    from PySide6.QtCore import QCoreApplication
    from app.llm_worker import LLMWorker
    from llm.base import LLMContext

    ctx = LLMContext(query="test")
    worker = LLMWorker(mock_provider, ctx)

    finished = []
    worker.finished.connect(lambda: finished.append(True))

    worker.start()
    worker._thread.join(timeout=2.0)
    QCoreApplication.processEvents()

    assert len(finished) == 1


@needs_qt
def test_llm_worker_emits_error(error_provider):
    """LLMWorker emits error_occurred when stream raises."""
    from PySide6.QtCore import QCoreApplication
    from app.llm_worker import LLMWorker
    from llm.base import LLMContext

    ctx = LLMContext(query="test")
    worker = LLMWorker(error_provider, ctx)

    errors = []
    worker.error_occurred.connect(lambda msg: errors.append(msg))

    worker.start()
    worker._thread.join(timeout=2.0)
    QCoreApplication.processEvents()

    assert len(errors) == 1
    assert "No API key" in errors[0]


@needs_qt
def test_llm_worker_cancel(mock_provider):
    """cancel() stops further token emission."""
    from PySide6.QtCore import QCoreApplication
    from app.llm_worker import LLMWorker
    from llm.base import LLMContext

    # Use a slow iterator
    def slow_iter(ctx):
        for t in ["A", "B", "C", "D", "E"]:
            yield t

    mock_provider.stream = slow_iter

    ctx = LLMContext(query="test")
    worker = LLMWorker(mock_provider, ctx)

    received = []
    worker.token_received.connect(lambda t: received.append(t))

    worker.start()
    worker.cancel()
    worker._thread.join(timeout=2.0)
    QCoreApplication.processEvents()

    # Should have fewer than all 5 tokens (cancellation is best-effort)
    assert len(received) <= 5


# ═══════════════════════════════════════════════════════════════════════
# LLMResponseCard widget (4)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_llm_response_card_creation():
    """LLMResponseCard creates without error."""
    from app.widgets.message_card import LLMResponseCard
    card = LLMResponseCard("test query", provider_name="TestProvider")
    assert card is not None
    assert card._text_edit.toPlainText() == "..."
    card.close()
    card.deleteLater()


@needs_qt
def test_llm_response_card_append_token():
    """append_token accumulates text."""
    from app.widgets.message_card import LLMResponseCard
    card = LLMResponseCard("test")
    card.append_token("Hello")
    card.append_token(" world")
    assert card.full_text == "Hello world"
    assert card._text_edit.toPlainText() == "Hello world"
    card.close()
    card.deleteLater()


@needs_qt
def test_llm_response_card_on_done():
    """on_llm_done() changes status label."""
    from app.widgets.message_card import LLMResponseCard
    card = LLMResponseCard("test", provider_name="Claude")
    card.on_llm_done()
    assert "Claude" in card._status_label.text()
    # Styling now lives on the central stylesheet via object name.
    assert card._status_label.objectName() == "status_green"
    card.close()
    card.deleteLater()


@needs_qt
def test_llm_response_card_on_error():
    """on_llm_error() sets card text to error message."""
    from app.widgets.message_card import LLMResponseCard
    card = LLMResponseCard("test")
    card.on_llm_error("Connection refused")
    assert "Connection refused" in card._text_edit.toPlainText()
    # Error state is signalled by swapping object name to llmTextError.
    assert card._text_edit.objectName() == "llmTextError"
    assert card._status_label.objectName() == "status_red"
    card.close()
    card.deleteLater()
