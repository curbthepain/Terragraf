"""
.scaffold/instances/transport.py
IPC transport layer for instance coordination.

Provides socket-based communication between the instance manager
and worker instances, replacing filesystem polling with event-driven
message dispatch.

Protocol (same as imgui bridge):
    [4 bytes: message length (uint32 big-endian)]
    [N bytes: JSON message]

Message format:
    {"type": "task_assign", "data": {...}}
    {"type": "task_result", "data": {...}}
    {"type": "heartbeat"}

Usage:
    # Manager side
    server = TransportServer(port=9877)
    server.start()
    server.broadcast({"type": "task_assign", "data": task_dict})
    messages = server.poll()
    server.stop()

    # Instance side
    client = TransportClient(port=9877)
    client.connect()
    client.send({"type": "task_result", "data": result_dict})
    messages = client.poll()
    client.disconnect()
"""

import json
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


def _send_msg(sock: socket.socket, msg: dict) -> bool:
    """Send a length-prefixed JSON message."""
    try:
        payload = json.dumps(msg).encode("utf-8")
        header = struct.pack(">I", len(payload))
        sock.sendall(header + payload)
        return True
    except (OSError, BrokenPipeError):
        return False


def _recv_msg(sock: socket.socket) -> Optional[dict]:
    """Receive a length-prefixed JSON message."""
    header = _recv_exact(sock, 4)
    if not header:
        return None
    length = struct.unpack(">I", header)[0]
    if length == 0 or length > 16 * 1024 * 1024:
        return None
    payload = _recv_exact(sock, length)
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


def _recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
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


@dataclass
class PeerConnection:
    """Tracks a connected peer (instance or manager)."""
    sock: socket.socket
    addr: tuple
    instance_id: str = ""
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)


class TransportServer:
    """
    Socket server for the instance manager.
    Accepts connections from worker instances, dispatches messages.
    """

    DEFAULT_PORT = 9877
    DEFAULT_HOST = "127.0.0.1"

    def __init__(self, host=None, port=None):
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT
        self._server: Optional[socket.socket] = None
        self._running = False
        self._accept_thread: Optional[threading.Thread] = None
        self._peers: list[PeerConnection] = []
        self._peer_threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._inbox: list[tuple[str, dict]] = []  # (instance_id, message)
        self._inbox_lock = threading.Lock()
        self._handlers: dict[str, Callable] = {}

    def on(self, msg_type: str, handler: Callable):
        """Register a handler for a message type."""
        self._handlers[msg_type] = handler

    def start(self):
        """Start listening for instance connections."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            # Windows: prevent multiple binds to the same port
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            # Linux/macOS: reuse port after close
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(16)
        self._server.settimeout(1.0)
        self._running = True
        self._accept_thread = threading.Thread(
            target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def stop(self):
        """Stop the server and disconnect all peers."""
        self._running = False
        with self._lock:
            for peer in self._peers:
                try:
                    peer.sock.close()
                except OSError:
                    pass
            self._peers.clear()
        if self._server:
            self._server.close()
        if self._accept_thread:
            self._accept_thread.join(timeout=2)
        for t in self._peer_threads:
            t.join(timeout=2)

    def send_to(self, instance_id: str, msg: dict) -> bool:
        """Send a message to a specific instance."""
        with self._lock:
            for peer in self._peers:
                if peer.instance_id == instance_id:
                    return _send_msg(peer.sock, msg)
        return False

    def broadcast(self, msg: dict):
        """Send a message to all connected instances."""
        with self._lock:
            dead = []
            for peer in self._peers:
                if not _send_msg(peer.sock, msg):
                    dead.append(peer)
            for peer in dead:
                self._peers.remove(peer)

    def poll(self) -> list[tuple[str, dict]]:
        """Return and clear queued messages. Each is (instance_id, msg)."""
        with self._inbox_lock:
            batch = self._inbox[:]
            self._inbox.clear()
        # Dispatch to handlers
        for instance_id, msg in batch:
            msg_type = msg.get("type", "")
            if msg_type in self._handlers:
                self._handlers[msg_type](instance_id, msg)
        return batch

    @property
    def connected_count(self) -> int:
        with self._lock:
            return len(self._peers)

    def connected_instances(self) -> list[str]:
        with self._lock:
            return [p.instance_id for p in self._peers if p.instance_id]

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server.accept()
                conn.settimeout(1.0)
                peer = PeerConnection(sock=conn, addr=addr)
                with self._lock:
                    self._peers.append(peer)
                t = threading.Thread(
                    target=self._peer_recv_loop, args=(peer,), daemon=True)
                self._peer_threads.append(t)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _peer_recv_loop(self, peer: PeerConnection):
        while self._running:
            msg = _recv_msg(peer.sock)
            if msg is None:
                break

            # Register instance ID on first message
            if not peer.instance_id and "instance_id" in msg:
                peer.instance_id = msg["instance_id"]

            if msg.get("type") == "heartbeat":
                peer.last_heartbeat = time.time()
                continue

            with self._inbox_lock:
                self._inbox.append((peer.instance_id, msg))

        # Peer disconnected
        with self._lock:
            if peer in self._peers:
                self._peers.remove(peer)
        try:
            peer.sock.close()
        except OSError:
            pass


class TransportClient:
    """
    Socket client for worker instances.
    Connects to the manager, sends results, receives task assignments.
    """

    def __init__(self, host=None, port=None):
        self.host = host or TransportServer.DEFAULT_HOST
        self.port = port or TransportServer.DEFAULT_PORT
        self._sock: Optional[socket.socket] = None
        self._running = False
        self._recv_thread: Optional[threading.Thread] = None
        self._inbox: list[dict] = []
        self._inbox_lock = threading.Lock()
        self._handlers: dict[str, Callable] = {}
        self._connected = False
        self.instance_id = ""

    @property
    def connected(self) -> bool:
        return self._connected

    def on(self, msg_type: str, handler: Callable):
        """Register a handler for a message type."""
        self._handlers[msg_type] = handler

    def connect(self, instance_id: str = "") -> bool:
        """Connect to the manager."""
        self.instance_id = instance_id
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect((self.host, self.port))
            self._sock.settimeout(5.0)
            self._connected = True
            self._running = True
            self._recv_thread = threading.Thread(
                target=self._recv_loop, daemon=True)
            self._recv_thread.start()

            # Announce ourselves
            self.send({"type": "register", "instance_id": instance_id})
            return True
        except (OSError, ConnectionRefusedError):
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from the manager."""
        self._running = False
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._recv_thread:
            self._recv_thread.join(timeout=2)

    def send(self, msg: dict) -> bool:
        """Send a message to the manager."""
        if not self._connected or not self._sock:
            return False
        if "instance_id" not in msg:
            msg["instance_id"] = self.instance_id
        return _send_msg(self._sock, msg)

    def poll(self) -> list[dict]:
        """Return and clear queued messages from the manager."""
        with self._inbox_lock:
            batch = self._inbox[:]
            self._inbox.clear()
        for msg in batch:
            msg_type = msg.get("type", "")
            if msg_type in self._handlers:
                self._handlers[msg_type](msg)
        return batch

    def heartbeat(self):
        """Send a heartbeat to the manager."""
        self.send({"type": "heartbeat"})

    def _recv_loop(self):
        while self._running:
            msg = _recv_msg(self._sock)
            if msg is None:
                if self._running:
                    self._connected = False
                break
            if msg.get("type") == "heartbeat":
                continue
            with self._inbox_lock:
                self._inbox.append(msg)
