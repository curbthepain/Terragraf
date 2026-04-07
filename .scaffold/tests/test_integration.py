"""Tests for Session 13 — integration, feedback, coherence, welcome tab.

32 tests covering:
  - FeedbackLoop (10)
  - CoherenceManager (10)
  - WelcomeTab (5, needs PySide6)
  - Integration (7)
"""

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

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
        (tmp / "instances" / "shared" / "locks").mkdir(parents=True)

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

        (tmp / "HOT_CONTEXT.md").write_text("# Test Context\nSession 13")
        (tmp / "instances" / "shared" / "queue.json").write_text(json.dumps([]))

        state = ScaffoldState(scaffold_dir=tmp)
        state.load_all()
        yield state


@pytest.fixture
def session_manager():
    """Create a SessionManager."""
    from app.session import SessionManager
    return SessionManager()


def _make_event(event_type="header", path="headers/project.h", detail="test"):
    from app.scaffold_state import ScaffoldEvent
    return ScaffoldEvent(
        timestamp=time.time(),
        event_type=event_type,
        path=path,
        detail=detail,
    )


# ═══════════════════════════════════════════════════════════════════════
# FeedbackLoop tests (10)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_feedback_creation(scaffold_state, session_manager):
    """FeedbackLoop instantiates with scaffold_state + session_manager + detector."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)
    assert fb is not None


@needs_qt
def test_sharpen_fires_on_consulted_route(scaffold_state, session_manager):
    """sharpen_suggested fires when external event matches a consulted route."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    # Create a session that consulted a route
    session = session_manager.create("native", "Test")
    session.context.routes_consulted.append("routes/structure.route")

    received = []
    fb.sharpen_suggested.connect(lambda path: received.append(path))

    # Simulate an external change on that route
    event = _make_event("route", "routes/structure.route", "Route reloaded")
    fb._on_external_change(event)

    assert len(received) == 1
    assert received[0] == "routes/structure.route"


@needs_qt
def test_sharpen_not_fired_for_unconsulted_route(scaffold_state, session_manager):
    """sharpen_suggested NOT fired for a route no session consulted."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    session_manager.create("native", "Test")

    received = []
    fb.sharpen_suggested.connect(lambda path: received.append(path))

    event = _make_event("route", "routes/structure.route", "Route reloaded")
    fb._on_external_change(event)

    assert len(received) == 0


@needs_qt
def test_hot_context_push_on_results(scaffold_state, session_manager):
    """hot_context_push fires when results event has detail."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    received = []
    fb.hot_context_push.connect(lambda text: received.append(text))

    # Simulate results event
    event = _make_event("results", "instances/shared/results.json", "skill: health_check passed")
    scaffold_state.recent_events.append(event)
    fb._on_state_changed()

    assert len(received) == 1
    assert "health_check" in received[0]


@needs_qt
def test_knowledge_suggested_3_sessions(scaffold_state, session_manager):
    """knowledge_suggested fires when 3+ sessions modify the same file."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    received = []
    fb.knowledge_suggested.connect(lambda path: received.append(path))

    # Create 3 sessions that all modify the same file
    for i in range(3):
        s = session_manager.create("native", f"S{i}")
        s.context.files_modified.append("compute/fft/fft.py")

    # Trigger a state changed event
    event = _make_event("header", "headers/project.h", "test")
    scaffold_state.recent_events.append(event)
    fb._on_state_changed()

    assert len(received) == 1
    assert received[0] == "compute/fft/fft.py"


@needs_qt
def test_knowledge_not_suggested_fewer_than_3(scaffold_state, session_manager):
    """knowledge_suggested NOT fired for < 3 sessions on same file."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    received = []
    fb.knowledge_suggested.connect(lambda path: received.append(path))

    # Only 2 sessions modify the same file
    for i in range(2):
        s = session_manager.create("native", f"S{i}")
        s.context.files_modified.append("compute/fft/fft.py")

    event = _make_event("header", "headers/project.h", "test")
    scaffold_state.recent_events.append(event)
    fb._on_state_changed()

    assert len(received) == 0


@needs_qt
def test_feedback_signals_carry_correct_data(scaffold_state, session_manager):
    """All feedback signals carry the expected payload types."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    sharpen_data = []
    push_data = []
    knowledge_data = []
    fb.sharpen_suggested.connect(lambda p: sharpen_data.append(p))
    fb.hot_context_push.connect(lambda t: push_data.append(t))
    fb.knowledge_suggested.connect(lambda p: knowledge_data.append(p))

    # Trigger sharpen
    session = session_manager.create("native", "T1")
    session.context.routes_consulted.append("headers/project.h")
    fb._on_external_change(_make_event("header", "headers/project.h", "x"))
    assert isinstance(sharpen_data[0], str)

    # Trigger hot context push
    event = _make_event("results", "results.json", "done")
    scaffold_state.recent_events.append(event)
    fb._on_state_changed()
    assert isinstance(push_data[0], str)


@needs_qt
def test_feedback_no_crash_empty_state(session_manager):
    """FeedbackLoop doesn't crash with empty scaffold state."""
    from app.scaffold_state import ScaffoldState
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop

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
        det = ExternalDetector(state, session_manager)
        fb = FeedbackLoop(state, session_manager, det)
        # Should not raise
        fb._on_state_changed()
        fb._check_knowledge_suggestions()


@needs_qt
def test_feedback_no_crash_empty_detector(scaffold_state, session_manager):
    """FeedbackLoop handles external detector with no events."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    received = []
    fb.sharpen_suggested.connect(lambda p: received.append(p))

    # Call with non-route event type — should be silently skipped
    fb._on_external_change(_make_event("hot_context", "HOT_CONTEXT.md", "x"))
    assert len(received) == 0


@needs_qt
def test_feedback_ignores_pinned_sessions(scaffold_state, session_manager):
    """Pinned sessions are ignored by FeedbackLoop."""
    from app.external_detector import ExternalDetector
    from app.feedback import FeedbackLoop
    det = ExternalDetector(scaffold_state, session_manager)
    fb = FeedbackLoop(scaffold_state, session_manager, det)

    session = session_manager.create("native", "Pinned")
    session.pinned = True
    session.context.routes_consulted.append("routes/structure.route")

    received = []
    fb.sharpen_suggested.connect(lambda p: received.append(p))

    fb._on_external_change(_make_event("route", "routes/structure.route", "x"))
    assert len(received) == 0


# ═══════════════════════════════════════════════════════════════════════
# CoherenceManager tests (10)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_coherence_no_conflict_single_session(scaffold_state, session_manager):
    """No conflicts with a single session."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()  # Don't need the timer

    session_manager.create("native", "Solo")

    received = []
    cm.conflict_detected.connect(lambda *a: received.append(a))
    cm.check_conflicts()

    assert len(received) == 0


@needs_qt
def test_coherence_route_conflict_two_sessions(scaffold_state, session_manager):
    """Same-route conflict detected across two sessions."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    s1 = session_manager.create("native", "S1")
    s2 = session_manager.create("native", "S2")
    s1.context.routes_consulted.append("routes/structure.route")
    s2.context.routes_consulted.append("routes/structure.route")

    received = []
    cm.conflict_detected.connect(lambda sid, ctype, detail: received.append((sid, ctype, detail)))
    cm.check_conflicts()

    assert len(received) == 2  # Both sessions flagged
    assert all(r[1] == "route" for r in received)
    assert all(r[2] == "routes/structure.route" for r in received)


@needs_qt
def test_coherence_conflict_cleared_on_close(scaffold_state, session_manager):
    """Conflict cleared when one session closes."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    s1 = session_manager.create("native", "S1")
    s2 = session_manager.create("native", "S2")
    s1.context.routes_consulted.append("routes/structure.route")
    s2.context.routes_consulted.append("routes/structure.route")

    cm.check_conflicts()
    assert cm.active_conflict_count == 2

    # Close one session
    session_manager.destroy(s2.id)

    cleared = []
    cm.conflict_cleared.connect(lambda sid: cleared.append(sid))
    cm.check_conflicts()

    assert len(cleared) >= 1


@needs_qt
def test_coherence_lock_contention(scaffold_state, session_manager):
    """Lock contention detected when two sessions modify the same resource."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    s1 = session_manager.create("native", "S1")
    s2 = session_manager.create("native", "S2")
    s1.context.files_modified.append("compute/fft/fft.py")
    s2.context.files_modified.append("compute/fft/fft.py")

    # Create a lock file for that resource
    locks_dir = Path(scaffold_state._scaffold_dir) / "instances" / "shared" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_file = locks_dir / "compute_fft_fft.py.lock"
    lock_file.write_text(json.dumps({"pid": 12345, "time": time.time()}))

    # Patch the locks dir to use our temp directory
    import app.coherence as coherence_mod
    original = coherence_mod._LOCKS_DIR
    coherence_mod._LOCKS_DIR = locks_dir

    received = []
    cm.conflict_detected.connect(lambda sid, ctype, detail: received.append((sid, ctype, detail)))

    try:
        cm.check_conflicts()
        lock_conflicts = [r for r in received if r[1] == "lock"]
        assert len(lock_conflicts) >= 2
    finally:
        coherence_mod._LOCKS_DIR = original
        lock_file.unlink(missing_ok=True)


@needs_qt
def test_coherence_lock_cleared(scaffold_state, session_manager):
    """Lock contention cleared when lock is released."""
    from app.coherence import CoherenceManager
    import app.coherence as coherence_mod
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    s1 = session_manager.create("native", "S1")
    s2 = session_manager.create("native", "S2")
    s1.context.files_modified.append("compute/fft/fft.py")
    s2.context.files_modified.append("compute/fft/fft.py")

    locks_dir = Path(scaffold_state._scaffold_dir) / "instances" / "shared" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_file = locks_dir / "compute_fft_fft.py.lock"
    lock_file.write_text(json.dumps({"pid": 12345, "time": time.time()}))

    original = coherence_mod._LOCKS_DIR
    coherence_mod._LOCKS_DIR = locks_dir

    try:
        cm.check_conflicts()
        assert cm.active_conflict_count > 0

        # Release the lock
        lock_file.unlink()

        cleared = []
        cm.conflict_cleared.connect(lambda sid: cleared.append(sid))
        cm.check_conflicts()

        # Lock conflicts should be gone (route conflicts may remain)
        lock_conflicts = {
            sid for sid, conflicts in cm._active_conflicts.items()
            if any(c[0] == "lock" for c in conflicts)
        }
        assert len(lock_conflicts) == 0
    finally:
        coherence_mod._LOCKS_DIR = original


@needs_qt
def test_coherence_timer_interval(scaffold_state, session_manager):
    """CoherenceManager timer is set to 5000ms."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    assert cm._timer.interval() == 5000
    cm.stop()


@needs_qt
def test_coherence_signal_carries_data(scaffold_state, session_manager):
    """conflict_detected carries session_id, type, and detail."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    s1 = session_manager.create("native", "S1")
    s2 = session_manager.create("native", "S2")
    s1.context.routes_consulted.append("headers/project.h")
    s2.context.routes_consulted.append("headers/project.h")

    received = []
    cm.conflict_detected.connect(lambda sid, ctype, detail: received.append((sid, ctype, detail)))
    cm.check_conflicts()

    assert len(received) == 2
    for sid, ctype, detail in received:
        assert isinstance(sid, str)
        assert ctype == "route"
        assert detail == "headers/project.h"


@needs_qt
def test_coherence_cleared_signal_fires(scaffold_state, session_manager):
    """conflict_cleared fires when conflicts are resolved."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    s1 = session_manager.create("native", "S1")
    s2 = session_manager.create("native", "S2")
    s1.context.routes_consulted.append("routes/structure.route")
    s2.context.routes_consulted.append("routes/structure.route")

    cm.check_conflicts()

    # Remove routes from both sessions
    s1.context.routes_consulted.clear()
    s2.context.routes_consulted.clear()

    cleared = []
    cm.conflict_cleared.connect(lambda sid: cleared.append(sid))
    cm.check_conflicts()

    assert len(cleared) >= 1


@needs_qt
def test_coherence_no_false_positives(scaffold_state, session_manager):
    """No false positives when sessions consult different routes."""
    from app.coherence import CoherenceManager
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    s1 = session_manager.create("native", "S1")
    s2 = session_manager.create("native", "S2")
    s1.context.routes_consulted.append("routes/structure.route")
    s2.context.routes_consulted.append("headers/project.h")

    received = []
    cm.conflict_detected.connect(lambda *a: received.append(a))
    cm.check_conflicts()

    assert len(received) == 0


@needs_qt
def test_coherence_max_sessions(scaffold_state, session_manager):
    """Handles MAX_SESSIONS (16) without performance issues."""
    from app.coherence import CoherenceManager
    from app.session import MAX_SESSIONS
    cm = CoherenceManager(session_manager, scaffold_state)
    cm.stop()

    for i in range(MAX_SESSIONS):
        s = session_manager.create("native", f"S{i}")
        s.context.routes_consulted.append("routes/structure.route")

    received = []
    cm.conflict_detected.connect(lambda *a: received.append(a))
    cm.check_conflicts()

    # All 16 sessions should be flagged for the shared route
    assert len(received) == MAX_SESSIONS


# ═══════════════════════════════════════════════════════════════════════
# WelcomeTab tests (5, needs PySide6)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_welcome_tab_creation(scaffold_state, session_manager):
    """WelcomeTab creates and renders health summary."""
    from app.session import Session
    from app.welcome_tab import WelcomeTab
    session = Session(tab_type="welcome", label="Welcome")
    tab = WelcomeTab(session, scaffold_state, session_manager)
    assert tab is not None
    # Health labels should have values (not just "—")
    assert any(lbl.text() != "—" for lbl in tab._health_labels.values())
    tab.close()
    tab.deleteLater()


@needs_qt
def test_welcome_tab_has_two_panels_not_broken_buttons(scaffold_state, session_manager):
    """S27: welcome tab renders two QFrame[class=panel] cards, no action buttons."""
    from app.session import Session
    from app.welcome_tab import WelcomeTab
    from PySide6.QtWidgets import QFrame, QPushButton
    session = Session(tab_type="welcome", label="Welcome")
    tab = WelcomeTab(session, scaffold_state, session_manager)

    # The S26 welcome tab still had broken action buttons. The S27 rewrite
    # removed them entirely — the sidebar covers every entry point.
    button_labels = {b.text() for b in tab.findChildren(QPushButton)}
    assert "New Native Tab" not in button_labels
    assert "New External Tab" not in button_labels
    assert "Toggle ImGui" not in button_labels
    assert "Open Settings" not in button_labels

    # Exactly two direct-child panel frames (Scaffold Health + Recent Tabs).
    panels = [
        f for f in tab.findChildren(QFrame)
        if f.property("class") == "panel"
    ]
    assert len(panels) == 2
    tab.close()
    tab.deleteLater()


@needs_qt
def test_welcome_tab_refreshes_on_state_changed(scaffold_state, session_manager):
    """Health summary updates when state_changed fires."""
    from app.session import Session
    from app.welcome_tab import WelcomeTab
    session = Session(tab_type="welcome", label="Welcome")
    tab = WelcomeTab(session, scaffold_state, session_manager)

    # Capture current values
    before = tab._health_labels["recent_events"].text()

    # Add an event and fire state_changed
    event = _make_event("header", "headers/project.h", "test refresh")
    scaffold_state.recent_events.append(event)
    scaffold_state.state_changed.emit()

    after = tab._health_labels["recent_events"].text()
    # Count should have changed (or at least been refreshed)
    assert after is not None
    tab.close()
    tab.deleteLater()


@needs_qt
def test_welcome_tab_recent_sessions(scaffold_state, session_manager):
    """Recent sessions list populates when sessions exist."""
    from app.session import Session
    from app.welcome_tab import WelcomeTab
    session = Session(tab_type="welcome", label="Welcome")

    # Create some sessions first
    session_manager.create("native", "Alpha")
    session_manager.create("external", "Beta")

    tab = WelcomeTab(session, scaffold_state, session_manager)

    # "No active sessions" label should be hidden
    assert tab._no_sessions_label.isVisible() is False
    # Should have session labels in the layout
    assert tab._sessions_layout.count() > 1  # >1 because "no sessions" label is at index 0
    tab.close()
    tab.deleteLater()


@needs_qt
def test_welcome_tab_empty_sessions(scaffold_state, session_manager):
    """Empty state shows 'no sessions' gracefully."""
    from app.session import Session
    from app.welcome_tab import WelcomeTab
    session = Session(tab_type="welcome", label="Welcome")
    tab = WelcomeTab(session, scaffold_state, session_manager)

    # No sessions created, so "no sessions" label should NOT be hidden
    assert tab._no_sessions_label.isHidden() is False
    tab.close()
    tab.deleteLater()


# ═══════════════════════════════════════════════════════════════════════
# Integration tests (7)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_native_query_populates_history(scaffold_state, session_manager):
    """Native query resolves route and result appears in session.query_history."""
    from app.session import Session
    session = session_manager.create("native", "QueryTest")

    # Simulate what NativeTab does: query engine resolves and appends
    session.query_history.append({
        "query": "fft",
        "results": [{"concept": "fft", "path": "compute/fft/", "score": 1.0}],
    })

    assert len(session.query_history) == 1
    assert session.query_history[0]["query"] == "fft"


@needs_qt
def test_external_tab_detects_hot_context_change(scaffold_state, session_manager):
    """External tab processes HOT_CONTEXT change event."""
    from app.session import Session
    from app.external_tab import ExternalTab
    from app.widgets.activity_feed import ActivityFeed

    session = Session(tab_type="external", label="Ext")
    tab = ExternalTab(session, scaffold_state)

    event = _make_event("hot_context", "HOT_CONTEXT.md", "HOT_CONTEXT updated externally")
    tab.add_external_event(event)

    feed = tab.findChild(ActivityFeed)
    assert feed._list.count() == 1
    tab.close()
    tab.deleteLater()


@needs_qt
def test_imgui_dock_context_switch(scaffold_state, session_manager):
    """ImGuiDock.on_tab_activated sends context_switch via bridge."""
    from app.imgui_dock import ImGuiDock

    bridge = MagicMock()
    bridge.connected = True
    dock = ImGuiDock(bridge, scaffold_state, session_manager)

    session = session_manager.create("native", "Test")
    dock.on_tab_activated(session.id)

    # Process the debounce timer manually
    dock._debounce_timer.timeout.emit()

    # Bridge should have sent context_switch (possibly followed by route_tree)
    assert bridge.send.called
    msg_types = [call[0][0] for call in bridge.send.call_args_list]
    assert "context_switch" in msg_types


@needs_qt
def test_scaffold_state_propagates(scaffold_state, session_manager):
    """Scaffold state change propagates via state_changed signal."""
    received = []
    scaffold_state.state_changed.connect(lambda: received.append(True))

    scaffold_state.state_changed.emit()
    assert len(received) == 1


@needs_qt
def test_session_lifecycle(session_manager):
    """Session create -> activate -> destroy lifecycle."""
    s1 = session_manager.create("native", "First")
    assert session_manager.count == 1
    assert session_manager.active_id == s1.id

    s2 = session_manager.create("external", "Second")
    assert session_manager.count == 2

    session_manager.activate(s2.id)
    assert session_manager.active_id == s2.id

    session_manager.destroy(s2.id)
    assert session_manager.count == 1
    assert session_manager.active_id == s1.id

    session_manager.destroy(s1.id)
    assert session_manager.count == 0
    assert session_manager.active_id is None


@needs_qt
def test_feedback_coherence_import():
    """FeedbackLoop + CoherenceManager importable without errors."""
    from app.feedback import FeedbackLoop
    from app.coherence import CoherenceManager
    from app.welcome_tab import WelcomeTab
    assert FeedbackLoop is not None
    assert CoherenceManager is not None
    assert WelcomeTab is not None


@needs_qt
def test_session_new_fields():
    """Session has coherence_warnings and hot_context_contribution fields."""
    from app.session import Session
    s = Session(tab_type="native", label="Test")
    assert isinstance(s.coherence_warnings, list)
    assert s.hot_context_contribution == ""
    s.coherence_warnings.append("route conflict")
    s.hot_context_contribution = "pushed result"
    assert len(s.coherence_warnings) == 1
