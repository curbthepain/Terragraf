#!/usr/bin/env bash
# .scaffold/hooks/on_commit.sh
# Runs around git commits. Can be used as a pre-commit or post-commit hook.
#
# Usage:
#   As pre-commit:  ln -s ../../.scaffold/hooks/on_commit.sh .git/hooks/pre-commit
#   As post-commit: ln -s ../../.scaffold/hooks/on_commit.sh .git/hooks/post-commit

set -euo pipefail

HOOK_TYPE="${1:-pre}"

case "$HOOK_TYPE" in
    pre)
        echo "[scaffold] pre-commit check"

        # Check for debug/temp files that shouldn't be committed
        STAGED=$(git diff --cached --name-only)
        for file in $STAGED; do
            case "$file" in
                *.pyc|__pycache__/*|.env|*.log|*.tmp)
                    echo "Warning: staging temp/sensitive file: $file" >&2
                    ;;
            esac
        done

        # Check for large files
        for file in $STAGED; do
            if [ -f "$file" ]; then
                size=$(wc -c < "$file" 2>/dev/null || echo 0)
                if [ "$size" -gt 1048576 ]; then  # 1MB
                    echo "Warning: large file (${size} bytes): $file" >&2
                fi
            fi
        done
        ;;
    post)
        echo "[scaffold] post-commit"
        git log --oneline -1
        ;;
esac
