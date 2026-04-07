"""
hot_context — Read, display, or update the session hot context.

The hot context file (.scaffold/HOT_CONTEXT.md) captures what was done in recent
sessions, what's in progress, key files, debug notes, and next steps. It lets
a new AI session orient itself instantly instead of re-exploring the codebase.

Usage:
    python run.py [show|update|reset|path]

    show    (default) Print the current hot context
    update  Append a timestamped session marker
    reset   Clear and write a fresh template
    path    Print the file path only
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TERRA_ROOT = Path(__file__).resolve().parent.parent.parent.parent
HOT_CONTEXT = TERRA_ROOT / ".scaffold" / "HOT_CONTEXT.md"

# ANSI
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

TEMPLATE = """\
# Hot Context — Terragraf

## Status: <describe current state>

## What's Done (This Session)

## Key Files (Updated)

```
```

## Debug Notes

## Plan: Next Session

## Decisions Made

## Backlog
"""


def cmd_show():
    if not HOT_CONTEXT.exists():
        print(f"  {DIM}No hot context found at {HOT_CONTEXT}{RESET}")
        print(f"  {DIM}Run: terra hot reset{RESET}")
        return 0

    content = HOT_CONTEXT.read_text(encoding="utf-8")
    # Print with light formatting
    for line in content.splitlines():
        if line.startswith("# "):
            print(f"{BOLD}{line}{RESET}")
        elif line.startswith("## "):
            print(f"{CYAN}{line}{RESET}")
        elif line.startswith("### "):
            print(f"{GREEN}{line}{RESET}")
        elif line.startswith("- ") and "✓" in line:
            print(f"  {GREEN}{line}{RESET}")
        elif line.startswith("- ") and ("✗" in line or "!" in line):
            print(f"  {YELLOW}{line}{RESET}")
        else:
            print(line)
    return 0


def cmd_update():
    if not HOT_CONTEXT.exists():
        print(f"  {YELLOW}No hot context to update. Run: terra hot reset{RESET}")
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    marker = f"\n---\n_Session marker: {now}_\n"

    with open(HOT_CONTEXT, "a", encoding="utf-8") as f:
        f.write(marker)

    print(f"  {GREEN}Session marker added{RESET} ({now})")
    return 0


def cmd_reset():
    HOT_CONTEXT.parent.mkdir(parents=True, exist_ok=True)
    HOT_CONTEXT.write_text(TEMPLATE, encoding="utf-8")
    print(f"  {GREEN}Hot context reset{RESET} at {HOT_CONTEXT}")
    return 0


def cmd_path():
    print(str(HOT_CONTEXT))
    return 0


def cli():
    parser = argparse.ArgumentParser(description="Hot context management")
    parser.add_argument("action", nargs="?", default="show",
                        choices=["show", "update", "reset", "path"],
                        help="Action to perform (default: show)")
    args = parser.parse_args()

    actions = {
        "show": cmd_show,
        "update": cmd_update,
        "reset": cmd_reset,
        "path": cmd_path,
    }
    return actions[args.action]()


if __name__ == "__main__":
    sys.exit(cli())
