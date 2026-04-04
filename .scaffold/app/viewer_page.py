"""Viewer page — launch and manage the ImGui process from Qt."""

import os
import subprocess
import signal
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QPlainTextEdit,
    QLineEdit,
    QGridLayout,
    QFrame,
)

from . import theme


class ViewerPage(QWidget):
    """Launch and monitor the ImGui viewer and bridge.py processes."""

    def __init__(self, bridge_client, parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._bridge_process: QProcess = None
        self._imgui_process: QProcess = None

        # Paths
        scaffold_dir = Path(__file__).parent.parent
        self._imgui_dir = scaffold_dir / "imgui"
        self._bridge_script = scaffold_dir / "imgui" / "bridge.py"
        _binary_name = "terragraf_imgui.exe" if sys.platform == "win32" else "terragraf_imgui"
        self._imgui_binary = scaffold_dir / "imgui" / "build" / _binary_name

        self._init_ui()

        # Refresh process status
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(1000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("ImGui Viewer")
        header.setObjectName("section_header")
        layout.addWidget(header)

        # ── Bridge server ──
        bridge_box = QGroupBox("Bridge Server (bridge.py)")
        bridge_layout = QVBoxLayout(bridge_box)

        info_row = QGridLayout()
        info_row.addWidget(QLabel("Script:"), 0, 0)
        self._bridge_path_label = QLabel(str(self._bridge_script))
        self._bridge_path_label.setObjectName("mono")
        info_row.addWidget(self._bridge_path_label, 0, 1)

        info_row.addWidget(QLabel("Status:"), 1, 0)
        self._bridge_status = QLabel("Stopped")
        self._bridge_status.setObjectName("status_red")
        info_row.addWidget(self._bridge_status, 1, 1)
        bridge_layout.addLayout(info_row)

        btn_row = QHBoxLayout()
        self._start_bridge_btn = QPushButton("Start Bridge")
        self._start_bridge_btn.setObjectName("primary")
        self._start_bridge_btn.clicked.connect(self._start_bridge)
        btn_row.addWidget(self._start_bridge_btn)

        self._stop_bridge_btn = QPushButton("Stop Bridge")
        self._stop_bridge_btn.setObjectName("danger")
        self._stop_bridge_btn.clicked.connect(self._stop_bridge)
        self._stop_bridge_btn.setEnabled(False)
        btn_row.addWidget(self._stop_bridge_btn)
        btn_row.addStretch()
        bridge_layout.addLayout(btn_row)

        self._bridge_log = QPlainTextEdit()
        self._bridge_log.setReadOnly(True)
        self._bridge_log.setMaximumHeight(120)
        self._bridge_log.setMaximumBlockCount(500)
        bridge_layout.addWidget(self._bridge_log)

        layout.addWidget(bridge_box)

        # ── ImGui viewer ──
        imgui_box = QGroupBox("ImGui Viewer (terragraf_imgui)")
        imgui_layout = QVBoxLayout(imgui_box)

        info_row2 = QGridLayout()
        info_row2.addWidget(QLabel("Binary:"), 0, 0)
        self._imgui_path_label = QLabel(str(self._imgui_binary))
        self._imgui_path_label.setObjectName("mono")
        info_row2.addWidget(self._imgui_path_label, 0, 1)

        info_row2.addWidget(QLabel("Status:"), 1, 0)
        self._imgui_status = QLabel("Stopped")
        self._imgui_status.setObjectName("status_red")
        info_row2.addWidget(self._imgui_status, 1, 1)

        self._imgui_exists = self._imgui_binary.exists()
        info_row2.addWidget(QLabel("Built:"), 2, 0)
        built_label = QLabel("Yes" if self._imgui_exists else "No — run cmake build first")
        built_label.setObjectName("status_green" if self._imgui_exists else "status_yellow")
        info_row2.addWidget(built_label, 2, 1)
        imgui_layout.addLayout(info_row2)

        btn_row2 = QHBoxLayout()
        self._start_imgui_btn = QPushButton("Launch Viewer")
        self._start_imgui_btn.setObjectName("primary")
        self._start_imgui_btn.clicked.connect(self._start_imgui)
        self._start_imgui_btn.setEnabled(self._imgui_exists)
        btn_row2.addWidget(self._start_imgui_btn)

        self._stop_imgui_btn = QPushButton("Stop Viewer")
        self._stop_imgui_btn.setObjectName("danger")
        self._stop_imgui_btn.clicked.connect(self._stop_imgui)
        self._stop_imgui_btn.setEnabled(False)
        btn_row2.addWidget(self._stop_imgui_btn)
        btn_row2.addStretch()
        imgui_layout.addLayout(btn_row2)

        self._imgui_log = QPlainTextEdit()
        self._imgui_log.setReadOnly(True)
        self._imgui_log.setMaximumHeight(120)
        self._imgui_log.setMaximumBlockCount(500)
        imgui_layout.addWidget(self._imgui_log)

        layout.addWidget(imgui_box)

        # ── Build instructions ──
        build_box = QGroupBox("Build Instructions")
        build_layout = QVBoxLayout(build_box)
        if sys.platform == "win32":
            build_cmds = (
                "To build the ImGui viewer:\n"
                "  cd .scaffold\\imgui\n"
                "  mkdir build && cd build\n"
                "  cmake .. && cmake --build . --parallel\n\n"
                "Requires: GLFW, OpenGL 4.5, C++17 compiler (VS2022)"
            )
        else:
            build_cmds = (
                "To build the ImGui viewer:\n"
                "  cd .scaffold/imgui\n"
                "  mkdir -p build && cd build\n"
                "  cmake .. && make -j$(nproc)\n\n"
                "Requires: GLFW, OpenGL 4.5, C++17 compiler"
            )
        instructions = QLabel(build_cmds)
        instructions.setObjectName("mono")
        instructions.setWordWrap(True)
        build_layout.addWidget(instructions)
        layout.addWidget(build_box)

        layout.addStretch()

    # ── Bridge process ──────────────────────────────────────────────

    def _start_bridge(self):
        if self._bridge_process and self._bridge_process.state() != QProcess.ProcessState.NotRunning:
            return
        self._bridge_process = QProcess(self)
        self._bridge_process.setWorkingDirectory(str(self._imgui_dir))
        self._bridge_process.readyReadStandardOutput.connect(
            lambda: self._bridge_log.appendPlainText(
                bytes(self._bridge_process.readAllStandardOutput()).decode(errors="replace")
            )
        )
        self._bridge_process.readyReadStandardError.connect(
            lambda: self._bridge_log.appendPlainText(
                bytes(self._bridge_process.readAllStandardError()).decode(errors="replace")
            )
        )
        self._bridge_process.finished.connect(self._on_bridge_finished)
        self._bridge_process.start(sys.executable, [str(self._bridge_script)])
        self._bridge_log.appendPlainText("[qt] starting bridge.py...")
        self._start_bridge_btn.setEnabled(False)
        self._stop_bridge_btn.setEnabled(True)

    def _stop_bridge(self):
        if self._bridge_process and self._bridge_process.state() != QProcess.ProcessState.NotRunning:
            self._bridge_process.terminate()
            self._bridge_process.waitForFinished(3000)
            if self._bridge_process.state() != QProcess.ProcessState.NotRunning:
                self._bridge_process.kill()
            self._bridge_log.appendPlainText("[qt] bridge stopped")

    def _on_bridge_finished(self, exit_code, exit_status):
        self._bridge_log.appendPlainText(f"[qt] bridge exited (code={exit_code})")
        self._start_bridge_btn.setEnabled(True)
        self._stop_bridge_btn.setEnabled(False)

    # ── ImGui process ───────────────────────────────────────────────

    def _start_imgui(self):
        if self._imgui_process and self._imgui_process.state() != QProcess.ProcessState.NotRunning:
            return
        if not self._imgui_binary.exists():
            self._imgui_log.appendPlainText("[qt] binary not found — build first")
            return
        self._imgui_process = QProcess(self)
        self._imgui_process.setWorkingDirectory(str(self._imgui_dir))
        self._imgui_process.readyReadStandardOutput.connect(
            lambda: self._imgui_log.appendPlainText(
                bytes(self._imgui_process.readAllStandardOutput()).decode(errors="replace")
            )
        )
        self._imgui_process.readyReadStandardError.connect(
            lambda: self._imgui_log.appendPlainText(
                bytes(self._imgui_process.readAllStandardError()).decode(errors="replace")
            )
        )
        self._imgui_process.finished.connect(self._on_imgui_finished)
        self._imgui_process.start(str(self._imgui_binary))
        self._imgui_log.appendPlainText("[qt] launching ImGui viewer...")
        self._start_imgui_btn.setEnabled(False)
        self._stop_imgui_btn.setEnabled(True)

    def _stop_imgui(self):
        if self._imgui_process and self._imgui_process.state() != QProcess.ProcessState.NotRunning:
            self._imgui_process.terminate()
            self._imgui_process.waitForFinished(3000)
            if self._imgui_process.state() != QProcess.ProcessState.NotRunning:
                self._imgui_process.kill()
            self._imgui_log.appendPlainText("[qt] viewer stopped")

    def _on_imgui_finished(self, exit_code, exit_status):
        self._imgui_log.appendPlainText(f"[qt] viewer exited (code={exit_code})")
        self._start_imgui_btn.setEnabled(self._imgui_binary.exists())
        self._stop_imgui_btn.setEnabled(False)

    # ── Status refresh ──────────────────────────────────────────────

    def _refresh_status(self):
        # Bridge
        if self._bridge_process and self._bridge_process.state() == QProcess.ProcessState.Running:
            self._bridge_status.setText("Running")
            self._bridge_status.setObjectName("status_green")
        else:
            self._bridge_status.setText("Stopped")
            self._bridge_status.setObjectName("status_red")
        self._bridge_status.style().unpolish(self._bridge_status)
        self._bridge_status.style().polish(self._bridge_status)

        # ImGui
        if self._imgui_process and self._imgui_process.state() == QProcess.ProcessState.Running:
            self._imgui_status.setText("Running")
            self._imgui_status.setObjectName("status_green")
        else:
            self._imgui_status.setText("Stopped")
            self._imgui_status.setObjectName("status_red")
        self._imgui_status.style().unpolish(self._imgui_status)
        self._imgui_status.style().polish(self._imgui_status)

    def cleanup(self):
        """Stop child processes on shutdown."""
        self._stop_bridge()
        self._stop_imgui()
