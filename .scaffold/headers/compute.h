// .scaffold/headers/compute.h
// GPU compute, FFT, and Vulkan contract.
// Declares the compute pipeline: what hardware, what operations, what shaders.

#ifndef COMPUTE_H
#define COMPUTE_H

#include "project.h"

// ─── FFT / Signal Processing ─────────────────────────────────────────
// Fast Fourier Transform and spectral analysis

#fft {
    backend: "{{compute.fft_backend}}",
    // Backends by capability:
    //   "numpy"   — CPU, pure Python, always available
    //   "scipy"   — CPU, optimized, needs scipy
    //   "fftw"    — CPU, fastest CPU FFT, needs libfftw3
    //   "cufft"   — CUDA GPU, needs CUDA toolkit
    //   "vulkan"  — Vulkan compute shader FFT (see shaders/fft.comp)

    templates: {
        python:  "compute/fft/fft.py",
        cpp:     "compute/fft/fft.cpp",
        spectral: "compute/fft/spectral.py"
    },

    // Common operations the AI should know about:
    //   fft1d, fft2d, ifft, rfft    — forward/inverse transforms
    //   stft, istft                  — short-time fourier (audio/signal)
    //   spectral_density             — power spectrum
    //   convolution via fft          — fast convolution for large kernels
    //   cross_correlation            — signal alignment
}

// ─── Vulkan ──────────────────────────────────────────────────────────
// Vulkan instance, compute pipelines, memory management, layers

#vulkan {
    api_version: "{{compute.vulkan_api}}",
    shader_lang: "{{compute.shader_lang}}",

    templates: {
        instance:  "compute/vulkan/instance.cpp",
        pipeline:  "compute/vulkan/pipeline.cpp",
        memory:    "compute/vulkan/memory.cpp",
        layer:     "compute/vulkan/layer.cpp"
    },

    // Vulkan layer development (Terragraf-specific):
    //   A Vulkan layer intercepts API calls between the app and the driver.
    //   Layers can validate, profile, debug, or modify Vulkan behavior.
    //   See compute/vulkan/layer.cpp for the scaffold.
}

// ─── GPU Compute ─────────────────────────────────────────────────────
// General-purpose GPU compute via shaders

#gpu_compute {
    shader_dir: "compute/shaders/",

    templates: {
        compute_shader: "compute/shaders/compute.comp",
        fft_shader:     "compute/shaders/fft.comp"
    },

    // Shader compilation:
    //   GLSL → SPIR-V via glslangValidator or shaderc
    //   HLSL → SPIR-V via dxc
    //   WGSL → native (WebGPU)
}

// ─── CUDA (optional) ─────────────────────────────────────────────────

#cuda {
    enabled: false,
    arch: "",           // "sm_70", "sm_86", "sm_90"
    // When enabled, prefer cuFFT over CPU FFT
    // When enabled, PyTorch automatically uses CUDA tensors
}

#endif // COMPUTE_H
