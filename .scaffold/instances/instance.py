"""
.scaffold/instances/instance.py
Single AI instance lifecycle.

Each instance is a peer — not a child agent. It reads the same scaffolding
as every other instance but has its own context window and task.

Supports two IPC modes:
  - "filesystem" — reads queue.json, writes results.json
  - "socket" — connects to manager via TransportClient

Lifecycle:
    1. Init — read ENTRY.md, MANIFEST.toml, task from queue
    2. Orient — read relevant headers for the task
    3. Route — consult .route files to find where to work
    4. Execute — do the work (generate, fix, build, train, etc.)
    5. Report — send result via socket or write to results.json
    6. Cleanup — release locks, disconnect, update status
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
    worktree_id: str = ""
    worktree_path: str = ""
    worktree_branch: str = ""


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
                 task_context: dict = None, instance_id: str = "",
                 ipc: str = "auto"):
        """
        Args:
            ipc: IPC mode — "auto", "socket", or "filesystem".
                 "auto" tries socket first, falls back to filesystem.
        """
        self.ctx = InstanceContext(
            instance_id=instance_id or f"inst-{int(time.time()) % 10000}",
            task_id=task_id,
            task_description=task_description,
            task_context=task_context or {},
            started_at=time.time(),
        )
        self._detect_platform()
        self._transport = None
        self._ipc_mode = ipc
        self._pending_task = None

        if ipc in ("auto", "socket"):
            try:
                from .transport import TransportClient
                self._transport = TransportClient()
                if self._transport.connect(instance_id=self.ctx.instance_id):
                    self._ipc_mode = "socket"
                    self._transport.on("task_assign", self._handle_task_assign)
                    self.log("connected to manager via socket")
                else:
                    self._transport = None
                    self._ipc_mode = "filesystem"
                    self.log("socket unavailable, using filesystem IPC")
            except Exception:
                self._transport = None
                self._ipc_mode = "filesystem"

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
            "routes_consulted": self.ctx.routes_consulted,
            "headers_read": self.ctx.headers_read,
            "duration": time.time() - self.ctx.started_at,
            "completed_at": time.time(),
        }

        if self._transport and self._ipc_mode == "socket":
            # Send result via socket
            self._transport.send({
                "type": "task_result",
                "data": {
                    "task_id": self.ctx.task_id,
                    "status": status,
                    "result": result,
                    "files_modified": self.ctx.files_modified,
                    "duration": time.time() - self.ctx.started_at,
                }
            })
            self.log(f"reported via socket: {status}")
        else:
            # Filesystem fallback
            results_file = SHARED_DIR / "results.json"
            results = []
            if results_file.exists():
                with open(results_file) as f:
                    results = json.load(f)
            results.append(report)
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            self.log(f"reported via filesystem: {status}")

    def poll(self):
        """Poll for messages from the manager (socket mode)."""
        if self._transport:
            self._transport.poll()

    def wait_for_task(self, timeout: float = 30.0) -> Optional[dict]:
        """
        Wait for a task assignment from the manager (socket mode).
        Returns the task data dict, or None on timeout.
        """
        if not self._transport:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            self._transport.poll()
            if self._pending_task:
                task = self._pending_task
                self._pending_task = None
                self.ctx.task_id = task.get("task_id", self.ctx.task_id)
                self.ctx.task_description = task.get("description", "")
                self.ctx.task_context = task.get("context", {})
                return task
            time.sleep(0.05)
        return None

    def cleanup(self):
        """Disconnect transport and release resources."""
        if self._transport:
            self._transport.disconnect()
            self._transport = None

    def log(self, message: str):
        """Instance-scoped logging."""
        print(f"[{self.ctx.instance_id}] {message}")

    # ─── Socket Handlers ─────────────────────────────────────────

    def _handle_task_assign(self, msg: dict):
        """Handle a task assignment from the manager."""
        self._pending_task = msg.get("data", {})
        self.log(f"received task: {self._pending_task.get('description', '?')}")

    # ─── Internal ─────────────────────────────────────────────────

    def _detect_platform(self):
        """Detect which target platform we're running on."""
        import platform as plat
        import os
        from pathlib import Path
        system = plat.system()
        if system == "Linux":
            # Check for WSL before classifying as native Linux
            try:
                proc_version = Path("/proc/version")
                if proc_version.exists():
                    text = proc_version.read_text().lower()
                    if "microsoft" in text or "wsl" in text:
                        self.ctx.platform = "wsl"
                        return
            except Exception:
                pass
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
