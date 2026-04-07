"""
mcp/server.py — MCP resource server over TCP.

JSON-RPC 2.0 over length-prefixed TCP on port 9878.
Reuses the wire protocol from instances/transport.py.

Supported methods:
  resources/list       List all resource descriptors
  resources/read       Read resource content by URI
  resources/subscribe  Subscribe to resource change notifications
  tools/list           List available tools (skills)
  tools/call           Execute a tool (skill)

Notifications (server -> client):
  resources/updated    Sent when a subscribed resource changes
"""

import json
import os
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .resources import ResourceRegistry
from .tools import SkillToolAdapter


DEFAULT_PORT = 9878
DEFAULT_HOST = "127.0.0.1"


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
class MCPPeer:
    """A connected MCP client."""
    sock: socket.socket
    addr: tuple
    peer_id: str = ""
    connected_at: float = field(default_factory=time.time)
    subscriptions: set = field(default_factory=set)  # URI patterns


class MCPServer:
    """
    TCP server exposing scaffold resources via JSON-RPC 2.0.

    Usage:
        registry = ResourceRegistry(scaffold_state)
        server = MCPServer(registry, scaffold_state)
        server.start()
        # ... server runs until stop()
        server.stop()
    """

    def __init__(self, resource_registry: ResourceRegistry,
                 scaffold_state=None, host: str = None, port: int = None):
        self.host = host or os.environ.get("TERRA_MCP_HOST", DEFAULT_HOST)
        self.port = int(os.environ.get("TERRA_MCP_PORT", port or DEFAULT_PORT))
        self._registry = resource_registry
        self._state = scaffold_state
        self._tool_adapter = SkillToolAdapter()

        self._server: Optional[socket.socket] = None
        self._running = False
        self._accept_thread: Optional[threading.Thread] = None
        self._peers: list[MCPPeer] = []
        self._peer_threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._started_at: float = 0.0

    def start(self):
        """Start the MCP server. Connects to ScaffoldState for live push."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(16)
        self._server.settimeout(1.0)
        self._running = True
        self._started_at = time.time()

        self._accept_thread = threading.Thread(
            target=self._accept_loop, daemon=True)
        self._accept_thread.start()

        # Wire state change notifications if ScaffoldState has signal
        if self._state is not None and hasattr(self._state, "state_changed"):
            try:
                self._state.state_changed.connect(self._on_state_changed)
            except Exception:
                pass  # Not in Qt context (CLI mode)

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

    def status(self) -> dict:
        """Return server status info."""
        with self._lock:
            client_count = len(self._peers)
            sub_count = sum(len(p.subscriptions) for p in self._peers)
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "connected_clients": client_count,
            "subscription_count": sub_count,
            "uptime": time.time() - self._started_at if self._started_at else 0,
        }

    @property
    def running(self) -> bool:
        return self._running

    # ── Accept loop ──────────────────────────────────────────────────

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server.accept()
                conn.settimeout(5.0)
                peer = MCPPeer(sock=conn, addr=addr,
                               peer_id=f"mcp-{int(time.time()) % 10000}")
                with self._lock:
                    self._peers.append(peer)
                t = threading.Thread(
                    target=self._peer_loop, args=(peer,), daemon=True)
                self._peer_threads.append(t)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _peer_loop(self, peer: MCPPeer):
        """Receive and dispatch messages from a single peer."""
        while self._running:
            msg = _recv_msg(peer.sock)
            if msg is None:
                break
            response = self._handle_message(peer, msg)
            if response is not None:
                _send_msg(peer.sock, response)

        # Peer disconnected
        with self._lock:
            if peer in self._peers:
                self._peers.remove(peer)
        try:
            peer.sock.close()
        except OSError:
            pass

    # ── Message dispatch ─────────────────────────────────────────────

    def _handle_message(self, peer: MCPPeer, msg: dict) -> Optional[dict]:
        """Dispatch a JSON-RPC 2.0 request and return response."""
        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        handler = {
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "resources/subscribe": self._handle_resources_subscribe,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
        }.get(method)

        if handler is None:
            return self._error_response(msg_id, -32601, f"Method not found: {method}")

        try:
            result = handler(peer, params)
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as exc:
            return self._error_response(msg_id, -32000, str(exc))

    # ── Handlers ─────────────────────────────────────────────────────

    def _handle_resources_list(self, peer: MCPPeer, params: dict) -> dict:
        descriptors = self._registry.list_resources()
        return {"resources": [d.to_dict() for d in descriptors]}

    def _handle_resources_read(self, peer: MCPPeer, params: dict) -> dict:
        uri = params.get("uri", "")
        if not uri:
            raise ValueError("Missing 'uri' parameter")
        resource = self._registry.read_resource(uri)
        if resource is None:
            raise ValueError(f"Resource not found: {uri}")
        return {"contents": [resource.to_dict()]}

    def _handle_resources_subscribe(self, peer: MCPPeer, params: dict) -> dict:
        uri = params.get("uri", "")
        if not uri:
            raise ValueError("Missing 'uri' parameter")
        peer.subscriptions.add(uri)
        return {"subscribed": True, "uri": uri}

    def _handle_tools_list(self, peer: MCPPeer, params: dict) -> dict:
        tools = self._tool_adapter.list_tools()
        return {"tools": tools}

    def _handle_tools_call(self, peer: MCPPeer, params: dict) -> dict:
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        if not name:
            raise ValueError("Missing 'name' parameter")
        return self._tool_adapter.call_tool(name, arguments)

    # ── Notifications ────────────────────────────────────────────────

    def _on_state_changed(self):
        """Push resource/updated notifications to subscribed peers."""
        notification = {
            "jsonrpc": "2.0",
            "method": "resources/updated",
            "params": {"timestamp": time.time()},
        }
        with self._lock:
            dead = []
            for peer in self._peers:
                if peer.subscriptions:
                    if not _send_msg(peer.sock, notification):
                        dead.append(peer)
            for peer in dead:
                self._peers.remove(peer)

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _error_response(msg_id, code: int, message: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        }
