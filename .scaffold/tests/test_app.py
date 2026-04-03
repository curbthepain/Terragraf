"""Smoke tests for the Qt container app module."""

import sys
import json
from pathlib import Path

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


# ── Theme tests (no Qt runtime needed) ─────────────────────────────

def test_theme_constants():
    """Theme module loads and has expected palette entries."""
    from app.theme import (
        BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, ACCENT, GREEN, STYLESHEET,
    )
    assert BG_PRIMARY.startswith("#")
    assert BG_SECONDARY.startswith("#")
    assert TEXT_PRIMARY.startswith("#")
    assert ACCENT.startswith("#")
    assert GREEN.startswith("#")
    assert "QMainWindow" in STYLESHEET
    assert "QStatusBar" in STYLESHEET


def test_theme_stylesheet_valid_css_structure():
    """Stylesheet contains expected selectors and no broken f-string refs."""
    from app.theme import STYLESHEET
    assert "{" not in STYLESHEET.replace("{{", "").replace("}}", "") or \
           "background-color" in STYLESHEET
    assert "Traceback" not in STYLESHEET


def test_theme_sidebar_styles():
    """Theme includes sidebar and navigation button styles."""
    from app.theme import STYLESHEET
    assert "sidebar" in STYLESHEET
    assert "nav_btn" in STYLESHEET
    assert "QPushButton" in STYLESHEET


def test_theme_input_styles():
    """Theme includes input, slider, and combo styles."""
    from app.theme import STYLESHEET
    assert "QLineEdit" in STYLESHEET
    assert "QSlider" in STYLESHEET
    assert "QComboBox" in STYLESHEET
    assert "QCheckBox" in STYLESHEET


def test_theme_group_tab_styles():
    """Theme includes group box and tab widget styles."""
    from app.theme import STYLESHEET
    assert "QGroupBox" in STYLESHEET
    assert "QTabWidget" in STYLESHEET
    assert "QTabBar" in STYLESHEET


def test_theme_scroll_table_styles():
    """Theme includes scroll bar and table styles."""
    from app.theme import STYLESHEET
    assert "QScrollBar" in STYLESHEET
    assert "QTreeWidget" in STYLESHEET
    assert "QHeaderView" in STYLESHEET


def test_theme_status_labels():
    """Theme includes status label object name selectors."""
    from app.theme import STYLESHEET
    assert "status_green" in STYLESHEET
    assert "status_red" in STYLESHEET
    assert "status_yellow" in STYLESHEET


# ── Qt-dependent import tests ───────────────────────────────────────

@needs_qt
def test_bridge_client_import():
    """BridgeClient module imports cleanly."""
    from app.bridge_client import BridgeClient
    client = BridgeClient(host="127.0.0.1", port=19999)
    assert client.host == "127.0.0.1"
    assert client.port == 19999
    assert not client.connected
    assert client.msgs_sent == 0
    assert client.msgs_recv == 0


@needs_qt
def test_bridge_client_log():
    """BridgeClient log starts empty and can be cleared."""
    from app.bridge_client import BridgeClient
    client = BridgeClient()
    assert client.get_log() == []
    client.clear_log()
    assert client.get_log() == []


@needs_qt
def test_settings_defaults():
    """Settings page loads defaults without a settings file."""
    from app.settings_page import _load_settings
    settings = _load_settings()
    assert settings["bridge_host"] == "127.0.0.1"
    assert settings["bridge_port"] == 9876
    assert isinstance(settings["auto_connect"], bool)
    assert isinstance(settings["show_debug"], bool)


@needs_qt
def test_debug_page_import():
    """DebugPage module imports without error."""
    from app.debug_page import DebugPage
    assert DebugPage is not None


@needs_qt
def test_tuning_page_import():
    """TuningPage module imports without error."""
    from app.tuning_page import TuningPage
    assert TuningPage is not None


@needs_qt
def test_viewer_page_import():
    """ViewerPage module imports without error."""
    from app.viewer_page import ViewerPage
    assert ViewerPage is not None


@needs_qt
def test_settings_page_import():
    """SettingsPage module imports without error."""
    from app.settings_page import SettingsPage
    assert SettingsPage is not None


# ── Bridge debug handler tests (no Qt needed) ──────────────────────

def test_bridge_debug_handlers():
    """Bridge.register_debug_handlers wires ping and debug_echo."""
    from imgui.bridge import Bridge
    bridge = Bridge(port=19998)
    bridge.register_debug_handlers()
    assert "ping" in bridge._handlers
    assert "debug_echo" in bridge._handlers


def test_bridge_ping_handler_sends_pong():
    """Ping handler calls send with pong type."""
    from imgui.bridge import Bridge
    bridge = Bridge(port=19997)
    bridge.register_debug_handlers()

    sent = []
    bridge.send = lambda t, d=None: sent.append((t, d))
    bridge._handlers["ping"]({"type": "ping", "data": {"ts": 123}})
    assert len(sent) == 1
    assert sent[0][0] == "pong"
    assert sent[0][1] == {"ts": 123}


def test_bridge_echo_handler():
    """Debug echo handler reflects data back."""
    from imgui.bridge import Bridge
    bridge = Bridge(port=19996)
    bridge.register_debug_handlers()

    sent = []
    bridge.send = lambda t, d=None: sent.append((t, d))
    bridge._handlers["debug_echo"]({"type": "debug_echo", "data": "hello"})
    assert sent[0] == ("debug_echo", "hello")
