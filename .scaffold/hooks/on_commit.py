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
import tomllib
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

    # Check HOT_CONTEXT size
    scaffold = Path(__file__).resolve().parent.parent
    hot_context = scaffold / "HOT_CONTEXT.md"
    manifest = scaffold / "MANIFEST.toml"
    if hot_context.exists():
        line_count = len(hot_context.read_text(encoding="utf-8").splitlines())
        max_lines = 80
        auto_decompose = False
        if manifest.exists():
            try:
                data = tomllib.loads(manifest.read_text(encoding="utf-8"))
                hc = data.get("hot_context", {})
                max_lines = hc.get("max_lines", 80)
                auto_decompose = hc.get("auto_decompose_on_commit", False)
            except Exception:
                pass
        if line_count > max_lines:
            print(f"Warning: HOT_CONTEXT.md is {line_count} lines "
                  f"(threshold: {max_lines}). Run: terra hot decompose",
                  file=sys.stderr)
            if auto_decompose:
                print("[scaffold] auto-running: terra hot decompose",
                      file=sys.stderr)
                subprocess.run(
                    [sys.executable, str(scaffold / "skills" / "hot_decompose" / "run.py")],
                    cwd=str(scaffold.parent),
                )


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
