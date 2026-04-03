"""IDE host page — launches and embeds a discovered IDE inside Terra."""

import os
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

from PySide6.QtCore import Qt, QTimer, QProcess, QUrl, QProcessEnvironment
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QPlainTextEdit,
    QStackedWidget,
    QGridLayout,
)

from . import theme
from .app_host import IDEManifest, AppHostManager


class IDEHostPage(QWidget):
    """Generic page that can host any IDE defined by an app.toml manifest.

    For 'webview' IDEs: launches the server process, waits for it to be ready,
    then loads the IDE's HTTP interface in an embedded QWebEngineView.

    For 'process' IDEs: launches the IDE as a managed child process with
    log output displayed in the page.
    """

    def __init__(self, manifest: IDEManifest, host_manager: AppHostManager, parent=None):
        super().__init__(parent)
        self._manifest = manifest
        self._host = host_manager
        self._process: QProcess | None = None
        self._port: int | None = None
        self._webview = None  # lazy-loaded QWebEngineView
        self._health_timer: QTimer | None = None
        self._health_retries = 0

        # Resolve project root for workspace
        self._project_root = Path(__file__).parent.parent.parent

        self._init_ui()

    @property
    def manifest(self) -> IDEManifest:
        return self._manifest

    # ── UI ──────────────────────────────────────────────────────────

    def _init_ui(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        # Stack: 0 = control panel (shown when IDE is stopped),
        #        1 = embedded IDE (shown when IDE is running)
        self._view_stack = QStackedWidget()
        self._outer.addWidget(self._view_stack)

        # ── Page 0: Control panel ──
        control = QWidget()
        cl = QVBoxLayout(control)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(12)

        header = QLabel(self._manifest.label)
        header.setObjectName("section_header")
        cl.addWidget(header)

        # Info box
        info_box = QGroupBox("IDE Info")
        info_layout = QGridLayout(info_box)
        row = 0
        for label_text, value in [
            ("Name:", self._manifest.name),
            ("Version:", self._manifest.version),
            ("Description:", self._manifest.description),
            ("License:", self._manifest.license),
            ("Type:", self._manifest.launch_type),
            ("Directory:", str(self._manifest.app_dir)),
        ]:
            info_layout.addWidget(QLabel(label_text), row, 0)
            val = QLabel(value)
            val.setObjectName("mono")
            val.setWordWrap(True)
            info_layout.addWidget(val, row, 1)
            row += 1
        cl.addWidget(info_box)

        # Status
        status_box = QGroupBox("Status")
        sl = QVBoxLayout(status_box)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("State:"))
        self._status_label = QLabel("Stopped")
        self._status_label.setObjectName("status_red")
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        sl.addLayout(status_row)

        # Readiness indicator for webview IDEs
        if self._manifest.launch_type == "webview":
            ready_row = QHBoxLayout()
            ready_row.addWidget(QLabel("Server:"))
            self._ready_label = QLabel("Not started")
            self._ready_label.setObjectName("dim")
            ready_row.addWidget(self._ready_label)
            ready_row.addStretch()
            sl.addLayout(ready_row)

        # Buttons
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton(f"Launch {self._manifest.label}")
        self._start_btn.setObjectName("primary")
        self._start_btn.clicked.connect(self._start_ide)
        btn_row.addWidget(self._start_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("danger")
        self._stop_btn.clicked.connect(self._stop_ide)
        self._stop_btn.setEnabled(False)
        btn_row.addWidget(self._stop_btn)
        btn_row.addStretch()
        sl.addLayout(btn_row)

        # Command resolution check
        self._cmd_label = QLabel()
        self._cmd_label.setObjectName("mono")
        self._cmd_label.setWordWrap(True)
        self._update_command_status()
        sl.addWidget(self._cmd_label)

        cl.addWidget(status_box)

        # Log output
        log_box = QGroupBox("Output")
        ll = QVBoxLayout(log_box)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(160)
        self._log.setMaximumBlockCount(500)
        ll.addWidget(self._log)
        cl.addWidget(log_box)

        cl.addStretch()
        self._view_stack.addWidget(control)

        # ── Page 1: Webview placeholder (created on demand) ──
        self._webview_container = QWidget()
        wl = QVBoxLayout(self._webview_container)
        wl.setContentsMargins(0, 0, 0, 0)

        # Toolbar above the webview
        toolbar = QWidget()
        toolbar.setObjectName("sidebar")  # reuse sidebar styling for the bar
        toolbar.setFixedHeight(32)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 0, 8, 0)
        tl.setSpacing(8)

        ide_label = QLabel(f"{self._manifest.label}")
        ide_label.setObjectName("dim")
        tl.addWidget(ide_label)
        tl.addStretch()

        self._back_btn = QPushButton("Controls")
        self._back_btn.setFixedHeight(24)
        self._back_btn.clicked.connect(lambda: self._view_stack.setCurrentIndex(0))
        tl.addWidget(self._back_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.setObjectName("danger")
        stop_btn.setFixedHeight(24)
        stop_btn.clicked.connect(self._stop_ide)
        tl.addWidget(stop_btn)

        wl.addWidget(toolbar)
        self._webview_slot = wl  # we'll insert the QWebEngineView here
        self._view_stack.addWidget(self._webview_container)

    def _update_command_status(self):
        """Check if the IDE binary is available and update the label."""
        test_port = self._manifest.port_range[0]
        resolved = self._host.resolve_command(self._manifest, test_port)
        if resolved:
            prog, args = resolved
            self._cmd_label.setText(f"Command: {prog} {' '.join(args)}")
            self._cmd_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
            self._start_btn.setEnabled(True)
        else:
            self._cmd_label.setText(
                f"IDE not found. Install it to:\n"
                f"  {self._manifest.app_dir}/bin/\n"
                f"Or ensure it's available on your system PATH."
            )
            self._cmd_label.setStyleSheet(f"color: {theme.YELLOW};")
            self._start_btn.setEnabled(False)

    # ── Process management ──────────────────────────────────────────

    def _start_ide(self):
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            return

        # Find a free port for webview IDEs
        if self._manifest.launch_type == "webview":
            low, high = self._manifest.port_range
            self._port = self._host.find_free_port(low, high)
            if self._port is None:
                self._log.appendPlainText(
                    f"[terra] no free port in range {low}-{high}"
                )
                return
        else:
            self._port = self._manifest.port_range[0]

        resolved = self._host.resolve_command(self._manifest, self._port)
        if not resolved:
            self._log.appendPlainText("[terra] IDE binary not found")
            return

        program, args = resolved

        self._process = QProcess(self)
        self._process.setWorkingDirectory(
            str(self._resolve_workspace())
        )

        # Set environment
        env = QProcessEnvironment.systemEnvironment()
        for k, v in self._manifest.env.items():
            env.insert(k, v)
        self._process.setProcessEnvironment(env)

        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)

        self._process.start(program, args)
        self._log.appendPlainText(f"[terra] launching {self._manifest.name}...")
        self._log.appendPlainText(f"[terra] {program} {' '.join(args)}")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_label.setText("Starting")
        self._status_label.setObjectName("status_yellow")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        # For webview IDEs, start polling the health check
        if self._manifest.launch_type == "webview":
            self._ready_label.setText("Waiting for server...")
            self._ready_label.setStyleSheet(f"color: {theme.YELLOW};")
            self._health_retries = 0
            self._health_timer = QTimer(self)
            self._health_timer.timeout.connect(self._check_health)
            self._health_timer.start(1000)

    def _stop_ide(self):
        if self._health_timer:
            self._health_timer.stop()
            self._health_timer = None

        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.terminate()
            self._process.waitForFinished(3000)
            if self._process.state() != QProcess.ProcessState.NotRunning:
                self._process.kill()
            self._log.appendPlainText(f"[terra] {self._manifest.name} stopped")

        self._view_stack.setCurrentIndex(0)
        self._status_label.setText("Stopped")
        self._status_label.setObjectName("status_red")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        if self._manifest.launch_type == "webview":
            self._ready_label.setText("Not started")
            self._ready_label.setStyleSheet(f"color: {theme.TEXT_DIM};")

    def _on_stdout(self):
        data = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
        self._log.appendPlainText(data.rstrip())

    def _on_stderr(self):
        data = bytes(self._process.readAllStandardError()).decode(errors="replace")
        self._log.appendPlainText(data.rstrip())

    def _on_finished(self, exit_code, exit_status):
        self._log.appendPlainText(f"[terra] {self._manifest.name} exited (code={exit_code})")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_label.setText("Stopped")
        self._status_label.setObjectName("status_red")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        if self._manifest.launch_type == "webview":
            self._ready_label.setText("Not started")
            self._ready_label.setStyleSheet(f"color: {theme.TEXT_DIM};")

        self._view_stack.setCurrentIndex(0)
        self._update_command_status()

    # ── Health check & webview ──────────────────────────────────────

    def _check_health(self):
        """Poll the IDE's health check URL until it responds."""
        if not self._port or not self._manifest.health_check:
            return

        url = self._manifest.health_check.replace("{port}", str(self._port))
        try:
            resp = urlopen(url, timeout=1)
            resp.close()
            # Server is up
            if self._health_timer:
                self._health_timer.stop()
                self._health_timer = None
            self._on_server_ready()
        except (URLError, OSError):
            self._health_retries += 1
            max_retries = self._manifest.startup_delay + 30  # generous timeout
            if self._health_retries > max_retries:
                if self._health_timer:
                    self._health_timer.stop()
                    self._health_timer = None
                self._log.appendPlainText(
                    f"[terra] server did not respond after {max_retries}s"
                )
                self._ready_label.setText("Timeout — check logs")
                self._ready_label.setStyleSheet(f"color: {theme.RED};")

    def _on_server_ready(self):
        """Server responded — load the webview."""
        self._log.appendPlainText(f"[terra] server ready on port {self._port}")

        self._status_label.setText("Running")
        self._status_label.setObjectName("status_green")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        self._ready_label.setText(f"Listening on 127.0.0.1:{self._port}")
        self._ready_label.setStyleSheet(f"color: {theme.GREEN};")

        # Lazy-load QWebEngineView (avoids hard dep if QtWebEngine not installed)
        if self._webview is None:
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView
                self._webview = QWebEngineView()
                self._webview_slot.addWidget(self._webview, stretch=1)
            except ImportError:
                self._log.appendPlainText(
                    "[terra] QWebEngineView not available.\n"
                    "Install PySide6-WebEngine: pip install PySide6-WebEngine\n"
                    "Falling back to log-only mode."
                )
                return

        url = f"http://127.0.0.1:{self._port}/"
        self._webview.setUrl(QUrl(url))
        self._view_stack.setCurrentIndex(1)

    # ── Helpers ─────────────────────────────────────────────────────

    def _resolve_workspace(self) -> Path:
        """Resolve the workspace directory for the IDE."""
        if self._manifest.workspace:
            ws = self._project_root / self._manifest.workspace
            if ws.is_dir():
                return ws
        return self._project_root

    def on_page_shown(self):
        """Called when this page becomes visible — refresh command status."""
        self._update_command_status()

    def cleanup(self):
        """Stop the IDE process on shutdown."""
        self._stop_ide()
