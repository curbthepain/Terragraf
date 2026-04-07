"""Workspace top bar + footer — Kohala preview chrome.

Two floating-card widgets that bracket the workspace content area:

* ``TopBar``  — 58px warm-glass card above the tab content, hosting the
  hamburger menu, sidebar toggle, the ``WorkspaceTabStrip`` of ws-tab
  pills, and the TERRA/GRAF brand-mark.
* ``Footer`` — 44px warm-glass strip at the bottom, rendering a single
  centered red-mono brand line (``BRIDGE: … · N SESSION · PATENT PENDING``).
  Bridge state, session count, and coherence warnings are folded into
  this one label; ``QStatusBar`` was removed in Session 27.

The pre-S27 ``TabCornerChrome`` (hamburger + sidebar toggle sitting inside
the QTabWidget's corner slot) is gone.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QWidget,
)

from .tab_strip import WorkspaceTabStrip


def _apply_class(widget: QWidget, cls: str) -> None:
    widget.setProperty("class", cls)
    s = widget.style()
    s.unpolish(widget)
    s.polish(widget)


# ── TopBar ─────────────────────────────────────────────────────────────

class TopBar(QFrame):
    """58px warm-glass card above the workspace tab content.

    Layout mirrors ``additions/terragraf_preview.py``:

        [☰] [▣]  [ws-tab pills...] <stretch>  TERRA GRAF

    Signals:
        sidebar_toggle_clicked() — user pressed the ``▣`` button
    """

    sidebar_toggle_clicked = Signal()

    def __init__(self, hamburger_menu: QMenu, parent=None):
        super().__init__(parent)
        _apply_class(self, "topbar")
        self.setFixedHeight(58)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 24, 10)
        layout.setSpacing(10)

        # ── Hamburger ──
        self.hamburger_button = QToolButton()
        _apply_class(self.hamburger_button, "iconbtn")
        self.hamburger_button.setText("≡")
        self.hamburger_button.setToolTip("Menu")
        self.hamburger_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.hamburger_button.setMenu(hamburger_menu)
        self.hamburger_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hamburger_button.setFixedSize(38, 32)
        layout.addWidget(self.hamburger_button)

        # ── Sidebar toggle ──
        self.sidebar_toggle = QToolButton()
        _apply_class(self.sidebar_toggle, "iconbtn")
        self.sidebar_toggle.setText("▣")
        self.sidebar_toggle.setToolTip("Toggle sidebar (Ctrl+B)")
        self.sidebar_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle.setFixedSize(38, 32)
        self.sidebar_toggle.clicked.connect(self.sidebar_toggle_clicked.emit)
        layout.addWidget(self.sidebar_toggle)

        # ── ws-tab pill strip ──
        self.tab_strip = WorkspaceTabStrip()
        layout.addWidget(self.tab_strip, 1)

        layout.addStretch(1)

        # ── Brand-mark ──
        self.brand_terra = QLabel("TERRA")
        _apply_class(self.brand_terra, "brand-mark")
        layout.addWidget(self.brand_terra)

        self.brand_graf = QLabel("GRAF")
        _apply_class(self.brand_graf, "brand-mark-red")
        layout.addWidget(self.brand_graf)

    def set_sidebar_expanded(self, expanded: bool) -> None:
        """Reflect sidebar expansion state on the toggle icon."""
        self.sidebar_toggle.setText("◧" if expanded else "▣")


# ── Footer ─────────────────────────────────────────────────────────────

class Footer(QFrame):
    """44px warm-glass footer strip with a single centered brand line.

    Bridge/session/coherence state all fold into the same label:

        BRIDGE: OFFLINE · 1 SESSION · PATENT PENDING

    When a coherence warning is active the ``PATENT PENDING`` tail is
    replaced by the warning text.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        _apply_class(self, "topbar")  # reuses the warm-glass top bar look
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 8)
        layout.setSpacing(0)
        layout.addStretch(1)

        self.center_label = QLabel("")
        _apply_class(self.center_label, "brand-footer")
        self.center_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.center_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        # Segment state
        self._bridge_state: str = "offline"
        self._session_count: int = 0
        self._coherence_warning: str | None = None

        self._rebuild()

    # ── Public setters ───────────────────────────────────────────────

    def set_bridge_state(self, state) -> None:
        """Update the BRIDGE segment.

        Accepts either a raw string (``"online"``/``"offline"``/…) or a
        boolean — ``True`` means online, ``False`` means offline — to
        make it easy to wire ``BridgeClient.connection_changed(bool)``
        directly.
        """
        if isinstance(state, bool):
            state = "online" if state else "offline"
        self._bridge_state = str(state or "offline")
        self._rebuild()

    def set_session_count(self, n: int) -> None:
        self._session_count = max(0, int(n))
        self._rebuild()

    def set_coherence_warning(self, warning: str | None) -> None:
        self._coherence_warning = warning.strip() if warning else None
        self._rebuild()

    # ── Internal ─────────────────────────────────────────────────────

    def _rebuild(self) -> None:
        n = self._session_count
        tail = self._coherence_warning or "PATENT PENDING"
        plural = "S" if n != 1 else ""
        text = (
            f"BRIDGE: {self._bridge_state.upper()}"
            f"   ·   {n} SESSION{plural}"
            f"   ·   {tail.upper()}"
        )
        self.center_label.setText(text)
