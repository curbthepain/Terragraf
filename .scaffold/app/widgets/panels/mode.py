"""ModePanel — read-only display of `terra mode` (CI vs App)."""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
)


def _detect_mode():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from modes.detector import detect
    return detect()


def _format_mode(info) -> str:
    lines: list[str] = []
    lines.append(f"mode      {info.mode.value}")
    lines.append(f"source    {info.source}")
    lines.append("")
    if info.is_ci:
        lines.append("Running in CI mode (headless, restricted).")
    else:
        lines.append("Running in App mode (interactive, full access).")
    if info.blocked:
        lines.append("")
        lines.append("Blocked systems:")
        for b in sorted(info.blocked):
            lines.append(f"  - {b}")
    lines.append("")
    lines.append("Capabilities:")
    for c in sorted(info.capabilities):
        lines.append(f"  - {c}")
    return "\n".join(lines)


class ModePanel(QDialog):
    """Mode + capability display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mode")
        self.setMinimumSize(560, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Mode")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.setObjectName("primary")
        refresh.clicked.connect(self._refresh)
        footer.addWidget(refresh)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._refresh()

    def _refresh(self):
        try:
            info = _detect_mode()
            self.output.setPlainText(_format_mode(info))
        except Exception as e:
            self.output.setPlainText(f"Error detecting mode: {e}")
