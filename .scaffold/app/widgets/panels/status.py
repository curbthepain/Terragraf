"""StatusPanel — `terra status` equivalent without importing terra.

Importing terra.py would prepend src/python to sys.path, conflicting with
the system torchvision install (same trap as DepsPanel). We replicate the
cheap inspection helpers inline.
"""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QCheckBox,
)


_TERRA_ROOT = Path(__file__).resolve().parents[4]
_SCAFFOLD = _TERRA_ROOT / ".scaffold"


def _has_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def _cmd_version(name: str, args: list[str]) -> str | None:
    if not _has_cmd(name):
        return None
    try:
        result = subprocess.run(
            [name] + args, capture_output=True, text=True, timeout=3
        )
        return (result.stdout or result.stderr or "").strip().split("\n", 1)[0]
    except Exception:
        return None


def _count_files(directory: Path, glob: str = "*") -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.glob(glob) if _.is_file())


def _read_json_safe(path: Path) -> object:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _format_status() -> str:
    lines: list[str] = []
    lines.append("Terragraf")
    lines.append("")

    # Platform / runtimes
    lines.append(f"  platform   {platform.system()} {platform.release()}")
    lines.append(f"  python     {sys.version.split()[0]}")
    lines.append(f"  bash       {'yes' if _has_cmd('bash') else 'not found'}")
    node_v = _cmd_version("node", ["--version"])
    lines.append(f"  node       {node_v or 'not found'}")
    lines.append(f"  git        {'yes' if _has_cmd('git') else 'no'}")
    lines.append("")

    # Structure counts
    lines.append("Structure")
    lines.append(f"  headers    {_count_files(_SCAFFOLD / 'headers', '*.h')}")
    lines.append(f"  routes     {_count_files(_SCAFFOLD / 'routes', '*.route')}")
    lines.append(f"  tables     {_count_files(_SCAFFOLD / 'tables', '*.table')}")
    lines.append("")

    # Queue
    queue_path = _SCAFFOLD / "instances" / "shared" / "queue.json"
    results_path = _SCAFFOLD / "instances" / "shared" / "results.json"
    queue = _read_json_safe(queue_path)
    results = _read_json_safe(results_path)
    pending = len(queue) if isinstance(queue, list) else (
        len(queue.get("tasks", [])) if isinstance(queue, dict) else 0
    )
    completed = len(results) if isinstance(results, list) else (
        len(results.get("results", [])) if isinstance(results, dict) else 0
    )
    lines.append(f"  queue      {pending} pending")
    lines.append(f"  results    {completed} completed")

    return "\n".join(lines)


class StatusPanel(QDialog):
    """`terra status` panel — does NOT import terra."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Status")
        self.setMinimumSize(560, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("System Status")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        font = self.output.font()
        font.setFamily("Consolas")
        self.output.setFont(font)
        layout.addWidget(self.output, 1)

        footer = QHBoxLayout()
        self.auto_refresh = QCheckBox("Auto-refresh (10s)")
        self.auto_refresh.toggled.connect(self._on_auto_toggled)
        footer.addWidget(self.auto_refresh)
        footer.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.setObjectName("primary")
        refresh.clicked.connect(self._refresh)
        footer.addWidget(refresh)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._timer = QTimer(self)
        self._timer.setInterval(10_000)
        self._timer.timeout.connect(self._refresh)

        self._refresh()

    def _on_auto_toggled(self, on: bool):
        if on:
            self._timer.start()
        else:
            self._timer.stop()

    def _refresh(self):
        try:
            self.output.setPlainText(_format_status())
        except Exception as e:
            self.output.setPlainText(f"Error: {e}")
