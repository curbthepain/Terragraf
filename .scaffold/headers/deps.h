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

// ─── Python (audio) ─────────────────────────────────────────────────

#dep sounddevice {
    #role "Audio device I/O — real-time recording and playback"
    #import "import sounddevice as sd"
    #version ">=0.4"
    #scope "compile"
}

#dep soundfile {
    #role "Sound file I/O — WAV, FLAC, OGG"
    #import "import soundfile as sf"
    #version ">=0.12"
    #scope "compile"
}

#dep pydub {
    #role "Audio manipulation — slicing, effects, format conversion"
    #import "from pydub import AudioSegment"
    #version ">=0.25"
    #scope "compile"
}

// ─── Python (ML) ────────────────────────────────────────────────────

#dep torch {
    #role "PyTorch ML framework — models, training, GPU compute"
    #import "import torch; import torch.nn as nn"
    #version ">=2.0"
    #scope "compile"
}

#dep torchvision {
    #role "Computer vision — datasets (CIFAR, ImageNet), transforms, pretrained models"
    #import "import torchvision; from torchvision import transforms"
    #version ">=0.15"
    #scope "compile"
}

#dep torchaudio {
    #role "Audio ML — spectrograms, transforms, pretrained audio models"
    #import "import torchaudio"
    #version ">=2.0"
    #scope "compile"
}

#dep scikit_learn {
    #role "Classical ML — preprocessing, metrics, train/test splits, baselines"
    #import "from sklearn import metrics, preprocessing, model_selection"
    #version ">=1.3"
    #scope "compile"
    #license "BSD-3"
}

#dep pandas {
    #role "Tabular data — DataFrames, CSV/JSON I/O, data wrangling"
    #import "import pandas as pd"
    #version ">=2.0"
    #scope "compile"
    #license "BSD-3"
}

// ─── Python (ML — model development) ───────────────────────────────

#dep transformers {
    #role "Hugging Face — pretrained models, fine-tuning, tokenizers"
    #import "from transformers import AutoModel, AutoTokenizer"
    #version ">=4.30"
    #scope "compile"
    #license "Apache-2.0"
}

#dep tokenizers {
    #role "Fast Rust-backed tokenization (BPE, WordPiece, Unigram)"
    #import "from tokenizers import Tokenizer"
    #version ">=0.13"
    #scope "compile"
    #license "Apache-2.0"
}

#dep datasets {
    #role "Hugging Face datasets — loading, streaming, processing"
    #import "from datasets import load_dataset"
    #version ">=2.14"
    #scope "compile"
    #license "Apache-2.0"
}

#dep safetensors {
    #role "Safe model weight serialization (no pickle)"
    #import "from safetensors.torch import save_file, load_file"
    #version ">=0.3"
    #scope "compile"
    #license "Apache-2.0"
}

#dep accelerate {
    #role "Multi-GPU, mixed-precision, distributed training"
    #import "from accelerate import Accelerator"
    #version ">=0.20"
    #scope "compile"
    #license "Apache-2.0"
}

// ─── Python (ML — training infra) ──────────────────────────────────

#dep tensorboard {
    #role "Training visualization — loss curves, metrics, histograms"
    #import "from torch.utils.tensorboard import SummaryWriter"
    #version ">=2.13"
    #scope "compile"
    #license "Apache-2.0"
}

#dep wandb {
    #role "Experiment tracking — runs, sweeps, model registry"
    #import "import wandb"
    #version ">=0.15"
    #scope "compile"
    #license "MIT"
}

// ─── Python (ML — inference/export) ────────────────────────────────

#dep onnx {
    #role "Open Neural Network Exchange — model graph format"
    #import "import onnx"
    #version ">=1.14"
    #scope "compile"
    #license "Apache-2.0"
}

#dep onnxruntime {
    #role "ONNX inference engine — CPU/GPU/TensorRT backends"
    #import "import onnxruntime as ort"
    #version ">=1.15"
    #scope "compile"
    #license "MIT"
}

// ─── Python (test) ──────────────────────────────────────────────────

#dep pytest {
    #role "Test framework"
    #import "import pytest"
    #version ">=7.0"
    #scope "test"
}

// ─── C++ — ImGui app ────────────────────────────────────────────────

#dep glfw {
    #role "Cross-platform windowing (Wayland + Win32)"
    #import "#include <GLFW/glfw3.h>"
    #version ">=3.4"
    #scope "compile"
    #license "zlib"
}

#dep glad {
    #role "OpenGL loader generator"
    #import "#include <glad/gl.h>"
    #version ">=2.0.8"
    #scope "compile"
    #license "MIT/Public Domain"
}

#dep glm {
    #role "OpenGL Mathematics library (header-only)"
    #import "#include <glm/glm.hpp>"
    #version ">=1.0.1"
    #scope "compile"
    #license "MIT"
}

#dep imgui {
    #role "Immediate mode GUI for interactive tools"
    #import "#include \"imgui.h\""
    #version ">=1.89"
    #scope "compile"
    #license "MIT"
}

#dep implot {
    #role "Real-time plotting for ImGui"
    #import "#include \"implot.h\""
    #version ">=0.16"
    #scope "compile"
    #license "MIT"
}

#dep imnodes {
    #role "Node graph editor for ImGui"
    #import "#include \"imnodes.h\""
    #version ">=0.5"
    #scope "compile"
    #license "MIT"
}

// ─── C++ — Vulkan toolchain ────────────────────────────────────────

#dep vulkan_headers {
    #role "Vulkan API headers"
    #import "#include <vulkan/vulkan.h>"
    #version "1.3.283"
    #scope "compile"
    #license "Apache-2.0"
}

#dep vulkan_loader {
    #role "Vulkan ICD loader (libvulkan.so.1 / vulkan-1.dll)"
    #version "1.3.283"
    #scope "compile"
    #license "Apache-2.0"
}

#dep vma {
    #role "Vulkan Memory Allocator — GPU memory management"
    #import "#include \"vk_mem_alloc.h\""
    #version ">=3.1.0"
    #scope "compile"
    #license "MIT"
}

#dep glslang {
    #role "GLSL/HLSL → SPIR-V compiler"
    #version ">=15.1.0"
    #scope "compile"
    #license "Apache-2.0 + BSD-3"
}

#dep spirv_tools {
    #role "SPIR-V optimizer, validator, linker"
    #version ">=2024.1"
    #scope "compile"
    #license "Apache-2.0"
}

#dep spirv_headers {
    #role "SPIR-V header definitions"
    #version ">=1.3.283"
    #scope "compile"
    #license "MIT"
}

#dep spirv_cross {
    #role "SPIR-V reflection and decompilation"
    #version ">=1.3.283"
    #scope "compile"
    #license "Apache-2.0"
}

// ─── C++ — FFT ─────────────────────────────────────────────────────

#dep fftw3 {
    #role "C++ FFT backend — fastest CPU FFT (optional, numpy/scipy default)"
    #import "#include <fftw3.h>"
    #version ">=3.3.10"
    #scope "compile"
    #license "GPL-2.0 (local only, not linked by default)"
}

// ─── C++ — Math ────────────────────────────────────────────────────

#dep eigen {
    #role "Linear algebra — matrices, vectors, solvers, decompositions"
    #import "#include <Eigen/Dense>"
    #version ">=3.4.0"
    #scope "compile"
    #license "MPL-2.0 (Apache-2.0 compatible)"
}

#dep ceres_solver {
    #role "Nonlinear least squares, optimization"
    #import "#include <ceres/ceres.h>"
    #version ">=2.2.0"
    #scope "compile"
    #license "BSD-3"
}

// ─── C++ — Game dev ────────────────────────────────────────────────

#dep nlohmann_json {
    #role "JSON parsing (header-only, used by bridge IPC protocol)"
    #import "#include <nlohmann/json.hpp>"
    #version ">=3.11.3"
    #scope "compile"
    #license "MIT"
}

#dep stb {
    #role "Single-header utilities — image loading, fonts, truetype, vorbis"
    #import "#include \"stb_image.h\""
    #version "latest"
    #scope "compile"
    #license "MIT/Public Domain"
}

#dep entt {
    #role "Entity Component System framework"
    #import "#include <entt/entt.hpp>"
    #version ">=3.13.2"
    #scope "compile"
    #license "MIT"
}

#dep bullet3 {
    #role "Physics simulation (rigid body, soft body, collision)"
    #import "#include <btBulletDynamicsCommon.h>"
    #version ">=3.25"
    #scope "compile"
    #license "zlib"
}

#dep assimp {
    #role "3D model import (40+ formats: OBJ, FBX, GLTF, DAE, ...)"
    #import "#include <assimp/Importer.hpp>"
    #version ">=5.4.3"
    #scope "compile"
    #license "BSD-3"
}

#dep spdlog {
    #role "Fast C++ logging"
    #import "#include <spdlog/spdlog.h>"
    #version ">=1.14.1"
    #scope "compile"
    #license "MIT"
}

// ─── Qt (app) ───────────────────────────────────────────────────────

#dep pyside6 {
    #role "Qt container application shell"
    #import "from PySide6.QtWidgets import QApplication"
    #version ">=6.5"
    #scope "app"
}

// ─── Licenses ───────────────────────────────────────────────────────
// Python:  numpy BSD-3 | scipy BSD-3 | matplotlib PSF | pillow HPND
//          networkx BSD-3 | trimesh MIT | torch BSD-3 | pytest MIT
//          pyside6 LGPL-3.0 | sounddevice MIT | soundfile BSD-3 | pydub MIT
// C++ ImGui: glfw zlib | glad MIT/PD | glm MIT | imgui MIT | implot MIT | imnodes MIT
// C++ Vulkan: Headers Apache-2.0 | Loader Apache-2.0 | VMA MIT
//             glslang Apache-2.0+BSD | SPIRV-Tools Apache-2.0
//             SPIRV-Headers MIT | SPIRV-Cross Apache-2.0
// C++ FFT:  fftw3 GPL-2.0 (local only, not linked by default)
// C++ Math: eigen MPL-2.0 | ceres-solver BSD-3
// C++ Game: json MIT | stb MIT/PD | entt MIT | bullet3 zlib | assimp BSD-3 | spdlog MIT
// All Apache 2.0 compatible except fftw3 (optional, local-only)

#endif // DEPS_H
