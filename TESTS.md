# Tests — 302 Passing

[![CI](https://github.com/curbthepain/Terragraf/actions/workflows/ci.yml/badge.svg)](https://github.com/curbthepain/Terragraf/actions/workflows/ci.yml)

```bash
# Run all tests
pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest .scaffold/tests/ -v

# Run a specific test file
python -m pytest .scaffold/tests/test_tuning.py -v

# Run with coverage
python -m pytest .scaffold/tests/ --cov=.scaffold --cov-report=term-missing
```

---

## Test Summary

| File | Tests | Module | What's tested |
|------|-------|--------|---------------|
| test_algebra.py | 10 | compute/math/algebra.py | poly_eval, poly_roots, interpolate, curve_fit_poly, lagrange, newton |
| test_fft.py | 15 | compute/fft/fft.py | FFT roundtrip, DC, single freq, 2D, RFFT, magnitude, phase, power spectrum, freqs, STFT, convolution, cross-correlation |
| test_generators.py | 10 | generators/ | gen_model (base, classifier, transformer, CNN), gen_shader (basic, buffers, push constants, workgroup) |
| test_linalg.py | 13 | compute/math/linalg.py | mat_mul, mat_inv, determinant, eigenvalues, eigenvectors, SVD, LU, solve, norm, rank |
| test_spectral.py | 10 | compute/fft/spectral.py | spectrogram, spectral_centroid, spectral_rolloff, dominant_frequency, bandpass_filter, mel_filterbank |
| test_stats.py | 15 | compute/math/stats.py | descriptive, correlation, covariance, linear_regression, normal_pdf/cdf, t_test, chi_squared, percentile, zscore |
| test_transforms.py | 10 | compute/math/transforms.py | DCT roundtrip, energy concentration, Hilbert analytic signal, wavelet, z_transform, laplace_transform |
| test_tuning.py | 82 | tuning/ | schema, loader, engine (profiles, zones, axes, knobs, directives, instructions), state persistence, CLI integration |
| test_transport.py | 16 | instances/ | wire protocol, server/client, broadcast, unicast, multiple clients, heartbeat, disconnect, manager socket integration |
| test_app.py | 17 | app/, imgui/bridge.py | theme constants/stylesheet/selectors, bridge_client init/log, settings defaults, page imports, bridge debug handlers, ping/pong/echo |
| test_sharpen.py | 30 | sharpen/ | config defaults, error normalization (paths/lines/hex), analytics IO, record_hit, record_outcome, unmatched errors, locking, engine passes (stale/hot/errors/low-confidence), file modification (comment-out/annotate/add-error), route/table parsing |
| test_viz.py | 17 | viz/ | heatmap (basic, labels, params), annotated_heatmap, figure export (PNG/SVG), figure_to_buffer, spectrogram rendering, mel spectrogram, stream plotter, dataset_to_volume (shape, normalization, feature dims) |
| test_viz3d.py | 45 | viz/3d/ | transfer_function (interpolation, clamping, presets, apply), mesh (surface gen, point cloud, rendering), node_graph (add/edge, spring layout, rendering), camera (view/projection matrix, orbit), light (direction, directional), scene (objects, bounds, auto_camera, rendering), volume_renderer (sample, interpolation, render output), 3D export (OBJ vertices/faces/normals, PLY vertices/colors/faces) |
| **Total** | **302** | | |

---

## Test Architecture

### Dependencies

```
requirements-dev.txt       numpy, scipy, pytest
requirements-app.txt       + PySide6 (for Qt widget tests)
matplotlib                 for viz tests (installed separately)
```

### Environment

- Tests run headless — no display server required
- `QT_QPA_PLATFORM=offscreen` for PySide6 widget tests
- `matplotlib.use("Agg")` for headless figure rendering
- All network tests use ephemeral ports (19000+) to avoid conflicts
- File-based tests use `tempfile.mkdtemp()` for isolation
- Socket tests include timeouts and cleanup

### Test Categories

**Unit tests** — isolated function/class behavior:
- Math functions (algebra, linalg, stats, transforms, FFT)
- Transfer functions, mesh generation, node graph layout
- Error normalization, analytics data structures
- Theme constants, config defaults

**Integration tests** — multi-component interaction:
- Transport protocol roundtrips (server + client over TCP)
- Manager dispatch via socket to instance
- Bridge handler wiring (ping/pong, debug echo)
- CLI command integration (subprocess + state file)

**Smoke tests** — import and basic sanity:
- Qt page modules import without error
- Bridge client initializes with correct defaults
- Settings load from defaults when no file exists

**Rendering tests** — headless figure generation:
- Heatmap, annotated heatmap, spectrogram, mel spectrogram
- 3D surface, point cloud, node graph, scene
- Volume renderer (trilinear sampling, ray marching)
- Figure export to PNG/SVG/buffer

**File I/O tests** — serialization correctness:
- OBJ export (vertices, faces, normals, 1-indexed)
- PLY export (vertices, colors, faces, header format)
- Analytics JSON save/load roundtrip
- Settings JSON persistence

---

## Coverage by Module

| Module | Coverage | Notes |
|--------|----------|-------|
| compute/math/ | Full | All functions in algebra, linalg, stats, transforms |
| compute/fft/ | Full | All functions in fft, spectral |
| generators/ | Full | gen_model (4 types), gen_shader (4 configs) |
| tuning/ | Full | schema, loader, engine, cli, state persistence |
| instances/ | Good | transport protocol, server/client, manager integration |
| sharpen/ | Good | config, tracker (IO, locking, normalization), engine (4 passes, file modification) |
| viz/ | Good | heatmap, export, spectrogram, ultrasound volume generation |
| viz/3d/ | Good | transfer_function, mesh, nodes, scene, volume, export (OBJ/PLY) |
| app/ | Moderate | theme, bridge_client, settings, page imports, bridge handlers |
| imgui/ | Moderate | bridge.py debug handlers (ping/pong/echo) |

---

## Running in CI

The GitHub Actions CI workflow runs:

```yaml
- pip install -r requirements-dev.txt
- python -m pytest .scaffold/tests/ -v
```

Qt-dependent tests are skipped in CI if PySide6 is not installed.
Viz tests require matplotlib (add to CI if needed).
