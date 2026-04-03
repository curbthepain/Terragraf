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
        ;;
    error)
        echo "[instance $INSTANCE_ID] ERROR: $DETAIL" >&2
        ;;
    *)
        echo "Usage: on_instance.sh <spawn|complete|error> <instance_id> <detail>"
        ;;
esac
