"""
External tab — scaffold observer for Claude Code / Cursor activity.

Three-panel read-only layout:
  - Activity feed (left): chronological scaffold events
  - Scaffold tree (center): parsed headers/routes/tables
  - Diff viewer (right): unified diff for selected changes

Connects to ExternalDetector to populate the feed with external-only events.
"""

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from .external_detector import ExternalDetector
from .widgets.activity_feed import ActivityFeed
from .widgets.diff_viewer import DiffViewer
from .widgets.scaffold_tree import ScaffoldTree


class ExternalTab(QWidget):
    """
    Read-only observer tab showing external scaffold activity.

    Layout:
        [Activity Feed] | [Scaffold Tree] | [Diff Viewer]
    """

    def __init__(self, session, scaffold_state, parent=None):
        super().__init__(parent)
        self.session = session
        self._state = scaffold_state
        self._last_snapshot = scaffold_state.take_snapshot()

        self._build_ui()
        self._wire_signals()

        # Initial tree population
        self._tree.refresh(scaffold_state)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._feed = ActivityFeed()
        self._tree = ScaffoldTree()
        self._diff = DiffViewer()

        splitter.addWidget(self._feed)
        splitter.addWidget(self._tree)
        splitter.addWidget(self._diff)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)

        root.addWidget(splitter, 1)

    def _wire_signals(self):
        # Feed click → show diff for that event
        self._feed.event_selected.connect(self._on_event_selected)

        # Tree click → show info for that item
        self._tree.item_selected.connect(self._on_tree_selected)

        # State changes → refresh tree + take snapshot for diffing
        self._state.state_changed.connect(self._on_state_changed)

    def add_external_event(self, event):
        """Called by window to feed external events from the detector."""
        self._feed.add_event(event)
        self._tree.highlight_item(event.event_type, event.path)

        # Track in session context
        if event.path and event.path not in self.session.context.routes_consulted:
            self.session.context.routes_consulted.append(event.path)

    def _on_event_selected(self, event):
        """Show diff for the selected event's path."""
        current_snapshot = self._state.take_snapshot()
        self._diff.show_snapshot_diff(
            self._last_snapshot, current_snapshot, event.path
        )

    def _on_tree_selected(self, category: str, name: str):
        """Show info when a tree item is clicked."""
        path = f"{category}s/{name}" if category != "queue" else "instances/shared/queue.json"
        # Just show the current snapshot entry as context
        snap = self._state.take_snapshot()
        content = snap.get(path, "")
        if content:
            self._diff.show_diff("", content, title=path)
        else:
            self._diff.clear()

    def _on_state_changed(self):
        """Refresh tree and update snapshot baseline."""
        self._tree.refresh(self._state)
        self._last_snapshot = self._state.take_snapshot()
