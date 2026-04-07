#!/usr/bin/env python3
"""
.scaffold/hooks/on_hot_threshold.py
Central HOT_CONTEXT threshold guard. All trigger surfaces route through here:

  - Claude Code PostToolUse hook (reads JSON envelope from stdin)
  - Every `terra <cmd>` invocation (imported and called from terra.py main)
  - Qt ScaffoldWatcher signal (warn-only)
  - Git pre-commit hook (delegates here when auto_decompose_on_commit is true)

Usage:
    python on_hot_threshold.py [--dry-run] [--no-auto] [--json]

CLI flags:
    --dry-run  Pass through to hot_decompose; do not rewrite files
    --no-auto  Warn-only; do not run decompose even if over threshold
    --json     Print result as JSON (for Claude Code hook consumption);
               also reads PostToolUse envelope from stdin if available

Importable API:
    from hooks.on_hot_threshold import check_threshold
    result = check_threshold(auto_decompose=True)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCAFFOLD = Path(__file__).resolve().parent.parent
HOT_CONTEXT = SCAFFOLD / "HOT_CONTEXT.md"
MANIFEST = SCAFFOLD / "MANIFEST.toml"
SKILL_PATH = SCAFFOLD / "skills" / "hot_decompose" / "run.py"
LOCKFILE = SCAFFOLD / ".hot_decompose.lock"
LOCK_STALE_SECONDS = 60

DEFAULT_MAX_LINES = 80


def _decompose_in_progress() -> bool:
    """Return True if a fresh hot_decompose lockfile exists.

    Mirrors `hot_decompose.run.is_locked()` so the hook can short-circuit
    re-entry without importing the skill (which would itself trigger
    sys.path mutations). Stale locks (> LOCK_STALE_SECONDS) are ignored.
    """
    if not LOCKFILE.exists():
        return False
    try:
        import time
        age = time.time() - LOCKFILE.stat().st_mtime
        return age <= LOCK_STALE_SECONDS
    except Exception:
        return False


def _read_threshold() -> int:
    """Read [hot_context] max_lines from MANIFEST.toml."""
    if not MANIFEST.exists():
        return DEFAULT_MAX_LINES
    try:
        data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        return int(data.get("hot_context", {}).get("max_lines", DEFAULT_MAX_LINES))
    except Exception:
        return DEFAULT_MAX_LINES


def _harness_summary() -> tuple[str, str]:
    """Return (harness_name, model_id). Lazy import — never fail."""
    try:
        # Add scaffold root so `llm` is importable
        if str(SCAFFOLD) not in sys.path:
            sys.path.insert(0, str(SCAFFOLD))
        from llm.harness import detect  # type: ignore
        info = detect()
        return info.name, info.model
    except Exception:
        return "unknown", "unknown"


def _run_decompose_in_process(dry_run: bool) -> tuple[bool, int, str]:
    """
    Invoke skills/hot_decompose/run.py:cmd_decompose in-process.
    Returns (success, moved_count, captured_output).
    """
    if not SKILL_PATH.exists():
        return False, 0, f"hot_decompose skill not found at {SKILL_PATH}"

    # Ensure skills dir importable
    skills_dir = SKILL_PATH.parent
    if str(skills_dir) not in sys.path:
        sys.path.insert(0, str(skills_dir))

    # Capture stdout so we can extract the routed-count line
    buf = StringIO()
    moved = 0
    success = False
    try:
        # Import the module by file path to avoid name collisions
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hot_decompose_skill", str(SKILL_PATH)
        )
        if spec is None or spec.loader is None:
            return False, 0, "could not load hot_decompose module"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with redirect_stdout(buf), redirect_stderr(buf):
            rc = mod.cmd_decompose(dry_run=dry_run)
        success = rc == 0
        out = buf.getvalue()
        # Extract "Routed: N block(s)" — strip ANSI first
        import re
        clean = re.sub(r"\x1b\[[0-9;]*m", "", out)
        m = re.search(r"Routed:\s+(\d+)\s+block", clean)
        if m:
            moved = int(m.group(1))
        return success, moved, out
    except Exception as e:
        return False, 0, f"hot_decompose failed: {e}\n{buf.getvalue()}"


def check_threshold(
    *, auto_decompose: bool = True, dry_run: bool = False
) -> dict[str, Any]:
    """
    Inspect HOT_CONTEXT.md against threshold. Optionally run decompose.

    Returns a dict suitable for JSON serialization:
        {
          "over": bool,
          "lines": int,
          "threshold": int,
          "decomposed": bool,    # True if decompose actually ran
          "moved": int,          # blocks moved out (0 if not run)
          "harness": str,
          "model": str,
        }
    """
    threshold = _read_threshold()

    if not HOT_CONTEXT.exists():
        harness, model = _harness_summary()
        return {
            "over": False,
            "lines": 0,
            "threshold": threshold,
            "decomposed": False,
            "moved": 0,
            "harness": harness,
            "model": model,
            "note": "HOT_CONTEXT.md missing",
        }

    lines = len(HOT_CONTEXT.read_text(encoding="utf-8").splitlines())
    over = lines > threshold

    decomposed = False
    moved = 0
    decompose_output = ""
    locked = False

    if over and auto_decompose:
        if _decompose_in_progress():
            # Re-entry guard: another decompose is already running (or we're
            # being called recursively from inside one). Skip silently to
            # avoid mutating HOT_CONTEXT mid-operation and breaking the
            # caller's read-then-edit cycle.
            locked = True
        else:
            success, moved, decompose_output = _run_decompose_in_process(dry_run=dry_run)
            decomposed = success and not dry_run

    harness, model = _harness_summary()

    result: dict[str, Any] = {
        "over": over,
        "lines": lines,
        "threshold": threshold,
        "decomposed": decomposed,
        "moved": moved,
        "locked": locked,
        "harness": harness,
        "model": model,
    }
    if decompose_output and os.environ.get("TERRAGRAF_HOT_DEBUG"):
        result["debug_output"] = decompose_output

    if over:
        if locked:
            action = "skipped (decompose already in progress)"
        elif decomposed:
            action = f"decomposed {moved} blocks"
        else:
            action = "run: terra hot decompose"
        msg = (
            f"[hot_context] {lines}/{threshold} over → {action} "
            f"(harness={harness} model={model})"
        )
        print(msg, file=sys.stderr)

    return result


def _read_stdin_envelope() -> dict[str, Any] | None:
    """
    Read a Claude Code PostToolUse JSON envelope from stdin if available.
    Returns the parsed dict or None if stdin is empty / not JSON.
    """
    if sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        return json.loads(raw)
    except Exception:
        return None


def _envelope_targets_hot_context(envelope: dict[str, Any] | None) -> bool:
    """
    Inspect a PostToolUse envelope to decide whether to act.
    Returns True iff the tool was a MUTATING op (Edit/Write/MultiEdit) on
    HOT_CONTEXT.md. Read is intentionally excluded — reading the file
    should never trigger a decompose, and the read-then-edit cycle that
    Claude Code uses to modify files would otherwise be broken by the
    hook firing on the Read step and mutating the file before the Edit.
    Defaults to True when envelope is None — caller is a non-hook surface.
    """
    if envelope is None:
        return True
    tool = envelope.get("tool_name") or envelope.get("tool") or ""
    tool_input = envelope.get("tool_input") or {}
    if tool not in ("Edit", "Write", "MultiEdit"):
        return False
    path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or ""
    )
    return "HOT_CONTEXT.md" in str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HOT_CONTEXT threshold guard — central trigger point"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Pass through to hot_decompose; do not rewrite")
    parser.add_argument("--no-auto", action="store_true",
                        help="Warn only; do not run decompose")
    parser.add_argument("--json", action="store_true",
                        help="Print result dict as JSON on stdout")
    args = parser.parse_args()

    envelope = _read_stdin_envelope() if args.json else None

    if envelope is not None and not _envelope_targets_hot_context(envelope):
        # Tool call wasn't on HOT_CONTEXT — silent no-op
        if args.json:
            print(json.dumps({"skipped": True, "reason": "tool not on HOT_CONTEXT"}))
        return 0

    result = check_threshold(
        auto_decompose=not args.no_auto,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
