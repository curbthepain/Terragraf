// .scaffold/headers/project.h
// Declares the project's module structure and boundaries.
// AI reads this to understand WHAT exists without scanning every file.

#ifndef PROJECT_H
#define PROJECT_H

// ─── Project Declaration ─────────────────────────────────────────────

#project {
    name: "terragraf",
    lang: "python, c++, glsl, javascript, bash",
    type: "scaffolding-system"
}

// ─── Module Declarations ─────────────────────────────────────────────
// Each module: what it does, where it lives, what it exports, what it needs.

#module math {
    #path "compute/math"
    #exports [mat_mul, mat_inv, determinant, eigenvalues, eigenvectors, svd, lu_decompose, solve, norm, rank, poly_eval, poly_roots, interpolate, curve_fit_poly, lagrange_interpolate, newton_interpolate, descriptive, correlation, covariance, linear_regression, normal_pdf, normal_cdf, t_test, chi_squared, percentile, zscore, dct, idct, hilbert, wavelet_transform, z_transform, laplace_transform_numerical]
    #depends [fft]
    #desc "Linear algebra, statistics, algebra, and signal transforms (NumPy/SciPy)"
}

#module fft {
    #path "compute/fft"
    #exports [fft1d, fft2d, ifft, rfft, magnitude, phase, power_spectrum, freqs, rfreqs, stft, istft, fft_convolve, cross_correlate, spectrogram, spectral_centroid, spectral_rolloff, dominant_frequency, bandpass_filter, mel_filterbank]
    #depends []
    #desc "FFT utilities and spectral analysis (NumPy backend)"
}

#module ml {
    #path "ml"
    #exports [ScaffoldModel, Classifier, CNN, Transformer, ScaffoldDataset, create_dataloader, Trainer, Evaluator]
    #depends [math]
    #desc "PyTorch ML pipeline — models, datasets, training, evaluation"
}

#module viz {
    #path "viz"
    #exports [render_spectrogram, render_mel_spectrogram, render_heatmap, StreamPlotter, export_figure, VolumeRenderer, NodeGraph3D, MeshGenerator, SceneManager]
    #depends [fft, math]
    #desc "2D and 3D visualization — spectrograms, heatmaps, volumes, node graphs"
}

#module vulkan {
    #path "compute/vulkan"
    #exports []
    #depends []
    #desc "Vulkan compute pipeline (instance, pipeline, memory, layers)"
}

#module render {
    #path "compute/render"
    #exports []
    #depends [vulkan]
    #desc "OpenGL rendering — GL context, mesh renderer, volume renderer"
}

#module generators {
    #path "generators"
    #exports [resolve, gen_module, gen_model, gen_shader, scaffold]
    #depends [ml, math, vulkan]
    #desc "Code generators — models, shaders, modules, include resolver"
}

#module instances {
    #path "instances"
    #exports [InstanceManager, ScaffoldInstance]
    #depends []
    #desc "Multi-instancing — parallel AI coordination via filesystem IPC"
}

#module git {
    #path "git"
    #exports [branch, commit, pr]
    #depends []
    #desc "Git workflow scripts — branch, commit, PR, CI/CD templates"
}

#module tests {
    #path "tests"
    #exports []
    #depends [math, fft, generators]
    #desc "Pytest test suite — 95 tests covering math, FFT, spectral, generators"
}

#endif // PROJECT_H
