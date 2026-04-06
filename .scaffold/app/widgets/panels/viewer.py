"""ViewerPanel — `terra viewer` lifecycle (build/launch/bridge/status).

Wraps the `viewer` skill via runner.run_skill_capture in a worker thread.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
)


def _run_viewer_skill(args: list[str]) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from skills.runner import run_skill_capture
    rc, stdout, stderr = run_skill_capture("viewer", args)
    text = stdout or ""
    if stderr:
        text += ("\n" if text else "") + stderr
    if rc != 0:
        text += f"\n[exit {rc}]"
    return text or "(no output)"


class _ViewerWorker(QThread):
    finished_with_output = Signal(str)

    def __init__(self, args: list[str], parent=None):
        super().__init__(parent)
        self._args = args

    def run(self):
        try:
            self.finished_with_output.emit(_run_viewer_skill(self._args))
        except Exception as e:
            self.finished_with_output.emit(f"Error: {e}")


class ViewerPanel(QDialog):
    """ImGui viewer lifecycle panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Viewer")
        self.setMinimumSize(640, 480)

        self._worker: _ViewerWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("ImGui Viewer")
        header.setObjectName("section_header")
        layout.addWidget(header)

        info = QLabel("Build, launch, and inspect the ImGui viewer process. Bridge port 9876.")
        info.setObjectName("dim")
        layout.addWidget(info)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        # Buttons
        buttons = QHBoxLayout()
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setObjectName("primary")
        self.launch_btn.clicked.connect(lambda: self._run(["launch"]))
        buttons.addWidget(self.launch_btn)
        self.build_btn = QPushButton("Build")
        self.build_btn.clicked.connect(lambda: self._run(["build"]))
        buttons.addWidget(self.build_btn)
        self.bridge_btn = QPushButton("Bridge Only")
        self.bridge_btn.clicked.connect(lambda: self._run(["bridge"]))
        buttons.addWidget(self.bridge_btn)
        self.status_btn = QPushButton("Status")
        self.status_btn.clicked.connect(lambda: self._run(["status"]))
        buttons.addWidget(self.status_btn)
        buttons.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        # Initial status
        self._run(["status"])

    def _run(self, args: list[str]):
        if self._worker is not None and self._worker.isRunning():
            return
        self.output.setPlainText(f"$ viewer {' '.join(args)}\n")
        self._set_busy(True)
        self._worker = _ViewerWorker(args, parent=self)
        self._worker.finished_with_output.connect(self._on_done)
        self._worker.start()

    def _on_done(self, output: str):
        self.output.appendPlainText(output)
        self._set_busy(False)
        self._worker = None

    def _set_busy(self, busy: bool):
        for b in (self.launch_btn, self.build_btn, self.bridge_btn, self.status_btn):
            b.setEnabled(not busy)
