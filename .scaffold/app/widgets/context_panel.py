"""
Context panel — shows live session state (headers read, routes consulted, files modified).

Reusable sidebar widget for both native and external tabs. All visual styling
lives in app.theme via object names.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ContextPanel(QWidget):
    """
    Collapsible sidebar showing Session.context state.

    Call `refresh(session)` after each query to update the display.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contextPanel")
        self.setFixedWidth(220)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(4)

        title = QLabel("Session Context")
        title.setObjectName("contextTitle")
        outer.addWidget(title)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(2)
        self._content_layout.addStretch()

        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)

        self._headers_label = QLabel("Headers: 0")
        self._routes_label = QLabel("Routes: 0")
        self._files_label = QLabel("Files: 0")
        self._queries_label = QLabel("Queries: 0")

        for lbl in (self._headers_label, self._routes_label,
                     self._files_label, self._queries_label):
            lbl.setObjectName("contextStat")

        # Insert before the stretch
        for i, lbl in enumerate((self._headers_label, self._routes_label,
                                  self._files_label, self._queries_label)):
            self._content_layout.insertWidget(i, lbl)

        # Detail lists
        self._detail_labels: list[QLabel] = []

    def refresh(self, session):
        """Update display from session context."""
        ctx = session.context
        history_len = len(session.query_history) if hasattr(session, "query_history") else 0

        self._headers_label.setText(f"Headers: {len(ctx.headers_read)}")
        self._routes_label.setText(f"Routes: {len(ctx.routes_consulted)}")
        self._files_label.setText(f"Files: {len(ctx.files_modified)}")
        self._queries_label.setText(f"Queries: {history_len}")

        # Clear old detail labels
        for lbl in self._detail_labels:
            self._content_layout.removeWidget(lbl)
            lbl.deleteLater()
        self._detail_labels.clear()

        # Add detail items
        insert_pos = 4  # After the 4 summary labels
        items = []
        for h in ctx.headers_read[-10:]:
            items.append(("H", h, "detail_yellow"))
        for r in ctx.routes_consulted[-10:]:
            items.append(("R", r, "detail_cyan"))
        for f in ctx.files_modified[-10:]:
            items.append(("F", f, "detail_green"))

        for prefix, text, obj_name in items:
            lbl = QLabel(f"  [{prefix}] {text}")
            lbl.setObjectName(obj_name)
            lbl.setWordWrap(True)
            self._content_layout.insertWidget(insert_pos, lbl)
            self._detail_labels.append(lbl)
            insert_pos += 1
