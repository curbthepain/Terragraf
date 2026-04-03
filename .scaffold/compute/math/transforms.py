"""
.scaffold/compute/math/transforms.py
Transforms beyond FFT — wavelet, DCT, Hilbert, z-transform.

Provides:
  - dct, idct                      — Discrete Cosine Transform
  - hilbert                        — Hilbert transform (analytic signal)
  - wavelet_transform              — Continuous wavelet transform (Morlet)
  - z_transform                    — Z-transform evaluation
  - laplace_transform_numerical    — Numerical Laplace transform
"""

import numpy as np
from typing import Optional


def dct(signal: np.ndarray, norm: str = "ortho") -> np.ndarray:
    """
    Discrete Cosine Transform (Type II).
    Used in JPEG, audio compression, feature extraction.
    """
    from scipy.fft import dct as scipy_dct
    return scipy_dct(signal, type=2, norm=norm)


def idct(spectrum: np.ndarray, norm: str = "ortho") -> np.ndarray:
    """Inverse DCT (Type III)."""
    from scipy.fft import idct as scipy_idct
    return scipy_idct(spectrum, type=2, norm=norm)


def hilbert(signal: np.ndarray) -> np.ndarray:
    """
    Hilbert transform — returns the analytic signal.
    The imaginary part is the Hilbert transform of the input.
    Useful for envelope detection, instantaneous frequency.
    """
    from scipy.signal import hilbert as scipy_hilbert
    return scipy_hilbert(signal)


def wavelet_transform(signal: np.ndarray, scales: Optional[np.ndarray] = None,
                       wavelet_freq: float = 6.0,
                       sample_rate: float = 1.0) -> np.ndarray:
    """
    Continuous wavelet transform using Morlet wavelet.
    Returns complex coefficients of shape (n_scales, n_samples).

    signal:       1D input signal
    scales:       array of wavelet scales (default: logarithmic 1-128)
    wavelet_freq: central frequency of Morlet wavelet (default: 6.0)
    sample_rate:  sampling rate of input signal
    """
    n = len(signal)
    if scales is None:
        scales = np.logspace(0, np.log2(128), num=64, base=2)

    dt = 1.0 / sample_rate
    result = np.zeros((len(scales), n), dtype=complex)

    # Compute in frequency domain for efficiency
    freqs = np.fft.fftfreq(n, d=dt)
    signal_fft = np.fft.fft(signal)

    for i, scale in enumerate(scales):
        # Morlet wavelet in frequency domain
        norm_freq = 2 * np.pi * freqs * scale * dt
        wavelet_fft = np.exp(-0.5 * (norm_freq - wavelet_freq) ** 2)
        wavelet_fft *= np.sqrt(2 * np.pi * scale / dt)

        # Convolution via multiplication in frequency domain
        result[i] = np.fft.ifft(signal_fft * np.conj(wavelet_fft))

    return result


def z_transform(signal: np.ndarray, z_values: np.ndarray) -> np.ndarray:
    """
    Evaluate the Z-transform of a discrete signal at given z values.
    X(z) = sum_{n=0}^{N-1} x[n] * z^{-n}
    """
    n = np.arange(len(signal))
    result = np.zeros(len(z_values), dtype=complex)
    for i, z in enumerate(z_values):
        result[i] = np.sum(signal * z ** (-n))
    return result


def laplace_transform_numerical(signal: np.ndarray, s_values: np.ndarray,
                                  dt: float = 1.0) -> np.ndarray:
    """
    Numerical approximation of the Laplace transform.
    F(s) = integral of f(t) * e^{-st} dt, approximated via trapezoidal rule.

    signal:   sampled signal values
    s_values: complex s-plane points to evaluate at
    dt:       time step between samples
    """
    t = np.arange(len(signal)) * dt
    result = np.zeros(len(s_values), dtype=complex)
    for i, s in enumerate(s_values):
        integrand = signal * np.exp(-s * t)
        result[i] = np.trapz(integrand, dx=dt)
    return result
