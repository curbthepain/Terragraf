"""HealthPanel — runs the health_check skill and displays the result."""

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QCheckBox,
)

from ..ansi import ansi_to_html


def _run_health_skill():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from skills.runner import run_skill_capture
    rc, stdout, stderr = run_skill_capture("health_check", [])
    text = stdout
    if stderr:
        text += "\n" + stderr
    if rc != 0:
        text += f"\n[exit {rc}]"
    return text


class HealthPanel(QDialog):
    """Health check display with re-run + auto-refresh."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Health")
        self.setMinimumSize(640, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("System Health")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        # Footer
        footer = QHBoxLayout()
        self.auto_refresh = QCheckBox("Auto-refresh (30s)")
        self.auto_refresh.toggled.connect(self._on_auto_toggled)
        footer.addWidget(self.auto_refresh)
        footer.addStretch(1)
        rerun = QPushButton("Re-run")
        rerun.setObjectName("primary")
        rerun.clicked.connect(self._run)
        footer.addWidget(rerun)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._timer = QTimer(self)
        self._timer.setInterval(30000)
        self._timer.timeout.connect(self._run)

        self._run()

    def _on_auto_toggled(self, on: bool):
        if on:
            self._timer.start()
        else:
            self._timer.stop()

    def _run(self):
        self.output.setPlainText("Running health check...")
        try:
            text = _run_health_skill()
        except Exception as e:
            text = f"Error: {e}"
        self.output.setHtml(ansi_to_html(text or "(no output)"))
