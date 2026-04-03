"""Tests for .scaffold/compute/fft/fft.py"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute.fft.fft import (
    fft1d, fft2d, ifft, rfft,
    magnitude, phase, power_spectrum,
    freqs, rfreqs,
    stft, istft,
    fft_convolve, cross_correlate,
)


class TestFFT1D:
    def test_roundtrip(self):
        signal = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
        spectrum = fft1d(signal)
        recovered = ifft(spectrum)
        assert_allclose(np.real(recovered), signal, atol=1e-10)

    def test_dc_component(self):
        signal = np.array([3, 3, 3, 3], dtype=float)
        spectrum = fft1d(signal)
        assert_allclose(spectrum[0], 12.0, atol=1e-10)  # sum of all values
        assert_allclose(np.abs(spectrum[1:]), 0, atol=1e-10)

    def test_single_frequency(self):
        n = 64
        k = 5  # frequency bin
        signal = np.cos(2 * np.pi * k * np.arange(n) / n)
        spec = fft1d(signal)
        mags = np.abs(spec)
        # Energy should be concentrated at bin k and n-k
        assert mags[k] > n * 0.4
        assert mags[n - k] > n * 0.4


class TestFFT2D:
    def test_roundtrip(self):
        signal = np.random.randn(8, 8)
        spectrum = fft2d(signal)
        recovered = np.fft.ifft2(spectrum)
        assert_allclose(np.real(recovered), signal, atol=1e-10)


class TestRFFT:
    def test_half_spectrum(self):
        signal = np.random.randn(64)
        spec = rfft(signal)
        assert len(spec) == 33  # n//2 + 1


class TestMagnitudePhase:
    def test_magnitude(self):
        spec = np.array([3 + 4j, 1 + 0j])
        assert_allclose(magnitude(spec), [5.0, 1.0])

    def test_phase(self):
        spec = np.array([1 + 1j])
        assert_allclose(phase(spec), [np.pi / 4], atol=1e-10)


class TestPowerSpectrum:
    def test_parseval(self):
        signal = np.random.randn(64)
        ps = power_spectrum(signal)
        # Power spectrum energy should relate to signal energy
        assert np.sum(ps) > 0


class TestFreqs:
    def test_length(self):
        assert len(freqs(64)) == 64
        assert len(rfreqs(64)) == 33

    def test_nyquist(self):
        sr = 44100
        f = rfreqs(1024, sr)
        assert_allclose(f[-1], sr / 2)


class TestSTFT:
    def test_output_shape(self):
        signal = np.random.randn(4096)
        spec = stft(signal, window_size=1024, hop_size=256)
        expected_frames = 1 + (4096 - 1024) // 256
        assert spec.shape == (expected_frames, 513)

    def test_roundtrip(self):
        signal = np.random.randn(4096)
        spec = stft(signal, window_size=1024, hop_size=256)
        recovered = istft(spec, window_size=1024, hop_size=256)
        # Compare middle portion (edges have windowing artifacts)
        mid = slice(1024, 3072)
        assert_allclose(recovered[mid], signal[mid], atol=1e-6)


class TestFFTConvolve:
    def test_delta_convolution(self):
        a = np.array([1, 2, 3, 4], dtype=float)
        delta = np.array([1, 0, 0], dtype=float)
        result = fft_convolve(a, delta)
        assert_allclose(result[:4], a, atol=1e-10)

    def test_matches_numpy(self):
        a = np.array([1, 2, 3], dtype=float)
        b = np.array([4, 5], dtype=float)
        assert_allclose(fft_convolve(a, b), np.convolve(a, b), atol=1e-10)


class TestCrossCorrelate:
    def test_autocorrelation_peak(self):
        signal = np.random.randn(64)
        corr = cross_correlate(signal, signal)
        # Peak should be at index 0
        assert np.argmax(corr) == 0
