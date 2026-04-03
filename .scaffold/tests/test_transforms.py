"""Tests for .scaffold/compute/math/transforms.py"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute.math.transforms import (
    dct, idct, hilbert, wavelet_transform,
    z_transform, laplace_transform_numerical,
)


class TestDCT:
    def test_roundtrip(self):
        signal = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
        transformed = dct(signal)
        recovered = idct(transformed)
        assert_allclose(recovered, signal, atol=1e-10)

    def test_energy_concentration(self):
        # DCT should concentrate energy in low coefficients for smooth signals
        signal = np.cos(np.linspace(0, 2 * np.pi, 64))
        transformed = dct(signal)
        low_energy = np.sum(transformed[:8] ** 2)
        total_energy = np.sum(transformed ** 2)
        assert low_energy / total_energy > 0.9


class TestHilbert:
    def test_analytic_signal_length(self):
        signal = np.sin(np.linspace(0, 4 * np.pi, 128))
        analytic = hilbert(signal)
        assert len(analytic) == len(signal)

    def test_envelope_of_sine(self):
        t = np.linspace(0, 1, 1000)
        signal = np.sin(2 * np.pi * 10 * t)
        analytic = hilbert(signal)
        envelope = np.abs(analytic)
        # Envelope of pure sine should be ~1.0
        assert_allclose(envelope[100:-100], 1.0, atol=0.05)


class TestWaveletTransform:
    def test_output_shape(self):
        signal = np.sin(np.linspace(0, 4 * np.pi, 256))
        scales = np.array([1, 2, 4, 8, 16])
        result = wavelet_transform(signal, scales=scales)
        assert result.shape == (5, 256)

    def test_default_scales(self):
        signal = np.random.randn(128)
        result = wavelet_transform(signal)
        assert result.shape[0] == 64  # default 64 scales
        assert result.shape[1] == 128


class TestZTransform:
    def test_unit_impulse(self):
        # Z-transform of delta[n] = 1 for all z
        signal = np.array([1, 0, 0, 0], dtype=float)
        z_vals = np.array([1 + 0j, 2 + 0j, 0.5 + 0.5j])
        result = z_transform(signal, z_vals)
        assert_allclose(result, [1, 1, 1], atol=1e-10)

    def test_geometric_series(self):
        # x[n] = a^n => X(z) = z/(z-a) = 1/(1-a*z^-1) for |z|>|a|
        a = 0.5
        signal = np.array([a ** n for n in range(50)])
        z = np.array([2.0 + 0j])  # |z|>|a|
        result = z_transform(signal, z)
        expected = 1.0 / (1 - a / z[0])
        assert_allclose(result[0], expected, atol=1e-6)


class TestLaplaceTransformNumerical:
    def test_exponential_decay(self):
        # f(t) = e^{-t}, F(s) = 1/(s+1)
        dt = 0.001
        t = np.arange(0, 10, dt)
        signal = np.exp(-t)
        s_vals = np.array([1.0 + 0j, 2.0 + 0j])
        result = laplace_transform_numerical(signal, s_vals, dt=dt)
        expected = 1.0 / (s_vals + 1)
        assert_allclose(result, expected, atol=0.01)
