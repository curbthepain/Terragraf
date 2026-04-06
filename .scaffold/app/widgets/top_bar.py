"""TabCornerChrome — hamburger menu + sidebar toggle, hosted as a tab-bar
corner widget on the workspace ``QTabWidget``.

Renders two compact ``QToolButton``s flush with the tab strip:
  ☰  hamburger menu  (popup contains the same actions as the old File/View menus)
  ▤  sidebar toggle  (collapsed/expanded; arrow appears when expanded)

The class lives in ``top_bar.py`` for git history continuity. The legacy
``TopBar`` name is exported as an alias so external imports keep working.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QToolButton,
    QMenu,
)


class TabCornerChrome(QWidget):
    """Compact two-button chrome widget designed for ``QTabWidget.setCornerWidget``.

    Signals:
        sidebar_toggle_clicked() — user pressed the sidebar toggle button
    """

    sidebar_toggle_clicked = Signal()

    def __init__(self, hamburger_menu: QMenu, parent=None):
        super().__init__(parent)
        self.setObjectName("top_bar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(2)

        # ── Hamburger ──
        self.hamburger_button = QToolButton()
        self.hamburger_button.setObjectName("chrome_button")
        self.hamburger_button.setText("☰")
        self.hamburger_button.setToolTip("Menu")
        self.hamburger_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.hamburger_button.setMenu(hamburger_menu)
        self.hamburger_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.hamburger_button)

        # ── Sidebar toggle ──
        self.sidebar_toggle = QToolButton()
        self.sidebar_toggle.setObjectName("chrome_button")
        self.sidebar_toggle.setText("▤")
        self.sidebar_toggle.setToolTip("Toggle sidebar (Ctrl+B)")
        self.sidebar_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle.clicked.connect(self.sidebar_toggle_clicked.emit)
        layout.addWidget(self.sidebar_toggle)

    def set_sidebar_expanded(self, expanded: bool):
        """Reflect sidebar expansion state on the toggle icon."""
        self.sidebar_toggle.setText("▤◀" if expanded else "▤")


# Backwards-compatible alias — keeps old `from .top_bar import TopBar` callsites working.
TopBar = TabCornerChrome
