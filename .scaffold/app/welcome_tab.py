"""
WelcomeTab — landing page for new workspace sessions.

Shows scaffold health summary, recent sessions, and quick action buttons.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QGridLayout,
)


class WelcomeTab(QWidget):
    """
    Welcome page showing scaffold health, recent sessions, and quick actions.
    Exposes .session for tab_widget._rebuild_index_map() compatibility.
    """

    def __init__(self, session, scaffold_state, session_manager, parent=None):
        super().__init__(parent)
        self.session = session
        self._state = scaffold_state
        self._session_mgr = session_manager

        self._build_ui()
        self._refresh()

        # Auto-refresh on state changes
        self._state.state_changed.connect(self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Terragraf Workspace")
        title.setObjectName("title")
        layout.addWidget(title)

        # Health summary group
        self._health_group = QGroupBox("Scaffold Health")
        self._health_grid = QGridLayout()
        self._health_group.setLayout(self._health_grid)
        layout.addWidget(self._health_group)

        # Health labels (populated in _refresh)
        self._health_labels: dict[str, QLabel] = {}
        health_keys = [
            ("header_files", "Header files"),
            ("modules", "Modules"),
            ("route_files", "Route files"),
            ("routes", "Routes"),
            ("table_files", "Table files"),
            ("queue_pending", "Queue pending"),
            ("queue_running", "Queue running"),
            ("hot_context_lines", "HOT_CONTEXT lines"),
            ("recent_events", "Recent events"),
        ]
        for i, (key, label_text) in enumerate(health_keys):
            row, col = divmod(i, 3)
            name_label = QLabel(f"{label_text}:")
            name_label.setObjectName("status_cyan")
            value_label = QLabel("—")
            value_label.setObjectName("dim")
            self._health_grid.addWidget(name_label, row, col * 2)
            self._health_grid.addWidget(value_label, row, col * 2 + 1)
            self._health_labels[key] = value_label

        # Recent sessions group
        self._sessions_group = QGroupBox("Recent Sessions")
        self._sessions_layout = QVBoxLayout()
        self._sessions_group.setLayout(self._sessions_layout)
        self._no_sessions_label = QLabel("No active sessions")
        self._no_sessions_label.setObjectName("dim")
        self._sessions_layout.addWidget(self._no_sessions_label)
        layout.addWidget(self._sessions_group)

        # Hint — sidebar already covers all entry points.
        hint = QLabel(
            "Use the sidebar on the left to create a new tab, browse routes, "
            "run a skill, or open settings."
        )
        hint.setObjectName("dim")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

    def _refresh(self):
        """Update health summary and sessions list."""
        # Health
        summary = self._state.health_summary()
        for key, label in self._health_labels.items():
            value = summary.get(key, 0)
            label.setText(str(value))

        # Sessions list — clear old labels
        while self._sessions_layout.count() > 1:
            item = self._sessions_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        sessions = self._session_mgr.all_sessions()
        recent = sorted(sessions, key=lambda s: s.created_at, reverse=True)[:5]

        if not recent:
            self._no_sessions_label.setVisible(True)
        else:
            self._no_sessions_label.setVisible(False)
            for s in recent:
                lbl = QLabel(f"  {s.label}  ({s.tab_type}, {s.id[:6]})")
                lbl.setObjectName("dim")
                self._sessions_layout.addWidget(lbl)
