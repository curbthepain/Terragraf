"""
Scaffold file watcher — detects changes to .scaffold/ files.

Wraps QFileSystemWatcher with debouncing (100ms) to coalesce rapid
filesystem events into single signal emissions. Cross-platform via Qt.

Watch targets:
  - HOT_CONTEXT.md
  - routes/*.route
  - headers/*.h
  - tables/*.table
  - tuning/analytics.json
  - instances/shared/queue.json, results.json
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer, QFileSystemWatcher


SCAFFOLD_DIR = Path(__file__).resolve().parent.parent

# Default watch targets relative to SCAFFOLD_DIR
_DEFAULT_TARGETS = [
    "HOT_CONTEXT.md",
    "routes/structure.route",
    "routes/tasks.route",
    "routes/bugs.route",
    "headers/project.h",
    "headers/platform.h",
    "headers/modes.h",
    "tables/deps.table",
    "tuning/analytics.json",
    "instances/shared/queue.json",
    "instances/shared/results.json",
]

# Categories for classifying file changes
_CATEGORY_MAP = {
    "headers": "header",
    "routes": "route",
    "tables": "table",
    "tuning": "tuning",
    "instances": "instance",
}


class ScaffoldWatcher(QObject):
    """
    Watches scaffold files for changes and emits categorized signals.

    Debounces rapid events within a 100ms window — multiple writes to
    the same file within 100ms emit only one signal.
    """

    # Categorized signals
    header_changed = Signal(str)        # header filename
    route_changed = Signal(str)         # route filename
    table_changed = Signal(str)         # table filename
    tuning_changed = Signal(str)        # tuning filename
    hot_context_changed = Signal()
    queue_changed = Signal()
    results_changed = Signal()
    file_modified = Signal(str)         # any scaffold file (absolute path)

    def __init__(self, scaffold_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self._scaffold_dir = Path(scaffold_dir) if scaffold_dir else SCAFFOLD_DIR
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_dir_changed)

        # Debounce state: path -> QTimer
        self._debounce_timers: dict[str, QTimer] = {}
        self._debounce_ms = 100

        # Track watched paths for cleanup
        self._watched_files: set[str] = set()
        self._watched_dirs: set[str] = set()

    # ── Setup ────────────────────────────────────────────────────────

    def watch_defaults(self):
        """Register default scaffold watch targets."""
        for rel in _DEFAULT_TARGETS:
            path = self._scaffold_dir / rel
            if path.exists():
                self.add_file(str(path))

        # Watch directories for new file creation
        for dirname in ("routes", "headers", "tables"):
            dirpath = self._scaffold_dir / dirname
            if dirpath.is_dir():
                self.add_directory(str(dirpath))

    def add_file(self, path: str) -> bool:
        """Add a file to the watch list. Returns True if successful."""
        path = str(Path(path).resolve())
        if path in self._watched_files:
            return True
        result = self._watcher.addPath(path)
        if result:
            self._watched_files.add(path)
        return result

    def add_directory(self, path: str) -> bool:
        """Add a directory to the watch list."""
        path = str(Path(path).resolve())
        if path in self._watched_dirs:
            return True
        result = self._watcher.addPath(path)
        if result:
            self._watched_dirs.add(path)
        return result

    def remove_file(self, path: str) -> bool:
        """Remove a file from the watch list."""
        path = str(Path(path).resolve())
        self._watched_files.discard(path)
        return self._watcher.removePath(path)

    def remove_directory(self, path: str) -> bool:
        """Remove a directory from the watch list."""
        path = str(Path(path).resolve())
        self._watched_dirs.discard(path)
        return self._watcher.removePath(path)

    @property
    def watched_files(self) -> set[str]:
        return set(self._watched_files)

    @property
    def watched_dirs(self) -> set[str]:
        return set(self._watched_dirs)

    def cleanup(self):
        """Remove all watches and cancel pending timers."""
        for timer in self._debounce_timers.values():
            timer.stop()
        self._debounce_timers.clear()

        for path in list(self._watched_files):
            self._watcher.removePath(path)
        for path in list(self._watched_dirs):
            self._watcher.removePath(path)
        self._watched_files.clear()
        self._watched_dirs.clear()

    # ── Event handling ───────────────────────────────────────────────

    def _on_file_changed(self, path: str):
        """Raw file change — debounce before emitting."""
        self._debounce(path)
        # QFileSystemWatcher may drop the watch after a change on some
        # platforms (e.g., atomic writes that replace the file).
        # Re-add if the file still exists.
        resolved = str(Path(path).resolve())
        if resolved in self._watched_files and Path(path).exists():
            if resolved not in self._watcher.files():
                self._watcher.addPath(resolved)

    def _on_dir_changed(self, path: str):
        """Directory changed — check for new files to watch."""
        dirpath = Path(path)
        scaffold_str = str(self._scaffold_dir)
        for child in dirpath.iterdir():
            if child.is_file():
                child_str = str(child.resolve())
                if child_str not in self._watched_files:
                    # Auto-watch new files in watched directories
                    if child_str.startswith(scaffold_str):
                        self.add_file(child_str)

    def _debounce(self, path: str):
        """Coalesce rapid events within the debounce window."""
        if path in self._debounce_timers:
            self._debounce_timers[path].stop()
        else:
            timer = QTimer(self)
            timer.setSingleShot(True)
            self._debounce_timers[path] = timer

        timer = self._debounce_timers[path]
        timer.timeout.connect(lambda p=path: self._emit_change(p))
        timer.start(self._debounce_ms)

    def _emit_change(self, path: str):
        """Emit the appropriate categorized signal."""
        # Clean up timer
        if path in self._debounce_timers:
            self._debounce_timers[path].deleteLater()
            del self._debounce_timers[path]

        # Always emit the generic signal
        self.file_modified.emit(path)

        # Classify and emit categorized signal
        try:
            rel = Path(path).resolve().relative_to(self._scaffold_dir.resolve())
        except ValueError:
            return  # Not under scaffold dir

        rel_str = str(rel).replace("\\", "/")
        name = rel.name

        if rel_str == "HOT_CONTEXT.md":
            self.hot_context_changed.emit()
        elif rel_str == "instances/shared/queue.json":
            self.queue_changed.emit()
        elif rel_str == "instances/shared/results.json":
            self.results_changed.emit()
        else:
            # Categorize by parent directory
            parts = rel.parts
            if parts:
                category = _CATEGORY_MAP.get(parts[0])
                if category == "header":
                    self.header_changed.emit(name)
                elif category == "route":
                    self.route_changed.emit(name)
                elif category == "table":
                    self.table_changed.emit(name)
                elif category == "tuning":
                    self.tuning_changed.emit(name)
