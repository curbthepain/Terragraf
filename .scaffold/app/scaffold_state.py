"""
Parsed scaffold state — in-memory cache of headers, routes, tables, and HOT_CONTEXT.

All sessions read from this singleton. ScaffoldWatcher triggers auto-refresh
when files change on disk. Changes propagate to all tabs via Qt signals.
"""

import re
import time
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal


SCAFFOLD_DIR = Path(__file__).resolve().parent.parent


@dataclass
class ScaffoldEvent:
    """A single scaffold state change event."""
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""      # "header", "route", "table", "tuning", "hot_context", "queue", "results", "file"
    path: str = ""            # Relative path within .scaffold/
    detail: str = ""          # Human-readable description


@dataclass
class RouteEntry:
    """A single concept -> path mapping from a .route file."""
    concept: str = ""
    path: str = ""
    description: str = ""


class ScaffoldState(QObject):
    """
    In-memory cache of parsed scaffold state.

    Connect to a ScaffoldWatcher to auto-refresh when files change.
    Emits `state_changed` after any refresh so UI can update.
    """

    state_changed = Signal()

    def __init__(self, scaffold_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self._scaffold_dir = Path(scaffold_dir) if scaffold_dir else SCAFFOLD_DIR

        # Parsed state
        self.headers: dict[str, dict] = {}          # filename -> {modules: [...]}
        self.routes: dict[str, list[RouteEntry]] = {} # filename -> [RouteEntry, ...]
        self.tables: dict[str, str] = {}            # filename -> raw text
        self.hot_context: str = ""
        self.queue_status: dict = {}                # Parsed queue.json summary

        # Event log
        self.recent_events: deque[ScaffoldEvent] = deque(maxlen=500)

        # Snapshot for diffing
        self._last_snapshot: dict[str, str] = {}

    # ── Initial load ─────────────────────────────────────────────────

    def load_all(self):
        """Parse all scaffold state from disk."""
        self._load_headers()
        self._load_routes()
        self._load_tables()
        self._load_hot_context()
        self._load_queue()
        self.state_changed.emit()

    # ── Connect to watcher ───────────────────────────────────────────

    def connect_watcher(self, watcher):
        """Wire ScaffoldWatcher signals to auto-refresh methods."""
        watcher.header_changed.connect(self._on_header_changed)
        watcher.route_changed.connect(self._on_route_changed)
        watcher.table_changed.connect(self._on_table_changed)
        watcher.tuning_changed.connect(self._on_tuning_changed)
        watcher.hot_context_changed.connect(self._on_hot_context_changed)
        watcher.queue_changed.connect(self._on_queue_changed)
        watcher.results_changed.connect(self._on_results_changed)

    # ── Refresh handlers ─────────────────────────────────────────────

    def _on_header_changed(self, filename: str):
        self._load_header_file(filename)
        self._record_event("header", f"headers/{filename}", f"Header {filename} reloaded")
        self.state_changed.emit()

    def _on_route_changed(self, filename: str):
        self._load_route_file(filename)
        self._record_event("route", f"routes/{filename}", f"Route {filename} reloaded")
        self.state_changed.emit()

    def _on_table_changed(self, filename: str):
        self._load_table_file(filename)
        self._record_event("table", f"tables/{filename}", f"Table {filename} reloaded")
        self.state_changed.emit()

    def _on_tuning_changed(self, filename: str):
        self._record_event("tuning", f"tuning/{filename}", f"Tuning {filename} changed")
        self.state_changed.emit()

    def _on_hot_context_changed(self):
        old = self.hot_context
        self._load_hot_context()
        self._record_event("hot_context", "HOT_CONTEXT.md", "HOT_CONTEXT updated")
        self.state_changed.emit()

    def _on_queue_changed(self):
        self._load_queue()
        self._record_event("queue", "instances/shared/queue.json", "Queue updated")
        self.state_changed.emit()

    def _on_results_changed(self):
        self._record_event("results", "instances/shared/results.json", "Results updated")
        self.state_changed.emit()

    # ── Parsers ──────────────────────────────────────────────────────

    def _load_headers(self):
        """Parse all .h files in headers/."""
        headers_dir = self._scaffold_dir / "headers"
        if not headers_dir.is_dir():
            return
        for hfile in headers_dir.glob("*.h"):
            self._load_header_file(hfile.name)

    def _load_header_file(self, filename: str):
        """Parse a single header file for module declarations."""
        path = self._scaffold_dir / "headers" / filename
        if not path.exists():
            self.headers.pop(filename, None)
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        modules = []
        # Extract #module NAME { ... } blocks
        for match in re.finditer(
            r'#module\s+(\w+)\s*\{([^}]*)\}', text, re.DOTALL
        ):
            name = match.group(1)
            body = match.group(2)
            module = {"name": name}
            # Extract fields
            for fmatch in re.finditer(r'#(\w+)\s+(.+)', body):
                key = fmatch.group(1)
                val = fmatch.group(2).strip().strip('"')
                if key == "exports":
                    val = [v.strip() for v in val.strip("[]").split(",") if v.strip()]
                elif key == "depends":
                    val = [v.strip() for v in val.strip("[]").split(",") if v.strip()]
                module[key] = val
            modules.append(module)
        self.headers[filename] = {"modules": modules, "raw": text}

    def _load_routes(self):
        """Parse all .route files in routes/."""
        routes_dir = self._scaffold_dir / "routes"
        if not routes_dir.is_dir():
            return
        for rfile in routes_dir.glob("*.route"):
            self._load_route_file(rfile.name)

    def _load_route_file(self, filename: str):
        """Parse a single route file for concept -> path mappings."""
        path = self._scaffold_dir / "routes" / filename
        if not path.exists():
            self.routes.pop(filename, None)
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: CONCEPT -> PATH [# description]
            match = re.match(r'^(.+?)\s*->\s*(.+?)(?:\s*#\s*(.*))?$', line)
            if match:
                concept = match.group(1).strip()
                target = match.group(2).strip()
                desc = (match.group(3) or "").strip()
                entries.append(RouteEntry(concept=concept, path=target, description=desc))
        self.routes[filename] = entries

    def _load_tables(self):
        """Load all .table files in tables/."""
        tables_dir = self._scaffold_dir / "tables"
        if not tables_dir.is_dir():
            return
        for tfile in tables_dir.glob("*.table"):
            self._load_table_file(tfile.name)

    def _load_table_file(self, filename: str):
        """Load a single table file as raw text."""
        path = self._scaffold_dir / "tables" / filename
        if not path.exists():
            self.tables.pop(filename, None)
            return
        self.tables[filename] = path.read_text(encoding="utf-8", errors="replace")

    def _load_hot_context(self):
        """Load HOT_CONTEXT.md."""
        path = self._scaffold_dir / "HOT_CONTEXT.md"
        if path.exists():
            self.hot_context = path.read_text(encoding="utf-8", errors="replace")
        else:
            self.hot_context = ""

    def _load_queue(self):
        """Load and summarize queue.json."""
        import json
        path = self._scaffold_dir / "instances" / "shared" / "queue.json"
        if not path.exists():
            self.queue_status = {"total": 0, "pending": 0, "running": 0}
            return
        try:
            with open(path) as f:
                tasks = json.load(f)
            pending = sum(1 for t in tasks if t.get("status") == "pending")
            running = sum(1 for t in tasks if t.get("status") == "running")
            self.queue_status = {
                "total": len(tasks),
                "pending": pending,
                "running": running,
                "tasks": tasks,
            }
        except (json.JSONDecodeError, OSError):
            self.queue_status = {"total": 0, "pending": 0, "running": 0}

    # ── Events ───────────────────────────────────────────────────────

    def _record_event(self, event_type: str, path: str, detail: str):
        self.recent_events.append(ScaffoldEvent(
            event_type=event_type,
            path=path,
            detail=detail,
        ))

    # ── Snapshot / Diff ──────────────────────────────────────────────

    def take_snapshot(self) -> dict[str, str]:
        """
        Capture current state as a flat dict for diffing.
        Returns {relative_path: content_hash_or_summary}.
        """
        snap = {}
        snap["HOT_CONTEXT.md"] = self.hot_context[:200] if self.hot_context else ""
        for fname, data in self.headers.items():
            modules = [m["name"] for m in data.get("modules", [])]
            snap[f"headers/{fname}"] = f"modules: {', '.join(modules)}"
        for fname, entries in self.routes.items():
            snap[f"routes/{fname}"] = f"{len(entries)} routes"
        for fname, text in self.tables.items():
            snap[f"tables/{fname}"] = f"{len(text)} bytes"
        self._last_snapshot = snap
        return deepcopy(snap)

    # ── Summary ──────────────────────────────────────────────────────

    def health_summary(self) -> dict:
        """Quick health overview for the welcome tab."""
        total_modules = sum(
            len(d.get("modules", [])) for d in self.headers.values()
        )
        total_routes = sum(len(entries) for entries in self.routes.values())
        return {
            "header_files": len(self.headers),
            "modules": total_modules,
            "route_files": len(self.routes),
            "routes": total_routes,
            "table_files": len(self.tables),
            "queue_pending": self.queue_status.get("pending", 0),
            "queue_running": self.queue_status.get("running", 0),
            "hot_context_lines": len(self.hot_context.splitlines()) if self.hot_context else 0,
            "recent_events": len(self.recent_events),
        }
