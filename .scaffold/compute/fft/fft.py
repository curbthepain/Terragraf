"""
.scaffold/compute/fft/fft.py
FFT utilities — NumPy/SciPy backend. Drop-in signal processing toolkit.

Provides:
  - fft1d, fft2d, ifft      — forward/inverse transforms
  - rfft                     — real-valued FFT (half spectrum)
  - stft, istft              — short-time Fourier (audio/signal)
  - magnitude, phase         — complex → real decomposition
  - fft_convolve             — fast convolution via FFT
  - cross_correlate          — signal alignment
"""

import numpy as np
from typing import Optional


def fft1d(signal: np.ndarray) -> np.ndarray:
    """1D FFT. Input: real or complex signal. Output: complex spectrum."""
    return np.fft.fft(signal)


def fft2d(signal: np.ndarray) -> np.ndarray:
    """2D FFT. For images, spatial filtering, etc."""
    return np.fft.fft2(signal)


def ifft(spectrum: np.ndarray) -> np.ndarray:
    """Inverse FFT. Spectrum → time/spatial domain."""
    return np.fft.ifft(spectrum)


def rfft(signal: np.ndarray) -> np.ndarray:
    """Real FFT. Only positive frequencies (input must be real)."""
    return np.fft.rfft(signal)


def magnitude(spectrum: np.ndarray) -> np.ndarray:
    """Complex spectrum → magnitude (amplitude)."""
    return np.abs(spectrum)


def phase(spectrum: np.ndarray) -> np.ndarray:
    """Complex spectrum → phase angle (radians)."""
    return np.angle(spectrum)


def power_spectrum(signal: np.ndarray) -> np.ndarray:
    """Power spectral density (magnitude squared)."""
    spec = rfft(signal)
    return np.abs(spec) ** 2 / len(signal)


def freqs(n: int, sample_rate: float = 1.0) -> np.ndarray:
    """Frequency bins for an FFT of length n."""
    return np.fft.fftfreq(n, d=1.0 / sample_rate)


def rfreqs(n: int, sample_rate: float = 1.0) -> np.ndarray:
    """Frequency bins for a real FFT of length n."""
    return np.fft.rfftfreq(n, d=1.0 / sample_rate)


def stft(signal: np.ndarray, window_size: int = 1024,
         hop_size: int = 256, window: str = "hann") -> np.ndarray:
    """
    Short-Time Fourier Transform.
    Returns complex spectrogram of shape (n_frames, n_freqs).
    """
    if window == "hann":
        win = np.hanning(window_size)
    elif window == "hamming":
        win = np.hamming(window_size)
    else:
        win = np.ones(window_size)

    n_frames = 1 + (len(signal) - window_size) // hop_size
    n_freqs = window_size // 2 + 1
    result = np.zeros((n_frames, n_freqs), dtype=complex)

    for i in range(n_frames):
        start = i * hop_size
        frame = signal[start:start + window_size] * win
        result[i] = np.fft.rfft(frame)

    return result


def istft(spectrogram: np.ndarray, window_size: int = 1024,
          hop_size: int = 256) -> np.ndarray:
    """Inverse STFT. Spectrogram → time-domain signal."""
    n_frames = spectrogram.shape[0]
    length = window_size + (n_frames - 1) * hop_size
    signal = np.zeros(length)
    window_sum = np.zeros(length)
    win = np.hanning(window_size)

    for i in range(n_frames):
        start = i * hop_size
        frame = np.fft.irfft(spectrogram[i])
        signal[start:start + window_size] += frame * win
        window_sum[start:start + window_size] += win ** 2

    # Normalize by window overlap
    nonzero = window_sum > 1e-8
    signal[nonzero] /= window_sum[nonzero]
    return signal


def fft_convolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Fast convolution via FFT. Much faster than np.convolve for large inputs."""
    n = len(a) + len(b) - 1
    # Pad to next power of 2 for speed
    fft_size = 1 << (n - 1).bit_length()
    fa = np.fft.fft(a, fft_size)
    fb = np.fft.fft(b, fft_size)
    result = np.fft.ifft(fa * fb)
    return np.real(result[:n])


def cross_correlate(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cross-correlation via FFT. Find where signals align."""
    n = len(a) + len(b) - 1
    fft_size = 1 << (n - 1).bit_length()
    fa = np.fft.fft(a, fft_size)
    fb = np.fft.fft(b, fft_size)
    result = np.fft.ifft(fa * np.conj(fb))
    return np.real(result[:n])
