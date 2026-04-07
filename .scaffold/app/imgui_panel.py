"""ImGui panel — embeds the ImGui viewer as a dockable Qt panel.

Absorbs ViewerPage's process management.  After launching the ImGui
QProcess with ``--embedded``, retrieves the native window handle via
the bridge and reparents it into a Qt container widget.

Falls back to side-by-side floating on Wayland (no reparentable handle).
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
)

from . import theme
from .widgets.imgui_container import ImGuiContainer


class ImGuiPanel(QWidget):
    """Dockable panel that manages and embeds the ImGui viewer process."""

    # How long to wait for bridge readiness before launching ImGui
    BRIDGE_STARTUP_DELAY_MS = 1000
    # How long to wait after ImGui starts before requesting window handle
    HANDLE_REQUEST_DELAY_MS = 500

    def __init__(self, bridge_client, parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._bridge_process: QProcess | None = None
        self._imgui_process: QProcess | None = None
        self._docked = True  # True = reparented, False = floating

        # Paths
        scaffold_dir = Path(__file__).parent.parent
        self._imgui_dir = scaffold_dir / "imgui"
        self._bridge_script = scaffold_dir / "imgui" / "bridge.py"
        self._imgui_binary = self._find_imgui_binary(scaffold_dir)

        # Register bridge handler for window handle response
        self._bridge.on("window_handle_response", self._on_window_handle)

        self._build_ui()

    # ── Binary discovery (reused from ViewerPage) ───────────────────

    @staticmethod
    def _find_imgui_binary(scaffold_dir):
        """Search candidate paths for the built ImGui binary."""
        candidates = [
            scaffold_dir / "imgui" / "build" / "Release" / "terragraf_imgui.exe",
            scaffold_dir / "imgui" / "build" / "terragraf_imgui.exe",
            scaffold_dir / "imgui" / "build" / "Debug" / "terragraf_imgui.exe",
            scaffold_dir / "imgui" / "build" / "terragraf_imgui",
        ]
        for p in candidates:
            if p.exists():
                return p
        if sys.platform == "win32":
            return scaffold_dir / "imgui" / "build" / "Release" / "terragraf_imgui.exe"
        return scaffold_dir / "imgui" / "build" / "terragraf_imgui"

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 4, 4, 4)
        toolbar.setSpacing(6)

        self._status_label = QLabel("offline")
        self._status_label.setObjectName("dim")
        toolbar.addWidget(self._status_label)

        toolbar.addStretch()

        self._dock_btn = QPushButton("Undock")
        self._dock_btn.setToolTip("Toggle docked/floating mode")
        self._dock_btn.clicked.connect(self._toggle_dock)
        self._dock_btn.setEnabled(False)
        toolbar.addWidget(self._dock_btn)

        self._start_btn = QPushButton("Start")
        self._start_btn.setObjectName("primary")
        self._start_btn.clicked.connect(self.start)
        toolbar.addWidget(self._start_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("danger")
        self._stop_btn.clicked.connect(self.stop)
        self._stop_btn.setEnabled(False)
        toolbar.addWidget(self._stop_btn)

        self._restart_btn = QPushButton("Restart")
        self._restart_btn.clicked.connect(self.restart)
        self._restart_btn.setEnabled(False)
        toolbar.addWidget(self._restart_btn)

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        layout.addWidget(toolbar_widget)

        # Container for the embedded GLFW window
        self._container = ImGuiContainer(self._bridge)
        layout.addWidget(self._container, 1)

        # Log area (collapsed by default, shows stderr)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(80)
        self._log.setMaximumBlockCount(200)
        self._log.setVisible(False)
        layout.addWidget(self._log)

    # ── Process lifecycle ───────────────────────────────────────────

    def start(self):
        """Launch bridge.py (if needed) and ImGui with --embedded."""
        if self._imgui_running():
            return

        if not self._imgui_binary.exists():
            self._set_status("binary not found")
            return

        # Auto-start bridge if needed
        if not self._bridge_running():
            self._start_bridge()
            QTimer.singleShot(
                self.BRIDGE_STARTUP_DELAY_MS, self._launch_imgui
            )
        else:
            self._launch_imgui()

    def stop(self):
        """Kill ImGui process and release embedded window."""
        self._container.release()
        self._stop_imgui()
        self._stop_bridge()
        self._set_status("offline")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._restart_btn.setEnabled(False)
        self._dock_btn.setEnabled(False)

    def restart(self):
        """Stop and re-launch."""
        self.stop()
        QTimer.singleShot(300, self.start)

    @property
    def container(self) -> ImGuiContainer:
        return self._container

    # ── Bridge process ──────────────────────────────────────────────

    def _start_bridge(self):
        if self._bridge_running():
            return
        self._bridge_process = QProcess(self)
        self._bridge_process.setWorkingDirectory(str(self._imgui_dir))
        self._bridge_process.readyReadStandardError.connect(
            lambda: self._append_log(
                bytes(self._bridge_process.readAllStandardError()).decode(
                    errors="replace"
                )
            )
        )
        self._bridge_process.start(sys.executable, [str(self._bridge_script)])
        self._set_status("bridge starting...")

    def _stop_bridge(self):
        if not self._bridge_running():
            return
        self._bridge_process.terminate()
        self._bridge_process.waitForFinished(3000)
        if self._bridge_process.state() != QProcess.ProcessState.NotRunning:
            self._bridge_process.kill()
        self._bridge_process = None

    def _bridge_running(self) -> bool:
        return (
            self._bridge_process is not None
            and self._bridge_process.state() == QProcess.ProcessState.Running
        )

    # ── ImGui process ───────────────────────────────────────────────

    def _launch_imgui(self):
        if self._imgui_running():
            return
        self._imgui_process = QProcess(self)
        self._imgui_process.setWorkingDirectory(str(self._imgui_dir))
        self._imgui_process.readyReadStandardOutput.connect(
            lambda: self._append_log(
                bytes(self._imgui_process.readAllStandardOutput()).decode(
                    errors="replace"
                )
            )
        )
        self._imgui_process.readyReadStandardError.connect(
            lambda: self._append_log(
                bytes(self._imgui_process.readAllStandardError()).decode(
                    errors="replace"
                )
            )
        )
        self._imgui_process.finished.connect(self._on_imgui_finished)
        self._imgui_process.start(
            str(self._imgui_binary), ["--embedded"]
        )
        self._set_status("launching...")
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._restart_btn.setEnabled(True)

        # After a short delay, request the window handle for reparenting
        QTimer.singleShot(
            self.HANDLE_REQUEST_DELAY_MS, self._request_window_handle
        )

    def _stop_imgui(self):
        if not self._imgui_running():
            return
        self._imgui_process.terminate()
        self._imgui_process.waitForFinished(3000)
        if self._imgui_process.state() != QProcess.ProcessState.NotRunning:
            self._imgui_process.kill()
        self._imgui_process = None

    def _imgui_running(self) -> bool:
        return (
            self._imgui_process is not None
            and self._imgui_process.state() == QProcess.ProcessState.Running
        )

    def _on_imgui_finished(self, exit_code, exit_status):
        self._container.release()
        self._set_status(f"exited ({exit_code})")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._restart_btn.setEnabled(False)
        self._dock_btn.setEnabled(False)

    # ── Window reparenting ──────────────────────────────────────────

    def _request_window_handle(self):
        """Ask ImGui for its native window handle via bridge."""
        if not self._bridge.connected:
            # Bridge not ready yet — retry
            if self._imgui_running():
                QTimer.singleShot(500, self._request_window_handle)
            return
        self._bridge.send("get_window_handle")

    def _on_window_handle(self, msg: dict):
        """Handle window_handle_response from ImGui."""
        data = msg.get("data", {})
        handle = data.get("handle", 0)
        platform = data.get("platform", "")

        if platform == "wayland" or not handle:
            self._set_status("floating (no reparenting)")
            self._docked = False
            self._dock_btn.setText("Dock")
            self._dock_btn.setEnabled(False)
            return

        success = self._container.embed(int(handle), platform)
        if success:
            self._set_status("embedded")
            self._docked = True
            self._dock_btn.setText("Undock")
            self._dock_btn.setEnabled(True)
        else:
            self._set_status("embed failed — floating")
            self._docked = False
            self._dock_btn.setEnabled(False)

    def _toggle_dock(self):
        """Toggle between embedded (reparented) and floating mode."""
        if self._docked:
            # Undock: release from container
            self._container.release()
            self._docked = False
            self._dock_btn.setText("Dock")
            self._set_status("floating")
        else:
            # Re-dock: request handle again
            self._request_window_handle()

    # ── Helpers ─────────────────────────────────────────────────────

    def _set_status(self, text: str):
        self._status_label.setText(text)

    def _append_log(self, text: str):
        if text.strip():
            self._log.setVisible(True)
            self._log.appendPlainText(text.rstrip())

    def cleanup(self):
        """Stop child processes on shutdown."""
        self._container.release()
        self._stop_imgui()
        self._stop_bridge()
