# Hot Context — Terragraf

## Status: Windows-Native Polish Complete — 382 Tests Passing

Sessions 1-2 of the Windows-native plan are complete. All hooks and generators converted to Python. App code fixed for Windows. CI runs on both Ubuntu and Windows. No bash dependency remains for core functionality.

## What's Done (Session 2)

### Phase 3B: Hooks & Generators Converted to Python
- `hooks/on_enter.py` — platform detection, runtime checks, GPU info, mode detection (all via Python stdlib)
- `hooks/on_commit.py` — pre-commit file checks (temp files, large files), post-commit log
- `hooks/on_generate.py` — auto-format generated files (black/ruff/prettier/clang-format/glslangValidator)
- `hooks/on_instance.py` — instance lifecycle events, sharpen analytics capture
- `generators/scaffold.py` — full Python orchestrator (resolve, module, model, shader, status, instance)
- `.sh` files kept as fallback — `terra.py` tries `.py` first, `.sh` second

### Phase 3C: App Code Fixed for Windows
- `viewer_page.py:38` — binary path uses `.exe` suffix on Windows
- `viewer_page.py:146` — build instructions show `cmake --build` on Windows, `make` on Linux
- `viewer_page.py:174` — `sys.executable` replaces hardcoded `python3`
- `detector.py` — WSL detection via `/proc/version`, `QT_QPA_PLATFORM=offscreen` checked first
- `instance.py` — WSL detected as distinct `"wsl"` platform (not `"linux"`)

### Phase 3D: CI — Windows Runner Added
- `.github/workflows/ci.yml` — matrix now includes `ubuntu-latest` + `windows-latest`
- Python 3.11 + 3.12 on both platforms
- `TERRAGRAF_MODE=ci` set on all runners

### Phase 3E: Documentation Updated
- `ROADMAP.md` — Phase 10 added, "Windows Native Polish" section removed from "What's Next"
- `README.md` — "What's next" trimmed (Windows polish done), test count fixed (382)

## What Was Done (Session 1)

### Socket Transport — Windows Fixed
- `transport.py` — `SO_EXCLUSIVEADDRUSE` on Windows prevents double-bind
- Test timing: retry loops replace fixed `time.sleep()` for cross-platform reliability
- All 16 transport tests pass on Windows

### Language-Aware Output — Complete
- `.scaffold/generators/lang_detect.py` — detects primary language from file patterns
- 22 tests passing

### Python CLI (`terra.py`) — Complete
- Full port of all 15 commands from bash `terra` script
- `terra.cmd` — Windows batch wrapper
- Platform detection via `platform.system()`, `sys.executable` for Python invocations

### Tests — 382 Total
- All passing on Windows native (no WSL)

## What's Next (Session 3)

### End-to-End Debug
- Compile and run ImGui + bridge.py + Qt on a machine with GLFW/Vulkan
- Verify the full loop: Qt launches bridge -> bridge accepts ImGui -> tuning panel populates -> knob changes flow back

### Polish
- Error handling and reconnection logic in bridge clients
- Panel layout persistence in ImGui (save/restore docking state)
- Qt container process management hardening

## Key Files

```
terra.py                               — Python CLI entry point (all 15 commands)
terra.cmd                              — Windows batch wrapper
terra                                  — Bash CLI (Linux backwards compat)
.scaffold/hooks/on_enter.py            — session start hook (Python)
.scaffold/hooks/on_commit.py           — git commit hook (Python)
.scaffold/hooks/on_generate.py         — post-generate hook (Python)
.scaffold/hooks/on_instance.py         — instance lifecycle hook (Python)
.scaffold/generators/scaffold.py       — Python orchestrator (replaces scaffold.sh)
.scaffold/generators/lang_detect.py    — project language detection
.scaffold/instances/transport.py       — socket IPC (Windows SO_EXCLUSIVEADDRUSE fix)
.scaffold/app/viewer_page.py           — ImGui viewer launcher (Windows-fixed)
.scaffold/modes/detector.py            — CI vs App mode detection (WSL-aware)
.scaffold/instances/instance.py        — instance lifecycle (WSL platform detection)
.github/workflows/ci.yml              — CI matrix (Ubuntu + Windows)
```

## Decisions Made
- Python hooks alongside `.sh` originals — gradual migration, `.sh` kept as fallback
- WSL is a distinct platform (`"wsl"`) not `"linux"` — different capabilities and display behavior
- `QT_QPA_PLATFORM=offscreen` checked before Windows display assumption in detector
- CI matrix uses `${{ matrix.os }}` for both Ubuntu and Windows runners

## Debug Notes (for next session)
- ImGui compile still needs a GUI machine with cmake + C++ toolchain
- 13 tests skipped (7 need PySide6 + libEGL, 6 need display server)
- `terra app` needs PySide6: `pip install -r requirements-app.txt`
