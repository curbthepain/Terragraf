"""Tests for Session 15 — MCP resource tools.

30 tests covering:
  - ResourceDescriptor (3)
  - ResourceRegistry (10)
  - SkillToolAdapter (5)
  - MCPServer (8)
  - Integration (4)
"""

import json
import os
import socket
import struct
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure .scaffold is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.resources import ResourceDescriptor, Resource, ResourceRegistry, _parse_uri
from mcp.tools import SkillToolAdapter
from mcp.server import MCPServer, _send_msg, _recv_msg


# ── Helpers ──────────────────────────────────────────────────────────

def _make_scaffold(tmp_path):
    """Create a minimal scaffold directory for testing."""
    scaffold = tmp_path / ".scaffold"
    scaffold.mkdir()
    (scaffold / "headers").mkdir()
    (scaffold / "routes").mkdir()
    (scaffold / "tables").mkdir()
    (scaffold / "instances" / "shared").mkdir(parents=True)
    (scaffold / "skills").mkdir()

    (scaffold / "headers" / "project.h").write_text(
        '#module math {\n'
        '    #path "compute/math"\n'
        '    #exports [mat_mul, fft1d]\n'
        '    #depends [fft]\n'
        '    #desc "Math operations"\n'
        '}\n'
    )
    (scaffold / "routes" / "structure.route").write_text(
        "fft -> compute/fft/ # FFT utilities\n"
        "math -> compute/math/ # Math primitives\n"
    )
    (scaffold / "tables" / "deps.table").write_text(
        "# deps table\nmath | fft | uses | low\n"
    )
    (scaffold / "HOT_CONTEXT.md").write_text("# Test Session\nStatus: testing\n")
    (scaffold / "instances" / "shared" / "queue.json").write_text("[]")
    return scaffold


def _make_scaffold_state(scaffold_dir):
    """Create a ScaffoldState without Qt dependency."""
    state = MagicMock()
    state.routes = {}
    state.headers = {}
    state.tables = {}
    state.hot_context = ""
    state.queue_status = {}

    # Parse routes
    routes_dir = scaffold_dir / "routes"
    if routes_dir.exists():
        import re
        for rfile in routes_dir.glob("*.route"):
            entries = []
            for line in rfile.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r'^(.+?)\s*->\s*(.+?)(?:\s*#\s*(.*))?$', line)
                if match:
                    entry = MagicMock()
                    entry.concept = match.group(1).strip()
                    entry.path = match.group(2).strip()
                    entry.description = (match.group(3) or "").strip()
                    entries.append(entry)
            state.routes[rfile.name] = entries

    # Parse headers
    headers_dir = scaffold_dir / "headers"
    if headers_dir.exists():
        import re
        for hfile in headers_dir.glob("*.h"):
            text = hfile.read_text()
            modules = []
            for match in re.finditer(r'#module\s+(\w+)\s*\{([^}]*)\}', text, re.DOTALL):
                name = match.group(1)
                body = match.group(2)
                module = {"name": name}
                for fmatch in re.finditer(r'#(\w+)\s+(.+)', body):
                    key = fmatch.group(1)
                    val = fmatch.group(2).strip().strip('"')
                    if key in ("exports", "depends"):
                        val = [v.strip() for v in val.strip("[]").split(",") if v.strip()]
                    module[key] = val
                modules.append(module)
            state.headers[hfile.name] = {"modules": modules, "raw": text}

    # Parse tables
    tables_dir = scaffold_dir / "tables"
    if tables_dir.exists():
        for tfile in tables_dir.glob("*.table"):
            state.tables[tfile.name] = tfile.read_text()

    # HOT_CONTEXT
    hc_path = scaffold_dir / "HOT_CONTEXT.md"
    if hc_path.exists():
        state.hot_context = hc_path.read_text()

    # Queue
    import json as _json
    q_path = scaffold_dir / "instances" / "shared" / "queue.json"
    if q_path.exists():
        state.queue_status = {"total": 0, "pending": 0, "running": 0}

    return state


def _send_rpc(sock, method, params=None, msg_id=1):
    """Send a JSON-RPC request over length-prefixed TCP."""
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}
    payload = json.dumps(msg).encode("utf-8")
    header = struct.pack(">I", len(payload))
    sock.sendall(header + payload)


def _recv_rpc(sock, timeout=5.0):
    """Receive a JSON-RPC response over length-prefixed TCP."""
    sock.settimeout(timeout)
    header = b""
    while len(header) < 4:
        chunk = sock.recv(4 - len(header))
        if not chunk:
            return None
        header += chunk
    length = struct.unpack(">I", header)[0]
    payload = b""
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        if not chunk:
            return None
        payload += chunk
    return json.loads(payload.decode("utf-8"))


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def scaffold_dir(tmp_path):
    return _make_scaffold(tmp_path)


@pytest.fixture
def scaffold_state(scaffold_dir):
    return _make_scaffold_state(scaffold_dir)


@pytest.fixture
def registry(scaffold_state):
    return ResourceRegistry(scaffold_state)


@pytest.fixture
def tool_adapter(scaffold_dir):
    return SkillToolAdapter(skills_dir=scaffold_dir / "skills")


# ── TestResourceDescriptor ───────────────────────────────────────────

class TestResourceDescriptor:
    def test_defaults(self):
        d = ResourceDescriptor()
        assert d.uri == ""
        assert d.mime_type == "application/json"

    def test_to_dict(self):
        d = ResourceDescriptor(uri="scaffold://routes/structure", name="routes/structure",
                               description="Routes", mime_type="application/json")
        result = d.to_dict()
        assert result["uri"] == "scaffold://routes/structure"
        assert result["name"] == "routes/structure"
        assert result["mimeType"] == "application/json"

    def test_equality(self):
        d1 = ResourceDescriptor(uri="scaffold://hot_context", name="hot_context")
        d2 = ResourceDescriptor(uri="scaffold://hot_context", name="hot_context")
        assert d1 == d2


# ── TestResourceRegistry ────────────────────────────────────────────

class TestResourceRegistry:
    def test_list_includes_routes(self, registry):
        descriptors = registry.list_resources()
        uris = [d.uri for d in descriptors]
        assert "scaffold://routes/structure" in uris

    def test_list_includes_headers(self, registry):
        descriptors = registry.list_resources()
        uris = [d.uri for d in descriptors]
        assert "scaffold://headers/project" in uris

    def test_list_includes_hot_context(self, registry):
        descriptors = registry.list_resources()
        uris = [d.uri for d in descriptors]
        assert "scaffold://hot_context" in uris

    def test_list_includes_queue(self, registry):
        descriptors = registry.list_resources()
        uris = [d.uri for d in descriptors]
        assert "scaffold://queue" in uris

    def test_list_includes_tables(self, registry):
        descriptors = registry.list_resources()
        uris = [d.uri for d in descriptors]
        assert "scaffold://tables/deps" in uris

    def test_read_routes(self, registry):
        resource = registry.read_resource("scaffold://routes/structure")
        assert resource is not None
        assert "routes" in resource.content
        assert len(resource.content["routes"]) == 2

    def test_read_headers(self, registry):
        resource = registry.read_resource("scaffold://headers/project")
        assert resource is not None
        modules = resource.content["modules"]
        assert len(modules) == 1
        assert modules[0]["name"] == "math"

    def test_read_hot_context(self, registry):
        resource = registry.read_resource("scaffold://hot_context")
        assert resource is not None
        assert "Test Session" in resource.content

    def test_read_nonexistent(self, registry):
        resource = registry.read_resource("scaffold://routes/nonexistent")
        assert resource is None

    def test_read_invalid_scheme(self, registry):
        resource = registry.read_resource("http://example.com")
        assert resource is None


# ── TestParseUri ─────────────────────────────────────────────────────

class TestParseUri:
    def test_routes(self):
        assert _parse_uri("scaffold://routes/structure") == ("routes", "structure")

    def test_hot_context(self):
        assert _parse_uri("scaffold://hot_context") == ("hot_context", "")

    def test_invalid(self):
        assert _parse_uri("bad://uri") == ("", "")


# ── TestSkillToolAdapter ────────────────────────────────────────────

class TestSkillToolAdapter:
    def test_list_tools_returns_list(self):
        with patch("skills.runner.list_skills", return_value=[]):
            adapter = SkillToolAdapter()
            tools = adapter.list_tools()
            assert isinstance(tools, list)

    def test_list_tools_has_name_and_description(self):
        mock_skills = [("health_check", {
            "skill": {"description": "System diagnostic", "type": "diagnostic"},
            "triggers": {"intents": ["health check"]},
        })]
        with patch("skills.runner.list_skills", return_value=mock_skills):
            adapter = SkillToolAdapter()
            tools = adapter.list_tools()
            assert len(tools) == 1
            assert tools[0]["name"] == "health_check"
            assert tools[0]["description"] == "System diagnostic"

    def test_list_tools_has_input_schema(self):
        mock_skills = [("test_suite", {
            "skill": {"description": "Run tests", "type": "validator"},
            "triggers": {"intents": ["run tests"]},
        })]
        with patch("skills.runner.list_skills", return_value=mock_skills):
            adapter = SkillToolAdapter()
            tools = adapter.list_tools()
            schema = tools[0]["inputSchema"]
            assert schema["type"] == "object"
            assert "args" in schema["properties"]

    def test_call_tool_success(self):
        with patch("skills.runner.run_skill_capture", return_value=(0, "OK", "")):
            adapter = SkillToolAdapter()
            result = adapter.call_tool("health_check", {"args": ["--quick"]})
            assert result["isError"] is False
            assert result["content"][0]["text"] == "OK"

    def test_call_tool_failure(self):
        with patch("skills.runner.run_skill_capture", return_value=(1, "", "Error: not found")):
            adapter = SkillToolAdapter()
            result = adapter.call_tool("nonexistent", {})
            assert result["isError"] is True
            assert "not found" in result["content"][0]["text"]


# ── TestMCPServer ───────────────────────────────────────────────────

def _find_free_port():
    """Find a free TCP port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestMCPServer:
    def test_start_stop(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        assert server.running
        server.stop()
        assert not server.running

    def test_status(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            status = server.status()
            assert status["running"] is True
            assert status["port"] == port
            assert status["connected_clients"] == 0
        finally:
            server.stop()

    def test_client_connects(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            time.sleep(0.1)
            assert server.status()["connected_clients"] == 1
            sock.close()
        finally:
            server.stop()

    def test_resources_list(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            _send_rpc(sock, "resources/list")
            response = _recv_rpc(sock)
            assert response is not None
            assert "result" in response
            resources = response["result"]["resources"]
            assert isinstance(resources, list)
            assert len(resources) > 0
            uris = [r["uri"] for r in resources]
            assert "scaffold://hot_context" in uris
            sock.close()
        finally:
            server.stop()

    def test_resources_read(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            _send_rpc(sock, "resources/read", {"uri": "scaffold://hot_context"})
            response = _recv_rpc(sock)
            assert "result" in response
            contents = response["result"]["contents"]
            assert len(contents) == 1
            assert "Test Session" in contents[0]["text"]
            sock.close()
        finally:
            server.stop()

    def test_resources_read_not_found(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            _send_rpc(sock, "resources/read", {"uri": "scaffold://routes/nonexistent"})
            response = _recv_rpc(sock)
            assert "error" in response
            sock.close()
        finally:
            server.stop()

    def test_unknown_method(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            _send_rpc(sock, "unknown/method")
            response = _recv_rpc(sock)
            assert "error" in response
            assert response["error"]["code"] == -32601
            sock.close()
        finally:
            server.stop()

    def test_subscribe(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            _send_rpc(sock, "resources/subscribe", {"uri": "scaffold://hot_context"})
            response = _recv_rpc(sock)
            assert response["result"]["subscribed"] is True
            assert server.status()["subscription_count"] == 1
            sock.close()
        finally:
            server.stop()


# ── TestMCPIntegration ──────────────────────────────────────────────

class TestMCPIntegration:
    def test_registry_reflects_state(self, scaffold_state):
        registry = ResourceRegistry(scaffold_state)
        descriptors = registry.list_resources()
        # Should have routes + headers + tables + hot_context + queue + skills
        assert len(descriptors) >= 5

    def test_resource_to_dict(self, registry):
        resource = registry.read_resource("scaffold://hot_context")
        d = resource.to_dict()
        assert "uri" in d
        assert "mimeType" in d
        assert d["text"] is not None

    def test_tools_list_roundtrip(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            _send_rpc(sock, "tools/list")
            response = _recv_rpc(sock)
            assert "result" in response
            assert "tools" in response["result"]
            assert isinstance(response["result"]["tools"], list)
            sock.close()
        finally:
            server.stop()

    def test_multiple_clients(self, registry, scaffold_state):
        port = _find_free_port()
        server = MCPServer(registry, scaffold_state, port=port)
        server.start()
        try:
            socks = []
            for _ in range(3):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("127.0.0.1", port))
                socks.append(s)
            time.sleep(0.2)
            assert server.status()["connected_clients"] == 3
            for s in socks:
                s.close()
        finally:
            server.stop()
