#!/usr/bin/env python3
"""
.scaffold/generators/scaffold.py
Master orchestrator — Python port of scaffold.sh.

Detects platform, dispatches to the right generator, resolves includes.
Works natively on Windows and Linux without bash.

Usage:
    python scaffold.py resolve <file>           — resolve #include directives
    python scaffold.py module <name> [lang]     — generate a new module
    python scaffold.py model <name> [base]      — generate an ML model
    python scaffold.py shader <name> [buffers]  — generate a compute shader
    python scaffold.py status                   — show scaffolding status
    python scaffold.py instance <task>          — spawn an AI instance
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
SCAFFOLD_DIR = SCRIPT_DIR.parent


# ─── Platform detection ──────────────────────────────────────────────

def detect_platform():
    system = platform.system()
    if system == "Linux":
        # Check for WSL
        try:
            proc_version = Path("/proc/version")
            if proc_version.exists():
                text = proc_version.read_text().lower()
                if "microsoft" in text or "wsl" in text:
                    return "wsl"
        except Exception:
            pass
        if os.environ.get("WAYLAND_DISPLAY"):
            return "linux_wayland"
        return "linux"
    elif system == "Windows":
        return "windows"
    return "unknown"


# ─── Runtime detection ───────────────────────────────────────────────

def has_node():
    return shutil.which("node") is not None


def has_python():
    return True  # We're already running Python


def python_cmd():
    return sys.executable


# ─── Commands ─────────────────────────────────────────────────────────

def cmd_resolve(args):
    if not args:
        print("Usage: scaffold.py resolve <file>", file=sys.stderr)
        sys.exit(1)
    if has_node():
        subprocess.run(["node", str(SCRIPT_DIR / "resolve.js")] + args)
    else:
        print("Error: Node.js required for resolve. Install node or resolve manually.",
              file=sys.stderr)
        sys.exit(1)


def cmd_module(args):
    if not args:
        print("Usage: scaffold.py module <name> [lang]", file=sys.stderr)
        sys.exit(1)
    name = args[0]
    lang = args[1] if len(args) > 1 else "python"
    if has_node():
        subprocess.run([
            "node", str(SCRIPT_DIR / "gen_module.js"),
            name, "--lang", lang,
        ])
    else:
        # Shell fallback: create basic directory structure
        module_dir = Path("src") / name
        module_dir.mkdir(parents=True, exist_ok=True)
        (module_dir / "__init__.py").touch()
        (module_dir / f"{name}.py").write_text(f"# {name}\n")
        print(f"Module '{name}' created at {module_dir} (Python fallback)")


def cmd_model(args):
    if not args:
        print("Usage: scaffold.py model <name> [base]", file=sys.stderr)
        sys.exit(1)
    name = args[0]
    base = args[1] if len(args) > 1 else "base"
    subprocess.run([
        python_cmd(), str(SCRIPT_DIR / "gen_model.py"),
        "--name", name, "--base", base,
    ])


def cmd_shader(args):
    if not args:
        print("Usage: scaffold.py shader <name> [buffers]", file=sys.stderr)
        sys.exit(1)
    name = args[0]
    buffers = args[1] if len(args) > 1 else "2"
    subprocess.run([
        python_cmd(), str(SCRIPT_DIR / "gen_shader.py"),
        "--name", name, "--buffers", buffers,
    ])


def cmd_status(args):
    plat = detect_platform()
    print("=== Terragraf Status ===")
    print(f"Platform:  {plat}")
    print(f"Node.js:   {'yes' if has_node() else 'no'}")
    print(f"Python:    yes ({sys.executable})")
    print()

    # Count files by type
    print("=== Structure ===")
    headers_dir = SCAFFOLD_DIR / "headers"
    includes_dir = SCAFFOLD_DIR / "includes"
    routes_dir = SCAFFOLD_DIR / "routes"
    tables_dir = SCAFFOLD_DIR / "tables"

    print(f"Headers:   {len(list(headers_dir.glob('*.h')))} files" if headers_dir.exists() else "Headers:   0 files")
    print(f"Includes:  {len(list(includes_dir.glob('*.inc')))} files" if includes_dir.exists() else "Includes:  0 files")
    print(f"Routes:    {len(list(routes_dir.glob('*.route')))} files" if routes_dir.exists() else "Routes:    0 files")
    print(f"Tables:    {len(list(tables_dir.glob('*.table')))} files" if tables_dir.exists() else "Tables:    0 files")
    print()

    # Instance stats
    print("=== Instances ===")
    shared_dir = SCAFFOLD_DIR / "instances" / "shared"

    queue_file = shared_dir / "queue.json"
    if queue_file.exists():
        try:
            data = json.loads(queue_file.read_text())
            count = len(data) if isinstance(data, list) else 0
            print(f"Queue:     {count} tasks")
        except Exception:
            print("Queue:     (error reading)")

    results_file = shared_dir / "results.json"
    if results_file.exists():
        try:
            data = json.loads(results_file.read_text())
            count = len(data) if isinstance(data, list) else 0
            print(f"Results:   {count} completed")
        except Exception:
            print("Results:   (error reading)")


def cmd_instance(args):
    if not args:
        print("Usage: scaffold.py instance <task_description>", file=sys.stderr)
        sys.exit(1)
    task = args[0]
    # Import from scaffold package
    sys.path.insert(0, str(SCAFFOLD_DIR.parent))
    try:
        from scaffold.instances.manager import InstanceManager
        m = InstanceManager()
        tid = m.enqueue(task)
        print(f"Task queued: {tid}")
        m.run()
    except ImportError:
        # Direct path approach
        subprocess.run([
            python_cmd(), "-c",
            f"import sys; sys.path.insert(0, {str(SCAFFOLD_DIR)!r}); "
            f"from instances.manager import InstanceManager; "
            f"m = InstanceManager(); tid = m.enqueue({task!r}); "
            f"print(f'Task queued: {{tid}}'); m.run()"
        ])


# ─── Dispatch ─────────────────────────────────────────────────────────

COMMANDS = {
    "resolve": cmd_resolve,
    "module": cmd_module,
    "model": cmd_model,
    "shader": cmd_shader,
    "status": cmd_status,
    "instance": cmd_instance,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Terragraf Generator")
        print()
        print("Usage: scaffold.py <command> [args]")
        print()
        print("Commands:")
        print("  resolve <file>        Resolve #include directives")
        print("  module <name> [lang]  Generate a new module")
        print("  model <name> [base]   Generate a PyTorch model")
        print("  shader <name> [bufs]  Generate a compute shader")
        print("  status                Show scaffolding status")
        print("  instance <task>       Spawn an AI instance")
        sys.exit(0)

    command = sys.argv[1]
    COMMANDS[command](sys.argv[2:])


if __name__ == "__main__":
    main()
