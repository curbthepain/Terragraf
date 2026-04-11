"""
viewer — ImGui viewer lifecycle management.

Checks mode, builds if needed, starts bridge, launches viewer.

Usage:
    python run.py [launch|build|bridge|status]
    python run.py launch --panel spectrogram
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
TERRA_ROOT = SCAFFOLD.parent

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def find_binary():
    """Find ImGui binary across build configurations."""
    candidates = [
        SCAFFOLD / "imgui" / "build" / "Release" / "terragraf_imgui.exe",
        SCAFFOLD / "imgui" / "build" / "terragraf_imgui.exe",
        SCAFFOLD / "imgui" / "build" / "Debug" / "terragraf_imgui.exe",
        SCAFFOLD / "imgui" / "build" / "terragraf_imgui",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def check_mode():
    """Check we're in app mode."""
    try:
        sys.path.insert(0, str(SCAFFOLD))
        from modes.detector import detect
        info = detect()
        if info.is_ci:
            print(f"  {RED}CI mode — viewer requires App mode{RESET}")
            return False
    except Exception:
        pass
    return True


def cmd_status():
    binary = find_binary()
    cmake = shutil.which("cmake")
    print(f"{BOLD}Viewer Status{RESET}")
    print(f"  cmake    {'yes' if cmake else RED + 'not found' + RESET}")
    print(f"  binary   {GREEN + str(binary) + RESET if binary else YELLOW + 'not built' + RESET}")
    print(f"  bridge   {DIM}.scaffold/imgui/bridge.py{RESET}")
    return 0


def cmd_build():
    return subprocess.run(
        [sys.executable, str(TERRA_ROOT / "terra.py"), "imgui", "build"]
    ).returncode


def cmd_bridge():
    print(f"  {CYAN}Starting bridge server on :9876{RESET}")
    return subprocess.run(
        [sys.executable, str(SCAFFOLD / "imgui" / "bridge.py")]
    ).returncode


def cmd_launch(panel=None):
    if not check_mode():
        return 1

    binary = find_binary()
    if not binary:
        print(f"  {YELLOW}Viewer not built. Building...{RESET}")
        code = cmd_build()
        if code != 0:
            return code
        binary = find_binary()
        if not binary:
            print(f"  {RED}Build failed — no binary found{RESET}")
            return 1

    # Start bridge in background
    print(f"  {CYAN}Starting bridge...{RESET}")
    bridge_proc = subprocess.Popen(
        [sys.executable, str(SCAFFOLD / "imgui" / "bridge.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    # Launch viewer
    print(f"  {CYAN}Launching viewer...{RESET}")
    try:
        subprocess.run([str(binary)])
    finally:
        bridge_proc.terminate()
        bridge_proc.wait(timeout=3)
        print(f"  {DIM}Bridge stopped{RESET}")

    return 0


def cli():
    action = sys.argv[1] if len(sys.argv) > 1 else "launch"
    panel = None
    if "--panel" in sys.argv:
        idx = sys.argv.index("--panel")
        if idx + 1 < len(sys.argv):
            panel = sys.argv[idx + 1]

    if action == "launch":
        return cmd_launch(panel)
    elif action == "build":
        return cmd_build()
    elif action == "bridge":
        return cmd_bridge()
    elif action == "status":
        return cmd_status()
    else:
        print(f"{BOLD}terra viewer{RESET}")
        print(f"  {CYAN}launch{RESET} [--panel P]   build+bridge+launch (default)")
        print(f"  {CYAN}build{RESET}                build ImGui app")
        print(f"  {CYAN}bridge{RESET}               start bridge server only")
        print(f"  {CYAN}status{RESET}               show build/binary status")
        return 0


if __name__ == "__main__":
    sys.exit(cli())
