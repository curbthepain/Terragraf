"""
.scaffold/instances/manager.py
Instance manager — spawn, track, and coordinate parallel AI instances.

This replaces the traditional agent/sub-agent model with peer instances
that share the same scaffolding structure.

Supports two IPC modes:
  - "filesystem" (default) — queue.json / results.json polling
  - "socket" — TCP transport via transport.py (event-driven, sub-ms dispatch)

Usage:
    manager = InstanceManager()
    manager.enqueue("fix bug in fft module", context={"file": "compute/fft/fft.py"})
    manager.enqueue("add new CNN variant", context={"base": "ml/models/cnn.py"})
    manager.run()       # Spawns instances for queued tasks
    results = manager.collect()  # Waits and returns results
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


SCAFFOLD_DIR = Path(__file__).parent.parent
SHARED_DIR = Path(__file__).parent / "shared"
QUEUE_FILE = SHARED_DIR / "queue.json"
RESULTS_FILE = SHARED_DIR / "results.json"
LOCKS_DIR = SHARED_DIR / "locks"


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    context: dict = field(default_factory=dict)
    status: str = "pending"     # pending, running, completed, failed
    assigned_to: str = ""       # instance ID
    result: Any = None
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


@dataclass
class InstanceInfo:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = ""
    pid: int = 0
    status: str = "idle"        # idle, working, done, error
    started_at: float = 0.0
    finished_at: float = 0.0


class InstanceManager:
    """
    Coordinates multiple AI instances working on the same scaffolding.

    Instead of a parent AI spawning child agents, the manager
    distributes tasks to peer instances that all share the same
    structure (headers, routes, tables, includes).
    """

    def __init__(self, max_concurrent=4, ipc="auto"):
        """
        Args:
            max_concurrent: Max parallel instances.
            ipc: IPC mode — "auto", "socket", or "filesystem".
                 "auto" tries socket first, falls back to filesystem.
        """
        self.max_concurrent = max_concurrent
        self.tasks: list[Task] = []
        self.instances: list[InstanceInfo] = []
        self._ipc_mode = ipc
        self._transport = None

        # Ensure shared directories exist
        SHARED_DIR.mkdir(parents=True, exist_ok=True)
        LOCKS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize queue and results files (filesystem fallback)
        if not QUEUE_FILE.exists():
            self._write_json(QUEUE_FILE, [])
        if not RESULTS_FILE.exists():
            self._write_json(RESULTS_FILE, [])

        # Try socket transport
        if ipc in ("auto", "socket"):
            try:
                from .transport import TransportServer
                self._transport = TransportServer()
                self._transport.on("task_result", self._handle_task_result)
                self._transport.on("register", self._handle_register)
                self._transport.start()
                self._ipc_mode = "socket"
            except Exception as e:
                if ipc == "socket":
                    raise
                self._transport = None
                self._ipc_mode = "filesystem"

    def enqueue(self, description: str, context: dict = None) -> str:
        """Add a task to the queue. Returns task ID."""
        task = Task(description=description, context=context or {})
        self.tasks.append(task)

        if self._ipc_mode == "filesystem":
            self._append_to_queue(task)

        return task.id

    def run(self):
        """
        Spawn instances for pending tasks.

        In socket mode, assigns tasks to connected instances.
        In filesystem mode, writes to queue.json for polling.
        """
        pending = [t for t in self.tasks if t.status == "pending"]
        to_run = pending[:self.max_concurrent]

        for task in to_run:
            instance = InstanceInfo(task_id=task.id, started_at=time.time())
            task.status = "running"
            task.assigned_to = instance.id
            instance.status = "working"
            self.instances.append(instance)

            if self._transport and self._ipc_mode == "socket":
                # Dispatch via socket to connected instances
                self._transport.broadcast({
                    "type": "task_assign",
                    "data": {
                        "task_id": task.id,
                        "description": task.description,
                        "context": task.context,
                    }
                })
                print(f"[manager] dispatched task {task.id} via socket: {task.description}")
            else:
                # Filesystem mode — write to queue
                print(f"[instance {instance.id}] spawned for task: {task.description}")

        self._sync_queue()

    def poll(self):
        """
        Poll for incoming messages (socket mode) or check results file.
        Call this periodically to process completed tasks.
        """
        if self._transport:
            self._transport.poll()
        else:
            self._poll_filesystem()

    def collect(self) -> list[dict]:
        """Read completed results from all instances."""
        self.poll()
        if RESULTS_FILE.exists():
            return self._read_json(RESULTS_FILE)
        return []

    def status(self) -> dict:
        """Get current status of all tasks and instances."""
        status = {
            "tasks": {
                "total": len(self.tasks),
                "pending": sum(1 for t in self.tasks if t.status == "pending"),
                "running": sum(1 for t in self.tasks if t.status == "running"),
                "completed": sum(1 for t in self.tasks if t.status == "completed"),
                "failed": sum(1 for t in self.tasks if t.status == "failed"),
            },
            "instances": {
                "active": sum(1 for i in self.instances if i.status == "working"),
                "max": self.max_concurrent,
            },
            "ipc_mode": self._ipc_mode,
        }
        if self._transport:
            status["instances"]["connected"] = self._transport.connected_count
        return status

    def shutdown(self):
        """Stop the transport server and clean up."""
        if self._transport:
            self._transport.stop()
            self._transport = None

    # ─── Socket Handlers ─────────────────────────────────────────

    def _handle_task_result(self, instance_id: str, msg: dict):
        """Handle a task_result message from an instance."""
        data = msg.get("data", {})
        task_id = data.get("task_id", "")
        result = data.get("result")
        status = data.get("status", "completed")

        for task in self.tasks:
            if task.id == task_id:
                task.status = status
                task.result = result
                task.completed_at = time.time()
                break

        for inst in self.instances:
            if inst.task_id == task_id:
                inst.status = "done" if status == "completed" else "error"
                inst.finished_at = time.time()
                break

        # Also write to results file for persistence
        self._append_result({
            "instance_id": instance_id,
            "task_id": task_id,
            "status": status,
            "result": result,
            "completed_at": time.time(),
        })

        print(f"[manager] task {task_id} {status} from instance {instance_id}")

    def _handle_register(self, instance_id: str, msg: dict):
        """Handle instance registration."""
        print(f"[manager] instance registered: {instance_id}")

    # ─── Filesystem IPC ──────────────────────────────────────────

    def _poll_filesystem(self):
        """Check results.json for completed tasks (filesystem mode)."""
        if not RESULTS_FILE.exists():
            return
        results = self._read_json(RESULTS_FILE)
        for result in results:
            task_id = result.get("task_id", "")
            status = result.get("status", "completed")
            for task in self.tasks:
                if task.id == task_id and task.status == "running":
                    task.status = status
                    task.result = result.get("result")
                    task.completed_at = result.get("completed_at", time.time())

    # ─── File Lock ────────────────────────────────────────────────

    def acquire_lock(self, resource: str) -> bool:
        """
        Acquire a file lock for a resource.
        Prevents two instances from editing the same file.
        """
        lock_file = LOCKS_DIR / f"{resource.replace('/', '_')}.lock"
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({
                "pid": os.getpid(),
                "time": time.time()
            }).encode())
            os.close(fd)
            return True
        except FileExistsError:
            return False

    def release_lock(self, resource: str):
        """Release a file lock."""
        lock_file = LOCKS_DIR / f"{resource.replace('/', '_')}.lock"
        lock_file.unlink(missing_ok=True)

    # ─── Internal ─────────────────────────────────────────────────

    def _append_to_queue(self, task: Task):
        data = self._read_json(QUEUE_FILE)
        # Handle both list format and {"tasks": [...]} format
        if isinstance(data, dict):
            queue = data.get("tasks", [])
        else:
            queue = data
        queue.append(asdict(task))
        self._write_json(QUEUE_FILE, queue)

    def _sync_queue(self):
        self._write_json(QUEUE_FILE, [asdict(t) for t in self.tasks])

    def _append_result(self, result: dict):
        results = []
        if RESULTS_FILE.exists():
            results = self._read_json(RESULTS_FILE)
        results.append(result)
        self._write_json(RESULTS_FILE, results)

    @staticmethod
    def _read_json(path: Path) -> list:
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def _write_json(path: Path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
