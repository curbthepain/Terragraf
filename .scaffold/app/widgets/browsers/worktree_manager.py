"""WorktreeManagerDialog — list/create/remove/gc git worktrees."""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
)


def _manager():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from worktree.manager import WorktreeManager
    return WorktreeManager()


class WorktreeManagerDialog(QDialog):
    """Manage git worktrees from the UI — no CLI shell-out."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Worktree Manager")
        self.setMinimumSize(720, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Worktrees")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Branch", "Path", "Status", "Task"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        # Buttons
        buttons = QHBoxLayout()

        create_btn = QPushButton("Create...")
        create_btn.setObjectName("primary")
        create_btn.clicked.connect(self._create)
        buttons.addWidget(create_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove)
        buttons.addWidget(remove_btn)

        gc_btn = QPushButton("GC Stale")
        gc_btn.clicked.connect(self._gc)
        buttons.addWidget(gc_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        buttons.addWidget(refresh_btn)

        buttons.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)

        layout.addLayout(buttons)

        self._refresh()

    def _refresh(self):
        try:
            mgr = _manager()
            entries = mgr.list()
        except Exception as e:
            self.table.setRowCount(0)
            QMessageBox.warning(self, "Worktrees", f"Could not list worktrees:\n{e}")
            return

        self.table.setRowCount(len(entries))
        for i, info in enumerate(entries):
            self.table.setItem(i, 0, QTableWidgetItem(getattr(info, "worktree_id", "")))
            self.table.setItem(i, 1, QTableWidgetItem(getattr(info, "branch", "")))
            self.table.setItem(i, 2, QTableWidgetItem(str(getattr(info, "path", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(getattr(info, "status", "")))
            self.table.setItem(i, 4, QTableWidgetItem(getattr(info, "task_id", "")))

    def _create(self):
        from ..dialogs.worktree_create import WorktreeCreateDialog
        dlg = WorktreeCreateDialog(parent=self)
        dlg.exec()
        self._refresh()

    def _remove(self):
        row = self.table.currentRow()
        if row < 0:
            return
        wt_id = self.table.item(row, 0).text()
        if not wt_id:
            return
        confirm = QMessageBox.question(
            self, "Remove worktree",
            f"Remove worktree {wt_id}? This deletes the worktree directory and branch.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            _manager().remove(wt_id, force=True)
        except Exception as e:
            QMessageBox.warning(self, "Worktrees", f"Remove failed:\n{e}")
        self._refresh()

    def _gc(self):
        try:
            removed = _manager().gc(max_age_hours=24)
        except Exception as e:
            QMessageBox.warning(self, "Worktrees", f"GC failed:\n{e}")
            return
        QMessageBox.information(self, "Worktrees", f"GC removed {removed} stale worktrees.")
        self._refresh()
