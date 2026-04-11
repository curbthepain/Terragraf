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
    """Theme module loads and has Kohala palette entries."""
    from app.theme import (
        BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, ACCENT, GREEN, RED, STYLESHEET,
    )
    assert BG_PRIMARY.startswith("#")
    assert BG_SECONDARY.startswith("#")
    assert TEXT_PRIMARY.startswith("#")
    assert ACCENT.startswith("#")
    assert GREEN.startswith("#")
    # Kohala signature red — both ACCENT and RED resolve to it.
    assert ACCENT.upper() == "#E83030"
    assert RED.upper() == "#E83030"
    # Both halves of the loaded stylesheet are present.
    assert "QMainWindow" in STYLESHEET
    assert "QStatusBar" in STYLESHEET


def test_theme_stylesheet_valid_css_structure():
    """Stylesheet has Kohala header, no broken f-string artifacts, no traceback."""
    from app.theme import STYLESHEET
    # Kohala header marker
    assert "PROJECT KOHALA" in STYLESHEET
    # No raw {{ }} escapes and no Python tracebacks in the loaded text
    assert "{{" not in STYLESHEET
    assert "Traceback" not in STYLESHEET
    # Critical kohala property classes are present
    assert "[class=\"nav-item\"]" in STYLESHEET
    assert "[class=\"panel\"]" in STYLESHEET
    assert "[class=\"ws-tab\"]" in STYLESHEET
    assert "[class=\"sidebar\"]" in STYLESHEET
    assert "[class=\"topbar\"]" in STYLESHEET


def test_theme_sidebar_styles():
    """Theme includes sidebar property class + legacy objectName fallback."""
    from app.theme import STYLESHEET
    # New (kohala property class)
    assert "[class=\"sidebar\"]" in STYLESHEET
    assert "[class=\"nav-item\"]" in STYLESHEET
    # Legacy (objectName) — preserved by legacy_objectnames.qss
    assert "QWidget#sidebar" in STYLESHEET
    assert "QPushButton.nav_btn" in STYLESHEET
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
    """Theme includes scroll bar and tree/table view styles."""
    from app.theme import STYLESHEET
    assert "QScrollBar" in STYLESHEET
    # Kohala styles QTreeView/QTableView/QListView together.
    assert "QTreeView" in STYLESHEET or "QTreeWidget" in STYLESHEET
    assert "QHeaderView" in STYLESHEET


def test_theme_status_labels():
    """Legacy compat block exposes status_* label selectors."""
    from app.theme import STYLESHEET
    assert "status_green" in STYLESHEET
    assert "status_red" in STYLESHEET
    assert "status_yellow" in STYLESHEET


def test_theme_loaded_from_files():
    """Stylesheet is loaded from themes/*.qss, not an inlined f-string."""
    from app import themes
    assert themes.load_stylesheet().startswith("/* ===")
    # Palette constants no longer interpolate into the QSS — there should be
    # no `{TEXT_PRIMARY}` style placeholders left over.
    from app.theme import STYLESHEET
    assert "{TEXT_PRIMARY}" not in STYLESHEET
    assert "{BG_PRIMARY}" not in STYLESHEET


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
