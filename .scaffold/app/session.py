"""
Session model for the tabbed workspace.

Each tab is an independent Session that tracks what scaffold state it has
read, which routes it consulted, and what files it modified. Sessions reuse
InstanceContext from .scaffold/instances/instance.py for state tracking
but run in-process — no subprocess boundary.

Two session types:
  - "native"   — runs QueryEngine inline (chat panel, tool execution)
  - "external" — observes scaffold state for Claude Code / Cursor
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from instances.instance import InstanceContext


MAX_SESSIONS = 16


@dataclass
class Session:
    """A single workspace session bound to one tab."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tab_type: str = "native"           # "native" or "external"
    label: str = ""                     # User-visible tab label
    created_at: float = field(default_factory=time.time)
    context: InstanceContext = field(default_factory=InstanceContext)
    pinned: bool = False
    query_history: list = field(default_factory=list)  # QueryResult entries
    coherence_warnings: list = field(default_factory=list)
    hot_context_contribution: str = ""
    llm_responses: list = field(default_factory=list)
    worktree_id: str = ""
    training_active: bool = False
    training_history: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.label:
            prefixes = {"native": "Native", "external": "External", "welcome": "Welcome"}
            prefix = prefixes.get(self.tab_type, self.tab_type.title())
            self.label = f"{prefix} {self.id[:4]}"
        self.context.instance_id = self.id
        self.context.started_at = self.created_at


class SessionManager:
    """
    Creates, destroys, and tracks workspace sessions.

    Exactly one session is "active" at a time (the visible tab).
    All sessions share the same ScaffoldState underneath.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._active_id: Optional[str] = None

    # ── Queries ──────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self._sessions)

    @property
    def active(self) -> Optional[Session]:
        if self._active_id and self._active_id in self._sessions:
            return self._sessions[self._active_id]
        return None

    @property
    def active_id(self) -> Optional[str]:
        return self._active_id

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def all_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def ids(self) -> list[str]:
        return list(self._sessions.keys())

    # ── Mutations ────────────────────────────────────────────────────

    def create(self, tab_type: str = "native", label: str = "") -> Session:
        """Create a new session. Raises if at capacity."""
        if self.count >= MAX_SESSIONS:
            raise RuntimeError(f"Maximum {MAX_SESSIONS} sessions reached")
        if tab_type not in ("native", "external", "welcome"):
            raise ValueError(f"Unknown tab type: {tab_type!r}")

        session = Session(tab_type=tab_type, label=label)
        self._sessions[session.id] = session

        # Auto-activate if this is the first session
        if self._active_id is None:
            self._active_id = session.id

        return session

    def destroy(self, session_id: str) -> bool:
        """Remove a session. Returns False if not found."""
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]

        # Clear active if it was this session
        if self._active_id == session_id:
            self._active_id = next(iter(self._sessions), None)

        return True

    def activate(self, session_id: str) -> bool:
        """Set a session as active. Returns False if not found."""
        if session_id not in self._sessions:
            return False
        self._active_id = session_id
        return True

    def destroy_all_except(self, keep_id: str):
        """Close all sessions except the one specified."""
        to_remove = [sid for sid in self._sessions if sid != keep_id]
        for sid in to_remove:
            self.destroy(sid)

    def has_file_in_context(self, filepath: str) -> list[str]:
        """Return session IDs that have modified the given file."""
        return [
            sid for sid, s in self._sessions.items()
            if filepath in s.context.files_modified
        ]
