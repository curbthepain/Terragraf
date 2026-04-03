"""
.scaffold/imgui/bridge.py
Python <-> C++ bridge for Terragraf ImGui panels.

Provides bidirectional communication between Python compute
(math, FFT, ML) and the C++ ImGui frontend via TCP socket.

Usage (Python side):
    bridge = Bridge()
    bridge.start()
    bridge.send("fft_result", spectrum_data)
    params = bridge.receive()  # slider values from ImGui
    bridge.stop()

Usage (C++ side):
    Connect to localhost:9876, send/receive JSON messages.
"""

import json
import socket
import struct
import threading
import numpy as np
from typing import Any, Callable, Optional


class Bridge:
    """
    TCP socket bridge between Python and C++ ImGui.

    Protocol:
      [4 bytes: message length (uint32 big-endian)]
      [N bytes: JSON message]

    Message format:
      {"type": "fft_result", "data": [...]}
      {"type": "slider_update", "name": "freq", "value": 440.0}
    """

    DEFAULT_PORT = 9876
    DEFAULT_HOST = "127.0.0.1"

    def __init__(self, host=None, port=None):
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT
        self._server = None
        self._client = None
        self._running = False
        self._thread = None
        self._handlers = {}

    def on(self, msg_type: str, handler: Callable):
        """Register a handler for a message type."""
        self._handlers[msg_type] = handler

    def start(self, as_server=True):
        """Start the bridge. as_server=True listens, False connects."""
        self._running = True
        if as_server:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((self.host, self.port))
            self._server.listen(1)
            self._server.settimeout(1.0)
            self._thread = threading.Thread(target=self._server_loop, daemon=True)
        else:
            self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._client.connect((self.host, self.port))
            self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the bridge."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._client:
            self._client.close()
        if self._server:
            self._server.close()

    def send(self, msg_type: str, data: Any = None):
        """Send a message to the other side."""
        if not self._client:
            return
        msg = {"type": msg_type}
        if data is not None:
            if isinstance(data, np.ndarray):
                msg["data"] = data.tolist()
                msg["shape"] = list(data.shape)
                msg["dtype"] = str(data.dtype)
            else:
                msg["data"] = data
        self._send_msg(self._client, msg)

    def _send_msg(self, sock: socket.socket, msg: dict):
        """Send a length-prefixed JSON message."""
        payload = json.dumps(msg).encode("utf-8")
        header = struct.pack(">I", len(payload))
        sock.sendall(header + payload)

    def _recv_msg(self, sock: socket.socket) -> Optional[dict]:
        """Receive a length-prefixed JSON message."""
        header = self._recv_exact(sock, 4)
        if not header:
            return None
        length = struct.unpack(">I", header)[0]
        payload = self._recv_exact(sock, length)
        if not payload:
            return None
        return json.loads(payload.decode("utf-8"))

    def _recv_exact(self, sock: socket.socket, n: int) -> Optional[bytes]:
        """Receive exactly n bytes."""
        data = b""
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except (socket.timeout, OSError):
                return None
        return data

    def _server_loop(self):
        """Accept connection then receive messages."""
        while self._running:
            try:
                self._client, addr = self._server.accept()
                self._receive_loop()
            except socket.timeout:
                continue

    def _receive_loop(self):
        """Read messages from client and dispatch to handlers."""
        while self._running and self._client:
            msg = self._recv_msg(self._client)
            if msg is None:
                break
            msg_type = msg.get("type", "")
            if msg_type in self._handlers:
                self._handlers[msg_type](msg)
