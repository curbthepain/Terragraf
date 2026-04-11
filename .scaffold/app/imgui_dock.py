"""ImGui dock — routes data from the active tab to ImGui via bridge.

Listens for tab switches and sends context-appropriate data to the
embedded ImGui viewer.  Native tabs send route trees and query results;
external tabs send scaffold snapshots and activity events.
"""

from PySide6.QtCore import QObject, QTimer


class ImGuiDock(QObject):
    """Routes data from the active tab to ImGui panels via bridge messages.

    On each tab switch, sends a ``context_switch`` message followed by
    tab-type-specific data (route_tree for native, scaffold_snapshot +
    activity_feed for external).

    Rapid tab switches are debounced to 200ms so ImGui doesn't get
    flooded during fast keyboard cycling.
    """

    DEBOUNCE_MS = 200

    def __init__(self, bridge_client, scaffold_state, session_manager,
                 parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._state = scaffold_state
        self._session_mgr = session_manager

        # Pending context switch (debounced)
        self._pending_session_id: str | None = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._flush)

        # Message queue for when bridge is disconnected
        self._queued: list[tuple[str, dict]] = []

        # Re-send queued messages on reconnect
        self._bridge.connection_changed.connect(self._on_connection_changed)

    # ── Public API ──────────────────────────────────────────────────

    def on_tab_activated(self, session_id: str):
        """Called when a tab becomes active.  Debounces rapid switches."""
        self._pending_session_id = session_id
        self._debounce_timer.start(self.DEBOUNCE_MS)

    # ── Internal ──────────────���─────────────────────────────────────

    def _flush(self):
        """Send context_switch + data for the pending session."""
        sid = self._pending_session_id
        if sid is None:
            return
        self._pending_session_id = None

        session = self._session_mgr.get(sid)
        if session is None:
            return

        # 1. context_switch
        self._send("context_switch", {
            "tab_type": session.tab_type,
            "session_id": session.id,
            "label": session.label,
        })

        # 2. Tab-type-specific data
        if session.tab_type == "native":
            self._send_native_data()
        elif session.tab_type == "external":
            self._send_external_data()

    def _send_native_data(self):
        """Send route tree from ScaffoldState."""
        routes = []
        for filename, entries in self._state.routes.items():
            for entry in entries:
                routes.append({
                    "concept": entry.concept,
                    "path": entry.path,
                    "description": entry.description,
                })
        self._send("route_tree", {"routes": routes})

    def _send_external_data(self):
        """Send scaffold snapshot + activity feed."""
        # Snapshot
        snapshot = self._state.take_snapshot()
        self._send("scaffold_snapshot", snapshot)

        # Activity feed (recent events)
        events = []
        for ev in self._state.recent_events:
            events.append({
                "ts": ev.timestamp,
                "type": ev.event_type,
                "path": ev.path,
                "detail": ev.detail,
            })
        self._send("activity_feed", {"events": events})

    # ── Training updates (ML pipeline → ImGui) ─────────────────────

    def send_training_started(self, data: dict):
        """Forward a training_started event to ImGui."""
        self._send("training_started", data)

    def send_training_update(self, data: dict):
        """Forward a per-epoch training update to ImGui."""
        self._send("training_update", data)

    def send_training_finished(self, data: dict):
        """Forward a training_finished event to ImGui."""
        self._send("training_finished", data)

    def _send(self, msg_type: str, data: dict):
        """Send via bridge, or queue if disconnected."""
        if self._bridge.connected:
            self._bridge.send(msg_type, data)
        else:
            self._queued.append((msg_type, data))

    def _on_connection_changed(self, connected: bool):
        """Flush queued messages when bridge reconnects."""
        if connected and self._queued:
            for msg_type, data in self._queued:
                self._bridge.send(msg_type, data)
            self._queued.clear()
