"""IconButton — flat icon+label sidebar button.

Used by Sidebar to render contextual action rows. In collapsed mode the
label is hidden and only the icon shows (with a tooltip).  In expanded
mode the icon and label sit side by side, left-aligned.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


class IconButton(QPushButton):
    """Flat sidebar button with optional text label.

    The icon is a unicode glyph rather than a QIcon — keeps the build
    asset-free and matches the existing terminal aesthetic.
    """

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_text = icon_text
        self._label = label
        self._expanded = False
        self.setObjectName("icon_btn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)
        self.setFixedHeight(36)
        self._refresh_text()

    def set_expanded(self, expanded: bool):
        if self._expanded == expanded:
            return
        self._expanded = expanded
        self._refresh_text()

    @property
    def label(self) -> str:
        return self._label

    @property
    def icon_text(self) -> str:
        return self._icon_text

    def _refresh_text(self):
        if self._expanded:
            self.setText(f"  {self._icon_text}   {self._label}")
        else:
            self.setText(f"  {self._icon_text}")
