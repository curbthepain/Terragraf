"""Sidebar — collapsible contextual rail.

Window chrome that observes which top-level tab is active and shows a
list of action buttons relevant to that tab. Pure view: emits
``action_triggered(action_id)`` and lets the window dispatch.

Two widths only — collapsed (icon-only) and expanded (icon + label).
The toggle is on the TopBar, not inside the sidebar.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
)

from .. import theme
from .icon_button import IconButton


# Per-tab layouts: list of (icon, label, action_id)
# Every action_id is dispatched in window._on_sidebar_action.
_TAB_LAYOUTS: dict[str, list[tuple[str, str, str]]] = {
    "welcome": [
        ("+", "New Native",        "new_native"),
        ("◫", "New External",      "new_external"),
        ("▣", "New Project...",    "dlg_project_new"),
        ("♥", "Health Check",      "panel_health"),
        ("◐", "Status",            "panel_status"),
        ("◑", "Mode",              "panel_mode"),
        ("✓", "Consistency Scan",  "skill:consistency_scan"),
        ("≡", "Knowledge",         "browse_knowledge"),
        ("⚙", "Settings",          "settings"),
    ],
    "native": [
        ("→", "Routes",            "browse_routes"),
        ("⤳", "Jump Route",        "route_jump"),
        ("◫", "Headers",           "browse_headers"),
        ("⚒", "Generate...",       "dlg_generate"),
        ("▲", "Train Model...",    "dlg_train"),
        ("∑", "Solve Math...",     "dlg_solve"),
        ("♪", "Analyze Signal...", "dlg_analyze"),
        ("◉", "Render 3D...",      "dlg_render"),
        ("⚡", "Run Skill...",     "browse_skills"),
        ("⚠", "Lookup Error",      "browse_lookup"),
        ("◇", "Patterns",          "browse_patterns"),
        ("◈", "Tune",              "panel_tune"),
        ("≡", "Knowledge",         "browse_knowledge"),
        ("⚙", "Settings",          "settings"),
    ],
    "external": [
        ("⟳", "Refresh Snapshot",  "refresh_snapshot"),
        ("⌫", "Clear Activity",    "clear_activity"),
        ("◫", "Headers",           "browse_headers"),
        ("⌥", "Worktrees",         "browse_worktrees"),
        ("☰", "Queue",             "panel_queue"),
        ("◰", "Deps",              "panel_deps"),
        ("◎", "MCP Server",        "panel_mcp"),
        ("▶", "Viewer",            "panel_viewer"),
        ("✦", "Sharpen",           "panel_sharpen"),
        ("⎇", "Git Flow...",       "dlg_git_flow"),
        ("♥", "Health Check",      "panel_health"),
        ("✓", "Consistency Scan",  "skill:consistency_scan"),
        ("¶", "Hot Context",       "panel_hot_context"),
        ("⚙", "Settings",          "settings"),
    ],
}


class Sidebar(QWidget):
    """Collapsible contextual sidebar.

    Signals:
        action_triggered(str) — action_id from _TAB_LAYOUTS
    """

    action_triggered = Signal(str)

    WIDTH_COLLAPSED = theme.SIDEBAR_WIDTH_COLLAPSED
    WIDTH_EXPANDED = theme.SIDEBAR_WIDTH_EXPANDED

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar_v2")

        self._expanded = False
        self._current_tab_type: str | None = None
        self._buttons: list[IconButton] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 4, 0, 4)
        self._layout.setSpacing(2)

        self._section_label = QLabel("")
        self._section_label.setObjectName("sidebar_section")
        self._section_label.setVisible(False)
        self._layout.addWidget(self._section_label)

        # Container that holds dynamic action buttons
        self._buttons_container = QWidget()
        self._buttons_layout = QVBoxLayout(self._buttons_container)
        self._buttons_layout.setContentsMargins(0, 0, 0, 0)
        self._buttons_layout.setSpacing(0)
        self._layout.addWidget(self._buttons_container)

        self._layout.addStretch(1)

        # Footer separator + bridge indicator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        self._layout.addWidget(sep)

        self._bridge_label = QLabel("●")
        self._bridge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bridge_label.setStyleSheet(f"color: {theme.RED}; padding: 6px;")
        self._bridge_label.setToolTip("bridge: offline")
        self._layout.addWidget(self._bridge_label)

        self.set_expanded(False)
        self.set_active_tab("welcome")

    # ── Public API ──────────────────────────────────────────────────

    def set_expanded(self, expanded: bool):
        """Switch between collapsed (icon only) and expanded (icon + label)."""
        self._expanded = expanded
        width = self.WIDTH_EXPANDED if expanded else self.WIDTH_COLLAPSED
        self.setFixedWidth(width)
        self._section_label.setVisible(expanded and self._current_tab_type is not None)
        for btn in self._buttons:
            btn.set_expanded(expanded)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_active_tab(self, tab_type: str):
        """Rebuild action buttons for the given tab type."""
        if tab_type == self._current_tab_type:
            return
        self._current_tab_type = tab_type
        self._section_label.setText(tab_type.upper())
        self._section_label.setVisible(self._expanded)
        self._rebuild_buttons()

    def set_bridge_status(self, connected: bool):
        color = theme.GREEN if connected else theme.RED
        self._bridge_label.setStyleSheet(f"color: {color}; padding: 6px;")
        self._bridge_label.setToolTip(
            f"bridge: {'online' if connected else 'offline'}"
        )

    def buttons(self) -> list[IconButton]:
        """Expose the current button list (for tests)."""
        return list(self._buttons)

    # ── Internal ────────────────────────────────────────────────────

    def _rebuild_buttons(self):
        # Drop existing
        while self._buttons_layout.count():
            item = self._buttons_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._buttons.clear()

        layout = _TAB_LAYOUTS.get(self._current_tab_type, [])
        for icon, label, action_id in layout:
            btn = IconButton(icon, label)
            btn.set_expanded(self._expanded)
            btn.clicked.connect(lambda _=False, aid=action_id: self.action_triggered.emit(aid))
            self._buttons.append(btn)
            self._buttons_layout.addWidget(btn)
