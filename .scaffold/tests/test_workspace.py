"""Tests for the tabbed workspace — Session 9.

33 tests covering:
  - Session lifecycle (8)
  - ScaffoldWatcher (10)
  - ScaffoldState (7)
  - WorkspaceTabWidget (8)
"""

import sys
import json
import time
import tempfile
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


# ── QApplication fixture (shared across Qt-dependent tests) ──────────

@pytest.fixture(scope="session", autouse=True)
def _ensure_qapp():
    """Create a QApplication if PySide6 is available and none exists."""
    if not HAS_PYSIDE6:
        yield
        return
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════════
# Session tests (no Qt runtime needed)
# ═══════════════════════════════════════════════════════════════════════

def test_session_create():
    """Session gets a unique ID and default label."""
    from app.session import Session
    s = Session(tab_type="native")
    assert len(s.id) == 8
    assert s.tab_type == "native"
    assert s.label.startswith("Native")
    assert s.context.instance_id == s.id


def test_session_external_type():
    """External sessions get correct label prefix."""
    from app.session import Session
    s = Session(tab_type="external")
    assert s.label.startswith("External")
    assert s.tab_type == "external"


def test_session_custom_label():
    """Custom label overrides the auto-generated one."""
    from app.session import Session
    s = Session(tab_type="native", label="My Tab")
    assert s.label == "My Tab"


def test_session_context_tracking():
    """Session context tracks headers/routes/files like an Instance."""
    from app.session import Session
    s = Session()
    s.context.headers_read.append("project.h")
    s.context.routes_consulted.append("structure.route")
    s.context.files_modified.append("compute/fft/fft.py")
    assert "project.h" in s.context.headers_read
    assert "structure.route" in s.context.routes_consulted
    assert "compute/fft/fft.py" in s.context.files_modified


def test_session_manager_create_destroy():
    """SessionManager creates and destroys sessions."""
    from app.session import SessionManager
    mgr = SessionManager()
    assert mgr.count == 0
    s = mgr.create("native")
    assert mgr.count == 1
    assert mgr.get(s.id) is s
    assert mgr.destroy(s.id)
    assert mgr.count == 0


def test_session_manager_active_switching():
    """Active session switches correctly."""
    from app.session import SessionManager
    mgr = SessionManager()
    s1 = mgr.create("native")
    s2 = mgr.create("external")
    # First created is auto-activated
    assert mgr.active_id == s1.id
    mgr.activate(s2.id)
    assert mgr.active_id == s2.id
    assert mgr.active is s2


def test_session_manager_max_sessions():
    """Cannot exceed MAX_SESSIONS limit."""
    from app.session import SessionManager, MAX_SESSIONS
    mgr = SessionManager()
    for _ in range(MAX_SESSIONS):
        mgr.create("native")
    assert mgr.count == MAX_SESSIONS
    with pytest.raises(RuntimeError, match="Maximum"):
        mgr.create("native")


def test_session_manager_invalid_type():
    """Rejects unknown tab types."""
    from app.session import SessionManager
    mgr = SessionManager()
    with pytest.raises(ValueError, match="Unknown tab type"):
        mgr.create("invalid_type")


def test_session_manager_destroy_nonexistent():
    """Destroying a nonexistent session returns False."""
    from app.session import SessionManager
    mgr = SessionManager()
    assert not mgr.destroy("nonexistent")


def test_session_manager_active_after_destroy():
    """Active switches to next session after destroying active."""
    from app.session import SessionManager
    mgr = SessionManager()
    s1 = mgr.create("native")
    s2 = mgr.create("native")
    mgr.activate(s1.id)
    mgr.destroy(s1.id)
    assert mgr.active_id == s2.id


def test_session_manager_destroy_all_except():
    """Close all except preserves the specified session."""
    from app.session import SessionManager
    mgr = SessionManager()
    s1 = mgr.create("native")
    s2 = mgr.create("native")
    s3 = mgr.create("external")
    mgr.destroy_all_except(s2.id)
    assert mgr.count == 1
    assert mgr.get(s2.id) is s2


def test_session_manager_has_file_in_context():
    """Finds sessions that modified a given file."""
    from app.session import SessionManager
    mgr = SessionManager()
    s1 = mgr.create("native")
    s2 = mgr.create("native")
    s1.context.files_modified.append("compute/fft/fft.py")
    result = mgr.has_file_in_context("compute/fft/fft.py")
    assert s1.id in result
    assert s2.id not in result


def test_session_manager_ids_and_all():
    """ids() and all_sessions() return correct values."""
    from app.session import SessionManager
    mgr = SessionManager()
    s1 = mgr.create("native")
    s2 = mgr.create("external")
    assert set(mgr.ids()) == {s1.id, s2.id}
    assert len(mgr.all_sessions()) == 2


# ═══════════════════════════════════════════════════════════════════════
# ScaffoldState tests (no Qt runtime for most)
# ═══════════════════════════════════════════════════════════════════════

def _make_scaffold(tmp_path):
    """Create a minimal scaffold structure for testing."""
    headers = tmp_path / "headers"
    routes = tmp_path / "routes"
    tables = tmp_path / "tables"
    tuning = tmp_path / "tuning"
    shared = tmp_path / "instances" / "shared"
    headers.mkdir()
    routes.mkdir()
    tables.mkdir()
    tuning.mkdir()
    shared.mkdir(parents=True)

    # project.h
    (headers / "project.h").write_text(
        '#module math {\n'
        '    #path "compute/math"\n'
        '    #exports [add, sub]\n'
        '    #depends []\n'
        '    #desc "Math"\n'
        '}\n'
        '#module fft {\n'
        '    #path "compute/fft"\n'
        '    #exports [fft1d]\n'
        '    #depends [math]\n'
        '    #desc "FFT"\n'
        '}\n'
    )

    # structure.route
    (routes / "structure.route").write_text(
        '# Test routes\n'
        'math       -> compute/math/     # Math\n'
        'fft        -> compute/fft/      # FFT\n'
        'viz        -> viz/              # Viz\n'
    )

    # deps.table
    (tables / "deps.table").write_text(
        'MODULE | DEPENDS_ON | RELATIONSHIP | CHANGE_RISK\n'
        'fft    | math       | uses         | low\n'
    )

    # HOT_CONTEXT.md
    (tmp_path / "HOT_CONTEXT.md").write_text("# Hot Context\nSession 9")

    # queue.json
    (shared / "queue.json").write_text(json.dumps([
        {"id": "abc", "status": "pending"},
        {"id": "def", "status": "running"},
    ]))

    return tmp_path


@needs_qt
def test_scaffold_state_initial_parse():
    """ScaffoldState parses headers, routes, tables, HOT_CONTEXT on load_all."""
    from app.scaffold_state import ScaffoldState
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        state = ScaffoldState(scaffold_dir=scaffold)
        state.load_all()

        # Headers
        assert "project.h" in state.headers
        modules = state.headers["project.h"]["modules"]
        names = [m["name"] for m in modules]
        assert "math" in names
        assert "fft" in names

        # Routes
        assert "structure.route" in state.routes
        entries = state.routes["structure.route"]
        concepts = [e.concept for e in entries]
        assert "math" in concepts
        assert "fft" in concepts
        assert "viz" in concepts

        # Tables
        assert "deps.table" in state.tables
        assert "MODULE" in state.tables["deps.table"]

        # HOT_CONTEXT
        assert "Session 9" in state.hot_context

        # Queue
        assert state.queue_status["total"] == 2
        assert state.queue_status["pending"] == 1
        assert state.queue_status["running"] == 1


@needs_qt
def test_scaffold_state_header_module_fields():
    """Header parser extracts path, exports, depends, desc."""
    from app.scaffold_state import ScaffoldState
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        state = ScaffoldState(scaffold_dir=scaffold)
        state.load_all()
        modules = state.headers["project.h"]["modules"]
        math_mod = [m for m in modules if m["name"] == "math"][0]
        assert math_mod["path"] == "compute/math"
        assert "add" in math_mod["exports"]
        assert math_mod["desc"] == "Math"


@needs_qt
def test_scaffold_state_route_descriptions():
    """Route parser extracts descriptions from comments."""
    from app.scaffold_state import ScaffoldState
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        state = ScaffoldState(scaffold_dir=scaffold)
        state.load_all()
        entries = state.routes["structure.route"]
        math_entry = [e for e in entries if e.concept == "math"][0]
        assert math_entry.path == "compute/math/"
        assert "Math" in math_entry.description


@needs_qt
def test_scaffold_state_snapshot():
    """take_snapshot captures current state for diffing."""
    from app.scaffold_state import ScaffoldState
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        state = ScaffoldState(scaffold_dir=scaffold)
        state.load_all()
        snap = state.take_snapshot()
        assert "HOT_CONTEXT.md" in snap
        assert "headers/project.h" in snap
        assert "routes/structure.route" in snap


@needs_qt
def test_scaffold_state_health_summary():
    """health_summary returns correct counts."""
    from app.scaffold_state import ScaffoldState
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        state = ScaffoldState(scaffold_dir=scaffold)
        state.load_all()
        health = state.health_summary()
        assert health["header_files"] == 1
        assert health["modules"] == 2
        assert health["route_files"] == 1
        assert health["routes"] == 3
        assert health["table_files"] == 1
        assert health["queue_pending"] == 1
        assert health["queue_running"] == 1
        assert health["hot_context_lines"] > 0


@needs_qt
def test_scaffold_state_empty_scaffold():
    """ScaffoldState handles empty/missing scaffold gracefully."""
    from app.scaffold_state import ScaffoldState
    with tempfile.TemporaryDirectory() as td:
        state = ScaffoldState(scaffold_dir=Path(td))
        state.load_all()
        assert state.headers == {}
        assert state.routes == {}
        assert state.tables == {}
        assert state.hot_context == ""
        assert state.queue_status["total"] == 0


@needs_qt
def test_scaffold_state_event_recording():
    """Events are recorded and capped at 500."""
    from app.scaffold_state import ScaffoldState
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        state = ScaffoldState(scaffold_dir=scaffold)
        state.load_all()
        # Manually trigger events
        for i in range(505):
            state._record_event("test", f"file_{i}", f"Event {i}")
        assert len(state.recent_events) == 500


# ═══════════════════════════════════════════════════════════════════════
# ScaffoldWatcher tests (need Qt event loop)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_watcher_add_file():
    """Can add and track a file."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.txt"
        p.write_text("hello")
        w = ScaffoldWatcher(scaffold_dir=Path(td))
        assert w.add_file(str(p))
        assert str(p.resolve()) in w.watched_files
        w.cleanup()


@needs_qt
def test_watcher_add_directory():
    """Can add and track a directory."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "sub"
        d.mkdir()
        w = ScaffoldWatcher(scaffold_dir=Path(td))
        assert w.add_directory(str(d))
        assert str(d.resolve()) in w.watched_dirs
        w.cleanup()


@needs_qt
def test_watcher_remove_file():
    """Can remove a watched file."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.txt"
        p.write_text("hello")
        w = ScaffoldWatcher(scaffold_dir=Path(td))
        w.add_file(str(p))
        w.remove_file(str(p))
        assert str(p.resolve()) not in w.watched_files
        w.cleanup()


@needs_qt
def test_watcher_cleanup():
    """Cleanup removes all watches."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.txt"
        p.write_text("hello")
        d = Path(td) / "sub"
        d.mkdir()
        w = ScaffoldWatcher(scaffold_dir=Path(td))
        w.add_file(str(p))
        w.add_directory(str(d))
        w.cleanup()
        assert len(w.watched_files) == 0
        assert len(w.watched_dirs) == 0


@needs_qt
def test_watcher_duplicate_add():
    """Adding the same file twice returns True without duplicating."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.txt"
        p.write_text("hello")
        w = ScaffoldWatcher(scaffold_dir=Path(td))
        assert w.add_file(str(p))
        assert w.add_file(str(p))  # Duplicate, still True
        assert len(w.watched_files) == 1
        w.cleanup()


@needs_qt
def test_watcher_watch_defaults():
    """watch_defaults registers existing scaffold files."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        w = ScaffoldWatcher(scaffold_dir=scaffold)
        w.watch_defaults()
        # Should have found HOT_CONTEXT.md and queue.json at minimum
        found_files = w.watched_files
        resolved_hc = str((scaffold / "HOT_CONTEXT.md").resolve())
        assert resolved_hc in found_files
        w.cleanup()


@needs_qt
def test_watcher_classify_header():
    """File change in headers/ emits header_changed signal."""
    from app.scaffold_watcher import ScaffoldWatcher
    from PySide6.QtCore import QCoreApplication
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        w = ScaffoldWatcher(scaffold_dir=scaffold)
        received = []
        w.header_changed.connect(lambda name: received.append(name))
        # Directly call _emit_change (bypasses filesystem events for unit test)
        w._emit_change(str((scaffold / "headers" / "project.h").resolve()))
        assert "project.h" in received
        w.cleanup()


@needs_qt
def test_watcher_classify_route():
    """File change in routes/ emits route_changed signal."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        w = ScaffoldWatcher(scaffold_dir=scaffold)
        received = []
        w.route_changed.connect(lambda name: received.append(name))
        w._emit_change(str((scaffold / "routes" / "structure.route").resolve()))
        assert "structure.route" in received
        w.cleanup()


@needs_qt
def test_watcher_classify_hot_context():
    """HOT_CONTEXT.md change emits hot_context_changed signal."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        w = ScaffoldWatcher(scaffold_dir=scaffold)
        received = []
        w.hot_context_changed.connect(lambda: received.append(True))
        w._emit_change(str((scaffold / "HOT_CONTEXT.md").resolve()))
        assert received == [True]
        w.cleanup()


@needs_qt
def test_watcher_classify_queue():
    """queue.json change emits queue_changed signal."""
    from app.scaffold_watcher import ScaffoldWatcher
    with tempfile.TemporaryDirectory() as td:
        scaffold = _make_scaffold(Path(td))
        w = ScaffoldWatcher(scaffold_dir=scaffold)
        received = []
        w.queue_changed.connect(lambda: received.append(True))
        w._emit_change(str((scaffold / "instances" / "shared" / "queue.json").resolve()))
        assert received == [True]
        w.cleanup()


# ═══════════════════════════════════════════════════════════════════════
# WorkspaceTabWidget tests (need Qt runtime)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_tab_widget_create_tab():
    """Creating a tab adds it to the widget and session manager."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    session = tabs.create_tab("native", label="Test")
    assert tabs.count() == 1
    assert mgr.count == 1
    assert tabs.session_for_tab(0) == session.id


@needs_qt
def test_tab_widget_close_tab():
    """Closing a tab removes it from widget and session manager."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    s1 = tabs.create_tab("native")
    s2 = tabs.create_tab("native")
    assert tabs.count() == 2
    tabs.close_tab(0)
    assert tabs.count() == 1
    assert mgr.count == 1


@needs_qt
def test_tab_widget_cannot_close_last():
    """Cannot close the last remaining tab."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    tabs.create_tab("native")
    # _on_close_tab guards against closing last tab
    tabs._on_close_tab(0)
    assert tabs.count() == 1


@needs_qt
def test_tab_widget_pin_prevents_close():
    """Pinned tabs cannot be closed."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    s1 = tabs.create_tab("native")
    s2 = tabs.create_tab("native")
    tabs.pin_tab(0, True)
    assert not tabs.close_tab(0)  # Should fail — pinned
    assert tabs.count() == 2


@needs_qt
def test_tab_widget_session_activation():
    """Switching tabs activates the correct session."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    s1 = tabs.create_tab("native")
    s2 = tabs.create_tab("external")
    tabs.setCurrentIndex(0)
    assert mgr.active_id == s1.id
    tabs.setCurrentIndex(1)
    assert mgr.active_id == s2.id


@needs_qt
def test_tab_widget_tab_for_session():
    """Can look up tab index from session ID."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    s1 = tabs.create_tab("native")
    s2 = tabs.create_tab("external")
    assert tabs.tab_for_session(s1.id) == 0
    assert tabs.tab_for_session(s2.id) == 1
    assert tabs.tab_for_session("nonexistent") == -1


@needs_qt
def test_tab_widget_close_all_except():
    """Close all except keeps the specified tab."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    s1 = tabs.create_tab("native")
    s2 = tabs.create_tab("native")
    s3 = tabs.create_tab("external")
    tabs.close_all_except(1)  # Keep s2
    assert tabs.count() == 1
    assert mgr.count == 1


@needs_qt
def test_tab_widget_signals():
    """Tab signals fire on create, close, activate."""
    from app.session import SessionManager
    from app.tab_widget import WorkspaceTabWidget
    mgr = SessionManager()
    tabs = WorkspaceTabWidget(mgr)
    created = []
    closed = []
    activated = []
    tabs.tab_session_created.connect(lambda sid: created.append(sid))
    tabs.tab_session_closed.connect(lambda sid: closed.append(sid))
    tabs.tab_session_activated.connect(lambda sid: activated.append(sid))

    s1 = tabs.create_tab("native")
    s2 = tabs.create_tab("native")
    assert s1.id in created
    assert s2.id in created
    # activated fires on create (due to setCurrentIndex)
    assert len(activated) >= 1
    tabs.close_tab(1)
    assert s2.id in closed
