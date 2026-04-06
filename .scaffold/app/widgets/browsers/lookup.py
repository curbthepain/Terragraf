"""LookupBrowser — filterable table over .scaffold/tables/errors.table.

UI for `terra lookup <error>`. Format: ERROR_PATTERN | CAUSE | FIX | FILE_HINT
"""

from pathlib import Path

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


_ERRORS_TABLE = Path(__file__).resolve().parents[3] / "tables" / "errors.table"


def _parse_errors_table(path: Path = _ERRORS_TABLE) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        while len(parts) < 4:
            parts.append("")
        rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


class LookupBrowser(QDialog):
    """UI for `terra lookup <error>`."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error Lookup")
        self.setMinimumSize(780, 480)
        self._all_rows: list[tuple[str, str, str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Error Lookup")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by error, cause, fix, or hint...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Error", "Cause", "Fix", "Where"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.count_label = QLabel("0 entries")
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
        self._all_rows = _parse_errors_table()
        self._apply_filter()

    def _apply_filter(self):
        needle = self.filter_edit.text().strip().lower()
        rows = [r for r in self._all_rows if not needle
                or any(needle in (s or "").lower() for s in r)]
        self.table.setRowCount(len(rows))
        for i, (err, cause, fix, where) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(err))
            self.table.setItem(i, 1, QTableWidgetItem(cause))
            self.table.setItem(i, 2, QTableWidgetItem(fix))
            self.table.setItem(i, 3, QTableWidgetItem(where))
        self.count_label.setText(f"{len(rows)} entries")

    def visible_row_count(self) -> int:
        return self.table.rowCount()

    def set_filter(self, text: str):
        self.filter_edit.setText(text or "")
        self._apply_filter()
