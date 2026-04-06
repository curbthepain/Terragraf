"""
Tabbed workspace widget — dynamic tab creation, closing, reordering.

Replaces the old QStackedWidget + sidebar navigation. Each tab is an
independent session (native or external).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QTabWidget,
    QTabBar,
    QWidget,
    QVBoxLayout,
    QLabel,
    QMenu,
)

from . import theme
from .session import Session, SessionManager


class WorkspaceTabWidget(QTabWidget):
    """
    Tab bar with close buttons, drag-to-reorder, and shortcuts.

    Signals:
        tab_session_created(str)  — session ID of newly created tab
        tab_session_closed(str)   — session ID of closed tab
        tab_session_activated(str) — session ID of activated tab
    """

    tab_session_created = Signal(str)
    tab_session_closed = Signal(str)
    tab_session_activated = Signal(str)

    def __init__(self, session_manager: SessionManager, parent=None):
        super().__init__(parent)
        self._session_mgr = session_manager
        self._tab_sessions: dict[int, str] = {}  # tab index -> session ID
        self._tab_factories: dict[str, type] = {}  # tab_type -> widget class

        # Tab bar config
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)

        # Signals
        self.tabCloseRequested.connect(self._on_close_tab)
        self.currentChanged.connect(self._on_tab_changed)

        # Context menu
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self._on_tab_context_menu)

        # Keyboard shortcuts
        self._bind_shortcuts()

    # ── Tab type registration ────────────────────────────────────────

    def register_tab_type(self, tab_type: str, widget_class: type):
        """Register a widget class for a tab type."""
        self._tab_factories[tab_type] = widget_class

    # ── Tab creation ─────────────────────────────────────────────────

    def create_tab(self, tab_type: str = "native", label: str = "",
                   activate: bool = True) -> Session:
        """Create a new tab with a fresh session."""
        session = self._session_mgr.create(tab_type=tab_type, label=label)

        # Create the tab content widget
        factory = self._tab_factories.get(tab_type)
        if factory:
            widget = factory(session)
        else:
            widget = _PlaceholderTab(session)

        idx = self.addTab(widget, session.label)
        self._tab_sessions[idx] = session.id

        if activate:
            self.setCurrentIndex(idx)

        self.tab_session_created.emit(session.id)
        return session

    def close_tab(self, index: int) -> bool:
        """Close a tab by index. Returns False if pinned or last tab."""
        session_id = self._tab_sessions.get(index)
        if not session_id:
            return False

        session = self._session_mgr.get(session_id)
        if session and session.pinned:
            return False

        # Remove tab and session
        widget = self.widget(index)
        self.removeTab(index)
        if widget:
            widget.deleteLater()

        self._session_mgr.destroy(session_id)
        self._rebuild_index_map()

        self.tab_session_closed.emit(session_id)
        return True

    def close_all_except(self, keep_index: int):
        """Close all tabs except the one at keep_index."""
        keep_id = self._tab_sessions.get(keep_index)
        if not keep_id:
            return
        # Close from right to left to avoid index shifting
        for i in range(self.count() - 1, -1, -1):
            if i != keep_index:
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
            self.setTabText(index, f"{prefix}{session.label}")

    # ── Session lookup ───────────────────────────────────────────────

    def session_for_tab(self, index: int) -> str:
        """Get session ID for a tab index."""
        return self._tab_sessions.get(index, "")

    def tab_for_session(self, session_id: str) -> int:
        """Get tab index for a session ID. Returns -1 if not found."""
        for idx, sid in self._tab_sessions.items():
            if sid == session_id:
                return idx
        return -1

    def active_session_id(self) -> str:
        """Get the active tab's session ID."""
        return self._tab_sessions.get(self.currentIndex(), "")

    # ── Internal ─────────────────────────────────────────────────────

    def _on_close_tab(self, index: int):
        if self.count() <= 1:
            return  # Don't close the last tab
        self.close_tab(index)

    def _on_tab_changed(self, index: int):
        session_id = self._tab_sessions.get(index, "")
        if session_id:
            self._session_mgr.activate(session_id)
            self.tab_session_activated.emit(session_id)

    def _on_tab_context_menu(self, pos):
        index = self.tabBar().tabAt(pos)
        if index < 0:
            return

        menu = QMenu(self)
        session_id = self._tab_sessions.get(index, "")
        session = self._session_mgr.get(session_id) if session_id else None

        close_action = menu.addAction("Close")
        close_action.setEnabled(self.count() > 1 and (not session or not session.pinned))
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

        menu.exec(self.tabBar().mapToGlobal(pos))

    def _rebuild_index_map(self):
        """Rebuild tab index -> session ID mapping after removals."""
        new_map = {}
        for i in range(self.count()):
            widget = self.widget(i)
            if hasattr(widget, 'session'):
                new_map[i] = widget.session.id
        self._tab_sessions = new_map

    def _bind_shortcuts(self):
        """Bind workspace keyboard shortcuts."""
        # Ctrl+T — new tab
        QShortcut(QKeySequence("Ctrl+T"), self, self._shortcut_new_tab)
        # Ctrl+W — close tab
        QShortcut(QKeySequence("Ctrl+W"), self, self._shortcut_close_tab)
        # Ctrl+Tab — next tab
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._shortcut_next_tab)
        # Ctrl+Shift+Tab — prev tab
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._shortcut_prev_tab)
        # Ctrl+1..9 — jump to tab
        for i in range(1, 10):
            QShortcut(
                QKeySequence(f"Ctrl+{i}"), self,
                lambda idx=i - 1: self.setCurrentIndex(min(idx, self.count() - 1))
            )

    def _shortcut_new_tab(self):
        # Default to native
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
