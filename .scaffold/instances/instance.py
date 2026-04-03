"""
.scaffold/instances/instance.py
Single AI instance lifecycle.

Each instance is a peer — not a child agent. It reads the same scaffolding
as every other instance but has its own context window and task.

Lifecycle:
    1. Init — read ENTRY.md, MANIFEST.toml, task from queue
    2. Orient — read relevant headers for the task
    3. Route — consult .route files to find where to work
    4. Execute — do the work (generate, fix, build, train, etc.)
    5. Report — write result to shared/results.json
    6. Cleanup — release locks, update status
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


SCAFFOLD_DIR = Path(__file__).parent.parent
SHARED_DIR = Path(__file__).parent / "shared"


@dataclass
class InstanceContext:
    """Everything an instance knows about itself and its task."""
    instance_id: str = ""
    task_id: str = ""
    task_description: str = ""
    task_context: dict = field(default_factory=dict)
    platform: str = ""          # "linux_wayland" or "windows"
    started_at: float = 0.0
    headers_read: list = field(default_factory=list)
    routes_consulted: list = field(default_factory=list)
    files_modified: list = field(default_factory=list)


class Instance:
    """
    A single AI instance working within the scaffolding.

    Usage:
        instance = Instance(task_id="abc123", task_description="fix FFT bug")
        instance.orient()       # Read headers, routes
        instance.execute()      # Do the work (override this)
        instance.report(result) # Write result to shared state
    """

    def __init__(self, task_id: str, task_description: str,
                 task_context: dict = None, instance_id: str = ""):
        self.ctx = InstanceContext(
            instance_id=instance_id or f"inst-{int(time.time()) % 10000}",
            task_id=task_id,
            task_description=task_description,
            task_context=task_context or {},
            started_at=time.time(),
        )
        self._detect_platform()

    def orient(self):
        """
        Phase 1: Read the scaffolding to understand the environment.
        Every instance does this on startup.
        """
        # Read manifest
        manifest_path = SCAFFOLD_DIR / "MANIFEST.toml"
        if manifest_path.exists():
            self.ctx.headers_read.append("MANIFEST.toml")

        # Read project header (always)
        self._read_header("project.h")

        # Read platform header
        self._read_header("platform.h")

        # Read task-relevant headers based on route consultation
        self._consult_route("tasks.route", self.ctx.task_description)

    def execute(self):
        """
        Phase 2: Do the work. Override this in subclasses or
        have the AI fill in the logic based on the task.
        """
        raise NotImplementedError(
            "Instance.execute() must be implemented per-task. "
            "The AI reads the task description and routes to determine what to do."
        )

    def report(self, result: Any, status: str = "completed"):
        """
        Phase 3: Write result to shared state so the coordinator
        and other instances can see it.
        """
        report = {
            "instance_id": self.ctx.instance_id,
            "task_id": self.ctx.task_id,
            "task_description": self.ctx.task_description,
            "status": status,
            "result": result,
            "files_modified": self.ctx.files_modified,
            "duration": time.time() - self.ctx.started_at,
            "completed_at": time.time(),
        }

        results_file = SHARED_DIR / "results.json"
        results = []
        if results_file.exists():
            with open(results_file) as f:
                results = json.load(f)
        results.append(report)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"[{self.ctx.instance_id}] reported: {status}")

    def log(self, message: str):
        """Instance-scoped logging."""
        print(f"[{self.ctx.instance_id}] {message}")

    # ─── Internal ─────────────────────────────────────────────────

    def _detect_platform(self):
        """Detect which target platform we're running on."""
        import platform as plat
        import os
        system = plat.system()
        if system == "Linux":
            if os.environ.get("WAYLAND_DISPLAY"):
                self.ctx.platform = "linux_wayland"
            else:
                self.ctx.platform = "linux"
        elif system == "Windows":
            ver = plat.version()
            self.ctx.platform = "windows_11" if ver.startswith("10.0.22") else "windows_10"

    def _read_header(self, header_name: str):
        """Mark a header as read (actual parsing done by the AI)."""
        path = SCAFFOLD_DIR / "headers" / header_name
        if path.exists():
            self.ctx.headers_read.append(header_name)
            self.log(f"read header: {header_name}")

    def _consult_route(self, route_name: str, intent: str):
        """Mark a route as consulted (actual matching done by the AI)."""
        path = SCAFFOLD_DIR / "routes" / route_name
        if path.exists():
            self.ctx.routes_consulted.append(route_name)
            self.log(f"consulted route: {route_name} for '{intent}'")
