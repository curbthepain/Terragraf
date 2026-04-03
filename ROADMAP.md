# Terraformer Feature Roadmap

**Branch:** `terra-yog`
**Status:** Plan saved. Ready to implement in next session.

## Context

Terraformer has a working `terra` CLI, FFT/spectral code (numpy + C++ FFTW), Vulkan compute scaffolds, GLSL shaders, and PyTorch ML. The next phase adds real math primitives, visualization pipelines, 3D data modeling, and interactive ImGui tooling. All code must stay Apache 2.0 compatible. README gets proper contributor credits.

---

## Phase 0: Housekeeping (do first)

### README contributor credits + license clarity

**Files:** `README.md`, `NOTICE` (new)

- Add professional Contributors section at bottom of README.md
- Create `NOTICE` file (Apache 2.0 convention for attribution)
- Add THIRD_PARTY_LICENSES.md for tracking dependency licenses

Contributors table for README:

| Name | Role | Contact |
|------|------|---------||
| Austin Wisniewski | Creator, Lead | [@curbthepain](https://github.com/curbthepain) |
| Claude (Anthropic) | AI Contributor | [anthropic.com](https://anthropic.com) |

---

## Phase 1: Math & Algebra Primitives

**New directory:** `.scaffold/compute/math/`

**Files to create:**
- `math/__init__.py` — exports
- `math/linalg.py` — linear algebra: matrix ops, eigenvalues, SVD, LU decomposition, determinants
- `math/algebra.py` — symbolic-style algebra: polynomial eval, roots, interpolation, curve fitting
- `math/stats.py` — statistics: distributions, hypothesis tests, correlation, regression
- `math/transforms.py` — beyond FFT: wavelet, DCT, Hilbert, z-transform

**Builds on:** existing `compute/fft/` code, numpy already in use

**Dependencies (all Apache 2.0 / BSD compatible):**

| Library | License | Purpose |
|---------|---------|---------||
| numpy | BSD-3 | Already used. Matrix ops, linalg |
| scipy | BSD-3 | Advanced linalg, signal, stats |
| sympy | BSD-3 | Symbolic math (optional) |

**Terra commands:**
- `terra math eval <expr>` — evaluate a math expression
- `terra math linalg <op>` — run a linear algebra operation

**Header:** Add `math.h` to `.scaffold/headers/`

---

## Phase 2: Spectrograms & 2D Visualization

**New directory:** `.scaffold/viz/`

**Files to create:**
- `viz/__init__.py` — exports
- `viz/spectrogram.py` — render spectrograms from FFT/STFT output (builds on `compute/fft/spectral.py` which already has `spectrogram()`)
- `viz/heatmap.py` — generic heatmap renderer for 2D data
- `viz/stream.py` — real-time data stream plotter (scrolling line charts, live updates)
- `viz/export.py` — save to PNG/SVG/raw buffer

**Builds on:** `compute/fft/spectral.py` already has `spectrogram()`, `mel_filterbank()`, `spectral_centroid()`

**Dependencies:**

| Library | License | Purpose |
|---------|---------|---------||
| matplotlib | PSF (BSD-like) | 2D plotting, spectrogram rendering |
| pillow | HPND (permissive) | Image export |

**Terra commands:**
- `terra viz spectrogram <data>` — generate spectrogram
- `terra viz heatmap <data>` — render heatmap
- `terra viz stream` — launch live data viewer

---

## Phase 3: 3D Data Modeling & Node Graphs

**New directory:** `.scaffold/viz/3d/`

**Files to create:**
- `viz/3d/__init__.py`
- `viz/3d/nodes.py` — 3D node graph generator (dependency graphs, data flow, neural net arch)
- `viz/3d/mesh.py` — mesh generation from data (surface plots, point clouds)
- `viz/3d/volume.py` — volumetric rendering ("ultrasound" view)
- `viz/3d/scene.py` — scene manager (camera, lighting, export)
- `viz/3d/export.py` — export to OBJ/PLY/GLTF

**C side:** `.scaffold/compute/render/`
- `render/gl_context.cpp` — OpenGL context (Wayland + Win32)
- `render/mesh_renderer.cpp` — basic mesh rendering
- `render/volume_renderer.cpp` — ray marching for volumetric data

**Dependencies (recommended lighter path):**

| Library | License | Purpose |
|---------|---------|---------||
| moderngl | MIT | OpenGL rendering |
| pyrr | MIT | 3D math (matrices, quaternions) |
| networkx | BSD-3 | Graph layouts |
| trimesh | MIT | Mesh I/O (OBJ, PLY, GLTF) |

**Terra commands:**
- `terra viz 3d nodes <data>` — 3D node map
- `terra viz 3d mesh <data>` — 3D surface
- `terra viz 3d volume <data>` — volumetric render

---

## Phase 4: Ultrasound-Style Dataset Imaging

**Lives in:** `.scaffold/viz/3d/volume.py` + `.scaffold/compute/shaders/volume.comp`

Volumetric rendering of datasets — treat a dataset's feature space as a 3D density field, render it like medical ultrasound/CT.

**Files to create:**
- `viz/3d/volume.py` — Python volume renderer (ray marching CPU or GPU)
- `compute/shaders/volume.comp` — GPU ray marching shader
- `viz/3d/transfer_function.py` — data values to colors/opacity
- `viz/ultrasound.py` — high-level API: dataset in, image out

**Builds on:** Phase 3 rendering + existing Vulkan pipeline.cpp + fft.comp shader pattern

---

## Phase 5: Real-Time ImGui Math Modeling

**New directory:** `.scaffold/imgui/`

**Files to create:**
- `imgui/CMakeLists.txt` — build config
- `imgui/main.cpp` — ImGui app entry (GLFW + OpenGL or Vulkan)
- `imgui/math_panel.cpp` — interactive math with sliders, live function plotting
- `imgui/spectrogram_panel.cpp` — real-time spectrogram display
- `imgui/node_editor.cpp` — visual node graph editor
- `imgui/volume_panel.cpp` — interactive 3D volume slicer
- `imgui/bridge.py` — Python<->C++ bridge (shared memory or socket)

**Dependencies:**

| Library | License | Purpose |
|---------|---------|---------||
| Dear ImGui | MIT | Immediate mode GUI |
| ImPlot | MIT | Real-time charts |
| ImNodes | MIT | Node editor |
| GLFW | zlib | Windowing |
| glad | MIT/PD | OpenGL loader |
| glm | MIT | Math for OpenGL |

All MIT/zlib/public domain. Fully Apache 2.0 compatible.

**Terra commands:**
- `terra imgui build` — build the ImGui app
- `terra imgui run` — launch interactive viewer
- `terra imgui math` — math modeling panel
- `terra imgui nodes` — node graph editor

**Platform notes:**
- Linux: GLFW + Wayland backend (GLFW 3.4+)
- Windows: GLFW + Win32 backend

---

## Dependency License Summary

**No GPL dependencies. Nothing requires license change.**

| License | Libraries |
|---------|-----------||
| **BSD-3** | numpy, scipy, matplotlib, pyglet, networkx |
| **MIT** | Dear ImGui, ImPlot, ImNodes, moderngl, trimesh, pyrr, glm |
| **zlib** | GLFW |
| **PSF** | matplotlib |
| **HPND** | Pillow |
| **Public Domain** | glad |

Create `THIRD_PARTY_LICENSES.md` listing each dependency, version, license, and URL.

---

## Implementation Order

```
Phase 0  Housekeeping         README credits, NOTICE, license tracking
   |
Phase 1  Math primitives      .scaffold/compute/math/ (numpy + scipy)
   |
Phase 2  Spectrograms + 2D    .scaffold/viz/ (matplotlib, builds on FFT)
   |
Phase 3  3D node graphs       .scaffold/viz/3d/ (moderngl + networkx)
   |
Phase 4  Ultrasound volumes   volume.py + volume.comp shader
   |
Phase 5  ImGui real-time      .scaffold/imgui/ (Dear ImGui + ImPlot + ImNodes)
```

Each phase is independently useful. Phase 5 ties it all together.

## Phase 6: Finish ImGui Real-Time App (next up)

**Status:** Scaffolded (Phase 5), needs implementation.

`imgui/main.cpp` exists but is entirely commented out. All panels are stubs.

### What needs to happen:
1. **GLFW/OpenGL/ImGui initialization** — uncomment and wire up `main.cpp` event loop
2. **Math panel** — connect `compute/math/` to ImPlot for live function plotting with sliders
3. **Spectrogram panel** — real-time spectrogram display fed by `compute/fft/spectral.py`
4. **Node editor** — wire ImNodes to `viz/3d/nodes.py` graph data
5. **Volume panel** — interactive 3D volume slicer using `viz/3d/volume.py`
6. **Python↔C++ bridge** — implement `imgui/bridge.py` using either:
   - Unix domain sockets (Linux) / named pipes (Windows)
   - Shared memory via mmap
   - HTTP localhost (simplest, highest latency)

### Build verification:
```
terra imgui build   # CMake build succeeds
terra imgui run     # Window opens, panels render
```

### Dependencies (already declared in deps.h):
Dear ImGui (MIT), ImPlot (MIT), ImNodes (MIT), GLFW (zlib), glad (PD), glm (MIT)

---

## Phase 7: Socket/Pipe IPC for Multi-Instancing

**Status:** Not started. Currently filesystem-only IPC.

Replace the filesystem-based queue/results IPC in `instances/` with real-time socket or pipe coordination.

### What needs to happen:
1. **IPC transport layer** — abstract over Unix sockets, named pipes, or ZeroMQ
2. **Message protocol** — define a simple JSON or msgpack wire format for task dispatch/results
3. **Instance manager upgrade** — `instances/manager.py` switches from file polling to event-driven dispatch
4. **Instance client upgrade** — `instances/instance.py` connects to manager via socket
5. **Self-sharpening routes** — routes and tables update based on instance feedback (which routes get used, which fail)
6. **Language-aware output** — generators adapt output style based on project conventions

### Design goals:
- Sub-millisecond task dispatch (vs. ~100ms filesystem polling)
- Support 10+ concurrent AI instances
- Graceful fallback to filesystem IPC if sockets unavailable

### Candidate libraries:
| Library | License | Purpose |
|---------|---------|---------||
| zmq (pyzmq) | LGPL/BSD | High-perf message passing |
| msgpack | Apache-2.0 | Binary serialization |

### MANIFEST.toml change:
```toml
[features]
ipc = "socket"  # was "filesystem"
```

---

## Files Modified (existing)

| File | Change |
|------|--------|
| `README.md` | Add Contributors, update roadmap |
| `MANIFEST.toml` | Add `[features]` flags: math, viz, imgui |
| `.scaffold/headers/` | Add `math.h`, `viz.h` |
| `.scaffold/routes/tasks.route` | Add math, viz, imgui entries |
| `.scaffold/routes/structure.route` | Add viz, imgui mappings |
| `.scaffold/tables/deps.table` | Add viz->compute, imgui->viz |
| `terra` | Add `math`, `viz`, `imgui` subcommands |
| `COMMANDS.md` | Add new commands |

## Files Created (new)

| Directory | Contents |
|-----------|----------|
| `.scaffold/compute/math/` | linalg.py, algebra.py, stats.py, transforms.py |
| `.scaffold/viz/` | spectrogram.py, heatmap.py, stream.py, export.py |
| `.scaffold/viz/3d/` | nodes.py, mesh.py, volume.py, scene.py, export.py |
| `.scaffold/imgui/` | main.cpp, panels, bridge.py, CMakeLists.txt |
| `.scaffold/compute/shaders/volume.comp` | GPU ray marching |
| `.scaffold/compute/render/` | gl_context.cpp, renderers |
| Root | `NOTICE`, `THIRD_PARTY_LICENSES.md` |

---

## Verification

After each phase:
1. `terra status` shows new subsystems
2. `terra route <intent>` finds new files
3. Python imports work: `from scaffold.compute.math import linalg`
4. Generators produce valid code
5. Phase 5: `terra imgui build && terra imgui run` launches viewer
6. All license files accurate and complete
