"""Debug page — bridge monitor, message log, connection diagnostics."""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QPlainTextEdit,
    QLineEdit,
    QCheckBox,
    QFrame,
    QGridLayout,
    QSplitter,
)

from . import theme


class DebugPage(QWidget):
    """Bridge debug monitor with live message log and stats."""

    def __init__(self, bridge_client, parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._auto_scroll = True
        self._filter_text = ""
        self._init_ui()

        # Refresh at 4 Hz
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(250)

        # Wire bridge signals
        self._bridge.message_received.connect(self._on_message)
        self._bridge.connection_changed.connect(self._on_connection_changed)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Header ──
        header = QLabel("Debug — End to End")
        header.setObjectName("section_header")
        layout.addWidget(header)

        # ── Connection status ──
        conn_box = QGroupBox("Connection")
        conn_layout = QGridLayout(conn_box)

        self._status_label = QLabel("DISCONNECTED")
        self._status_label.setObjectName("status_red")
        conn_layout.addWidget(QLabel("Status:"), 0, 0)
        conn_layout.addWidget(self._status_label, 0, 1)

        self._host_label = QLabel(f"{self._bridge.host}:{self._bridge.port}")
        self._host_label.setObjectName("mono")
        conn_layout.addWidget(QLabel("Endpoint:"), 1, 0)
        conn_layout.addWidget(self._host_label, 1, 1)

        btn_row = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setObjectName("primary")
        self._connect_btn.clicked.connect(self._do_connect)
        btn_row.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setObjectName("danger")
        self._disconnect_btn.clicked.connect(self._do_disconnect)
        self._disconnect_btn.setEnabled(False)
        btn_row.addWidget(self._disconnect_btn)

        self._ping_btn = QPushButton("Ping")
        self._ping_btn.clicked.connect(self._do_ping)
        self._ping_btn.setEnabled(False)
        btn_row.addWidget(self._ping_btn)

        btn_row.addStretch()
        conn_layout.addLayout(btn_row, 2, 0, 1, 2)
        layout.addWidget(conn_box)

        # ── Stats ──
        stats_box = QGroupBox("Stats")
        stats_layout = QGridLayout(stats_box)

        self._sent_msgs = QLabel("0")
        self._recv_msgs = QLabel("0")
        self._sent_bytes = QLabel("0 B")
        self._recv_bytes = QLabel("0 B")

        stats_layout.addWidget(QLabel("Sent:"), 0, 0)
        self._sent_msgs.setObjectName("mono")
        stats_layout.addWidget(self._sent_msgs, 0, 1)
        stats_layout.addWidget(self._sent_bytes, 0, 2)

        stats_layout.addWidget(QLabel("Recv:"), 1, 0)
        self._recv_msgs.setObjectName("mono")
        stats_layout.addWidget(self._recv_msgs, 1, 1)
        stats_layout.addWidget(self._recv_bytes, 1, 2)

        layout.addWidget(stats_box)

        # ── Test message ──
        test_box = QGroupBox("Send Test Message")
        test_layout = QHBoxLayout(test_box)

        self._test_type = QLineEdit("ping")
        self._test_type.setPlaceholderText("msg type")
        self._test_type.setFixedWidth(140)
        test_layout.addWidget(self._test_type)

        self._test_data = QLineEdit("{}")
        self._test_data.setPlaceholderText("JSON data")
        test_layout.addWidget(self._test_data)

        send_btn = QPushButton("Send")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(self._do_send_test)
        test_layout.addWidget(send_btn)
        layout.addWidget(test_box)

        # ── Message log ──
        log_box = QGroupBox("Message Log")
        log_layout = QVBoxLayout(log_box)

        toolbar = QHBoxLayout()
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("filter by type...")
        self._filter_input.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._filter_input)

        self._auto_scroll_cb = QCheckBox("Auto-scroll")
        self._auto_scroll_cb.setChecked(True)
        self._auto_scroll_cb.toggled.connect(lambda v: setattr(self, '_auto_scroll', v))
        toolbar.addWidget(self._auto_scroll_cb)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._do_clear_log)
        toolbar.addWidget(clear_btn)
        log_layout.addLayout(toolbar)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(1000)
        log_layout.addWidget(self._log_view)

        layout.addWidget(log_box, stretch=1)

    # ── Actions ─────────────────────────────────────────────────────

    def _do_connect(self):
        ok = self._bridge.connect_to_bridge()
        if not ok:
            self._log_view.appendPlainText("[debug] connection failed")

    def _do_disconnect(self):
        self._bridge.disconnect_from_bridge()

    def _do_ping(self):
        self._bridge.send("ping")
        self._ping_time = time.time()

    def _do_send_test(self):
        import json
        msg_type = self._test_type.text().strip()
        if not msg_type:
            return
        try:
            data = json.loads(self._test_data.text())
        except json.JSONDecodeError:
            data = self._test_data.text()
        self._bridge.send(msg_type, data)

    def _do_clear_log(self):
        self._log_view.clear()
        self._bridge.clear_log()

    # ── Signals / refresh ───────────────────────────────────────────

    def _on_message(self, msg_type: str, msg: dict):
        # Check for pong RTT
        if msg_type == "pong" and hasattr(self, '_ping_time'):
            rtt = (time.time() - self._ping_time) * 1000
            self._log_view.appendPlainText(f"[pong] RTT: {rtt:.1f} ms")

    def _on_connection_changed(self, connected: bool):
        if connected:
            self._status_label.setText("CONNECTED")
            self._status_label.setObjectName("status_green")
            self._connect_btn.setEnabled(False)
            self._disconnect_btn.setEnabled(True)
            self._ping_btn.setEnabled(True)
        else:
            self._status_label.setText("DISCONNECTED")
            self._status_label.setObjectName("status_red")
            self._connect_btn.setEnabled(True)
            self._disconnect_btn.setEnabled(False)
            self._ping_btn.setEnabled(False)
        # Force style refresh
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _on_filter_changed(self, text):
        self._filter_text = text.strip().lower()

    def _refresh(self):
        # Stats
        self._sent_msgs.setText(f"{self._bridge.msgs_sent} msgs")
        self._recv_msgs.setText(f"{self._bridge.msgs_recv} msgs")
        self._sent_bytes.setText(self._format_bytes(self._bridge.bytes_sent))
        self._recv_bytes.setText(self._format_bytes(self._bridge.bytes_recv))

        # Endpoint
        self._host_label.setText(f"{self._bridge.host}:{self._bridge.port}")

        # Append new log entries
        log = self._bridge.get_log()
        current_count = self._log_view.blockCount()
        for entry in log[max(0, current_count - 1):]:
            msg_type = entry["type"]
            if self._filter_text and self._filter_text not in msg_type.lower():
                continue
            direction = entry["dir"]
            ts = time.strftime("%H:%M:%S", time.localtime(entry["time"]))
            data_str = ""
            if entry.get("data") is not None:
                import json
                raw = json.dumps(entry["data"])
                data_str = f"  {raw[:100]}" if len(raw) > 100 else f"  {raw}"
            self._log_view.appendPlainText(
                f"[{ts}] {direction:4s} {msg_type}{data_str}"
            )

        if self._auto_scroll:
            sb = self._log_view.verticalScrollBar()
            sb.setValue(sb.maximum())

    @staticmethod
    def _format_bytes(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n / (1024 * 1024):.1f} MB"
