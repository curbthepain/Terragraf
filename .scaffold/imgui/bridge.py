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
import sys
import threading
from pathlib import Path
import numpy as np
from typing import Any, Callable, Optional

# Add .scaffold/ to path for tuning imports
_SCAFFOLD_DIR = Path(__file__).parent.parent
if str(_SCAFFOLD_DIR) not in sys.path:
    sys.path.insert(0, str(_SCAFFOLD_DIR))


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
        """Accept connections and receive messages. Re-accepts after disconnect."""
        while self._running:
            try:
                client, addr = self._server.accept()
                self._client = client
                print(f"[bridge] client connected from {addr[0]}:{addr[1]}")
                self._receive_loop()
                # Client disconnected — clean up so send() doesn't write to dead socket
                self._client = None
                print("[bridge] client disconnected, waiting for new connection...")
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
                try:
                    self._handlers[msg_type](msg)
                except Exception as e:
                    print(f"[bridge] handler error for '{msg_type}': {e}")

    # ── Tuning Integration ──────────────────────────────────────────

    def register_tuning_handlers(self):
        """Register handlers for thematic tension calibration messages.

        Call after start() to wire up tune_* message handling.
        The ThematicEngine is instantiated lazily on first use.
        """
        from tuning.engine import ThematicEngine
        engine = ThematicEngine()

        def _profile_to_json(profile):
            """Serialize a UniverseProfile for the C++ panel."""
            knobs = []
            for k in profile.knobs:
                knob_data = {
                    "id": k.id,
                    "domain": k.domain,
                    "label": k.label,
                    "knob_type": k.knob_type,
                    "description": k.description,
                    "behavior": k.behavior,
                    "default": k.default,
                    "value": k.value,
                }
                if k.knob_type == "slider":
                    knob_data.update({
                        "min_val": k.min_val,
                        "max_val": k.max_val,
                        "step": k.step,
                    })
                elif k.knob_type == "dropdown":
                    knob_data["options"] = k.options or []
                elif k.knob_type == "curve":
                    knob_data["x_label"] = k.x_label
                    knob_data["y_label"] = k.y_label
                elif k.knob_type == "text":
                    knob_data["max_length"] = k.max_length or 256
                knobs.append(knob_data)

            zones = [{"name": z.name} for z in profile.zones]

            return {
                "name": profile.name,
                "genre": profile.genre,
                "description": profile.description,
                "thematic_promise": profile.thematic_promise,
                "register": profile.register,
                "mortality_weight": profile.mortality_weight,
                "power_fantasy": profile.power_fantasy,
                "shitpost_tolerance": profile.shitpost_tolerance,
                "reaction_template": profile.reaction.template,
                "reaction_description": profile.reaction.description,
                "bot_directive": profile.bot_directive,
                "zones": zones,
                "knobs": knobs,
                "knob_domains": profile.knob_domains(),
            }

        def _state_update():
            """Build a state update response dict."""
            axes = engine.get_active_axes()
            zone = engine.active_zone
            return {
                "axes": axes,
                "zone": zone.name if zone else None,
                "knobs": engine.get_knob_state(),
                "instructions": engine.get_behavioral_instructions(),
            }

        def handle_tune_list(msg):
            profiles = engine.list_profiles()
            self.send("tune_profiles", {"profiles": profiles})

        def handle_tune_load(msg):
            name = msg.get("data", {}).get("name", "")
            profile = engine.load(name)
            data = _profile_to_json(profile)
            data["instructions"] = engine.get_behavioral_instructions()
            self.send("tune_profile_data", data)

        def handle_tune_zone(msg):
            zone_name = msg.get("data", {}).get("zone", "")
            engine.enter_zone(zone_name)
            self.send("tune_state_update", _state_update())

        def handle_tune_zone_exit(msg):
            engine.exit_zone()
            self.send("tune_state_update", _state_update())

        def handle_tune_set_knob(msg):
            data = msg.get("data", {})
            knob_id = data.get("id", "")
            value = data.get("value")
            engine.set_knob(knob_id, value)
            self.send("tune_state_update", _state_update())

        def handle_tune_reset_knobs(msg):
            engine.reset_knob()
            self.send("tune_state_update", _state_update())

        def handle_tune_get_instructions(msg):
            text = engine.get_behavioral_instructions()
            self.send("tune_instructions", {"text": text})

        self.on("tune_list", handle_tune_list)
        self.on("tune_load", handle_tune_load)
        self.on("tune_zone", handle_tune_zone)
        self.on("tune_zone_exit", handle_tune_zone_exit)
        self.on("tune_set_knob", handle_tune_set_knob)
        self.on("tune_reset_knobs", handle_tune_reset_knobs)
        self.on("tune_get_instructions", handle_tune_get_instructions)

    def register_debug_handlers(self):
        """Register ping/pong and debug echo handlers."""

        def handle_ping(msg):
            self.send("pong", msg.get("data"))

        def handle_debug_echo(msg):
            self.send("debug_echo", msg.get("data"))

        self.on("ping", handle_ping)
        self.on("debug_echo", handle_debug_echo)


if __name__ == "__main__":
    import signal

    shutdown = threading.Event()

    bridge = Bridge()
    bridge.start(as_server=True)
    bridge.register_tuning_handlers()
    bridge.register_debug_handlers()

    print(f"Bridge server listening on {bridge.host}:{bridge.port}")
    print("Press Ctrl+C to stop.")

    signal.signal(signal.SIGINT, lambda *_: shutdown.set())
    signal.signal(signal.SIGTERM, lambda *_: shutdown.set())

    shutdown.wait()
    bridge.stop()
    print("Bridge stopped.")
