"""QueuePanel — list pending/completed tasks from instances/shared/queue.json."""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
)


SCAFFOLD = Path(__file__).resolve().parents[3]
QUEUE_FILE = SCAFFOLD / "instances" / "shared" / "queue.json"
RESULTS_FILE = SCAFFOLD / "instances" / "shared" / "results.json"


def _read_json(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict):
        return data.get("tasks") or data.get("items") or list(data.values())
    return data if isinstance(data, list) else []


class QueuePanel(QDialog):
    """Two-table view of pending and completed tasks."""

    def __init__(self, scaffold_state=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Task Queue")
        self.setMinimumSize(720, 520)
        self._state = scaffold_state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Task Queue")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.pending_table = self._make_table()
        self.completed_table = self._make_table()
        self.tabs.addTab(self.pending_table, "Pending")
        self.tabs.addTab(self.completed_table, "Completed")
        layout.addWidget(self.tabs, 1)

        # Footer
        footer = QHBoxLayout()
        add_btn = QPushButton("Add Task...")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_task)
        footer.addWidget(add_btn)
        clear_btn = QPushButton("Clear Completed")
        clear_btn.clicked.connect(self._clear_completed)
        footer.addWidget(clear_btn)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._reload)
        footer.addWidget(refresh)
        footer.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._reload()

    def _make_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(3)
        t.setHorizontalHeaderLabels(["ID", "Task", "Status"])
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    def _populate(self, table: QTableWidget, items: list):
        table.setRowCount(len(items))
        for i, item in enumerate(items):
            if isinstance(item, dict):
                tid = str(item.get("id", item.get("task_id", "")))
                task = str(item.get("task", item.get("description", "")))
                status = str(item.get("status", ""))
            else:
                tid, task, status = "", str(item), ""
            table.setItem(i, 0, QTableWidgetItem(tid))
            table.setItem(i, 1, QTableWidgetItem(task))
            table.setItem(i, 2, QTableWidgetItem(status))

    def _reload(self):
        self._populate(self.pending_table, _read_json(QUEUE_FILE))
        self._populate(self.completed_table, _read_json(RESULTS_FILE))

    def _add_task(self):
        from ..dialogs.dispatch import DispatchDialog
        DispatchDialog(parent=self).exec()
        self._reload()

    def _clear_completed(self):
        confirm = QMessageBox.question(
            self, "Clear Completed",
            "Erase all completed task records?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            RESULTS_FILE.write_text("[]", encoding="utf-8")
        except OSError as e:
            QMessageBox.warning(self, "Queue", f"Failed to clear: {e}")
        self._reload()
