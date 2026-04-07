"""SkillPicker — modal listing real skills from runner.list_skills()."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
)


def _list_skills():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from skills.runner import list_skills
    return list_skills()


def _run_skill_capture(name, args=None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from skills.runner import run_skill_capture
    return run_skill_capture(name, args or [])


class SkillPicker(QDialog):
    """Pick and run a registered skill."""

    skill_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Skill")
        self.setMinimumSize(640, 540)

        self._skills = _list_skills()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Available Skills")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter skills...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget, 1)

        # Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFixedHeight(140)
        self.output.setPlaceholderText("Skill output will appear here.")
        layout.addWidget(self.output)

        # Footer
        footer = QHBoxLayout()
        run_btn = QPushButton("Run Selected")
        run_btn.setObjectName("primary")
        run_btn.clicked.connect(self._run_selected)
        footer.addWidget(run_btn)
        footer.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._apply_filter()

    def _apply_filter(self):
        needle = self.filter_edit.text().strip().lower()
        self.list_widget.clear()
        for name, manifest in self._skills:
            info = manifest.get("skill", {})
            desc = info.get("description", "")
            text = f"{name}  —  {desc}"
            if needle and needle not in text.lower():
                continue
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)

    def _on_double_click(self, item):
        self._run_item(item)

    def _run_selected(self):
        item = self.list_widget.currentItem()
        if item:
            self._run_item(item)

    def _run_item(self, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        if not name:
            return
        self.skill_selected.emit(name)
        self.output.setPlainText(f"Running skill: {name}...")
        rc, stdout, stderr = _run_skill_capture(name)
        text = stdout + ("\n" + stderr if stderr else "")
        if rc != 0:
            text += f"\n[exit {rc}]"
        self.output.setPlainText(text or "(no output)")

    def visible_count(self) -> int:
        return self.list_widget.count()
