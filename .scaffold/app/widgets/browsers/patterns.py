"""PatternBrowser — filterable table over .scaffold/tables/patterns.table.

UI for `terra pattern <name>`. Format: PATTERN | WHERE_USED | EXAMPLE_FILE | NOTES
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


_PATTERNS_TABLE = Path(__file__).resolve().parents[3] / "tables" / "patterns.table"


def _parse_patterns_table(path: Path = _PATTERNS_TABLE) -> list[tuple[str, str, str, str]]:
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


class PatternBrowser(QDialog):
    """UI for `terra pattern <name>`."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Design Patterns")
        self.setMinimumSize(780, 480)
        self._all_rows: list[tuple[str, str, str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Design Patterns")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by name, location, example, or notes...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Where", "Example", "Notes"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.count_label = QLabel("0 patterns")
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
        self._all_rows = _parse_patterns_table()
        self._apply_filter()

    def _apply_filter(self):
        needle = self.filter_edit.text().strip().lower()
        rows = [r for r in self._all_rows if not needle
                or any(needle in (s or "").lower() for s in r)]
        self.table.setRowCount(len(rows))
        for i, (name, where, example, notes) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(where))
            self.table.setItem(i, 2, QTableWidgetItem(example))
            self.table.setItem(i, 3, QTableWidgetItem(notes))
        self.count_label.setText(f"{len(rows)} patterns")

    def visible_row_count(self) -> int:
        return self.table.rowCount()

    def set_filter(self, text: str):
        self.filter_edit.setText(text or "")
        self._apply_filter()
