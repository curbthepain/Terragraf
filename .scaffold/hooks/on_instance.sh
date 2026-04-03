#!/usr/bin/env bash
# .scaffold/hooks/on_instance.sh
# Runs when an AI instance spawns or completes.
#
# Usage:
#   on_instance.sh spawn <instance_id> <task_description>
#   on_instance.sh complete <instance_id> <status>

set -euo pipefail

EVENT="${1:-}"
INSTANCE_ID="${2:-unknown}"
DETAIL="${3:-}"

case "$EVENT" in
    spawn)
        echo "[instance $INSTANCE_ID] spawned: $DETAIL"
        ;;
    complete)
        echo "[instance $INSTANCE_ID] completed: $DETAIL"
        # Capture analytics for self-sharpening
        SCAFFOLD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
        if command -v python3 &>/dev/null || command -v python &>/dev/null; then
            PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
            "$PYTHON_CMD" -c "
import sys; sys.path.insert(0, '$SCAFFOLD_DIR')
from sharpen.tracker import record_outcome_from_results
record_outcome_from_results('$INSTANCE_ID')
" 2>/dev/null || true
        fi
        ;;
    error)
        echo "[instance $INSTANCE_ID] ERROR: $DETAIL" >&2
        ;;
    *)
        echo "Usage: on_instance.sh <spawn|complete|error> <instance_id> <detail>"
        ;;
esac
