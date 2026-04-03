// .scaffold/headers/platform.h
// Platform contract. Declares target environments and their specifics.
// Linux (Wayland) and Windows 10/11 only.

#ifndef PLATFORM_H
#define PLATFORM_H

#include "project.h"

// ─── Target Platforms ────────────────────────────────────────────────

#platform linux_wayland {
    display: "wayland",         // Wayland compositor (not X11)
    shell: "bash",
    path_sep: "/",
    line_end: "LF",
    exec_ext: "",               // No extension for executables
    lib_ext: ".so",
    shader_compiler: "glslangValidator",    // or glslc
    vulkan_loader: "libvulkan.so.1",
    package_manager: "",        // "apt", "dnf", "pacman", "nix"

    // Wayland-specific:
    //   - No X11 fallback. Wayland-native only.
    //   - Use wl_display, wl_surface for windowing
    //   - Vulkan WSI: VK_KHR_wayland_surface
    //   - GPU access: DRM/KMS for direct, Vulkan for compute
}

#platform windows_10 {
    display: "win32",
    shell: "powershell",        // PowerShell 5.1+ or pwsh 7+
    shell_alt: "cmd",           // Fallback
    path_sep: "\\",
    line_end: "CRLF",
    exec_ext: ".exe",
    lib_ext: ".dll",
    shader_compiler: "glslangValidator.exe",
    vulkan_loader: "vulkan-1.dll",

    // Windows-specific:
    //   - Vulkan WSI: VK_KHR_win32_surface
    //   - GPU access: DXGI for enumeration, Vulkan for compute
    //   - Paths: use forward slashes in code, OS normalizes
}

#platform windows_11 {
    // Inherits from windows_10 with additions:
    #extends windows_10

    // Win11 additions:
    //   - DirectStorage for fast GPU data loading
    //   - WSL2 integration for Linux tooling
    //   - Windows Terminal as default
}

// ─── Platform Detection ──────────────────────────────────────────────
// Generators and hooks use these to branch behavior.
//
// Shell:
//   uname -s → "Linux"     → linux_wayland (check $WAYLAND_DISPLAY)
//   uname -s → "MINGW*"    → windows
//   $env:OS  → "Windows_NT" → windows (PowerShell)
//
// Python:
//   import platform; platform.system()  → "Linux" or "Windows"
//   os.environ.get("WAYLAND_DISPLAY")   → non-None = Wayland
//
// C++:
//   #ifdef __linux__    → Linux
//   #ifdef _WIN32       → Windows
//   Check VK_KHR_wayland_surface vs VK_KHR_win32_surface

// ─── Cross-Platform Abstractions ─────────────────────────────────────
// Things that differ between platforms but the AI shouldn't have to
// think about every time.

#crossplatform {
    // File paths: always use forward slashes internally.
    // Generators normalize to OS-native on output.

    // Shell commands: generators emit .sh for Linux, .ps1 for Windows.
    // scaffold.sh detects platform and dispatches.

    // Vulkan: same API on both platforms.
    // Only WSI (window surface) differs. Abstracted in compute/vulkan/.

    // FFT: same Python/C++ code on both platforms.
    // FFTW3 available on both. NumPy/SciPy identical.

    // PyTorch: same on both. CUDA on both.
}

#endif // PLATFORM_H
