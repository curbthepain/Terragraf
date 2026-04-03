"""
.scaffold/instances/manager.py
Instance manager — spawn, track, and coordinate parallel AI instances.

This replaces the traditional agent/sub-agent model with peer instances
that share the same scaffolding structure.

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
from typing import Any
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

    def __init__(self, max_concurrent=4):
        self.max_concurrent = max_concurrent
        self.tasks: list[Task] = []
        self.instances: list[InstanceInfo] = []

        # Ensure shared directories exist
        SHARED_DIR.mkdir(parents=True, exist_ok=True)
        LOCKS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize queue and results files
        if not QUEUE_FILE.exists():
            self._write_json(QUEUE_FILE, [])
        if not RESULTS_FILE.exists():
            self._write_json(RESULTS_FILE, [])

    def enqueue(self, description: str, context: dict = None) -> str:
        """Add a task to the queue. Returns task ID."""
        task = Task(description=description, context=context or {})
        self.tasks.append(task)
        self._append_to_queue(task)
        return task.id

    def run(self):
        """
        Spawn instances for pending tasks.

        In a real implementation, this would:
        1. Read pending tasks from queue.json
        2. Spawn AI processes (each with their own context window)
        3. Each process reads the scaffolding independently
        4. Each process works on its assigned task
        5. Each process writes results to results.json
        """
        pending = [t for t in self.tasks if t.status == "pending"]
        to_run = pending[:self.max_concurrent]

        for task in to_run:
            instance = InstanceInfo(task_id=task.id, started_at=time.time())
            task.status = "running"
            task.assigned_to = instance.id
            instance.status = "working"
            self.instances.append(instance)

            # In production: subprocess.Popen() or equivalent
            # The spawned process reads ENTRY.md, follows routes,
            # and works on the task.
            print(f"[instance {instance.id}] spawned for task: {task.description}")

        self._sync_queue()

    def collect(self) -> list[dict]:
        """Read completed results from all instances."""
        if RESULTS_FILE.exists():
            return self._read_json(RESULTS_FILE)
        return []

    def status(self) -> dict:
        """Get current status of all tasks and instances."""
        return {
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
            }
        }

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
        queue = self._read_json(QUEUE_FILE)
        queue.append(asdict(task))
        self._write_json(QUEUE_FILE, queue)

    def _sync_queue(self):
        self._write_json(QUEUE_FILE, [asdict(t) for t in self.tasks])

    @staticmethod
    def _read_json(path: Path) -> list:
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def _write_json(path: Path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
