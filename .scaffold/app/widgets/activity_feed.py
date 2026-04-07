"""
Activity feed — chronological scaffold events with timestamps and filtering.

Used by ExternalTab to show a live stream of scaffold state changes,
color-coded by event type.
"""

import time
from collections import deque

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import theme


_MAX_EVENTS = 500

# Event type -> display color
_TYPE_COLORS = {
    "header": theme.YELLOW,
    "route": theme.CYAN,
    "table": theme.TEXT_PRIMARY,
    "tuning": theme.TEXT_SECONDARY,
    "hot_context": "#c084fc",  # Purple / magenta
    "queue": theme.GREEN,
    "results": theme.GREEN,
    "file": theme.TEXT_DIM,
}

_FILTER_OPTIONS = [
    "All",
    "Headers",
    "Routes",
    "Tables",
    "Queue",
    "HOT_CONTEXT",
]

_FILTER_MAP = {
    "All": None,
    "Headers": ["header"],
    "Routes": ["route"],
    "Tables": ["table"],
    "Queue": ["queue", "results"],
    "HOT_CONTEXT": ["hot_context"],
}


class ActivityFeed(QWidget):
    """Chronological event list with filtering by type."""

    event_selected = Signal(object)  # Emits ScaffoldEvent on click

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: deque = deque(maxlen=_MAX_EVENTS)
        self._active_filter: list[str] | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header row: title + filter combo
        header = QWidget()
        header.setObjectName("activityHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)

        title = QLabel("Activity")
        title.setObjectName("activityTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(_FILTER_OPTIONS)
        self._filter_combo.setFixedWidth(110)
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self._filter_combo)

        layout.addWidget(header)

        # Event list
        self._list = QListWidget()
        self._list.setObjectName("activityList")
        self._list.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self._list, 1)

    def add_event(self, event):
        """Append a ScaffoldEvent to the feed."""
        self._events.append(event)
        if self._passes_filter(event):
            self._insert_list_item(event)

    def clear(self):
        """Remove all events."""
        self._events.clear()
        self._list.clear()

    def set_filter(self, event_types: list[str] | None):
        """Set active filter. None = show all."""
        self._active_filter = event_types
        self._rebuild_list()

    def _passes_filter(self, event) -> bool:
        if self._active_filter is None:
            return True
        return event.event_type in self._active_filter

    def _insert_list_item(self, event):
        """Create and insert a list item for an event."""
        ts = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
        text = f"[{ts}] {event.event_type}: {event.detail}"

        item = QListWidgetItem(text)
        color = _TYPE_COLORS.get(event.event_type, theme.TEXT_DIM)
        item.setForeground(QColor(color))
        item.setData(Qt.ItemDataRole.UserRole, event)

        self._list.addItem(item)

        # Auto-scroll to bottom
        self._list.scrollToBottom()

        # Enforce cap on visible items
        while self._list.count() > _MAX_EVENTS:
            self._list.takeItem(0)

    def _rebuild_list(self):
        """Rebuild the visible list from stored events + current filter."""
        self._list.clear()
        for event in self._events:
            if self._passes_filter(event):
                self._insert_list_item(event)

    def _on_filter_changed(self, text: str):
        types = _FILTER_MAP.get(text)
        self._active_filter = types
        self._rebuild_list()

    def _on_item_changed(self, current, previous):
        if current is not None:
            event = current.data(Qt.ItemDataRole.UserRole)
            if event is not None:
                self.event_selected.emit(event)
