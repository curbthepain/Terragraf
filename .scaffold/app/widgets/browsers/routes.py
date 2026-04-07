"""RoutesBrowser — filterable table of scaffold routes."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
)


class RoutesBrowser(QDialog):
    """Live filter over `scaffold_state.routes` (RouteEntry list).

    Doubles as the UI for `terra route <intent>`.
    """

    def __init__(self, scaffold_state, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Routes")
        self.setMinimumSize(720, 480)
        self._state = scaffold_state
        self._all_rows: list[tuple[str, str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Routes")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by concept, path, or description...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Concept", "Path", "Description"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        # Footer
        footer = QHBoxLayout()
        self.count_label = QLabel("0 routes")
        self.count_label.setObjectName("dim")
        footer.addWidget(self.count_label)
        footer.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._reload)
        footer.addWidget(refresh)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._reload()

    def _reload(self):
        self._all_rows = []
        for filename, entries in self._state.routes.items():
            for entry in entries:
                self._all_rows.append(
                    (entry.concept, entry.path, entry.description)
                )
        self._apply_filter()

    def _apply_filter(self):
        needle = self.filter_edit.text().strip().lower()
        rows = [r for r in self._all_rows if not needle
                or any(needle in (s or "").lower() for s in r)]
        self.table.setRowCount(len(rows))
        for i, (concept, path, desc) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(concept))
            self.table.setItem(i, 1, QTableWidgetItem(path))
            self.table.setItem(i, 2, QTableWidgetItem(desc))
        self.count_label.setText(f"{len(rows)} routes")

    def visible_row_count(self) -> int:
        return self.table.rowCount()

    def set_filter(self, text: str):
        """Pre-fill the filter (used by the route_jump sidebar action)."""
        self.filter_edit.setText(text or "")
        self._apply_filter()
