#!/usr/bin/env bash
# .scaffold/hooks/on_enter.sh
# Runs when an AI enters the scaffolting for the first time in a session.
#
# Purpose: orient the AI, check the environment, report what's available.

set -euo pipefail

SCAFFOLD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Kohala Scaffolting — Session Start ==="
echo ""

# Platform
case "$(uname -s)" in
    Linux*)
        if [ -n "${WAYLAND_DISPLAY:-}" ]; then
            echo "Platform: Linux (Wayland)"
        else
            echo "Platform: Linux"
        fi
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo "Platform: Windows"
        ;;
esac

# Runtimes
echo ""
echo "Runtimes:"
command -v node &>/dev/null && echo "  Node.js: $(node --version)" || echo "  Node.js: not found"
command -v python3 &>/dev/null && echo "  Python: $(python3 --version 2>&1)" || echo "  Python: not found"
command -v cmake &>/dev/null && echo "  CMake: $(cmake --version | head -1)" || echo "  CMake: not found"
command -v glslangValidator &>/dev/null && echo "  GLSL compiler: available" || echo "  GLSL compiler: not found"
command -v git &>/dev/null && echo "  Git: $(git --version)" || echo "  Git: not found"

# GPU
echo ""
echo "GPU:"
if command -v vulkaninfo &>/dev/null; then
    vulkaninfo --summary 2>/dev/null | grep -E "deviceName|apiVersion" | head -2 || echo "  Vulkan: available but no details"
elif command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null || echo "  NVIDIA: available but no details"
else
    echo "  No GPU tools found (vulkaninfo, nvidia-smi)"
fi

echo ""
echo "Read .scaffold/ENTRY.md to begin."
