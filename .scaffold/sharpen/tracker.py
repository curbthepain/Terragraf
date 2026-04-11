"""
.scaffold/sharpen/tracker.py
Record route/table hits and instance outcomes for self-sharpening.

All data stored in analytics.json. Uses file locking to prevent
corruption from concurrent background writes.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import SharpenConfig

SHARPEN_DIR = Path(__file__).parent
ANALYTICS_FILE = SHARPEN_DIR / "analytics.json"
LOCK_FILE = SHARPEN_DIR / "analytics.lock"
SHARED_DIR = Path(__file__).parent.parent / "instances" / "shared"
RESULTS_FILE = SHARED_DIR / "results.json"
ERRORS_TABLE = Path(__file__).parent.parent / "tables" / "errors.table"

CONFIG = SharpenConfig()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_analytics() -> dict:
    now = _now_iso()
    return {
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "entries": {},
        "unmatched_errors": [],
        "instance_outcomes": [],
    }


def _acquire_lock() -> bool:
    """Acquire file lock. Returns True on success."""
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        # Check for stale lock
        try:
            age = time.time() - os.path.getmtime(str(LOCK_FILE))
            if age > CONFIG.lock_timeout_seconds:
                os.unlink(str(LOCK_FILE))
                return _acquire_lock()
        except OSError:
            pass
        return False


def _release_lock():
    try:
        os.unlink(str(LOCK_FILE))
    except OSError:
        pass


def load_analytics() -> dict:
    if ANALYTICS_FILE.exists():
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    return _empty_analytics()


def save_analytics(data: dict):
    data["updated_at"] = _now_iso()
    tmp = ANALYTICS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(ANALYTICS_FILE)


def record_hit(source_file: str, entry_key: str, query: str):
    """Record a route/table entry hit from the terra CLI."""
    if not _acquire_lock():
        return
    try:
        data = load_analytics()
        key = f"{source_file}::{entry_key.strip()}"
        now = _now_iso()

        if key not in data["entries"]:
            data["entries"][key] = {
                "source_file": source_file,
                "entry_key": entry_key.strip(),
                "hit_count": 0,
                "first_hit": now,
                "last_hit": now,
                "queries": [],
                "outcomes": {"completed": 0, "failed": 0},
            }

        entry = data["entries"][key]
        entry["hit_count"] += 1
        entry["last_hit"] = now

        q = query.strip()
        if q and q not in entry["queries"]:
            entry["queries"].append(q)
            if len(entry["queries"]) > CONFIG.max_queries_per_entry:
                entry["queries"] = entry["queries"][-CONFIG.max_queries_per_entry:]

        save_analytics(data)
    finally:
        _release_lock()


def record_outcome(instance_id: str, task_id: str, status: str,
                   routes_consulted: list, error_text: Optional[str] = None):
    """Record an instance outcome, correlating routes to success/failure."""
    if not _acquire_lock():
        return
    try:
        data = load_analytics()

        # Record the outcome
        outcome = {
            "instance_id": instance_id,
            "task_id": task_id,
            "status": status,
            "routes_consulted": routes_consulted,
            "timestamp": _now_iso(),
        }
        data["instance_outcomes"].append(outcome)
        if len(data["instance_outcomes"]) > CONFIG.max_instance_outcomes:
            data["instance_outcomes"] = data["instance_outcomes"][-CONFIG.max_instance_outcomes:]

        # Correlate routes to outcome
        outcome_key = "completed" if status == "completed" else "failed"
        for route in routes_consulted:
            for key, entry in data["entries"].items():
                if entry["source_file"] == route:
                    entry["outcomes"][outcome_key] = entry["outcomes"].get(outcome_key, 0) + 1

        # Track unmatched errors
        if status == "failed" and error_text:
            normalized = _normalize_error(error_text)
            if not _matches_errors_table(normalized):
                _add_unmatched_error(data, normalized, instance_id, task_id)

        save_analytics(data)
    finally:
        _release_lock()


def record_outcome_from_results(instance_id: str):
    """Read shared/results.json and record outcome for the given instance."""
    if not RESULTS_FILE.exists():
        return
    with open(RESULTS_FILE) as f:
        results = json.load(f)

    for result in reversed(results):
        if result.get("instance_id") == instance_id:
            record_outcome(
                instance_id=instance_id,
                task_id=result.get("task_id", ""),
                status=result.get("status", "unknown"),
                routes_consulted=result.get("routes_consulted", []),
                error_text=result.get("result", {}).get("error") if isinstance(result.get("result"), dict) else None,
            )
            return


def _normalize_error(error_text: str) -> str:
    """Strip variable parts (line numbers, paths, timestamps) from error text."""
    import re
    text = error_text.strip()
    # Strip file paths
    text = re.sub(r'[A-Za-z]:\\[^\s]+', '<path>', text)
    text = re.sub(r'/[^\s:]+', '<path>', text)
    # Strip line numbers
    text = re.sub(r'line \d+', 'line N', text)
    # Strip hex addresses
    text = re.sub(r'0x[0-9a-fA-F]+', '0xN', text)
    return text


def _matches_errors_table(normalized_error: str) -> bool:
    """Check if the error matches any existing errors.table entry."""
    if not ERRORS_TABLE.exists():
        return False
    lower = normalized_error.lower()
    with open(ERRORS_TABLE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pattern = line.split("|")[0].strip().lower()
            if pattern and pattern in lower:
                return True
    return False


def _add_unmatched_error(data: dict, normalized: str, instance_id: str, task_id: str):
    """Add or increment an unmatched error entry."""
    for entry in data["unmatched_errors"]:
        if entry["error_text"] == normalized:
            entry["occurrences"] += 1
            entry["last_seen"] = _now_iso()
            return
    data["unmatched_errors"].append({
        "error_text": normalized,
        "instance_id": instance_id,
        "task_id": task_id,
        "timestamp": _now_iso(),
        "last_seen": _now_iso(),
        "occurrences": 1,
    })
