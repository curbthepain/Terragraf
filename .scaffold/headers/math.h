// .scaffold/headers/math.h
// Math & algebra primitives contract.
// Declares the math subsystem: linalg, algebra, statistics, transforms.

#ifndef MATH_H
#define MATH_H

#include "project.h"
#include "compute.h"

// ─── Linear Algebra ─────────────────────────────────────────────────
// Matrix operations, decompositions, solvers

#linalg {
    template: "compute/math/linalg.py",
    backend: "numpy",   // numpy.linalg + scipy.linalg

    // Operations:
    //   mat_mul, mat_inv, determinant — basic matrix ops
    //   eigenvalues, eigenvectors     — eigendecomposition
    //   svd                           — singular value decomposition
    //   lu_decompose                  — LU factorization (scipy)
    //   solve                         — linear system solver (Ax = b)
    //   norm, rank                    — matrix properties
}

// ─── Algebra ────────────────────────────────────────────────────────
// Polynomial evaluation, roots, interpolation, curve fitting

#algebra {
    template: "compute/math/algebra.py",

    // Operations:
    //   poly_eval              — evaluate polynomial at points
    //   poly_roots             — find polynomial roots
    //   interpolate            — polynomial interpolation from data
    //   curve_fit_poly         — least-squares polynomial fit
    //   lagrange_interpolate   — Lagrange interpolation
    //   newton_interpolate     — Newton divided difference
}

// ─── Statistics ─────────────────────────────────────────────────────
// Distributions, hypothesis tests, correlation, regression

#stats {
    template: "compute/math/stats.py",
    backend: "numpy",   // numpy + scipy.stats

    // Operations:
    //   descriptive        — mean, median, std, var, skew, kurtosis
    //   correlation        — Pearson r
    //   covariance         — covariance matrix
    //   linear_regression  — y = mx + b with R²
    //   normal_pdf/cdf     — Gaussian distribution
    //   t_test             — Welch's two-sample t-test (scipy)
    //   chi_squared        — chi² goodness-of-fit (scipy)
    //   percentile, zscore — data standardization
}

// ─── Transforms (beyond FFT) ────────────────────────────────────────
// DCT, Hilbert, wavelet, z-transform

#transforms {
    template: "compute/math/transforms.py",
    backend: "scipy",

    // Operations:
    //   dct, idct                      — Discrete Cosine Transform
    //   hilbert                        — analytic signal / envelope
    //   wavelet_transform              — continuous wavelet (Morlet)
    //   z_transform                    — Z-transform evaluation
    //   laplace_transform_numerical    — numerical Laplace approx
    //
    // Builds on: compute/fft/ for FFT-based operations
}

#endif // MATH_H
