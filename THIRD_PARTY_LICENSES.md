# Third-Party Licenses

Terragraf uses the following third-party libraries. All Apache 2.0
compatible. The only GPL dependency (FFTW3) is optional and not linked
by default.

## Python — Core (requirements.txt)

| Library | License | Purpose | URL |
|---------|---------|---------|-----|
| NumPy | BSD-3-Clause | Matrix ops, FFT, linalg | https://numpy.org |
| SciPy | BSD-3-Clause | Advanced linalg, signal, stats | https://scipy.org |

## Python — Dev (requirements-dev.txt)

| Library | License | Purpose | URL |
|---------|---------|---------|-----|
| pytest | MIT | Test framework | https://pytest.org |

## Python — ML (requirements-ml.txt)

| Library | License | Purpose | URL |
|---------|---------|---------|-----|
| PyTorch | BSD-3-Clause | ML framework, models, training | https://pytorch.org |

## Python — App (requirements-app.txt)

| Library | License | Purpose | URL |
|---------|---------|---------|-----|
| PySide6 | LGPL-3.0 | Qt container application | https://doc.qt.io/qtforpython-6/ |

## C++ — ImGui App (fetched via CMake)

| Library | License | Purpose | URL |
|---------|---------|---------|-----|
| Dear ImGui | MIT | Immediate mode GUI | https://github.com/ocornut/imgui |
| ImPlot | MIT | Real-time charts | https://github.com/epezent/implot |
| ImNodes | MIT | Node editor | https://github.com/Nelarius/imnodes |
| GLFW | zlib | Windowing (Wayland + Win32) | https://www.glfw.org |
| glad | MIT/Public Domain | OpenGL loader | https://github.com/Dav1dde/glad |
| GLM | MIT | Math for OpenGL | https://github.com/g-truc/glm |

## C++ — Optional

| Library | License | Purpose | URL |
|---------|---------|---------|-----|
| FFTW3 | GPL-2.0 | C++ FFT backend (not linked by default) | https://fftw.org |
| Vulkan SDK | Apache-2.0 | GPU compute pipeline | https://vulkan.lunarg.com |

## Planned (declared in deps.h, not yet imported)

| Library | License | Purpose | URL |
|---------|---------|---------|-----|
| matplotlib | PSF (BSD-like) | 2D plotting, spectrogram rendering | https://matplotlib.org |
| Pillow | HPND (permissive) | Image export | https://python-pillow.org |
| NetworkX | BSD-3-Clause | Graph layouts | https://networkx.org |
| trimesh | MIT | Mesh I/O (OBJ, PLY, GLTF) | https://trimesh.org |

## License Summary

| License | Compatible with Apache 2.0 | Notes |
|---------|---------------------------|-------|
| BSD-3-Clause | Yes | |
| MIT | Yes | |
| LGPL-3.0 | Yes | Dynamic linking (PySide6) |
| zlib | Yes | |
| PSF | Yes | |
| HPND | Yes | |
| Public Domain | Yes | |
| GPL-2.0 | No | FFTW3 optional, not linked by default |
