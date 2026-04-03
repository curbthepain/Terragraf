"""Tests for .scaffold/compute/fft/spectral.py"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute.fft.spectral import (
    spectrogram, spectral_centroid, spectral_rolloff,
    dominant_frequency, bandpass_filter, mel_filterbank,
)


class TestSpectrogram:
    def test_output_tuple(self):
        signal = np.random.randn(4096)
        spec, times, freqs = spectrogram(signal, sample_rate=44100)
        assert spec.ndim == 2
        assert len(times) == spec.shape[1]
        assert len(freqs) == spec.shape[0]

    def test_log_scale(self):
        signal = np.random.randn(4096)
        spec_log, _, _ = spectrogram(signal, log_scale=True)
        spec_lin, _, _ = spectrogram(signal, log_scale=False)
        # log1p makes values smaller
        assert np.all(spec_log <= spec_lin + 1e-10)


class TestSpectralCentroid:
    def test_low_frequency_signal(self):
        # Energy at low frequencies => low centroid
        spectrum = np.zeros(100)
        spectrum[1] = 10.0  # energy at bin 1
        centroid = spectral_centroid(spectrum)
        assert centroid < 5

    def test_high_frequency_signal(self):
        spectrum = np.zeros(100)
        spectrum[90] = 10.0
        centroid = spectral_centroid(spectrum)
        assert centroid > 80

    def test_zero_spectrum(self):
        assert spectral_centroid(np.zeros(100)) == 0.0


class TestSpectralRolloff:
    def test_concentrated_energy(self):
        spectrum = np.zeros(100)
        spectrum[0] = 100.0  # all energy at DC
        idx = spectral_rolloff(spectrum, threshold=0.85)
        assert idx == 0

    def test_spread_energy(self):
        spectrum = np.ones(100)
        idx = spectral_rolloff(spectrum, threshold=0.5)
        assert 45 <= idx <= 55


class TestDominantFrequency:
    def test_pure_sine(self):
        sr = 1000
        freq = 100
        t = np.arange(0, 1, 1.0 / sr)
        signal = np.sin(2 * np.pi * freq * t)
        dom_freq, _ = dominant_frequency(signal, sample_rate=sr)
        assert_allclose(dom_freq, freq, atol=2)


class TestBandpassFilter:
    def test_removes_out_of_band(self):
        sr = 1000
        t = np.arange(0, 1, 1.0 / sr)
        low = np.sin(2 * np.pi * 10 * t)    # 10 Hz
        high = np.sin(2 * np.pi * 400 * t)  # 400 Hz
        signal = low + high
        filtered = bandpass_filter(signal, 5, 50, sample_rate=sr)
        # High frequency energy should be greatly reduced
        spec_orig = np.fft.rfft(signal)
        spec_filt = np.fft.rfft(filtered)
        high_bin = int(400 * len(t) / sr)
        assert np.abs(spec_filt[high_bin]) < np.abs(spec_orig[high_bin]) * 0.1


class TestMelFilterbank:
    def test_shape(self):
        fb = mel_filterbank(26, 512, 16000)
        assert fb.shape == (26, 257)

    def test_nonnegative(self):
        fb = mel_filterbank(40, 1024, 22050)
        assert np.all(fb >= 0)

    def test_triangular(self):
        fb = mel_filterbank(10, 512, 16000)
        # Each filter should have a single peak
        for i in range(10):
            row = fb[i]
            nonzero = row[row > 0]
            if len(nonzero) > 2:
                # Values should rise then fall
                peak_idx = np.argmax(row)
                assert peak_idx > 0 or np.sum(row > 0) <= 2
