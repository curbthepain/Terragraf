"""MCPServerPanel — start/stop/status the MCP resource server."""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton,
    QPlainTextEdit,
)


def _import_server():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    try:
        from mcp.server import MCPServer
    except Exception:
        return None
    return MCPServer


class MCPServerPanel(QDialog):
    """Inline MCP server lifecycle panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MCP Server")
        self.setMinimumSize(540, 420)

        self._server = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("MCP Server")
        header.setObjectName("section_header")
        layout.addWidget(header)

        info = QLabel("JSON-RPC 2.0 over TCP. Default port 9878.")
        info.setObjectName("dim")
        layout.addWidget(info)

        # Port row
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(9878)
        port_row.addWidget(self.port_spin)
        port_row.addStretch(1)
        layout.addLayout(port_row)

        # Status indicator
        self.status_label = QLabel("● stopped")
        self.status_label.setObjectName("status_red")
        layout.addWidget(self.status_label)

        # Output / log
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        # Buttons
        buttons = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start)
        buttons.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        buttons.addWidget(self.stop_btn)
        status_btn = QPushButton("Status")
        status_btn.clicked.connect(self._status)
        buttons.addWidget(status_btn)
        buttons.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def _start(self):
        cls = _import_server()
        if cls is None:
            self.output.appendPlainText("MCP package not importable.")
            return
        try:
            self._server = cls(port=self.port_spin.value())
            if hasattr(self._server, "start"):
                self._server.start()
            self.status_label.setText(f"● running on {self.port_spin.value()}")
            self.status_label.setObjectName("status_green")
            self.status_label.setStyleSheet(f"")  # re-apply stylesheet
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.output.appendPlainText(
                f"Started MCP server on port {self.port_spin.value()}"
            )
        except Exception as e:
            self.output.appendPlainText(f"Start failed: {e}")

    def _stop(self):
        if self._server is None:
            return
        try:
            if hasattr(self._server, "stop"):
                self._server.stop()
            self.output.appendPlainText("Stopped MCP server")
        except Exception as e:
            self.output.appendPlainText(f"Stop failed: {e}")
        self._server = None
        self.status_label.setText("● stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _status(self):
        if self._server is None:
            self.output.appendPlainText("Status: stopped")
        else:
            self.output.appendPlainText(
                f"Status: running on port {self.port_spin.value()}"
            )
