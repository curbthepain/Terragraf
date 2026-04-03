# Hot Context — Terragraf

## Status: TCP Bridge + Socket IPC Done — 193 Tests Passing

All work through socket IPC is complete and tested. 193 tests pass across 9 suites.

## What's Done

### Python Tuning Engine — Complete
- `.scaffold/tuning/` — schema, loader, engine, config, tracker, CLI
- 8 universe profiles, 6 reaction signatures
- 82 tests passing

### ImGui App — Complete (TCP Bridge Wired)
- 5 panels: math, spectrogram, node editor, volume slicer, tuning
- `bridge_client.h/cpp` — C++ TCP client, background recv thread, main-thread dispatch
- `tuning_panel.cpp` — all bridge_send calls wired (tune_list, tune_load, tune_zone, tune_set_knob, etc.)
- `main.cpp` — bridge connect on startup, poll each frame, disconnect on cleanup
- `CMakeLists.txt` — bridge_client.cpp added, Threads + ws2_32 linked
- **Needs debug at home**: compile + run the ImGui app with bridge.py to verify end-to-end

### Python Bridge Server — Complete
- `bridge.py` — TCP server, 7 tune_* handlers, length-prefixed JSON protocol

### Socket IPC for Instances — Complete
- `transport.py` — TransportServer + TransportClient, same wire protocol as imgui bridge
- `manager.py` — upgraded to support "auto"/"socket"/"filesystem" IPC modes
- `instance.py` — upgraded with socket transport, wait_for_task(), cleanup()
- `MANIFEST.toml` — ipc mode changed from "filesystem" to "auto"
- 16 transport tests passing (protocol, server/client, manager integration)

### Tests — 193 Total
- `test_algebra.py` — 10 | `test_fft.py` — 15 | `test_generators.py` — 10
- `test_linalg.py` — 13 | `test_spectral.py` — 10 | `test_stats.py` — 15
- `test_transforms.py` — 10 | `test_tuning.py` — 82
- `test_transport.py` — 16 (protocol, server/client, manager integration)
- Dependencies: numpy, scipy, pytest, pytest-timeout

## Next Goal

**Qt container app** — build the CLI entry point as a Qt application. Replaces the `terra` bash script as the primary interface. Start in a new session.

## Key Files

```
.scaffold/imgui/bridge_client.h    — C++ TCP client header
.scaffold/imgui/bridge_client.cpp  — C++ TCP client impl
.scaffold/imgui/bridge.py          — Python TCP server
.scaffold/imgui/main.cpp           — ImGui app entry (bridge wired)
.scaffold/imgui/tuning_panel.cpp   — tuning panel (bridge calls live)
.scaffold/imgui/CMakeLists.txt     — build config (bridge + threads)
.scaffold/instances/transport.py   — socket IPC transport layer
.scaffold/instances/manager.py     — instance manager (socket + filesystem)
.scaffold/instances/instance.py    — instance lifecycle (socket + filesystem)
.scaffold/tests/test_transport.py  — 16 transport tests
.scaffold/tests/test_tuning.py     — 82 tuning tests
```

## Debug Notes (for home session)

The C++ TCP bridge client is written but not compiled yet (no GLFW/ImGui on this machine). To test end-to-end:

1. `cd .scaffold/imgui && mkdir build && cd build && cmake .. && make`
2. In one terminal: `python .scaffold/imgui/bridge.py` (or run via terra)
3. In another: `./build/terragraf_imgui`
4. Tuning panel should show "Waiting for profile list..." then populate after bridge responds
5. Check: profile load, zone switching, knob adjustment, behavioral instructions refresh
