"""
.scaffold/tuning/tracker.py
Record tuning session outcomes for self-sharpening.

Mirrors sharpen/tracker.py file-locking pattern.
Tracks: which profiles get loaded, which knobs get adjusted,
which zone transitions happen, and session quality signals.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import TuningConfig


SCAFFOLD_DIR = Path(__file__).parent.parent
ANALYTICS_FILE = SCAFFOLD_DIR / "tuning" / "analytics.json"
LOCK_FILE = ANALYTICS_FILE.with_suffix(".lock")


# ── File Locking (mirrors sharpen/tracker.py) ────────────────────────

def _acquire_lock(timeout: float = 5.0) -> bool:
    """Acquire file lock for analytics. Returns True on success."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            time.sleep(0.05)
    return False


def _release_lock():
    """Release the analytics file lock."""
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


# ── Analytics I/O ────────────────────────────────────────────────────

def load_analytics() -> dict:
    """Load analytics data from disk."""
    if not ANALYTICS_FILE.exists():
        return _new_analytics()
    try:
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _new_analytics()


def save_analytics(data: dict):
    """Save analytics data to disk."""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _new_analytics() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "profile_loads": {},
        "knob_adjustments": {},
        "zone_transitions": [],
        "session_outcomes": [],
    }


# ── Recording Functions ──────────────────────────────────────────────

def record_profile_load(profile_name: str):
    """Record that a profile was loaded."""
    if not _acquire_lock():
        return
    try:
        data = load_analytics()
        loads = data.setdefault("profile_loads", {})
        if profile_name not in loads:
            loads[profile_name] = {
                "count": 0,
                "first_load": datetime.now(timezone.utc).isoformat(),
                "last_load": "",
            }
        loads[profile_name]["count"] += 1
        loads[profile_name]["last_load"] = datetime.now(timezone.utc).isoformat()
        save_analytics(data)
    finally:
        _release_lock()


def record_knob_adjustment(
    profile_name: str,
    knob_id: str,
    old_value: object,
    new_value: object,
):
    """Record a knob adjustment."""
    if not _acquire_lock():
        return
    try:
        data = load_analytics()
        adjustments = data.setdefault("knob_adjustments", {})
        key = f"{profile_name}::{knob_id}"
        if key not in adjustments:
            adjustments[key] = {
                "profile": profile_name,
                "knob_id": knob_id,
                "adjustment_count": 0,
                "last_values": [],
            }
        entry = adjustments[key]
        entry["adjustment_count"] += 1
        # Keep last 20 values
        entry["last_values"].append({
            "from": _serialize_value(old_value),
            "to": _serialize_value(new_value),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(entry["last_values"]) > 20:
            entry["last_values"] = entry["last_values"][-20:]
        save_analytics(data)
    finally:
        _release_lock()


def record_zone_transition(
    profile_name: str,
    from_zone: Optional[str],
    to_zone: Optional[str],
):
    """Record a zone transition."""
    if not _acquire_lock():
        return
    try:
        data = load_analytics()
        transitions = data.setdefault("zone_transitions", [])
        transitions.append({
            "profile": profile_name,
            "from": from_zone,
            "to": to_zone,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Cap at max_history
        max_entries = TuningConfig().max_history_entries
        if len(transitions) > max_entries:
            data["zone_transitions"] = transitions[-max_entries:]
        save_analytics(data)
    finally:
        _release_lock()


def record_session_outcome(
    profile_name: str,
    state_snapshot: dict,
    outcome: str,
    score: Optional[float] = None,
    notes: str = "",
):
    """Record a session outcome for self-sharpening correlation.

    Args:
        profile_name: Active profile.
        state_snapshot: Engine state at time of outcome.
        outcome: "kept_promise" | "broke_promise" | "partial"
        score: Optional quality score (0.0 to 1.0).
        notes: Freeform notes about where the promise held/broke.
    """
    if not _acquire_lock():
        return
    try:
        data = load_analytics()
        outcomes = data.setdefault("session_outcomes", [])
        outcomes.append({
            "profile": profile_name,
            "state": state_snapshot,
            "outcome": outcome,
            "score": score,
            "notes": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        max_entries = TuningConfig().max_history_entries
        if len(outcomes) > max_entries:
            data["session_outcomes"] = outcomes[-max_entries:]
        save_analytics(data)
    finally:
        _release_lock()


def _serialize_value(value: object) -> object:
    """Make a value JSON-serializable."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    return str(value)
