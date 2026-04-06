"""KnowledgeBrowser — list/search knowledge entries via knowledge_reader.py."""

import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
)

READER = Path(__file__).resolve().parents[4] / "projects" / "knowledge_reader.py"


class KnowledgeBrowser(QDialog):
    """Filterable knowledge entry browser. UI for `terra knowledge list/search/add`."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Knowledge")
        self.setMinimumSize(720, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Knowledge")
        header.setObjectName("section_header")
        layout.addWidget(header)

        # Search bar
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search query (leave empty for full list)")
        self.search_edit.returnPressed.connect(self._search)
        search_row.addWidget(self.search_edit, 1)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search)
        search_row.addWidget(search_btn)
        list_btn = QPushButton("List All")
        list_btn.clicked.connect(self._list_all)
        search_row.addWidget(list_btn)
        layout.addLayout(search_row)

        # Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        # Footer
        footer = QHBoxLayout()
        add_btn = QPushButton("Add Entry...")
        add_btn.clicked.connect(self._open_add)
        footer.addWidget(add_btn)
        footer.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._list_all()

    def _list_all(self):
        if not READER.exists():
            self.output.setPlainText(f"knowledge_reader.py not found at {READER}")
            return
        try:
            result = subprocess.run(
                [sys.executable, str(READER)],
                capture_output=True, text=True,
            )
            self.output.setPlainText(result.stdout + (result.stderr or ""))
        except OSError as e:
            self.output.setPlainText(f"Error: {e}")

    def _search(self):
        q = self.search_edit.text().strip()
        if not q:
            return self._list_all()
        if not READER.exists():
            self.output.setPlainText(f"knowledge_reader.py not found at {READER}")
            return
        try:
            result = subprocess.run(
                [sys.executable, str(READER), "--search", q],
                capture_output=True, text=True,
            )
            self.output.setPlainText(result.stdout + (result.stderr or ""))
        except OSError as e:
            self.output.setPlainText(f"Error: {e}")

    def _open_add(self):
        from ..dialogs.knowledge_add import KnowledgeAddDialog
        KnowledgeAddDialog(parent=self).exec()
        self._list_all()
