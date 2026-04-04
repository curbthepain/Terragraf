"""Tests for .scaffold/instances/transport.py — socket IPC transport layer."""

import json
import time
import threading
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from instances.transport import TransportServer, TransportClient, _send_msg, _recv_msg


# Use a unique port per test run to avoid conflicts
TEST_PORT = 19877


class TestTransportProtocol:
    """Test the wire protocol helpers directly."""

    def test_send_recv_roundtrip(self):
        """Send and receive a message through a socket pair."""
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", TEST_PORT + 100))
        server.listen(1)
        server.settimeout(5)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", TEST_PORT + 100))
        conn, _ = server.accept()
        conn.settimeout(5)

        msg = {"type": "test", "data": {"key": "value", "num": 42}}
        assert _send_msg(client, msg)
        received = _recv_msg(conn)

        assert received is not None
        assert received["type"] == "test"
        assert received["data"]["key"] == "value"
        assert received["data"]["num"] == 42

        client.close()
        conn.close()
        server.close()

    def test_multiple_messages(self):
        """Send multiple messages in sequence."""
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", TEST_PORT + 101))
        server.listen(1)
        server.settimeout(5)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", TEST_PORT + 101))
        conn, _ = server.accept()
        conn.settimeout(5)

        for i in range(5):
            _send_msg(client, {"type": "seq", "n": i})

        for i in range(5):
            msg = _recv_msg(conn)
            assert msg is not None
            assert msg["n"] == i

        client.close()
        conn.close()
        server.close()

    def test_large_message(self):
        """Send a message larger than typical buffer sizes."""
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", TEST_PORT + 102))
        server.listen(1)
        server.settimeout(5)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", TEST_PORT + 102))
        conn, _ = server.accept()
        conn.settimeout(5)

        big_data = "x" * 100_000
        _send_msg(client, {"type": "big", "payload": big_data})
        msg = _recv_msg(conn)

        assert msg is not None
        assert len(msg["payload"]) == 100_000

        client.close()
        conn.close()
        server.close()


class TestTransportServerClient:
    """Test TransportServer and TransportClient together."""

    def test_connect_and_register(self):
        """Client connects and registers with server."""
        server = TransportServer(port=TEST_PORT)
        server.start()
        time.sleep(0.1)

        client = TransportClient(port=TEST_PORT)
        assert client.connect(instance_id="test-inst-1")
        time.sleep(0.2)

        assert server.connected_count >= 1

        client.disconnect()
        server.stop()

    def test_client_send_to_server(self):
        """Client sends a message, server receives it via poll."""
        server = TransportServer(port=TEST_PORT + 1)
        received = []
        server.on("task_result", lambda iid, msg: received.append((iid, msg)))
        server.start()
        time.sleep(0.1)

        client = TransportClient(port=TEST_PORT + 1)
        client.connect(instance_id="worker-1")
        time.sleep(0.1)

        client.send({
            "type": "task_result",
            "data": {"task_id": "abc", "status": "completed", "result": "ok"}
        })
        time.sleep(0.2)
        server.poll()

        assert len(received) == 1
        assert received[0][1]["data"]["task_id"] == "abc"

        client.disconnect()
        server.stop()

    def test_server_broadcast_to_client(self):
        """Server broadcasts a message, client receives it."""
        server = TransportServer(port=TEST_PORT + 2)
        server.start()
        time.sleep(0.1)

        client = TransportClient(port=TEST_PORT + 2)
        received = []
        client.on("task_assign", lambda msg: received.append(msg))
        client.connect(instance_id="worker-2")
        time.sleep(0.1)

        server.broadcast({
            "type": "task_assign",
            "data": {"task_id": "xyz", "description": "fix bug"}
        })
        time.sleep(0.2)
        client.poll()

        assert len(received) == 1
        assert received[0]["data"]["task_id"] == "xyz"

        client.disconnect()
        server.stop()

    def test_server_send_to_specific_instance(self):
        """Server sends to a specific instance by ID."""
        server = TransportServer(port=TEST_PORT + 3)
        server.start()
        time.sleep(0.1)

        client1 = TransportClient(port=TEST_PORT + 3)
        client2 = TransportClient(port=TEST_PORT + 3)
        received1 = []
        received2 = []
        client1.on("task_assign", lambda msg: received1.append(msg))
        client2.on("task_assign", lambda msg: received2.append(msg))
        client1.connect(instance_id="worker-a")
        client2.connect(instance_id="worker-b")
        time.sleep(0.2)

        server.send_to("worker-a", {
            "type": "task_assign",
            "data": {"task_id": "targeted"}
        })
        time.sleep(0.2)
        client1.poll()
        client2.poll()

        assert len(received1) == 1
        assert len(received2) == 0

        client1.disconnect()
        client2.disconnect()
        server.stop()

    def test_multiple_clients(self):
        """Multiple clients connect simultaneously."""
        server = TransportServer(port=TEST_PORT + 4)
        server.start()
        time.sleep(0.1)

        clients = []
        for i in range(4):
            c = TransportClient(port=TEST_PORT + 4)
            c.connect(instance_id=f"multi-{i}")
            clients.append(c)

        time.sleep(0.3)
        assert server.connected_count >= 4

        for c in clients:
            c.disconnect()
        server.stop()

    def test_heartbeat(self):
        """Client heartbeat doesn't appear in inbox."""
        server = TransportServer(port=TEST_PORT + 5)
        server.start()
        time.sleep(0.1)

        client = TransportClient(port=TEST_PORT + 5)
        client.connect(instance_id="hb-test")
        time.sleep(0.1)

        client.heartbeat()
        time.sleep(0.2)
        messages = server.poll()

        # Only the register message should be there, not heartbeat
        for _, msg in messages:
            assert msg.get("type") != "heartbeat"

        client.disconnect()
        server.stop()

    def test_client_disconnect_detection(self):
        """Server detects when client disconnects."""
        server = TransportServer(port=TEST_PORT + 6)
        server.start()
        time.sleep(0.1)

        client = TransportClient(port=TEST_PORT + 6)
        client.connect(instance_id="dc-test")
        time.sleep(0.2)
        assert server.connected_count >= 1

        client.disconnect()
        time.sleep(1.0)
        # After disconnect, peer count should decrease
        # (recv loop timeout is 5s, but disconnect closes socket immediately)
        assert server.connected_count == 0

        server.stop()

    def test_reconnect_after_disconnect(self):
        """Client can reconnect after disconnecting."""
        server = TransportServer(port=TEST_PORT + 7)
        server.start()
        time.sleep(0.1)

        client = TransportClient(port=TEST_PORT + 7)
        assert client.connect(instance_id="rc-test")
        client.disconnect()
        time.sleep(0.2)

        client2 = TransportClient(port=TEST_PORT + 7)
        assert client2.connect(instance_id="rc-test-2")
        time.sleep(0.1)
        assert server.connected_count >= 1

        client2.disconnect()
        server.stop()


class TestManagerSocketIntegration:
    """Test InstanceManager with socket IPC."""

    def test_manager_starts_with_socket(self):
        """Manager starts in socket mode."""
        from instances.manager import InstanceManager
        mgr = InstanceManager(ipc="socket")
        assert mgr._ipc_mode == "socket"
        assert mgr._transport is not None
        status = mgr.status()
        assert status["ipc_mode"] == "socket"
        mgr.shutdown()

    def test_manager_falls_back_to_filesystem(self):
        """Manager falls back to filesystem when socket unavailable."""
        from instances.manager import InstanceManager
        # Occupy the port so manager can't bind
        import socket
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", 9877))
        blocker.listen(1)

        mgr = InstanceManager(ipc="auto")
        assert mgr._ipc_mode == "filesystem"
        mgr.shutdown()
        blocker.close()

    def test_manager_enqueue_and_status(self):
        """Enqueue tasks and check status."""
        from instances.manager import InstanceManager
        mgr = InstanceManager(ipc="filesystem")
        mgr.enqueue("task A")
        mgr.enqueue("task B")
        status = mgr.status()
        assert status["tasks"]["total"] == 2
        assert status["tasks"]["pending"] == 2
        mgr.shutdown()

    def test_manager_dispatch_via_socket(self):
        """Manager dispatches task to connected instance."""
        from instances.manager import InstanceManager
        mgr = InstanceManager(ipc="socket")
        time.sleep(0.2)

        client = TransportClient(port=9877)
        received = []
        client.on("task_assign", lambda msg: received.append(msg))
        client.connect(instance_id="dispatch-test")
        time.sleep(0.3)

        mgr.enqueue("test task", context={"file": "foo.py"})
        mgr.run()

        # Retry polling — Windows socket dispatch can be slower
        for _ in range(20):
            time.sleep(0.1)
            client.poll()
            if received:
                break

        assert len(received) == 1
        assert received[0]["data"]["description"] == "test task"

        client.disconnect()
        mgr.shutdown()

    def test_instance_reports_back_via_socket(self):
        """Instance sends result back through socket to manager."""
        from instances.manager import InstanceManager
        mgr = InstanceManager(ipc="socket")
        time.sleep(0.2)

        task_id = mgr.enqueue("socket report test")
        mgr.run()
        time.sleep(0.2)

        client = TransportClient(port=9877)
        client.connect(instance_id="reporter")
        time.sleep(0.2)

        client.send({
            "type": "task_result",
            "data": {
                "task_id": task_id,
                "status": "completed",
                "result": "all good"
            }
        })

        # Retry polling — Windows socket dispatch can be slower
        task = next(t for t in mgr.tasks if t.id == task_id)
        for _ in range(20):
            time.sleep(0.1)
            mgr.poll()
            if task.status == "completed":
                break

        assert task.status == "completed"
        assert task.result == "all good"

        client.disconnect()
        mgr.shutdown()
