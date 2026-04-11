#!/usr/bin/env python3
"""
.scaffold/hooks/on_instance.py
Runs when an AI instance spawns or completes.

Usage:
    python on_instance.py spawn <instance_id> <task_description>
    python on_instance.py complete <instance_id> <status>
    python on_instance.py error <instance_id> <detail>
"""

import sys
from pathlib import Path


SCAFFOLD_DIR = Path(__file__).parent.parent


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    instance_id = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    detail = sys.argv[3] if len(sys.argv) > 3 else ""

    if event == "spawn":
        print(f"[instance {instance_id}] spawned: {detail}")

    elif event == "complete":
        print(f"[instance {instance_id}] completed: {detail}")
        # Capture analytics for self-sharpening
        try:
            sys.path.insert(0, str(SCAFFOLD_DIR))
            from sharpen.tracker import record_outcome_from_results
            record_outcome_from_results(instance_id)
        except Exception:
            pass

    elif event == "error":
        print(f"[instance {instance_id}] ERROR: {detail}", file=sys.stderr)

    else:
        print(f"Usage: {sys.argv[0]} <spawn|complete|error> <instance_id> <detail>")


if __name__ == "__main__":
    main()
