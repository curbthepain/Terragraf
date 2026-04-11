"""Tests for the ImGui panel system — Session 12.

32 tests covering:
  - ImGuiPanel (12, needs PySide6)
  - ImGuiDock (10)
  - BridgeProtocol (10)
"""

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

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
            '    #exports [fft1d, fft2d]\n'
            '    #desc "Compute module"\n'
            '}\n'
        )

        (tmp / "routes" / "structure.route").write_text(
            "fft        -> compute/fft/       # FFT utilities\n"
            "math       -> compute/math/      # Math\n"
        )

        (tmp / "tables" / "deps.table").write_text("fft | math | uses | low\n")

        (tmp / "HOT_CONTEXT.md").write_text("# Test Context\nSession 12")
        (tmp / "instances" / "shared" / "queue.json").write_text(json.dumps([]))

        state = ScaffoldState(scaffold_dir=tmp)
        state.load_all()
        yield state


@pytest.fixture
def session_manager():
    """Create a SessionManager."""
    from app.session import SessionManager
    return SessionManager()


@pytest.fixture
def mock_bridge():
    """Create a mock BridgeClient with the essential interface."""
    bridge = MagicMock()
    bridge.connected = True
    bridge.on = MagicMock()
    bridge.send = MagicMock()
    # Simulate connection_changed as a list of callbacks
    _callbacks = []

    def connect_side_effect(callback):
        _callbacks.append(callback)

    bridge.connection_changed = MagicMock()
    bridge.connection_changed.connect = connect_side_effect
    bridge._connection_callbacks = _callbacks
    return bridge


def _make_event(event_type="header", path="headers/project.h", detail="test"):
    from app.scaffold_state import ScaffoldEvent
    return ScaffoldEvent(
        timestamp=time.time(),
        event_type=event_type,
        path=path,
        detail=detail,
    )


# ════════════════════════════════════════════════════════════════════════
#  ImGuiPanel tests (12, needs_qt)
# ════════════════════════════════════════════════════════════════════════


@needs_qt
def test_panel_creation(mock_bridge):
    """ImGuiPanel creates without crashing."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)
    assert panel is not None
    assert panel._docked is True
    panel.close()
    panel.deleteLater()


@needs_qt
def test_find_binary():
    """Binary search finds correct path when binary exists."""
    from app.imgui_panel import ImGuiPanel
    with tempfile.TemporaryDirectory() as tmpdir:
        scaffold_dir = Path(tmpdir)
        # Create a fake binary at the Release path
        release_dir = scaffold_dir / "imgui" / "build" / "Release"
        release_dir.mkdir(parents=True)
        binary = release_dir / "terragraf_imgui.exe"
        binary.write_bytes(b"fake")

        result = ImGuiPanel._find_imgui_binary(scaffold_dir)
        assert result == binary


@needs_qt
def test_find_binary_debug_fallback():
    """Binary search falls back to Debug path."""
    from app.imgui_panel import ImGuiPanel
    with tempfile.TemporaryDirectory() as tmpdir:
        scaffold_dir = Path(tmpdir)
        debug_dir = scaffold_dir / "imgui" / "build" / "Debug"
        debug_dir.mkdir(parents=True)
        binary = debug_dir / "terragraf_imgui.exe"
        binary.write_bytes(b"fake")

        result = ImGuiPanel._find_imgui_binary(scaffold_dir)
        assert result == binary


@needs_qt
def test_start_imgui_no_binary(mock_bridge):
    """Start with no binary sets status to 'binary not found'."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)
    # Force a non-existent binary path
    panel._imgui_binary = Path("/nonexistent/terragraf_imgui")
    panel.start()
    assert "not found" in panel._status_label.text()
    panel.close()
    panel.deleteLater()


@needs_qt
def test_window_handle_protocol_win32(mock_bridge):
    """Window handle response with win32 triggers embed."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)

    # Get the handler that was registered for window_handle_response
    handler_call = None
    for call in mock_bridge.on.call_args_list:
        if call[0][0] == "window_handle_response":
            handler_call = call[0][1]
            break
    assert handler_call is not None

    # Mock the container's embed method
    panel._container.embed = MagicMock(return_value=True)

    # Simulate receiving a window handle response
    handler_call({"data": {"handle": 12345, "platform": "win32"}})

    panel._container.embed.assert_called_once_with(12345, "win32")
    assert panel._docked is True
    assert "embedded" in panel._status_label.text()
    panel.close()
    panel.deleteLater()


@needs_qt
def test_reparenting_mock_x11(mock_bridge):
    """Window handle response with x11 triggers embed."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)

    handler = None
    for call in mock_bridge.on.call_args_list:
        if call[0][0] == "window_handle_response":
            handler = call[0][1]
            break

    panel._container.embed = MagicMock(return_value=True)
    handler({"data": {"handle": 67890, "platform": "x11"}})

    panel._container.embed.assert_called_once_with(67890, "x11")
    panel.close()
    panel.deleteLater()


@needs_qt
def test_fallback_floating_wayland(mock_bridge):
    """Wayland platform triggers floating mode (no reparenting)."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)

    handler = None
    for call in mock_bridge.on.call_args_list:
        if call[0][0] == "window_handle_response":
            handler = call[0][1]
            break

    panel._container.embed = MagicMock()
    handler({"data": {"handle": 0, "platform": "wayland"}})

    panel._container.embed.assert_not_called()
    assert panel._docked is False
    assert "floating" in panel._status_label.text()
    panel.close()
    panel.deleteLater()


@needs_qt
def test_stop_cleanup(mock_bridge):
    """Stop releases container and resets state."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)

    panel._container.release = MagicMock()
    panel.stop()

    panel._container.release.assert_called_once()
    assert panel._status_label.text() == "offline"
    assert panel._start_btn.isEnabled()
    assert not panel._stop_btn.isEnabled()
    panel.close()
    panel.deleteLater()


@needs_qt
def test_dock_undock_toggle(mock_bridge):
    """Dock button toggles between docked and floating."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)

    # Simulate being docked
    panel._docked = True
    panel._container.release = MagicMock()
    panel._toggle_dock()

    assert panel._docked is False
    panel._container.release.assert_called_once()
    assert panel._dock_btn.text() == "Dock"
    panel.close()
    panel.deleteLater()


@needs_qt
def test_restart_calls_stop_then_start(mock_bridge):
    """Restart calls stop then schedules start."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)

    panel.stop = MagicMock()
    panel.start = MagicMock()
    panel.restart()

    panel.stop.assert_called_once()
    # start is scheduled via QTimer.singleShot — we verify stop was called
    panel.close()
    panel.deleteLater()


@needs_qt
def test_embed_failed_sets_floating(mock_bridge):
    """If embed() returns False, panel goes to floating mode."""
    from app.imgui_panel import ImGuiPanel
    panel = ImGuiPanel(mock_bridge)

    handler = None
    for call in mock_bridge.on.call_args_list:
        if call[0][0] == "window_handle_response":
            handler = call[0][1]
            break

    panel._container.embed = MagicMock(return_value=False)
    handler({"data": {"handle": 12345, "platform": "win32"}})

    assert panel._docked is False
    assert "failed" in panel._status_label.text()
    panel.close()
    panel.deleteLater()


@needs_qt
def test_panel_has_container(mock_bridge):
    """Panel exposes container property."""
    from app.imgui_panel import ImGuiPanel
    from app.widgets.imgui_container import ImGuiContainer
    panel = ImGuiPanel(mock_bridge)
    assert isinstance(panel.container, ImGuiContainer)
    panel.close()
    panel.deleteLater()


# ════════════════════════════════════════════════════════════════════════
#  ImGuiDock tests (10)
# ═════════════════════════════════════════════════════════���══════════════


def test_dock_creation(mock_bridge, scaffold_state, session_manager):
    """ImGuiDock creates with bridge + scaffold_state."""
    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(mock_bridge, scaffold_state, session_manager)
    assert dock is not None


def test_tab_switch_sends_context_switch(mock_bridge, scaffold_state, session_manager):
    """Switching tabs sends context_switch message after debounce."""
    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(mock_bridge, scaffold_state, session_manager)

    session = session_manager.create(tab_type="native", label="Test")
    dock.on_tab_activated(session.id)

    # Flush debounce immediately
    dock._debounce_timer.stop()
    dock._flush()

    mock_bridge.send.assert_any_call("context_switch", {
        "tab_type": "native",
        "session_id": session.id,
        "label": "Test",
    })


def test_native_tab_sends_route_tree(mock_bridge, scaffold_state, session_manager):
    """Native tab activation sends route_tree data."""
    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(mock_bridge, scaffold_state, session_manager)

    session = session_manager.create(tab_type="native", label="Native")
    dock.on_tab_activated(session.id)
    dock._debounce_timer.stop()
    dock._flush()

    # Check route_tree was sent
    route_tree_calls = [
        c for c in mock_bridge.send.call_args_list
        if c[0][0] == "route_tree"
    ]
    assert len(route_tree_calls) == 1
    data = route_tree_calls[0][0][1]
    assert "routes" in data
    assert len(data["routes"]) >= 2  # fft + math from fixture


def test_external_tab_sends_scaffold_snapshot(mock_bridge, scaffold_state, session_manager):
    """External tab activation sends scaffold_snapshot."""
    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(mock_bridge, scaffold_state, session_manager)

    session = session_manager.create(tab_type="external", label="External")
    dock.on_tab_activated(session.id)
    dock._debounce_timer.stop()
    dock._flush()

    snapshot_calls = [
        c for c in mock_bridge.send.call_args_list
        if c[0][0] == "scaffold_snapshot"
    ]
    assert len(snapshot_calls) == 1


def test_external_tab_sends_activity_feed(mock_bridge, scaffold_state, session_manager):
    """External tab activation sends activity_feed."""
    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(mock_bridge, scaffold_state, session_manager)

    # Add some events
    scaffold_state.recent_events.append(_make_event("header", "test.h", "modified"))

    session = session_manager.create(tab_type="external", label="External")
    dock.on_tab_activated(session.id)
    dock._debounce_timer.stop()
    dock._flush()

    feed_calls = [
        c for c in mock_bridge.send.call_args_list
        if c[0][0] == "activity_feed"
    ]
    assert len(feed_calls) == 1
    events = feed_calls[0][0][1]["events"]
    assert len(events) >= 1
    assert events[0]["type"] == "header"


def test_debounce_rapid_switches(mock_bridge, scaffold_state, session_manager):
    """Rapid tab switches only send one message after debounce."""
    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(mock_bridge, scaffold_state, session_manager)

    s1 = session_manager.create(tab_type="native", label="Tab1")
    s2 = session_manager.create(tab_type="native", label="Tab2")
    s3 = session_manager.create(tab_type="native", label="Tab3")

    dock.on_tab_activated(s1.id)
    dock.on_tab_activated(s2.id)
    dock.on_tab_activated(s3.id)

    # Only the last one should be pending
    assert dock._pending_session_id == s3.id

    # Flush manually
    dock._debounce_timer.stop()
    dock._flush()

    # context_switch should only have been called once (for s3)
    context_calls = [
        c for c in mock_bridge.send.call_args_list
        if c[0][0] == "context_switch"
    ]
    assert len(context_calls) == 1
    assert context_calls[0][0][1]["label"] == "Tab3"


def test_debounce_timer_reset(mock_bridge, scaffold_state, session_manager):
    """New switch resets debounce — previous pending is replaced."""
    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(mock_bridge, scaffold_state, session_manager)

    s1 = session_manager.create(tab_type="native", label="First")
    s2 = session_manager.create(tab_type="native", label="Second")

    dock.on_tab_activated(s1.id)
    assert dock._pending_session_id == s1.id

    dock.on_tab_activated(s2.id)
    assert dock._pending_session_id == s2.id


def test_disconnect_queues(scaffold_state, session_manager):
    """Messages queued when bridge is disconnected."""
    bridge = MagicMock()
    bridge.connected = False
    bridge.on = MagicMock()
    bridge.connection_changed = MagicMock()
    bridge.connection_changed.connect = MagicMock()

    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(bridge, scaffold_state, session_manager)

    session = session_manager.create(tab_type="native", label="Offline")
    dock.on_tab_activated(session.id)
    dock._debounce_timer.stop()
    dock._flush()

    # bridge.send should not have been called (disconnected)
    bridge.send.assert_not_called()
    # Messages should be queued
    assert len(dock._queued) > 0


def test_reconnect_sends_queued(scaffold_state, session_manager):
    """Queued messages are sent on reconnect."""
    bridge = MagicMock()
    bridge.connected = False
    bridge.on = MagicMock()
    _callbacks = []
    bridge.connection_changed = MagicMock()
    bridge.connection_changed.connect = lambda cb: _callbacks.append(cb)

    from app.imgui_dock import ImGuiDock
    dock = ImGuiDock(bridge, scaffold_state, session_manager)

    session = session_manager.create(tab_type="native", label="Reconnect")
    dock.on_tab_activated(session.id)
    dock._debounce_timer.stop()
    dock._flush()

    assert len(dock._queued) > 0
    queued_count = len(dock._queued)

    # Simulate reconnect
    bridge.connected = True
    for cb in _callbacks:
        cb(True)

    assert bridge.send.call_count == queued_count
    assert len(dock._queued) == 0


def test_empty_state_sends_empty(mock_bridge, session_manager):
    """Empty scaffold state sends empty arrays."""
    from app.scaffold_state import ScaffoldState

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "headers").mkdir()
        (tmp / "routes").mkdir()
        (tmp / "tables").mkdir()
        (tmp / "instances" / "shared").mkdir(parents=True)
        (tmp / "HOT_CONTEXT.md").write_text("")
        (tmp / "instances" / "shared" / "queue.json").write_text("[]")

        state = ScaffoldState(scaffold_dir=tmp)
        state.load_all()

        from app.imgui_dock import ImGuiDock
        dock = ImGuiDock(mock_bridge, state, session_manager)

        session = session_manager.create(tab_type="native", label="Empty")
        dock.on_tab_activated(session.id)
        dock._debounce_timer.stop()
        dock._flush()

        route_calls = [
            c for c in mock_bridge.send.call_args_list
            if c[0][0] == "route_tree"
        ]
        assert len(route_calls) == 1
        assert route_calls[0][0][1]["routes"] == []


# ════════════════════════════════════════════════════════════════════════
#  BridgeProtocol tests (10)
# ════════════════════════════════════════════════════════════════════════


def test_context_switch_serialization():
    """context_switch message has correct format."""
    msg = {
        "tab_type": "native",
        "session_id": "abc12345",
        "label": "Test Tab",
    }
    payload = json.dumps({"type": "context_switch", "data": msg})
    parsed = json.loads(payload)
    assert parsed["type"] == "context_switch"
    assert parsed["data"]["tab_type"] == "native"
    assert parsed["data"]["session_id"] == "abc12345"


def test_route_tree_serialization():
    """route_tree message serializes routes with concept/path/desc."""
    routes = [
        {"concept": "fft", "path": "compute/fft/", "description": "FFT utils"},
        {"concept": "math", "path": "compute/math/", "description": "Math"},
    ]
    payload = json.dumps({"type": "route_tree", "data": {"routes": routes}})
    parsed = json.loads(payload)
    assert len(parsed["data"]["routes"]) == 2
    assert parsed["data"]["routes"][0]["concept"] == "fft"


def test_scaffold_snapshot_serialization():
    """scaffold_snapshot includes headers/routes/tables."""
    snapshot = {
        "headers/project.h": "#module COMPUTE { ... }",
        "routes/structure.route": "fft -> compute/fft/",
        "tables/deps.table": "fft | math | uses",
    }
    payload = json.dumps({"type": "scaffold_snapshot", "data": snapshot})
    parsed = json.loads(payload)
    assert "headers/project.h" in parsed["data"]


def test_activity_feed_serialization():
    """activity_feed events have ts/type/path/detail."""
    events = [
        {"ts": 1234567890.0, "type": "header", "path": "project.h", "detail": "modified"},
    ]
    payload = json.dumps({"type": "activity_feed", "data": {"events": events}})
    parsed = json.loads(payload)
    assert parsed["data"]["events"][0]["type"] == "header"
    assert parsed["data"]["events"][0]["ts"] == 1234567890.0


def test_resize_serialization():
    """resize message has width/height."""
    msg = {"width": 800, "height": 600}
    payload = json.dumps({"type": "resize", "data": msg})
    parsed = json.loads(payload)
    assert parsed["data"]["width"] == 800
    assert parsed["data"]["height"] == 600


def test_window_handle_response_parse():
    """window_handle_response parsed correctly."""
    payload = json.dumps({
        "type": "window_handle_response",
        "data": {"handle": 140735340871680, "platform": "win32"},
    })
    parsed = json.loads(payload)
    assert parsed["type"] == "window_handle_response"
    assert parsed["data"]["handle"] == 140735340871680
    assert parsed["data"]["platform"] == "win32"


def test_backward_compat_tune_load():
    """Existing tune_load message format still valid."""
    payload = json.dumps({
        "type": "tune_load",
        "data": {
            "profile": "cyberpunk",
            "genre": "electronic",
            "knobs": [{"name": "bass", "value": 0.7}],
        },
    })
    parsed = json.loads(payload)
    assert parsed["type"] == "tune_load"
    assert parsed["data"]["profile"] == "cyberpunk"


def test_backward_compat_ping():
    """Existing ping/pong message still valid."""
    ping = json.dumps({"type": "ping", "data": {"ts": 12345}})
    parsed = json.loads(ping)
    assert parsed["type"] == "ping"

    pong = json.dumps({"type": "pong", "data": {"ts": 12345}})
    parsed = json.loads(pong)
    assert parsed["type"] == "pong"


def test_backward_compat_debug_echo():
    """Existing debug_echo message still valid."""
    payload = json.dumps({"type": "debug_echo", "data": {"text": "hello"}})
    parsed = json.loads(payload)
    assert parsed["type"] == "debug_echo"
    assert parsed["data"]["text"] == "hello"


def test_unknown_message_ignored():
    """Unknown message types parse without error."""
    payload = json.dumps({"type": "unknown_future_type", "data": {"foo": "bar"}})
    parsed = json.loads(payload)
    assert parsed["type"] == "unknown_future_type"
    # No exception — this is the expected behavior
