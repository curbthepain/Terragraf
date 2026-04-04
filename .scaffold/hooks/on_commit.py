#!/usr/bin/env python3
"""
.scaffold/hooks/on_commit.py
Runs around git commits. Can be used as a pre-commit or post-commit hook.

Usage:
    python on_commit.py pre     # pre-commit checks
    python on_commit.py post    # post-commit log
"""

import subprocess
import sys
from pathlib import Path

# Patterns that shouldn't be committed
_BAD_PATTERNS = (".pyc", "__pycache__", ".env", ".log", ".tmp")

# 1 MB threshold
_MAX_FILE_SIZE = 1_048_576


def _pre_commit():
    print("[scaffold] pre-commit check")

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True,
    )
    staged = [f for f in result.stdout.strip().splitlines() if f]

    # Check for debug/temp files
    for filepath in staged:
        for pattern in _BAD_PATTERNS:
            if pattern in filepath:
                print(f"Warning: staging temp/sensitive file: {filepath}",
                      file=sys.stderr)
                break

    # Check for large files
    for filepath in staged:
        p = Path(filepath)
        if p.exists():
            size = p.stat().st_size
            if size > _MAX_FILE_SIZE:
                print(f"Warning: large file ({size} bytes): {filepath}",
                      file=sys.stderr)


def _post_commit():
    print("[scaffold] post-commit")
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        capture_output=True, text=True,
    )
    print(result.stdout.strip())


def main():
    hook_type = sys.argv[1] if len(sys.argv) > 1 else "pre"

    if hook_type == "pre":
        _pre_commit()
    elif hook_type == "post":
        _post_commit()
    else:
        print(f"Usage: {sys.argv[0]} <pre|post>")


if __name__ == "__main__":
    main()
