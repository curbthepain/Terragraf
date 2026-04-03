"""
.scaffold/viz/spectrogram.py
Spectrogram rendering — builds on compute/fft/spectral.py.

Provides:
  - render_spectrogram     — time-frequency spectrogram plot
  - render_mel_spectrogram — mel-scale spectrogram plot
"""

import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from compute.fft import spectral


def render_spectrogram(signal, sample_rate=1.0, window_size=1024,
                       hop_size=256, cmap="viridis", title="Spectrogram",
                       figsize=(12, 4)):
    """
    Render a spectrogram from a signal.
    Returns a matplotlib Figure object.
    """
    import matplotlib.pyplot as plt

    spec, times, freqs = spectral.spectrogram(
        signal, sample_rate, window_size, hop_size
    )

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    ax.imshow(
        spec, aspect="auto", origin="lower", cmap=cmap,
        extent=[times[0], times[-1], freqs[0], freqs[-1]]
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def render_mel_spectrogram(signal, sample_rate=22050, n_filters=128,
                           window_size=2048, hop_size=512,
                           cmap="magma", title="Mel Spectrogram",
                           figsize=(12, 4)):
    """
    Render a mel-scale spectrogram.
    Uses mel filterbank from compute/fft/spectral.py.
    """
    import matplotlib.pyplot as plt

    spec, times, freqs = spectral.spectrogram(
        signal, sample_rate, window_size, hop_size, log_scale=False
    )

    mel_fb = spectral.mel_filterbank(n_filters, window_size, sample_rate)
    mel_spec = mel_fb @ spec
    mel_spec = np.log1p(mel_spec)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    ax.imshow(
        mel_spec, aspect="auto", origin="lower", cmap=cmap,
        extent=[times[0], times[-1], 0, n_filters]
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mel Band")
    ax.set_title(title)
    fig.tight_layout()
    return fig
