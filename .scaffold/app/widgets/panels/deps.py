"""DepsPanel — Python + C++ deps status with sync/clean controls."""

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
)

TERRA_ROOT = Path(__file__).resolve().parents[4]
TERRA_CLI = TERRA_ROOT / "terra.py"


def _detect_deps() -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    """Scan src/python and src/cpp directly.

    Importing terra.py puts src/python on sys.path, which conflicts with the
    system torchvision install. So we walk the directories instead — we don't
    need the full registry, just whether things exist.
    """
    src = TERRA_ROOT / "src"
    py_dir = src / "python"
    cpp_dir = src / "cpp"

    py_results: list[tuple[str, bool]] = []
    cpp_results: list[tuple[str, bool]] = []

    if py_dir.is_dir():
        for child in sorted(py_dir.iterdir()):
            if child.name.startswith((".", "__")):
                continue
            # Each direct child is a top-level package or .py module
            py_results.append((child.name, True))
    else:
        py_results.append(("(src/python missing — run 'terra deps sync')", False))

    if cpp_dir.is_dir():
        for child in sorted(cpp_dir.iterdir()):
            if child.name.startswith((".", "__")):
                continue
            cpp_results.append((child.name, child.is_dir()))
    else:
        cpp_results.append(("(src/cpp missing — run 'terra deps sync')", False))

    return (py_results, cpp_results)


class _DepsWorker(QThread):
    finished_with_output = Signal(str, bool)

    def __init__(self, args, parent=None):
        super().__init__(parent)
        self._args = args

    def run(self):
        try:
            cmd = [sys.executable, str(TERRA_CLI)] + self._args
            result = subprocess.run(cmd, cwd=str(TERRA_ROOT),
                                    capture_output=True, text=True)
            out = result.stdout + (result.stderr or "")
            if result.returncode != 0:
                out += f"\n[exit {result.returncode}]"
            self.finished_with_output.emit(out, False)
        except Exception as e:
            self.finished_with_output.emit(str(e), True)


class DepsPanel(QDialog):
    """Local dependency status with sync/clean buttons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Local Dependencies")
        self.setMinimumSize(720, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Local Dependencies")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.python_table = self._make_table()
        self.cpp_table = self._make_table()
        self.tabs.addTab(self.python_table, "Python")
        self.tabs.addTab(self.cpp_table, "C++")
        layout.addWidget(self.tabs, 1)

        # Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFixedHeight(120)
        layout.addWidget(self.output)

        # Buttons
        buttons = QHBoxLayout()
        sync_all = QPushButton("Sync All")
        sync_all.setObjectName("primary")
        sync_all.clicked.connect(lambda: self._run(["deps", "sync"]))
        buttons.addWidget(sync_all)
        sync_py = QPushButton("Sync Python")
        sync_py.clicked.connect(lambda: self._run(["deps", "sync", "python"]))
        buttons.addWidget(sync_py)
        sync_cpp = QPushButton("Sync C++")
        sync_cpp.clicked.connect(lambda: self._run(["deps", "sync", "cpp"]))
        buttons.addWidget(sync_cpp)
        clean_btn = QPushButton("Clean")
        clean_btn.setObjectName("danger")
        clean_btn.clicked.connect(self._clean)
        buttons.addWidget(clean_btn)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._reload)
        buttons.addWidget(refresh)
        buttons.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self._worker: _DepsWorker | None = None
        self._reload()

    def _make_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(2)
        t.setHorizontalHeaderLabels(["Name", "Status"])
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    def _populate(self, table: QTableWidget, items: list[tuple[str, bool]]):
        table.setRowCount(len(items))
        for i, (name, ok) in enumerate(items):
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem("✓ present" if ok else "✗ missing"))

    def _reload(self):
        py, cpp = _detect_deps()
        self._populate(self.python_table, py)
        self._populate(self.cpp_table, cpp)
        self.tabs.setTabText(0, f"Python ({sum(1 for _, ok in py if ok)}/{len(py)})")
        self.tabs.setTabText(1, f"C++ ({sum(1 for _, ok in cpp if ok)}/{len(cpp)})")

    def _run(self, args):
        if self._worker is not None and self._worker.isRunning():
            return
        self.output.setPlainText(f"Running: terra {' '.join(args)}...")
        self._worker = _DepsWorker(args, parent=self)
        self._worker.finished_with_output.connect(self._on_done)
        self._worker.start()

    def _on_done(self, output: str, was_error: bool):
        self.output.setPlainText(output or "(no output)")
        self._worker = None
        self._reload()

    def _clean(self):
        confirm = QMessageBox.question(
            self, "Clean", "Remove all locally-sourced dependencies?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._run(["deps", "clean"])
