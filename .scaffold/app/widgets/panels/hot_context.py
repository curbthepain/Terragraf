"""HotContextEditor — read/edit/decompose .scaffold/HOT_CONTEXT.md."""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QMessageBox,
)


HOT_CONTEXT_FILE = Path(__file__).resolve().parents[3] / "HOT_CONTEXT.md"


def _run_decompose() -> str:
    sys.path.insert(0, str(HOT_CONTEXT_FILE.parents[1]))
    from skills.runner import run_skill_capture
    rc, stdout, stderr = run_skill_capture("hot_decompose", [])
    out = stdout
    if stderr:
        out += "\n" + stderr
    if rc != 0:
        out += f"\n[exit {rc}]"
    return out


class HotContextEditor(QDialog):
    """Plain text editor for HOT_CONTEXT.md with reload/save/decompose."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hot Context")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Hot Context")
        header.setObjectName("section_header")
        layout.addWidget(header)

        path_label = QLabel(str(HOT_CONTEXT_FILE))
        path_label.setObjectName("dim")
        layout.addWidget(path_label)

        self.editor = QPlainTextEdit()
        layout.addWidget(self.editor, 1)

        # Buttons
        buttons = QHBoxLayout()
        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(self._reload)
        buttons.addWidget(reload_btn)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        buttons.addWidget(save_btn)
        decompose_btn = QPushButton("Decompose")
        decompose_btn.clicked.connect(self._decompose)
        buttons.addWidget(decompose_btn)
        buttons.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self._reload()

    def _reload(self):
        try:
            text = HOT_CONTEXT_FILE.read_text(encoding="utf-8")
        except OSError as e:
            text = f"# Error reading file: {e}"
        self.editor.setPlainText(text)

    def _save(self):
        text = self.editor.toPlainText()
        try:
            HOT_CONTEXT_FILE.write_text(text, encoding="utf-8")
        except OSError as e:
            QMessageBox.warning(self, "Hot Context", f"Save failed: {e}")
            return
        QMessageBox.information(self, "Hot Context", "Saved.")

    def _decompose(self):
        confirm = QMessageBox.question(
            self, "Decompose",
            "Run hot_decompose to triage HOT_CONTEXT into scaffold files?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            out = _run_decompose()
        except Exception as e:
            out = f"Error: {e}"
        QMessageBox.information(self, "hot_decompose", out or "(no output)")
        self._reload()
