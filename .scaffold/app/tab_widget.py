"""
Workspace tab widget — dynamic tab creation, closing, reordering.

Session 27 refactor: no longer a ``QTabWidget`` subclass. Instead this is a
plain ``QWidget`` wrapping a ``QStackedWidget`` for tab bodies. The visible
tab strip lives in ``TopBar.tab_strip`` (a ``WorkspaceTabStrip`` of
``ws-tab`` pills) and ``MainWindow`` wires the two together via the new
``tab_added`` / ``tab_removed`` / ``tab_label_changed`` / ``current_changed``
signals on this class.

The existing public API (``register_tab_type``, ``create_tab``, ``close_tab``,
``session_for_tab``, ``tab_for_session``, ``active_session_id``,
``setCurrentIndex``, ``currentIndex``, ``count``, ``widget``) and the existing
``tab_session_created`` / ``tab_session_closed`` / ``tab_session_activated``
signals are preserved so call sites don't need to change.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .session import Session, SessionManager


class WorkspaceTabWidget(QWidget):
    """
    Stack-of-pages workspace with no built-in tab bar.

    Signals:
        tab_session_created(str)   — session ID of newly created tab
        tab_session_closed(str)    — session ID of closed tab
        tab_session_activated(str) — session ID of activated tab
        tab_added(int, str)        — new pill index + label (for TabStrip)
        tab_removed(int)           — pill index (for TabStrip)
        tab_label_changed(int, str) — pill index + new label
        current_changed(int)       — current pill index
    """

    tab_session_created = Signal(str)
    tab_session_closed = Signal(str)
    tab_session_activated = Signal(str)

    tab_added = Signal(int, str)
    tab_removed = Signal(int)
    tab_label_changed = Signal(int, str)
    current_changed = Signal(int)

    def __init__(self, session_manager: SessionManager, parent=None):
        super().__init__(parent)
        self._session_mgr = session_manager
        self._tab_sessions: dict[int, str] = {}
        self._tab_factories: dict[str, Callable[[Session], QWidget]] = {}
        self._tab_labels: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)
        self._stack.currentChanged.connect(self._on_stack_changed)

        self._bind_shortcuts()

    # ── Tab type registration ────────────────────────────────────────

    def register_tab_type(self, tab_type: str, factory: Callable[[Session], QWidget]):
        """Register a widget factory for a tab type.

        ``factory`` is any callable that takes a ``Session`` and returns
        the content widget for the tab (``MainWindow`` passes lambdas).
        """
        self._tab_factories[tab_type] = factory

    # ── Tab creation ─────────────────────────────────────────────────

    def create_tab(
        self,
        tab_type: str = "native",
        label: str = "",
        activate: bool = True,
    ) -> Session:
        """Create a new tab with a fresh session."""
        session = self._session_mgr.create(tab_type=tab_type, label=label)

        factory = self._tab_factories.get(tab_type)
        if factory:
            widget = factory(session)
        else:
            widget = _PlaceholderTab(session)

        # Pre-compute the index so the session mapping is already in place
        # before QStackedWidget.addWidget fires currentChanged(0) on the
        # very first insertion (otherwise _on_stack_changed would look up
        # an empty session ID and skip activation).
        idx = self._stack.count()
        self._tab_sessions[idx] = session.id
        self._tab_labels[idx] = session.label

        added_idx = self._stack.addWidget(widget)
        assert added_idx == idx, (
            f"QStackedWidget index drift: expected {idx}, got {added_idx}"
        )

        self.tab_added.emit(idx, session.label)
        self.tab_session_created.emit(session.id)

        if activate:
            self.setCurrentIndex(idx)
        return session

    def close_tab(self, index: int) -> bool:
        """Close a tab by index. Returns False if pinned."""
        session_id = self._tab_sessions.get(index)
        if not session_id:
            return False

        session = self._session_mgr.get(session_id)
        if session and session.pinned:
            return False

        # Welcome tabs are non-closable (mirrors the old QTabWidget guard
        # plus the sidebar rule that welcome is the home tab).
        if session and session.tab_type == "welcome":
            return False

        widget = self._stack.widget(index)
        if widget is None:
            return False
        self._stack.removeWidget(widget)
        widget.deleteLater()

        self._session_mgr.destroy(session_id)
        self._rebuild_index_map()

        self.tab_removed.emit(index)
        self.tab_session_closed.emit(session_id)
        return True

    def close_all_except(self, keep_index: int):
        """Close all tabs except the one at keep_index."""
        keep_id = self._tab_sessions.get(keep_index)
        if not keep_id:
            return
        for i in range(self.count() - 1, -1, -1):
            if i == keep_index:
                continue
            sid = self._tab_sessions.get(i)
            session = self._session_mgr.get(sid) if sid else None
            if session and not session.pinned:
                self.close_tab(i)

    def pin_tab(self, index: int, pinned: bool = True):
        """Toggle pin state on a tab."""
        session_id = self._tab_sessions.get(index)
        if not session_id:
            return
        session = self._session_mgr.get(session_id)
        if session:
            session.pinned = pinned
            prefix = "[P] " if pinned else ""
            new_label = f"{prefix}{session.label}"
            self._tab_labels[index] = new_label
            self.tab_label_changed.emit(index, new_label)

    # ── Session lookup ───────────────────────────────────────────────

    def session_for_tab(self, index: int) -> str:
        return self._tab_sessions.get(index, "")

    def tab_for_session(self, session_id: str) -> int:
        for idx, sid in self._tab_sessions.items():
            if sid == session_id:
                return idx
        return -1

    def active_session_id(self) -> str:
        return self._tab_sessions.get(self.currentIndex(), "")

    # ── QTabWidget-compatible wrappers ───────────────────────────────

    def count(self) -> int:
        return self._stack.count()

    def currentIndex(self) -> int:
        return self._stack.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)

    def widget(self, index: int) -> QWidget | None:
        return self._stack.widget(index)

    def currentWidget(self) -> QWidget | None:
        return self._stack.currentWidget()

    def tab_label(self, index: int) -> str:
        return self._tab_labels.get(index, "")

    def show_tab_context_menu(self, index: int, global_pos) -> None:
        """Show the right-click context menu for a pill (called by MainWindow)."""
        if index < 0 or index >= self.count():
            return

        menu = QMenu(self)
        session_id = self._tab_sessions.get(index, "")
        session = self._session_mgr.get(session_id) if session_id else None

        close_action = menu.addAction("Close")
        close_action.setEnabled(
            self.count() > 1 and (not session or not session.pinned)
            and not (session and session.tab_type == "welcome")
        )
        close_action.triggered.connect(lambda: self.close_tab(index))

        close_others = menu.addAction("Close Others")
        close_others.setEnabled(self.count() > 1)
        close_others.triggered.connect(lambda: self.close_all_except(index))

        menu.addSeparator()

        pin_text = "Unpin" if (session and session.pinned) else "Pin"
        pin_action = menu.addAction(pin_text)
        pin_action.triggered.connect(
            lambda: self.pin_tab(index, not (session.pinned if session else False))
        )

        menu.addSeparator()

        dup_action = menu.addAction("Duplicate")
        dup_action.triggered.connect(
            lambda: self.create_tab(
                tab_type=session.tab_type if session else "native",
                label=f"{session.label} (copy)" if session else "",
            )
        )

        menu.exec(global_pos)

    # ── Internal ─────────────────────────────────────────────────────

    def _on_stack_changed(self, index: int):
        session_id = self._tab_sessions.get(index, "")
        if session_id:
            self._session_mgr.activate(session_id)
            self.tab_session_activated.emit(session_id)
        self.current_changed.emit(index)

    def _on_close_tab(self, index: int):
        # Kept for backward compat with the "don't close the last tab" guard
        # that tests expect. The new MainWindow flow routes
        # WorkspaceTabStrip.close_requested straight here.
        if self.count() <= 1:
            return
        self.close_tab(index)

    def _rebuild_index_map(self):
        """Rebuild tab index -> session ID + label mapping after removals."""
        new_sessions: dict[int, str] = {}
        new_labels: dict[int, str] = {}
        for i in range(self._stack.count()):
            w = self._stack.widget(i)
            if hasattr(w, "session"):
                new_sessions[i] = w.session.id
                # Prefer the label we already tracked if present; otherwise
                # fall back to the session's own label.
                new_labels[i] = self._tab_labels.get(i, w.session.label)
        self._tab_sessions = new_sessions
        self._tab_labels = new_labels

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, self._shortcut_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, self._shortcut_close_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._shortcut_next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._shortcut_prev_tab)
        for i in range(1, 10):
            QShortcut(
                QKeySequence(f"Ctrl+{i}"),
                self,
                lambda idx=i - 1: self.setCurrentIndex(min(idx, self.count() - 1)),
            )

    def _shortcut_new_tab(self):
        self.create_tab(tab_type="native")

    def _shortcut_close_tab(self):
        if self.count() > 1:
            self.close_tab(self.currentIndex())

    def _shortcut_next_tab(self):
        if self.count() > 1:
            self.setCurrentIndex((self.currentIndex() + 1) % self.count())

    def _shortcut_prev_tab(self):
        if self.count() > 1:
            self.setCurrentIndex((self.currentIndex() - 1) % self.count())


class _PlaceholderTab(QWidget):
    """Fallback widget when no factory is registered for a tab type."""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{session.tab_type} session: {session.id}")
        label.setObjectName("subtitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        hint = QLabel("Tab type not yet implemented")
        hint.setObjectName("dim")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
