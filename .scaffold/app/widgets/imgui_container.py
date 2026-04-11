"""ImGui container — holds the reparented GLFW surface inside Qt."""

import sys

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout


class ImGuiContainer(QWidget):
    """Thin wrapper around a reparented GLFW window surface.

    Handles:
    - Resize forwarding to ImGui via bridge ``resize`` message
    - Click-to-focus: ensures the embedded GLFW window gets input focus
      when the user clicks inside the container area.  On Windows this
      requires explicit ``SetForegroundWindow`` because Qt eats the
      initial click that would normally focus the child HWND.
    """

    MIN_WIDTH = 400
    MIN_HEIGHT = 300

    def __init__(self, bridge_client, parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._foreign_window = None   # QWindow wrapping the GLFW HWND/XID
        self._container = None        # QWidget from createWindowContainer
        self._native_handle = 0       # Raw HWND / XID
        self._platform = ""           # "win32" | "x11" | "wayland"
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    # ── Embedding ───────────────────────────────────────────────────

    def embed(self, handle: int, platform: str):
        """Reparent a native window into this container.

        Args:
            handle: Native window handle (HWND on Win32, XID on X11).
            platform: ``"win32"`` or ``"x11"``.  ``"wayland"`` is not
                      supported for reparenting — caller should use
                      floating fallback instead.

        Returns:
            True if reparenting succeeded.
        """
        if platform == "wayland":
            return False

        self._native_handle = handle
        self._platform = platform

        self._foreign_window = QWindow.fromWinId(handle)
        if self._foreign_window is None:
            return False

        self._container = QWidget.createWindowContainer(
            self._foreign_window, self
        )
        self._container.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._layout.addWidget(self._container)

        # Send initial size so GLFW matches the container
        self._send_resize()
        return True

    def release(self):
        """Remove the embedded window (does not destroy the GLFW window)."""
        if self._container:
            self._layout.removeWidget(self._container)
            self._container.setParent(None)
            self._container.deleteLater()
            self._container = None
        self._foreign_window = None
        self._native_handle = 0
        self._platform = ""

    @property
    def is_embedded(self) -> bool:
        return self._container is not None

    # ── Events ──────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._send_resize()

    def mousePressEvent(self, event):
        """Click-to-focus: explicitly push focus to the GLFW child window.

        On Windows, Qt's ``createWindowContainer`` sometimes swallows the
        first click without forwarding WM_SETFOCUS to the child HWND.
        We call ``SetForegroundWindow`` directly to fix this.

        On X11, ``XSetInputFocus`` is used as a fallback if Qt's normal
        focus propagation doesn't reach the embedded window.
        """
        super().mousePressEvent(event)
        if not self._native_handle:
            return

        if self._platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(self._native_handle)
            except Exception:
                pass
        elif self._platform == "x11":
            # On X11, setting focus on the QWindow wrapper usually works.
            # If not, callers can override with Xlib calls.
            if self._foreign_window:
                self._foreign_window.requestActivate()

        # Also tell Qt to focus the container widget
        if self._container:
            self._container.setFocus(Qt.FocusReason.MouseFocusReason)

    # ── Internal ────────────────────────────────────────────────────

    def _send_resize(self):
        """Send current dimensions to ImGui via bridge."""
        if not self._bridge or not self._bridge.connected:
            return
        w = self.width()
        h = self.height()
        if w > 0 and h > 0:
            self._bridge.send("resize", {"width": w, "height": h})
