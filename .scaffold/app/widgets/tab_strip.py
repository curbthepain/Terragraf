"""WorkspaceTabStrip — horizontal pill-strip replacement for QTabBar.

Each open workspace tab renders as a ``QPushButton[class="ws-tab"]`` — the
glowing red pill from the Kohala preview (see ``additions/terragraf_preview.py``
and the ``.ws-tab`` rule in ``themes/kohala.qss``). Pills are exclusive
(only one is checked at a time) and carry an inline ``×`` close affordance
on non-welcome tabs.

The strip is a pure view: it owns no session state, mirrors whatever
``WorkspaceTabWidget`` tells it, and emits ``current_changed(int)`` /
``close_requested(int)`` on user interaction. ``MainWindow`` is responsible
for wiring the two together.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QToolButton,
)


def _apply_class(widget: QWidget, cls: str) -> None:
    """Set a ``class`` property and re-polish so the QSS rule applies."""
    widget.setProperty("class", cls)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


class _TabPill(QWidget):
    """Single ws-tab pill: a checkable button + an optional close `×`."""

    clicked = Signal()
    close_clicked = Signal()

    def __init__(self, label: str, closable: bool = True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.button = QPushButton(label.upper())
        _apply_class(self.button, "ws-tab")
        self.button.setCheckable(True)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setMinimumHeight(34)
        self.button.clicked.connect(self.clicked.emit)
        layout.addWidget(self.button)

        self.close_btn = QToolButton()
        _apply_class(self.close_btn, "iconbtn")
        self.close_btn.setText("×")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Close tab")
        self.close_btn.clicked.connect(self.close_clicked.emit)
        self.close_btn.setVisible(closable)
        layout.addWidget(self.close_btn)

    def set_label(self, label: str) -> None:
        self.button.setText(label.upper())

    def set_checked(self, checked: bool) -> None:
        self.button.setChecked(checked)

    def set_closable(self, closable: bool) -> None:
        self.close_btn.setVisible(closable)


class WorkspaceTabStrip(QWidget):
    """Horizontal strip of ``ws-tab`` pills that mirrors ``WorkspaceTabWidget``.

    Signals:
        current_changed(int)    — user clicked a pill; argument is its index
        close_requested(int)    — user clicked a pill's `×`; argument is its index
    """

    current_changed = Signal(int)
    close_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ws_tab_strip")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

        self._pills: list[_TabPill] = []

    # ── Mirroring API (called by MainWindow from WorkspaceTabWidget signals) ──

    def add_tab(self, index: int, label: str, closable: bool = True) -> None:
        pill = _TabPill(label, closable=closable, parent=self)
        pill.clicked.connect(lambda p=pill: self._on_pill_clicked(p))
        pill.close_clicked.connect(lambda p=pill: self._on_pill_close(p))
        if 0 <= index < len(self._pills):
            self._pills.insert(index, pill)
            self._layout.insertWidget(index, pill)
        else:
            self._pills.append(pill)
            self._layout.addWidget(pill)

    def remove_tab(self, index: int) -> None:
        if not (0 <= index < len(self._pills)):
            return
        pill = self._pills.pop(index)
        self._layout.removeWidget(pill)
        pill.deleteLater()

    def set_label(self, index: int, label: str) -> None:
        if 0 <= index < len(self._pills):
            self._pills[index].set_label(label)

    def set_closable(self, index: int, closable: bool) -> None:
        if 0 <= index < len(self._pills):
            self._pills[index].set_closable(closable)

    def set_current(self, index: int) -> None:
        for i, pill in enumerate(self._pills):
            pill.set_checked(i == index)

    def count(self) -> int:
        return len(self._pills)

    def clear(self) -> None:
        while self._pills:
            self.remove_tab(0)

    # ── Internal ─────────────────────────────────────────────────────

    def _index_of(self, pill: _TabPill) -> int:
        try:
            return self._pills.index(pill)
        except ValueError:
            return -1

    def _on_pill_clicked(self, pill: _TabPill) -> None:
        idx = self._index_of(pill)
        if idx < 0:
            return
        # Force-check the clicked pill (QPushButton.setCheckable may toggle off
        # if the user re-clicks the already-active pill).
        self.set_current(idx)
        self.current_changed.emit(idx)

    def _on_pill_close(self, pill: _TabPill) -> None:
        idx = self._index_of(pill)
        if idx >= 0:
            self.close_requested.emit(idx)
