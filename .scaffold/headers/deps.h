// .scaffold/headers/deps.h
// External dependency declarations. AI reads this to know what's available.

#ifndef DEPS_H
#define DEPS_H

// ─── Python (core) ──────────────────────────────────────────────────

#dep numpy {
    #role "Array operations, linear algebra, FFT"
    #import "import numpy as np"
    #version ">=1.24"
    #scope "compile"
}

#dep scipy {
    #role "Advanced linalg, signal processing, statistics, transforms"
    #import "from scipy import linalg, signal, stats, fft"
    #version ">=1.11"
    #scope "compile"
}

#dep matplotlib {
    #role "2D plotting — spectrograms, heatmaps, stream plots"
    #import "import matplotlib.pyplot as plt"
    #version ">=3.7"
    #scope "compile"
}

#dep pillow {
    #role "Image export (PNG, JPEG)"
    #import "from PIL import Image"
    #version ">=10.0"
    #scope "compile"
}

#dep networkx {
    #role "Graph layouts for 3D node visualization"
    #import "import networkx as nx"
    #version ">=3.1"
    #scope "compile"
}

#dep trimesh {
    #role "Mesh I/O — OBJ, PLY, GLTF export"
    #import "import trimesh"
    #version ">=3.23"
    #scope "compile"
}

// ─── Python (ML) ────────────────────────────────────────────────────

#dep torch {
    #role "PyTorch ML framework — models, training, GPU compute"
    #import "import torch; import torch.nn as nn"
    #version ">=2.0"
    #scope "compile"
}

// ─── Python (test) ──────────────────────────────────────────────────

#dep pytest {
    #role "Test framework"
    #import "import pytest"
    #version ">=7.0"
    #scope "test"
}

// ─── C++ (compile) ──────────────────────────────────────────────────

#dep vulkan {
    #role "GPU compute pipeline"
    #import "#include <vulkan/vulkan.h>"
    #version "1.3"
    #scope "compile"
}

#dep glfw {
    #role "Cross-platform windowing (Wayland + Win32)"
    #import "#include <GLFW/glfw3.h>"
    #version ">=3.4"
    #scope "compile"
}

#dep imgui {
    #role "Immediate mode GUI for interactive tools"
    #import "#include \"imgui.h\""
    #version ">=1.89"
    #scope "compile"
}

#dep implot {
    #role "Real-time plotting for ImGui"
    #import "#include \"implot.h\""
    #version ">=0.16"
    #scope "compile"
}

#dep imnodes {
    #role "Node graph editor for ImGui"
    #import "#include \"imnodes.h\""
    #version ">=0.5"
    #scope "compile"
}

#dep fftw3 {
    #role "C++ FFT backend (optional, numpy/scipy default)"
    #import "#include <fftw3.h>"
    #version ">=3.3"
    #scope "compile"
}

// ─── Qt (app) ───────────────────────────────────────────────────────

#dep pyside6 {
    #role "Qt container application shell"
    #import "from PySide6.QtWidgets import QApplication"
    #version ">=6.5"
    #scope "app"
}

// ─── Licenses ───────────────────────────────────────────────────────
// numpy: BSD-3 | scipy: BSD-3 | matplotlib: PSF (BSD-like)
// pillow: HPND | networkx: BSD-3 | trimesh: MIT | torch: BSD-3
// pytest: MIT | pyside6: LGPL-3.0 | vulkan: Apache-2.0 | glfw: zlib
// imgui: MIT | implot: MIT | imnodes: MIT | glad: MIT/PD | glm: MIT
// fftw3: GPL (optional, not linked by default)
// All Apache 2.0 compatible except fftw3 (optional)

#endif // DEPS_H
