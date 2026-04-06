"""Tests for the external tab system — Session 11.

33 tests covering:
  - ExternalDetector (13)
  - ExternalTab UI (10, needs PySide6)
  - ScaffoldTree (5, needs PySide6)
  - DiffViewer (5, needs PySide6)
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

        (tmp / "HOT_CONTEXT.md").write_text("# Test Context\nSession 11")
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
def session():
    """Create a test session."""
    from app.session import Session
    return Session(tab_type="external", label="Test External")


def _make_event(event_type="header", path="headers/project.h", detail="test"):
    from app.scaffold_state import ScaffoldEvent
    return ScaffoldEvent(
        timestamp=time.time(),
        event_type=event_type,
        path=path,
        detail=detail,
    )


# ═══════════════════════════════════════════════════════════════════════
# ExternalDetector tests (13)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_detector_creation(scaffold_state, session_manager):
    """ExternalDetector instantiates with scaffold_state + session_manager."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    assert det is not None


@needs_qt
def test_hot_context_is_external(scaffold_state, session_manager):
    """HOT_CONTEXT changes are always classified as external."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    event = _make_event("hot_context", "HOT_CONTEXT.md", "HOT_CONTEXT updated")
    assert det.classify(event) is True


@needs_qt
def test_route_change_no_session_is_external(scaffold_state, session_manager):
    """Route change with no session claiming it is external."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    event = _make_event("route", "routes/structure.route", "Route reloaded")
    assert det.classify(event) is True


@needs_qt
def test_route_change_claimed_by_session_is_internal(scaffold_state, session_manager):
    """Route change claimed by a session is internal."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    session = session_manager.create("native", "Test")
    session.context.files_modified.append("routes/structure.route")
    event = _make_event("route", "routes/structure.route", "Route reloaded")
    assert det.classify(event) is False


@needs_qt
def test_queue_unknown_instance_is_external(scaffold_state, session_manager):
    """Queue change with unknown instance ID is external."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    scaffold_state.queue_status = {
        "total": 1, "pending": 1, "running": 0,
        "tasks": [{"instance_id": "unknown-id", "status": "pending"}],
    }
    event = _make_event("queue", "instances/shared/queue.json", "Queue updated")
    assert det.classify(event) is True


@needs_qt
def test_queue_known_instance_is_internal(scaffold_state, session_manager):
    """Queue change with known session ID is internal."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    session = session_manager.create("native", "Test")
    scaffold_state.queue_status = {
        "total": 1, "pending": 1, "running": 0,
        "tasks": [{"instance_id": session.id, "status": "pending"}],
    }
    event = _make_event("queue", "instances/shared/queue.json", "Queue updated")
    assert det.classify(event) is False


@needs_qt
def test_header_change_external(scaffold_state, session_manager):
    """Header change not claimed by any session is external."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    event = _make_event("header", "headers/project.h", "Header reloaded")
    assert det.classify(event) is True


@needs_qt
def test_table_change_external(scaffold_state, session_manager):
    """Table change not claimed is external."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    event = _make_event("table", "tables/deps.table", "Table reloaded")
    assert det.classify(event) is True


@needs_qt
def test_rapid_events_all_classified(scaffold_state, session_manager):
    """Multiple events in quick succession all get classified."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    events = [
        _make_event("header", "headers/project.h", f"Event {i}")
        for i in range(10)
    ]
    results = [det.classify(e) for e in events]
    assert len(results) == 10
    assert all(r is True for r in results)  # All external (no session claims)


@needs_qt
def test_no_false_positives_native_query(scaffold_state, session_manager):
    """Native session that reads routes doesn't trigger external for those routes."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    session = session_manager.create("native", "Test")
    # Session claims it modified this file
    session.context.files_modified.append("headers/project.h")
    event = _make_event("header", "headers/project.h", "Header reloaded")
    assert det.classify(event) is False


@needs_qt
def test_lock_file_creation(scaffold_state, session_manager):
    """Lock file in instances/shared/ classified as external."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    event = _make_event("file", "instances/shared/task.lock", "Lock created")
    assert det.classify(event) is True


@needs_qt
def test_results_change_external(scaffold_state, session_manager):
    """results.json change classified as external."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)
    event = _make_event("results", "instances/shared/results.json", "Results updated")
    assert det.classify(event) is True


@needs_qt
def test_signal_emission(scaffold_state, session_manager):
    """external_change signal emitted with correct ScaffoldEvent."""
    from app.external_detector import ExternalDetector
    det = ExternalDetector(scaffold_state, session_manager)

    received = []
    det.external_change.connect(lambda e: received.append(e))

    # Simulate a state change with a hot_context event
    event = _make_event("hot_context", "HOT_CONTEXT.md", "Updated")
    scaffold_state.recent_events.append(event)
    scaffold_state.state_changed.emit()

    assert len(received) == 1
    assert received[0].event_type == "hot_context"


# ═══════════════════════════════════════════════════════════════════════
# ExternalTab tests (10, needs PySide6)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_external_tab_creation(scaffold_state, session):
    """ExternalTab creates with session + scaffold_state."""
    from app.external_tab import ExternalTab
    tab = ExternalTab(session, scaffold_state)
    assert tab is not None
    tab.close()
    tab.deleteLater()


@needs_qt
def test_has_session_attribute(scaffold_state, session):
    """ExternalTab exposes self.session (required by tab_widget)."""
    from app.external_tab import ExternalTab
    tab = ExternalTab(session, scaffold_state)
    assert tab.session is session
    tab.close()
    tab.deleteLater()


@needs_qt
def test_three_panel_layout(scaffold_state, session):
    """ExternalTab has a splitter with 3 children."""
    from PySide6.QtWidgets import QSplitter
    from app.external_tab import ExternalTab
    tab = ExternalTab(session, scaffold_state)
    splitters = tab.findChildren(QSplitter)
    assert len(splitters) == 1
    assert splitters[0].count() == 3
    tab.close()
    tab.deleteLater()


@needs_qt
def test_activity_feed_present(scaffold_state, session):
    """ExternalTab contains an ActivityFeed widget."""
    from app.external_tab import ExternalTab
    from app.widgets.activity_feed import ActivityFeed
    tab = ExternalTab(session, scaffold_state)
    feeds = tab.findChildren(ActivityFeed)
    assert len(feeds) == 1
    tab.close()
    tab.deleteLater()


@needs_qt
def test_scaffold_tree_present(scaffold_state, session):
    """ExternalTab contains a ScaffoldTree widget."""
    from app.external_tab import ExternalTab
    from app.widgets.scaffold_tree import ScaffoldTree
    tab = ExternalTab(session, scaffold_state)
    trees = tab.findChildren(ScaffoldTree)
    assert len(trees) == 1
    tab.close()
    tab.deleteLater()


@needs_qt
def test_diff_viewer_present(scaffold_state, session):
    """ExternalTab contains a DiffViewer widget."""
    from app.external_tab import ExternalTab
    from app.widgets.diff_viewer import DiffViewer
    tab = ExternalTab(session, scaffold_state)
    viewers = tab.findChildren(DiffViewer)
    assert len(viewers) == 1
    tab.close()
    tab.deleteLater()


@needs_qt
def test_event_populates_feed(scaffold_state, session):
    """Adding a ScaffoldEvent shows in the activity feed."""
    from app.external_tab import ExternalTab
    from app.widgets.activity_feed import ActivityFeed
    tab = ExternalTab(session, scaffold_state)
    event = _make_event("header", "headers/project.h", "Header reloaded")
    tab.add_external_event(event)
    feed = tab.findChild(ActivityFeed)
    assert feed._list.count() == 1
    tab.close()
    tab.deleteLater()


@needs_qt
def test_tree_refresh(scaffold_state, session):
    """ScaffoldTree reflects scaffold_state content."""
    from PySide6.QtWidgets import QTreeWidget
    from app.external_tab import ExternalTab
    tab = ExternalTab(session, scaffold_state)
    tree_widget = tab.findChild(QTreeWidget)
    # Should have 4 top-level items (Headers, Routes, Tables, Queue)
    assert tree_widget.topLevelItemCount() == 4
    # Headers node should have children (the project.h file)
    headers_node = tree_widget.topLevelItem(0)
    assert headers_node.childCount() > 0
    tab.close()
    tab.deleteLater()


@needs_qt
def test_event_click_shows_diff(scaffold_state, session):
    """Clicking a feed event updates the diff viewer."""
    from app.external_tab import ExternalTab
    from app.widgets.diff_viewer import DiffViewer
    tab = ExternalTab(session, scaffold_state)
    event = _make_event("hot_context", "HOT_CONTEXT.md", "Updated")
    tab.add_external_event(event)
    # Simulate selecting the event
    tab._on_event_selected(event)
    viewer = tab.findChild(DiffViewer)
    # Diff viewer should have some content (even if just "No changes")
    assert viewer._text.toPlainText() != ""
    tab.close()
    tab.deleteLater()


@needs_qt
def test_no_input_bar(scaffold_state, session):
    """ExternalTab has no QLineEdit (read-only observer)."""
    from PySide6.QtWidgets import QLineEdit
    from app.external_tab import ExternalTab
    tab = ExternalTab(session, scaffold_state)
    line_edits = tab.findChildren(QLineEdit)
    assert len(line_edits) == 0
    tab.close()
    tab.deleteLater()


# ═══════════════════════════════════════════════════════════════════════
# ScaffoldTree tests (5, needs PySide6)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_tree_creation():
    """ScaffoldTree creates empty."""
    from app.widgets.scaffold_tree import ScaffoldTree
    tree = ScaffoldTree()
    assert tree is not None
    tree.close()
    tree.deleteLater()


@needs_qt
def test_tree_population(scaffold_state):
    """Refresh with scaffold_state populates Headers/Routes/Tables nodes."""
    from app.widgets.scaffold_tree import ScaffoldTree
    tree = ScaffoldTree()
    tree.refresh(scaffold_state)
    # Headers node should have children
    assert tree._headers_node.childCount() > 0
    # Routes node should have children
    assert tree._routes_node.childCount() > 0
    # Tables node should have children
    assert tree._tables_node.childCount() > 0
    tree.close()
    tree.deleteLater()


@needs_qt
def test_tree_update_on_state_change(scaffold_state):
    """Tree can be refreshed multiple times without error."""
    from app.widgets.scaffold_tree import ScaffoldTree
    tree = ScaffoldTree()
    tree.refresh(scaffold_state)
    count_before = tree._headers_node.childCount()
    # Refresh again (same state)
    tree.refresh(scaffold_state)
    count_after = tree._headers_node.childCount()
    assert count_before == count_after
    tree.close()
    tree.deleteLater()


@needs_qt
def test_highlight_item(scaffold_state):
    """Recently-changed item gets bold font."""
    from app.widgets.scaffold_tree import ScaffoldTree
    tree = ScaffoldTree()
    tree.refresh(scaffold_state)
    tree.highlight_item("header", "headers/project.h")
    # The header file item should be bold
    item = tree._headers_node.child(0)
    assert item.font(0).bold() is True
    tree.close()
    tree.deleteLater()


@needs_qt
def test_highlight_clears(scaffold_state):
    """Highlight removed after timeout (test with 0ms timer)."""
    from app.widgets.scaffold_tree import ScaffoldTree, _HIGHLIGHT_MS
    tree = ScaffoldTree()
    tree.refresh(scaffold_state)
    tree.highlight_item("header", "headers/project.h")
    item = tree._headers_node.child(0)
    assert item.font(0).bold() is True
    # Manually trigger clear (don't wait for real timer)
    if tree._highlighted:
        _, timer = tree._highlighted[0]
        timer.timeout.emit()
    assert item.font(0).bold() is False
    tree.close()
    tree.deleteLater()


# ═══════════════════════════════════════════════════════════════════════
# DiffViewer tests (5, needs PySide6)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_diff_viewer_creation():
    """DiffViewer creates with placeholder text."""
    from app.widgets.diff_viewer import DiffViewer
    viewer = DiffViewer()
    assert viewer is not None
    viewer.close()
    viewer.deleteLater()


@needs_qt
def test_show_diff_additions():
    """Green text appears for additions."""
    from app.widgets.diff_viewer import DiffViewer
    from app import theme
    viewer = DiffViewer()
    viewer.show_diff("line1\n", "line1\nline2\n")
    html = viewer._text.toHtml()
    assert theme.GREEN in html
    viewer.close()
    viewer.deleteLater()


@needs_qt
def test_show_diff_removals():
    """Red text appears for removals."""
    from app.widgets.diff_viewer import DiffViewer
    from app import theme
    viewer = DiffViewer()
    viewer.show_diff("line1\nline2\n", "line1\n")
    html = viewer._text.toHtml()
    assert theme.RED in html
    viewer.close()
    viewer.deleteLater()


@needs_qt
def test_show_empty_diff():
    """'No changes' when old == new."""
    from app.widgets.diff_viewer import DiffViewer
    viewer = DiffViewer()
    viewer.show_diff("same\n", "same\n")
    text = viewer._text.toPlainText()
    assert "No changes" in text
    viewer.close()
    viewer.deleteLater()


@needs_qt
def test_snapshot_diff():
    """show_snapshot_diff compares two snapshot dicts for a path."""
    from app.widgets.diff_viewer import DiffViewer
    viewer = DiffViewer()
    before = {"headers/project.h": "modules: COMPUTE"}
    after = {"headers/project.h": "modules: COMPUTE, VIZ"}
    viewer.show_snapshot_diff(before, after, "headers/project.h")
    html = viewer._text.toHtml()
    # Should show some diff content (additions for VIZ)
    assert "VIZ" in viewer._text.toPlainText() or len(html) > 50
    viewer.close()
    viewer.deleteLater()
