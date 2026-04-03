#!/usr/bin/env bash
# .scaffold/generators/scaffold.sh
# Master orchestrator. Shell-based, always works (no runtime deps).
#
# Detects platform, dispatches to the right generator, resolves includes.
# This is the fallback executor when Node/Python aren't available.
#
# Usage:
#   ./scaffold.sh resolve <file>           — resolve #include directives
#   ./scaffold.sh module <name> [lang]     — generate a new module
#   ./scaffold.sh model <name> [base]      — generate an ML model
#   ./scaffold.sh shader <name> [buffers]  — generate a compute shader
#   ./scaffold.sh status                   — show scaffolding status
#   ./scaffold.sh instance <task>          — spawn an AI instance

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAFFOLD_DIR="$(dirname "$SCRIPT_DIR")"

# ─── Platform detection ──────────────────────────────────────────────

detect_platform() {
    case "$(uname -s)" in
        Linux*)
            if [ -n "${WAYLAND_DISPLAY:-}" ]; then
                echo "linux_wayland"
            else
                echo "linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# ─── Runtime detection ───────────────────────────────────────────────

has_node() { command -v node &>/dev/null; }
has_python() { command -v python3 &>/dev/null || command -v python &>/dev/null; }
python_cmd() { command -v python3 &>/dev/null && echo "python3" || echo "python"; }

# ─── Commands ─────────────────────────────────────────────────────────

cmd_resolve() {
    local file="${1:?Usage: scaffold.sh resolve <file>}"
    if has_node; then
        node "$SCRIPT_DIR/resolve.js" "$file" "${@:2}"
    else
        echo "Error: Node.js required for resolve. Install node or resolve manually." >&2
        exit 1
    fi
}

cmd_module() {
    local name="${1:?Usage: scaffold.sh module <name> [lang]}"
    local lang="${2:-python}"
    if has_node; then
        node "$SCRIPT_DIR/gen_module.js" "$name" --lang "$lang"
    else
        # Shell fallback: create basic directory structure
        local dir="src/$name"
        mkdir -p "$dir"
        touch "$dir/__init__.py"
        echo "# $name" > "$dir/$name.py"
        echo "Module '$name' created at $dir (shell fallback)"
    fi
}

cmd_model() {
    local name="${1:?Usage: scaffold.sh model <name> [base]}"
    local base="${2:-base}"
    if has_python; then
        $(python_cmd) "$SCRIPT_DIR/gen_model.py" --name "$name" --base "$base"
    else
        echo "Error: Python required for model generation." >&2
        exit 1
    fi
}

cmd_shader() {
    local name="${1:?Usage: scaffold.sh shader <name> [buffers]}"
    local buffers="${2:-2}"
    if has_python; then
        $(python_cmd) "$SCRIPT_DIR/gen_shader.py" --name "$name" --buffers "$buffers"
    else
        echo "Error: Python required for shader generation." >&2
        exit 1
    fi
}

cmd_status() {
    local platform
    platform=$(detect_platform)
    echo "=== Terraformer Status ==="
    echo "Platform:  $platform"
    echo "Node.js:   $(has_node && echo 'yes' || echo 'no')"
    echo "Python:    $(has_python && echo 'yes' || echo 'no')"
    echo ""
    echo "=== Structure ==="
    echo "Headers:   $(ls "$SCAFFOLD_DIR/headers/"*.h 2>/dev/null | wc -l) files"
    echo "Includes:  $(ls "$SCAFFOLD_DIR/includes/"*.inc 2>/dev/null | wc -l) files"
    echo "Routes:    $(ls "$SCAFFOLD_DIR/routes/"*.route 2>/dev/null | wc -l) files"
    echo "Tables:    $(ls "$SCAFFOLD_DIR/tables/"*.table 2>/dev/null | wc -l) files"
    echo ""
    echo "=== Instances ==="
    if [ -f "$SCAFFOLD_DIR/instances/shared/queue.json" ]; then
        echo "Queue:     $(cat "$SCAFFOLD_DIR/instances/shared/queue.json" | grep -c '"id"' || echo 0) tasks"
    fi
    if [ -f "$SCAFFOLD_DIR/instances/shared/results.json" ]; then
        echo "Results:   $(cat "$SCAFFOLD_DIR/instances/shared/results.json" | grep -c '"instance_id"' || echo 0) completed"
    fi
}

cmd_instance() {
    local task="${1:?Usage: scaffold.sh instance <task_description>}"
    if has_python; then
        $(python_cmd) -c "
from scaffold.instances.manager import InstanceManager
m = InstanceManager()
tid = m.enqueue('$task')
print(f'Task queued: {tid}')
m.run()
"
    else
        echo "Error: Python required for instance management." >&2
        exit 1
    fi
}

# ─── Dispatch ─────────────────────────────────────────────────────────

case "${1:-}" in
    resolve)  cmd_resolve "${@:2}" ;;
    module)   cmd_module "${@:2}" ;;
    model)    cmd_model "${@:2}" ;;
    shader)   cmd_shader "${@:2}" ;;
    status)   cmd_status ;;
    instance) cmd_instance "${@:2}" ;;
    *)
        echo "Terraformer Generator"
        echo ""
        echo "Usage: scaffold.sh <command> [args]"
        echo ""
        echo "Commands:"
        echo "  resolve <file>        Resolve #include directives"
        echo "  module <name> [lang]  Generate a new module"
        echo "  model <name> [base]   Generate a PyTorch model"
        echo "  shader <name> [bufs]  Generate a compute shader"
        echo "  status                Show scaffolding status"
        echo "  instance <task>       Spawn an AI instance"
        ;;
esac
