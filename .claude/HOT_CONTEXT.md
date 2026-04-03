# Hot Context — Thematic Tension Calibration Framework

## Status: Phase 2 Complete + Goals 3 & 4 Done — Tests Passing

All Phase 1 and Phase 2 work is done and verified. 177 tests pass (95 existing + 82 tuning).

## What's Been Done

### Phase 1 — Python Engine
- `.scaffold/tuning/` package — schema, loader, engine, config, tracker, CLI
- 7 starter universe profiles at `.scaffold/tuning/profiles/`
- 6 reaction signature `.inc` fragments at `.scaffold/includes/reactions/`
- Scaffold integration — headers, manifest, routes, deps, terra CLI

### Phase 2 — ImGui Integration & Docs
- `tuning_panel.cpp` — data-driven ImGui panel (profile selector, axes, zones, knobs by domain, behavioral instructions)
- `bridge.py` — 7 tune_* message handlers with ThematicEngine integration
- Build integration (CMakeLists.txt, main.cpp)
- Commands card updated + SVG regenerated (11 categories, TUNING added)
- README + COMMANDS.md updated
- `test_tuning.py` — 82 tests covering schema, loader, engine, axes, zones, knobs, instructions, behavior parsing, state export/import, JSON persistence, CLI state round-trip, and end-to-end CLI integration (subprocess)

## Next Goals

1. **Construct the ImGui app** — uncomment scaffold code in main.cpp and all panels, vendor ImGui/ImPlot/ImNodes/GLFW/glad as submodules, get the app compiling and rendering on Windows 11. Target: all 5 panels render in a docked layout.

2. **TCP bridge connection** — wire the C++ side of the bridge protocol. ImGui panels need a TCP client that connects to bridge.py on localhost:9876, sends/receives length-prefixed JSON. Start with tuning panel as the first live-connected panel.

## Completed Goals

3. **CLI integration test** — 14 subprocess tests covering all `terra tune` subcommands + error paths. `TestCLIIntegration` in `test_tuning.py`.

4. **Tuning state JSON persistence test** — 9 tests for `.tuning_state.json` round-trip through CLI `_load_engine`/`_save_state`. `TestCLIStatePersistence` in `test_tuning.py`. Added `TUNING_STATE_FILE` env var override in `cli.py` for test isolation.

## Key Files

```
.scaffold/tuning/           — Python engine package
.scaffold/imgui/             — ImGui app (panels, bridge, build)
.scaffold/tests/test_tuning.py — 82 tuning tests
terra                        — CLI entry point
```
