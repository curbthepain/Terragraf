"""
External detector — classifies scaffold state changes as external or internal.

External changes come from outside the app (Claude Code, Cursor, manual edits).
Internal changes come from native sessions running QueryEngine inline.

Heuristics:
  - HOT_CONTEXT.md changes → always external (native tabs don't write it)
  - queue.json / results.json → check instance IDs against SessionManager
  - Route/header/table → check session.context.files_modified across all sessions
  - Lock files in instances/shared/ → external
"""

from PySide6.QtCore import QObject, Signal


class ExternalDetector(QObject):
    """
    Receives scaffold state changes and emits external_change
    for events not attributable to any active native session.
    """

    external_change = Signal(object)  # Emits ScaffoldEvent

    def __init__(self, scaffold_state, session_manager, parent=None):
        super().__init__(parent)
        self._state = scaffold_state
        self._session_mgr = session_manager

        # Wire to state changes
        self._state.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self):
        """Check the most recent event and classify it."""
        if not self._state.recent_events:
            return
        event = self._state.recent_events[-1]
        if self._is_external(event):
            self.external_change.emit(event)

    def _is_external(self, event) -> bool:
        """Determine if a scaffold event was caused by an external agent."""
        etype = event.event_type

        # HOT_CONTEXT changes are always external — native tabs don't write it
        if etype == "hot_context":
            return True

        # Results changes are always external
        if etype == "results":
            return True

        # Lock files are always external
        if etype == "file" and "lock" in event.path.lower():
            return True

        # Queue changes — check if any session owns the instance ID
        if etype == "queue":
            return self._is_queue_external()

        # Route/header/table — check if any session claims the file
        if etype in ("header", "route", "table", "tuning"):
            return not self._is_file_claimed(event.path)

        return True  # Unknown types default to external

    def _is_queue_external(self) -> bool:
        """Check if queue.json contains tasks from unknown instances."""
        tasks = self._state.queue_status.get("tasks", [])
        known_ids = set(self._session_mgr.ids())

        for task in tasks:
            instance_id = task.get("instance_id", "")
            if instance_id and instance_id not in known_ids:
                return True

        # If no tasks or all tasks have known IDs, it's internal
        return not tasks or not known_ids

    def _is_file_claimed(self, rel_path: str) -> bool:
        """Check if any active session has modified this file."""
        for session in self._session_mgr.all_sessions():
            for modified in session.context.files_modified:
                # Match on suffix — rel_path is like "headers/project.h",
                # files_modified entries may be full or relative paths
                if modified.endswith(rel_path) or rel_path.endswith(modified):
                    return True
        return False

    def classify(self, event) -> bool:
        """Public API for testing: returns True if event is external."""
        return self._is_external(event)
