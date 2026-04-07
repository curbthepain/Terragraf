"""
CoherenceManager — detects conflicting state across sessions.

Polls all sessions on a 5-second timer and emits signals when:
  - Two tabs consult the same route (same-route conflict)
  - Two sessions contend for the same filesystem lock
"""

import json
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal


# Lock directory — same as instances/manager.py
_LOCKS_DIR = Path(__file__).resolve().parent.parent / "instances" / "shared" / "locks"


class CoherenceManager(QObject):
    """
    Periodically checks all sessions for conflicts and emits
    conflict_detected / conflict_cleared signals.
    """

    conflict_detected = Signal(str, str, str)  # session_id, conflict_type, detail
    conflict_cleared = Signal(str)             # session_id

    def __init__(self, session_manager, scaffold_state, parent=None):
        super().__init__(parent)
        self._session_mgr = session_manager
        self._state = scaffold_state

        # Active conflicts: session_id -> set of (conflict_type, detail) tuples
        self._active_conflicts: dict[str, set[tuple[str, str]]] = {}

        # Poll every 5 seconds
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self.check_conflicts)
        self._timer.start()

    def check_conflicts(self):
        """Run all conflict checks and emit appropriate signals."""
        current_conflicts: dict[str, set[tuple[str, str]]] = {}

        self._check_route_conflicts(current_conflicts)
        self._check_lock_contention(current_conflicts)

        # Emit new conflicts
        for sid, conflict_set in current_conflicts.items():
            prev = self._active_conflicts.get(sid, set())
            for conflict_type, detail in conflict_set - prev:
                self.conflict_detected.emit(sid, conflict_type, detail)

        # Emit cleared conflicts
        for sid, prev_set in self._active_conflicts.items():
            current = current_conflicts.get(sid, set())
            if not current and prev_set:
                self.conflict_cleared.emit(sid)

        self._active_conflicts = current_conflicts

    def _check_route_conflicts(self, conflicts: dict[str, set]):
        """Detect sessions that consult the same routes."""
        sessions = self._session_mgr.all_sessions()

        # Build route -> [session_ids] map
        route_sessions: dict[str, list[str]] = {}
        for session in sessions:
            for route in session.context.routes_consulted:
                route_sessions.setdefault(route, []).append(session.id)

        # Flag sessions sharing routes
        for route, sids in route_sessions.items():
            if len(sids) >= 2:
                for sid in sids:
                    conflicts.setdefault(sid, set()).add(("route", route))

    def _check_lock_contention(self, conflicts: dict[str, set]):
        """Detect sessions contending for filesystem locks."""
        if not _LOCKS_DIR.exists():
            return

        known_ids = set(self._session_mgr.ids())

        for lock_file in _LOCKS_DIR.glob("*.lock"):
            try:
                data = json.loads(lock_file.read_text())
                # Lock files don't store session IDs directly — they store PIDs.
                # Check if the resource name matches anything a session is working on.
                resource = lock_file.stem.replace("_", "/")
                holders = self._session_mgr.has_file_in_context(resource)
                if len(holders) >= 2:
                    for sid in holders:
                        conflicts.setdefault(sid, set()).add(
                            ("lock", resource)
                        )
            except (json.JSONDecodeError, OSError):
                continue

    @property
    def active_conflict_count(self) -> int:
        """Number of sessions with active conflicts."""
        return len(self._active_conflicts)

    def stop(self):
        """Stop the polling timer."""
        self._timer.stop()
