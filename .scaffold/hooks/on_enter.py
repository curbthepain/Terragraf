#!/usr/bin/env python3
"""
.scaffold/hooks/on_enter.py
Runs when an AI enters the scaffolding for the first time in a session.

Purpose: orient the AI, check the environment, report what's available.
"""

import os
import platform
import shutil
import subprocess
import sys


def _get_version(cmd, args=None):
    """Run a command and return its first line of output, or None."""
    try:
        result = subprocess.run(
            [cmd] + (args or []),
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip().split("\n")[0]
    except Exception:
        return None


def main():
    print("=== Terragraf — Session Start ===")
    print()

    # Platform
    system = platform.system()
    if system == "Linux":
        if os.environ.get("WAYLAND_DISPLAY"):
            print("Platform: Linux (Wayland)")
        else:
            print("Platform: Linux")
    elif system == "Windows":
        print("Platform: Windows")
    else:
        print(f"Platform: {system}")

    # Runtimes
    print()
    print("Runtimes:")

    if shutil.which("node"):
        print(f"  Node.js: {_get_version('node', ['--version'])}")
    else:
        print("  Node.js: not found")

    print(f"  Python: {platform.python_version()} ({sys.executable})")

    if shutil.which("cmake"):
        print(f"  CMake: {_get_version('cmake', ['--version'])}")
    else:
        print("  CMake: not found")

    if shutil.which("glslangValidator"):
        print("  GLSL compiler: available")
    else:
        print("  GLSL compiler: not found")

    if shutil.which("git"):
        print(f"  Git: {_get_version('git', ['--version'])}")
    else:
        print("  Git: not found")

    # GPU
    print()
    print("GPU:")
    if shutil.which("vulkaninfo"):
        try:
            result = subprocess.run(
                ["vulkaninfo", "--summary"],
                capture_output=True, text=True, timeout=10,
            )
            lines = [
                l.strip() for l in result.stdout.splitlines()
                if "deviceName" in l or "apiVersion" in l
            ]
            for line in lines[:2]:
                print(f"  {line}")
            if not lines:
                print("  Vulkan: available but no details")
        except Exception:
            print("  Vulkan: available but no details")
    elif shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10,
            )
            out = result.stdout.strip()
            print(f"  {out}" if out else "  NVIDIA: available but no details")
        except Exception:
            print("  NVIDIA: available but no details")
    else:
        print("  No GPU tools found (vulkaninfo, nvidia-smi)")

    # Mode detection
    print()
    print("Mode:")
    terragraf_mode = os.environ.get("TERRAGRAF_MODE", "").strip().lower()
    if terragraf_mode:
        print(f"  Explicit: {terragraf_mode} (TERRAGRAF_MODE env var)")
    elif os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        print("  Detected: ci (CI environment variables present)")
    elif system == "Windows":
        print("  Detected: app (Windows interactive session)")
    elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        print("  Detected: app (display server available)")
    else:
        print("  Detected: ci (no display server)")

    print()
    print("Read .scaffold/ENTRY.md to begin.")


if __name__ == "__main__":
    main()
