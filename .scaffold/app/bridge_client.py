"""Qt-side bridge client — connects to bridge.py for live communication."""

import json
import socket
import struct
import threading
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Signal, QTimer


class BridgeClient(QObject):
    """TCP client that talks to bridge.py, emitting Qt signals on message receipt."""

    message_received = Signal(str, dict)  # (msg_type, full_msg)
    connection_changed = Signal(bool)      # connected state

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 9876

    def __init__(self, host: str = None, port: int = None, parent=None):
        super().__init__(parent)
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._handlers: dict[str, Callable] = {}

        # Stats
        self.msgs_sent = 0
        self.msgs_recv = 0
        self.bytes_sent = 0
        self.bytes_recv = 0

        # Message log (bounded)
        self._log: list[dict] = []
        self._log_max = 500

    @property
    def connected(self) -> bool:
        return self._connected

    def on(self, msg_type: str, handler: Callable):
        """Register a handler for a message type."""
        self._handlers[msg_type] = handler

    def connect_to_bridge(self) -> bool:
        """Connect to the bridge server. Returns True on success."""
        if self._connected:
            return True
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(3.0)
            self._socket.connect((self.host, self.port))
            self._socket.settimeout(1.0)
            self._running = True
            self._connected = True
            self._thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._thread.start()
            self.connection_changed.emit(True)
            return True
        except (OSError, ConnectionRefusedError):
            self._connected = False
            self._socket = None
            self.connection_changed.emit(False)
            return False

    def disconnect_from_bridge(self):
        """Disconnect from the bridge."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
        self._connected = False
        self.connection_changed.emit(False)

    def send(self, msg_type: str, data: Any = None):
        """Send a message to bridge.py."""
        if not self._connected or not self._socket:
            return
        msg = {"type": msg_type}
        if data is not None:
            msg["data"] = data
        try:
            payload = json.dumps(msg).encode("utf-8")
            header = struct.pack(">I", len(payload))
            self._socket.sendall(header + payload)
            self.msgs_sent += 1
            self.bytes_sent += len(payload)
            self._push_log("SEND", msg_type, msg)
        except OSError:
            self._handle_disconnect()

    def get_log(self) -> list[dict]:
        """Return the message log (newest last)."""
        return list(self._log)

    def clear_log(self):
        """Clear the message log."""
        self._log.clear()

    # ── Internal ────────────────────────────────────────────────────

    def _recv_loop(self):
        """Background thread: read messages and emit signals."""
        while self._running:
            msg = self._recv_msg()
            if msg is None:
                if self._running:
                    self._handle_disconnect()
                break
            msg_type = msg.get("type", "")
            self.msgs_recv += 1
            self.bytes_recv += len(json.dumps(msg))
            self._push_log("RECV", msg_type, msg)

            # Dispatch handler
            handler = self._handlers.get(msg_type)
            if handler:
                handler(msg)

            # Emit signal (cross-thread safe via Qt signal)
            self.message_received.emit(msg_type, msg)

    def _recv_msg(self) -> Optional[dict]:
        header = self._recv_exact(4)
        if not header:
            return None
        length = struct.unpack(">I", header)[0]
        if length > 16 * 1024 * 1024:
            return None
        payload = self._recv_exact(length)
        if not payload:
            return None
        self.bytes_recv += 4 + length
        return json.loads(payload.decode("utf-8"))

    def _recv_exact(self, n: int) -> Optional[bytes]:
        data = b""
        while len(data) < n and self._running:
            try:
                chunk = self._socket.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                continue
            except OSError:
                return None
        return data if len(data) == n else None

    def _handle_disconnect(self):
        self._connected = False
        self._running = False
        self.connection_changed.emit(False)

    def _push_log(self, direction: str, msg_type: str, msg: dict):
        import time
        entry = {
            "time": time.time(),
            "dir": direction,
            "type": msg_type,
            "data": msg.get("data"),
        }
        self._log.append(entry)
        if len(self._log) > self._log_max:
            self._log = self._log[-self._log_max:]
