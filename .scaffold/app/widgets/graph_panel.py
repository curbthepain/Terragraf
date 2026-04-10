"""
GraphPanel — embedded viewer for graphify knowledge-graph output.

Loads ``graphify-out/graph.html`` into a ``QWebEngineView``. Shows a
hint label when no graph exists yet.  Follows the lazy-load pattern
from ``ide_host_page.py`` so PySide6-WebEngine is not a hard dep.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

# Repo root — one level above .scaffold/
_TERRA_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_GRAPH_HTML = _TERRA_ROOT / "graphify-out" / "graph.html"


class GraphPanel(QWidget):
    """Knowledge-graph viewer panel, hosted inside a QDockWidget."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._webview = None  # lazy-loaded QWebEngineView

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Hint label — visible when no graph.html exists.
        self._hint = QLabel(
            "No knowledge graph yet.\n"
            "Run  terra graphify .  to build one."
        )
        self._hint.setProperty("class", "hint")
        self._hint.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint, 1)

        self.refresh()

    # ── Public API ──────────────────────────────────────────────────

    def refresh(self):
        """Reload graph.html if it exists, otherwise show the hint."""
        if _GRAPH_HTML.exists():
            self._ensure_webview()
            if self._webview is not None:
                self._webview.setUrl(QUrl.fromLocalFile(str(_GRAPH_HTML)))
                self._webview.setVisible(True)
                self._hint.setVisible(False)
                return
        # No graph or no WebEngine — show the hint.
        if self._webview is not None:
            self._webview.setVisible(False)
        self._hint.setVisible(True)

    # ── Internals ───────────────────────────────────────────────────

    def _ensure_webview(self):
        """Lazy-load QWebEngineView (avoids hard dep)."""
        if self._webview is not None:
            return
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self._webview = QWebEngineView()
            self.layout().addWidget(self._webview, 1)
        except ImportError:
            pass  # hint label stays visible
