# Hot Context — Terragraf

## Status: Qt Container App Wired — 203 Tests Passing

Full Qt container shell with sidebar navigation, debug page, tuning page, viewer page, and settings page. ImGui app updated with debug panel and settings window.

## What's Done

### Python Tuning Engine — Complete
- `.scaffold/tuning/` — schema, loader, engine, config, tracker, CLI
- 8 universe profiles, 6 reaction signatures
- 82 tests passing

### ImGui App — Complete (TCP Bridge + Debug + Settings)
- 7 panels: math, spectrogram, node editor, volume slicer, tuning, **debug**, **settings**
- `bridge_client.h/cpp` — C++ TCP client, background recv thread, main-thread dispatch
- `tuning_panel.cpp` — all bridge_send calls wired
- `debug_panel.cpp` — message log, connection status, FPS/RTT graphs, test message sender
- `settings_panel.cpp` — bridge config, render settings, theme selection, panel visibility
- `main.cpp` — bridge connect on startup, panel visibility via settings, FPS overlay
- `CMakeLists.txt` — all 7 panels + bridge linked
- **Needs debug at home**: compile + run with bridge.py to verify end-to-end

### Python Bridge Server — Complete
- `bridge.py` — TCP server, 7 tune_* handlers + ping/pong + debug_echo

### Socket IPC for Instances — Complete
- `transport.py` — TransportServer + TransportClient, same wire protocol
- `manager.py` — "auto"/"socket"/"filesystem" IPC modes
- `instance.py` — socket transport, wait_for_task(), cleanup()
- 16 transport tests passing

### Qt Container App — Complete
- `.scaffold/app/` — full container shell with 5 pages
- **window.py** — sidebar navigation, page stack, bridge status in statusbar, Ctrl+1-5 shortcuts
- **bridge_client.py** — Qt-native TCP client with signals/slots, message log, stats
- **debug_page.py** — bridge monitor, connection controls, stats, message log with filter
- **tuning_page.py** — profile selector, metadata display, zone buttons, knob widgets (slider/dropdown/toggle/text), behavioral instructions
- **viewer_page.py** — launch/manage bridge.py and ImGui processes, build instructions
- **settings_page.py** — bridge host/port, paths, panel visibility, persistent settings
- **theme.py** — comprehensive dark CI theme (sidebar, buttons, inputs, sliders, combos, tabs, groups, tables, scroll bars, status labels)
- Dark CI aesthetic, monospace, fluid maximize/fullscreen (F10/F11)
- `terra app` command wired in CLI
- 10 tests passing (+ 7 skipped without PySide6)

### Dependency Packaging — Done
- `requirements.txt` — core (numpy, scipy)
- `requirements-dev.txt` — core + pytest
- `requirements-ml.txt` — core + torch
- `requirements-app.txt` — core + PySide6
- CI updated to use `requirements-dev.txt`

### Tests — 203 Total (7 skipped)
- `test_algebra.py` — 10 | `test_fft.py` — 15 | `test_generators.py` — 10
- `test_linalg.py` — 13 | `test_spectral.py` — 10 | `test_stats.py` — 15
- `test_transforms.py` — 10 | `test_tuning.py` — 82
- `test_transport.py` — 16 | `test_app.py` — 17 (10 pass, 7 skip without PySide6)
- Dependencies: numpy, scipy, pytest (via requirements-dev.txt)

## Next Goals

- **ImGui end-to-end debug** — compile + run with bridge.py on a machine with GLFW/Vulkan
- Verify Qt ↔ bridge ↔ ImGui full loop on a GUI-capable machine
- Polish: error handling, reconnection logic, panel layout persistence

## Key Files

```
.scaffold/app/main.py              — Qt app entry point
.scaffold/app/window.py            — main window + sidebar navigation
.scaffold/app/bridge_client.py     — Qt-side TCP bridge client
.scaffold/app/debug_page.py        — debug/monitor page
.scaffold/app/tuning_page.py       — tuning controls page
.scaffold/app/viewer_page.py       — ImGui viewer launcher page
.scaffold/app/settings_page.py     — settings page (persistent)
.scaffold/app/theme.py             — dark CI theme + full stylesheet
.scaffold/imgui/bridge_client.h    — C++ TCP client header
.scaffold/imgui/bridge_client.cpp  — C++ TCP client impl
.scaffold/imgui/bridge.py          — Python TCP server (tune + debug handlers)
.scaffold/imgui/main.cpp           — ImGui app entry (all panels + settings/debug)
.scaffold/imgui/debug_panel.cpp    — ImGui debug panel
.scaffold/imgui/settings_panel.cpp — ImGui settings window
.scaffold/imgui/tuning_panel.cpp   — tuning panel (bridge calls live)
.scaffold/imgui/CMakeLists.txt     — build config (9 source files)
.scaffold/instances/transport.py   — socket IPC transport layer
.scaffold/instances/manager.py     — instance manager
.scaffold/instances/instance.py    — instance lifecycle
requirements.txt                   — core deps (numpy, scipy)
requirements-dev.txt               — dev deps (+ pytest)
requirements-ml.txt                — ML deps (+ torch)
requirements-app.txt               — GUI deps (+ PySide6)
```

## Debug Notes (for home session)

The C++ TCP bridge client + debug/settings panels are written but not compiled yet (no GLFW/ImGui on this machine). To test end-to-end:

1. `cd .scaffold/imgui && mkdir build && cd build && cmake .. && make`
2. In one terminal: `python .scaffold/imgui/bridge.py` (or run via terra)
3. In another: `./build/terragraf_imgui`
4. Debug panel: check connection status, send pings, view RTT graph, monitor message log
5. Settings panel: toggle panels, change theme, configure bridge host/port
6. Tuning panel: profile load, zone switching, knob adjustment
7. Qt app: `python -m app` from .scaffold/ — test sidebar nav, all pages, bridge connect
