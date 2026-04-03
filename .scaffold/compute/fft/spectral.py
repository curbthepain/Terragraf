"""
.scaffold/compute/fft/spectral.py
Spectral analysis utilities built on top of fft.py.

Provides:
  - spectrogram          — visual-ready time-frequency representation
  - mel_filterbank       — mel-scale filters for audio
  - spectral_centroid    — "center of mass" of the spectrum
  - spectral_rolloff     — frequency below which X% of energy sits
  - bandpass_filter      — FFT-based frequency band filtering
  - dominant_frequency   — find the strongest frequency component
"""

import numpy as np
from . import fft as fft_utils


def spectrogram(signal, sample_rate=1.0, window_size=1024,
                hop_size=256, log_scale=True):
    """
    Compute a spectrogram (magnitude of STFT).
    Returns (spec, times, freqs) for plotting.
    """
    stft = fft_utils.stft(signal, window_size, hop_size)
    spec = np.abs(stft).T  # (n_freqs, n_frames) for imshow

    if log_scale:
        spec = np.log1p(spec)

    n_frames = stft.shape[0]
    times = np.arange(n_frames) * hop_size / sample_rate
    freqs = fft_utils.rfreqs(window_size, sample_rate)

    return spec, times, freqs


def spectral_centroid(spectrum, freqs=None):
    """
    Spectral centroid — the "center of mass" of the spectrum.
    Higher = brighter sound. Lower = darker sound.
    """
    mag = np.abs(spectrum)
    if freqs is None:
        freqs = np.arange(len(mag))
    total = np.sum(mag)
    if total == 0:
        return 0.0
    return np.sum(freqs * mag) / total


def spectral_rolloff(spectrum, threshold=0.85):
    """
    Frequency below which `threshold` (e.g. 85%) of spectral energy sits.
    """
    mag = np.abs(spectrum) ** 2
    total_energy = np.sum(mag)
    cumulative = np.cumsum(mag)
    idx = np.searchsorted(cumulative, threshold * total_energy)
    return min(idx, len(spectrum) - 1)


def dominant_frequency(signal, sample_rate=1.0):
    """Find the strongest frequency component in a signal."""
    spec = fft_utils.rfft(signal)
    freqs = fft_utils.rfreqs(len(signal), sample_rate)
    magnitudes = np.abs(spec)
    peak_idx = np.argmax(magnitudes[1:]) + 1  # Skip DC
    return freqs[peak_idx], magnitudes[peak_idx]


def bandpass_filter(signal, low_freq, high_freq, sample_rate=1.0):
    """
    FFT-based bandpass filter. Zero out frequencies outside [low, high].
    """
    spec = np.fft.fft(signal)
    freqs = np.fft.fftfreq(len(signal), d=1.0 / sample_rate)

    mask = (np.abs(freqs) >= low_freq) & (np.abs(freqs) <= high_freq)
    spec_filtered = spec * mask

    return np.real(np.fft.ifft(spec_filtered))


def mel_filterbank(n_filters, n_fft, sample_rate, low_freq=0, high_freq=None):
    """
    Create a mel-scale filterbank matrix.
    Useful for audio ML features (mel spectrograms).
    """
    if high_freq is None:
        high_freq = sample_rate / 2

    def hz_to_mel(hz):
        return 2595 * np.log10(1 + hz / 700)

    def mel_to_hz(mel):
        return 700 * (10 ** (mel / 2595) - 1)

    low_mel = hz_to_mel(low_freq)
    high_mel = hz_to_mel(high_freq)
    mel_points = np.linspace(low_mel, high_mel, n_filters + 2)
    hz_points = mel_to_hz(mel_points)

    bins = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
    n_freqs = n_fft // 2 + 1
    filterbank = np.zeros((n_filters, n_freqs))

    for i in range(n_filters):
        left, center, right = bins[i], bins[i + 1], bins[i + 2]
        for j in range(left, center):
            if center != left:
                filterbank[i, j] = (j - left) / (center - left)
        for j in range(center, right):
            if right != center:
                filterbank[i, j] = (right - j) / (right - center)

    return filterbank
