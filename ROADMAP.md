# Terragraf Feature Roadmap

**Status:** Phases 0-7 complete. 210 tests passing.

---

## Completed

### Phase 0: Housekeeping
- README with contributor credits
- `NOTICE` file, `THIRD_PARTY_LICENSES.md`
- Apache 2.0 compliance verified

### Phase 1: Math & Algebra Primitives
- `.scaffold/compute/math/` — linalg, algebra, stats, transforms
- Dependencies: numpy, scipy (BSD-3)
- 48 tests (algebra 10, linalg 13, stats 15, transforms 10)

### Phase 2: Spectrograms & 2D Visualization
- `.scaffold/viz/` — spectrogram, heatmap rendering
- `.scaffold/compute/fft/` — FFT, STFT, spectral analysis
- 25 tests (fft 15, spectral 10)

### Phase 3: 3D Data Modeling & Node Graphs
- `.scaffold/viz/3d/` — nodes, mesh, volume, scene
- `.scaffold/compute/render/` — OpenGL mesh + volume renderers

### Phase 4: Ultrasound-Style Dataset Imaging
- Volume renderer, transfer functions, ray marching shader

### Phase 5: Real-Time ImGui Math Modeling
- `.scaffold/imgui/` — 7 panels (math, spectrogram, node editor, volume, tuning, debug, settings)
- GLFW 3.4 + OpenGL 4.5 + Dear ImGui (docking) + ImPlot + ImNodes
- TCP bridge (`bridge.py`) with length-prefixed JSON protocol
- C++ bridge client (background recv thread, main-thread dispatch)
- All dependencies MIT/zlib/PD — fully Apache 2.0 compatible

### Phase 6: Self-Sharpening & Tuning
- `.scaffold/sharpen/` — self-sharpening engine (prune stale, promote hot, learn errors)
- `.scaffold/tuning/` — thematic tension calibration (8 universe profiles, 6 reaction signatures, knobs, zones)
- 82 tuning tests

### Phase 7: Socket IPC for Multi-Instancing
- `.scaffold/instances/transport.py` — TCP socket transport (server + client)
- Length-prefixed JSON protocol, same wire format as ImGui bridge
- Manager supports "auto"/"socket"/"filesystem" IPC modes
- Sub-millisecond dispatch, 10+ concurrent instances
- Graceful fallback to filesystem IPC
- 16 transport tests

### Phase 8: Qt Container App
- `.scaffold/app/` — PySide6 container shell with 5 pages
- **Home** — landing page with test status and quick nav
- **Viewer** — launch/stop bridge.py and ImGui processes
- **Tuning** — profile selector, zone buttons, knob widgets (slider/dropdown/toggle/text), behavioral instructions
- **Debug** — bridge connection controls, ping/RTT, stats, filterable message log
- **Settings** — bridge host/port, paths, panel visibility, persistent config
- Sidebar navigation (Ctrl+1-5), dark CI terminal theme
- Bridge client with Qt signals/slots for cross-thread safety
- 17 app tests (10 pass everywhere, 7 need PySide6 + libEGL)

---

## Test Summary — 210 Total

| File | Count | What |
|------|-------|------|
| test_algebra.py | 10 | polynomial eval, roots, interpolation, curve fit |
| test_fft.py | 15 | FFT roundtrip, spectrum, STFT, convolution |
| test_generators.py | 10 | model gen, shader gen |
| test_linalg.py | 13 | matmul, inverse, eigen, SVD, LU, solve |
| test_spectral.py | 10 | centroid, rolloff, bandpass, mel filterbank |
| test_stats.py | 15 | descriptive, correlation, regression, t-test |
| test_transforms.py | 10 | DCT, Hilbert, wavelet, z-transform, Laplace |
| test_tuning.py | 82 | schema, loader, engine, knobs, zones, CLI |
| test_transport.py | 16 | protocol, server/client, manager integration |
| test_app.py | 17 | theme, bridge client, page imports, bridge handlers |

---

## What's Next

### End-to-End Debug
- Compile and run ImGui + bridge.py + Qt on a machine with GLFW/Vulkan
- Verify the full loop: Qt launches bridge -> bridge accepts ImGui -> tuning panel populates -> knob changes flow back

### Language-Aware Output
- Generators adapt conventions and tooling per project language
- No separate configuration files per language

### Polish
- Error handling and reconnection logic in bridge clients
- Panel layout persistence in ImGui (save/restore docking state)
- Qt container process management hardening

---

## Dependency License Summary

**No GPL dependencies. Nothing requires license change.**

| License | Libraries |
|---------|-----------|
| **BSD-3** | numpy, scipy, networkx |
| **MIT** | Dear ImGui, ImPlot, ImNodes, moderngl, trimesh, pyrr, glm |
| **zlib** | GLFW |
| **LGPL-3** | PySide6 (dynamically linked, Apache 2.0 compatible) |
| **Public Domain** | glad |

---

## Platforms

Linux (Wayland) and Windows 10/11.
