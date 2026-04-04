"""
instance_dispatch — Parallel instance orchestration.

Manages the task queue and instance lifecycle: enqueue tasks, check status,
collect results.

Usage:
    python run.py enqueue <description>
    python run.py status
    python run.py collect
    python run.py clear
"""

import json
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCAFFOLD))

SHARED = SCAFFOLD / "instances" / "shared"
QUEUE_FILE = SHARED / "queue.json"
RESULTS_FILE = SHARED / "results.json"

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def cmd_enqueue(description):
    import hashlib, time
    task_id = hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:12]

    if QUEUE_FILE.exists():
        data = json.loads(QUEUE_FILE.read_text())
    else:
        data = []
    if isinstance(data, dict):
        data = data.get("tasks", [])

    task = {
        "id": task_id,
        "description": description,
        "context": {},
        "status": "pending",
        "assigned_to": None,
        "result": None,
        "created_at": __import__("time").time(),
        "completed_at": 0.0,
    }
    data.append(task)
    QUEUE_FILE.write_text(json.dumps(data, indent=2))
    print(f"  {GREEN}Enqueued{RESET} {task_id}  {description}")
    return 0


def cmd_status():
    print(f"{BOLD}Instance Status{RESET}")
    print()

    # Queue
    if QUEUE_FILE.exists():
        queue = json.loads(QUEUE_FILE.read_text())
        if isinstance(queue, dict):
            queue = queue.get("tasks", [])
        pending = sum(1 for t in queue if t.get("status") == "pending")
        running = sum(1 for t in queue if t.get("status") == "running")
        print(f"  Queue: {pending} pending, {running} running")
        for t in queue:
            sid = t.get("id", "?")[:8]
            status = t.get("status", "?")
            desc = t.get("description", "?")
            color = {"completed": GREEN, "pending": YELLOW, "running": CYAN}.get(status, RESET)
            print(f"    {color}{status:<10}{RESET} {sid}  {desc}")
    else:
        print(f"  Queue: {DIM}empty{RESET}")

    # Results
    if RESULTS_FILE.exists():
        results = json.loads(RESULTS_FILE.read_text())
        print(f"  Results: {len(results)} completed")
    else:
        print(f"  Results: {DIM}none{RESET}")

    # IPC mode
    print()
    try:
        from modes.detector import detect
        info = detect()
        ipc = "socket" if info.can("instances_socket") else "filesystem"
        print(f"  IPC: {ipc}")
    except Exception:
        print(f"  IPC: {DIM}auto{RESET}")

    return 0


def cmd_collect():
    if not RESULTS_FILE.exists():
        print(f"  {DIM}No results{RESET}")
        return 0

    results = json.loads(RESULTS_FILE.read_text())
    print(f"{BOLD}Completed Results{RESET} ({len(results)})")
    for r in results[-10:]:  # Last 10
        tid = r.get("task_id", "?")[:8]
        status = r.get("status", "?")
        result = r.get("result", "")
        color = GREEN if status == "completed" else RED
        print(f"  {color}{status:<10}{RESET} {tid}  {result}")

    return 0


def cmd_clear():
    if QUEUE_FILE.exists():
        QUEUE_FILE.write_text("[]")
    if RESULTS_FILE.exists():
        RESULTS_FILE.write_text("[]")
    print(f"  {GREEN}Queue and results cleared{RESET}")
    return 0


def cli():
    if len(sys.argv) < 2:
        print(f"{BOLD}terra dispatch{RESET}")
        print(f"  {CYAN}enqueue{RESET} <desc>   add task to queue")
        print(f"  {CYAN}status{RESET}           show queue and instances")
        print(f"  {CYAN}collect{RESET}          show completed results")
        print(f"  {CYAN}clear{RESET}            clear queue and results")
        return 0

    action = sys.argv[1]
    if action == "enqueue":
        desc = " ".join(sys.argv[2:])
        if not desc:
            print("Usage: terra dispatch enqueue <description>")
            return 1
        return cmd_enqueue(desc)
    elif action == "status":
        return cmd_status()
    elif action == "collect":
        return cmd_collect()
    elif action == "clear":
        return cmd_clear()
    else:
        # Treat everything as enqueue description
        return cmd_enqueue(" ".join(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(cli())
