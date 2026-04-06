"""
FeedbackLoop — cross-tab intelligence layer.

Watches activity across sessions and suggests actions:
  - Sharpen suggestion: external route consulted by a session
  - HOT_CONTEXT push: native skill execution result summary
  - Knowledge suggestion: same file modified across 3+ sessions
"""

from PySide6.QtCore import QObject, Signal


class FeedbackLoop(QObject):
    """
    Connects ExternalDetector, ScaffoldState, and SessionManager to
    produce cross-tab feedback signals.
    """

    sharpen_suggested = Signal(str)    # route path
    hot_context_push = Signal(str)     # text to push
    knowledge_suggested = Signal(str)  # file path

    def __init__(self, scaffold_state, session_manager, external_detector, parent=None):
        super().__init__(parent)
        self._state = scaffold_state
        self._session_mgr = session_manager
        self._external_detector = external_detector

        # Track which files we've already suggested knowledge for
        self._knowledge_suggested: set[str] = set()

        # Wire to external change events
        self._external_detector.external_change.connect(self._on_external_change)

        # Wire to scaffold state changes for skill execution detection
        self._state.state_changed.connect(self._on_state_changed)

    def _on_external_change(self, event):
        """Check if an external event touches a route consulted by any session."""
        if event.event_type not in ("route", "header", "table"):
            return

        path = event.path
        for session in self._session_mgr.all_sessions():
            if session.pinned:
                continue
            if path in session.context.routes_consulted:
                self.sharpen_suggested.emit(path)
                return

    def _on_state_changed(self):
        """Check for skill execution results and file modification patterns."""
        if not self._state.recent_events:
            return

        event = self._state.recent_events[-1]

        # HOT_CONTEXT push: when results.json changes (skill execution completed)
        if event.event_type == "results":
            detail = event.detail or ""
            if detail:
                self.hot_context_push.emit(detail)

        # Knowledge suggestion: check file modification frequency across sessions
        self._check_knowledge_suggestions()

    def _check_knowledge_suggestions(self):
        """Emit knowledge_suggested when 3+ sessions have modified the same file."""
        file_counts: dict[str, int] = {}
        for session in self._session_mgr.all_sessions():
            if session.pinned:
                continue
            for filepath in session.context.files_modified:
                file_counts[filepath] = file_counts.get(filepath, 0) + 1

        for filepath, count in file_counts.items():
            if count >= 3 and filepath not in self._knowledge_suggested:
                self._knowledge_suggested.add(filepath)
                self.knowledge_suggested.emit(filepath)
