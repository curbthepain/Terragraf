"""SharpenPanel — analyze/preview/apply via the sharpen_run skill."""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
)


def _run_sharpen(action: str) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from skills.runner import run_skill_capture
    rc, stdout, stderr = run_skill_capture("sharpen_run", [action])
    out = stdout
    if stderr:
        out += "\n" + stderr
    if rc != 0:
        out += f"\n[exit {rc}]"
    return out


class SharpenPanel(QDialog):
    """Sequential analyze -> preview -> apply workflow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sharpen")
        self.setMinimumSize(640, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Self-Sharpening")
        header.setObjectName("section_header")
        layout.addWidget(header)

        info = QLabel(
            "Workflow: analyze (collect feedback) → preview (proposed changes) "
            "→ apply (commit changes)."
        )
        info.setObjectName("dim")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Workflow buttons
        buttons = QHBoxLayout()
        self.analyze_btn = QPushButton("1. Analyze")
        self.analyze_btn.setObjectName("primary")
        self.analyze_btn.clicked.connect(lambda: self._run("analyze"))
        buttons.addWidget(self.analyze_btn)

        self.preview_btn = QPushButton("2. Preview")
        self.preview_btn.clicked.connect(lambda: self._run("preview"))
        buttons.addWidget(self.preview_btn)

        self.apply_btn = QPushButton("3. Apply")
        self.apply_btn.setObjectName("danger")
        self.apply_btn.clicked.connect(lambda: self._run("apply"))
        buttons.addWidget(self.apply_btn)

        buttons.addStretch(1)
        layout.addLayout(buttons)

        # Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def _run(self, action: str):
        self.output.setPlainText(f"Running sharpen {action}...")
        try:
            text = _run_sharpen(action)
        except Exception as e:
            text = f"Error: {e}"
        self.output.setPlainText(text or "(no output)")
