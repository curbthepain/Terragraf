"""
WelcomeTab — landing page for new workspace sessions.

Session 27 rewrite: two warm-glass ``QFrame[class="panel"]`` cards
side-by-side (Scaffold Health + Recent Tabs), matching
``additions/terragraf_preview.py``. Still drives off
``ScaffoldState.health_summary()`` and ``SessionManager.all_sessions()``,
and still exposes ``self.session`` / ``self._health_labels`` /
``self._sessions_layout`` / ``self._no_sessions_label`` so existing
integration tests continue to work.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .widgets.panel import make_panel, stat_row


# Keys + display labels for the 3×3 health grid. Order matches the preview.
_HEALTH_KEYS: list[tuple[str, str]] = [
    ("header_files",     "Header files"),
    ("modules",          "Modules"),
    ("route_files",      "Route files"),
    ("routes",           "Routes"),
    ("table_files",      "Table files"),
    ("queue_pending",    "Queue pending"),
    ("queue_running",    "Queue running"),
    ("hot_context_lines", "HOT_CONTEXT lines"),
    ("recent_events",    "Recent events"),
]


def _apply_class(widget: QWidget, cls: str) -> None:
    widget.setProperty("class", cls)
    s = widget.style()
    s.unpolish(widget)
    s.polish(widget)


class WelcomeTab(QWidget):
    """Two-panel welcome page: Scaffold Health + Recent Tabs.

    Exposes ``.session`` for ``WorkspaceTabWidget._rebuild_index_map()``
    compatibility. Health refreshes on ``ScaffoldState.state_changed``.
    """

    def __init__(self, session, scaffold_state, session_manager, parent=None):
        super().__init__(parent)
        self.session = session
        self._state = scaffold_state
        self._session_mgr = session_manager

        self._health_labels: dict[str, QLabel] = {}
        self._sessions_layout: QVBoxLayout | None = None
        self._no_sessions_label: QLabel | None = None

        self._build_ui()
        self._refresh()

        self._state.state_changed.connect(self._refresh)

    # ── UI build ─────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        root.addWidget(self._build_health_panel(), 3)
        root.addWidget(self._build_sessions_panel(), 2)

    def _build_health_panel(self) -> QFrame:
        panel, inner = make_panel("Scaffold Health")

        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(8)

        for i, (key, label_text) in enumerate(_HEALTH_KEYS):
            r, c = divmod(i, 3)
            row_widget, value_label = stat_row(label_text)
            grid.addWidget(row_widget, r, c)
            self._health_labels[key] = value_label

        for c in range(3):
            grid.setColumnStretch(c, 1)

        grid_wrap = QWidget()
        grid_wrap.setLayout(grid)
        inner.addWidget(grid_wrap)
        inner.addStretch(1)
        return panel

    def _build_sessions_panel(self) -> QFrame:
        panel, inner = make_panel("Recent Tabs")

        # The sessions layout is populated in _refresh(). We keep a
        # persistent "No active sessions" label at index 0 so existing
        # tests (which check .isHidden() / .isVisible() on it) continue
        # to work against the new layout.
        sessions_wrap = QWidget()
        self._sessions_layout = QVBoxLayout(sessions_wrap)
        self._sessions_layout.setContentsMargins(0, 0, 0, 0)
        self._sessions_layout.setSpacing(4)

        self._no_sessions_label = QLabel("— NO ACTIVE SESSIONS")
        _apply_class(self._no_sessions_label, "stat-key")
        self._sessions_layout.addWidget(self._no_sessions_label)

        inner.addWidget(sessions_wrap)
        inner.addStretch(1)
        return panel

    # ── Refresh ──────────────────────────────────────────────────────

    def _refresh(self):
        """Update health summary and recent-tabs list."""
        summary = self._state.health_summary()
        for key, lbl in self._health_labels.items():
            lbl.setText(str(summary.get(key, 0)))

        layout = self._sessions_layout
        if layout is None:
            return

        # Drop everything after the sentinel "no sessions" label at index 0.
        while layout.count() > 1:
            item = layout.takeAt(1)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        sessions = self._session_mgr.all_sessions()
        recent = sorted(sessions, key=lambda s: s.created_at, reverse=True)[:5]

        if not recent:
            if self._no_sessions_label is not None:
                self._no_sessions_label.setVisible(True)
            return

        if self._no_sessions_label is not None:
            self._no_sessions_label.setVisible(False)

        active_id = getattr(self._session_mgr, "active_id", None)
        for s in recent:
            is_active = (s.id == active_id)
            dot_color = "#6EE0B0" if is_active else "#8FA0B6"
            state_text = "ACTIVE" if is_active else "RECENT"
            layout.addWidget(
                _tab_row(s.label, f"{s.tab_type} · {s.id[:6]}", state_text, dot_color)
            )


def _tab_row(name: str, slug: str, state: str, dot_color: str) -> QWidget:
    """Single row inside the Recent Tabs panel."""
    row = QWidget()
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 4, 0, 4)
    rl.setSpacing(12)

    dot = QLabel("●")
    dot.setStyleSheet(
        f"color: {dot_color}; font-size: 11px;"
        " background: transparent; border: none;"
    )
    rl.addWidget(dot)

    name_lbl = QLabel(name.upper())
    _apply_class(name_lbl, "stat-compact")
    rl.addWidget(name_lbl)

    slug_lbl = QLabel(slug)
    _apply_class(slug_lbl, "hint")
    rl.addWidget(slug_lbl)

    rl.addStretch(1)

    state_lbl = QLabel(state)
    _apply_class(state_lbl, "stat-key")
    rl.addWidget(state_lbl, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return row
