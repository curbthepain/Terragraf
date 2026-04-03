"""Tests for the visualization layer — heatmap, spectrogram, export, ultrasound, stream."""

import sys
import io
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# matplotlib backend for headless
import matplotlib
matplotlib.use("Agg")


# ── Heatmap ─────────────────────────────────────────────────────────

class TestHeatmap:
    def test_heatmap_returns_figure(self):
        from viz.heatmap import heatmap
        data = np.random.rand(5, 5)
        fig = heatmap(data)
        assert fig is not None
        import matplotlib.pyplot as plt
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_heatmap_with_labels(self):
        from viz.heatmap import heatmap
        data = np.random.rand(3, 4)
        fig = heatmap(data, x_labels=["a", "b", "c", "d"], y_labels=["x", "y", "z"])
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_heatmap_custom_params(self):
        from viz.heatmap import heatmap
        data = np.eye(4)
        fig = heatmap(data, cmap="hot", title="Identity", figsize=(6, 4))
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_annotated_heatmap_returns_figure(self):
        from viz.heatmap import annotated_heatmap
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        fig = annotated_heatmap(data)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_annotated_heatmap_with_labels(self):
        from viz.heatmap import annotated_heatmap
        data = np.random.rand(3, 3)
        fig = annotated_heatmap(data, x_labels=["a", "b", "c"],
                                y_labels=["x", "y", "z"], fmt=".1f")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


# ── Export ──────────────────────────────────────────────────────────

class TestExport:
    def test_save_figure_png(self):
        from viz.export import save_figure
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            save_figure(fig, f.name)
            assert Path(f.name).stat().st_size > 0
        plt.close(fig)

    def test_save_figure_svg(self):
        from viz.export import save_figure
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            save_figure(fig, f.name)
            content = Path(f.name).read_text()
            assert "<svg" in content
        plt.close(fig)

    def test_figure_to_buffer_png(self):
        from viz.export import figure_to_buffer
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        buf = figure_to_buffer(fig, format="png")
        assert isinstance(buf, bytes)
        assert len(buf) > 100
        assert buf[:4] == b'\x89PNG'
        plt.close(fig)

    def test_figure_to_buffer_svg(self):
        from viz.export import figure_to_buffer
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        buf = figure_to_buffer(fig, format="svg")
        assert b"<svg" in buf
        plt.close(fig)


# ── Spectrogram rendering ──────────────────────────────────────────

class TestSpectrogramRender:
    def test_render_spectrogram_returns_figure(self):
        from viz.spectrogram import render_spectrogram
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 8000))
        fig = render_spectrogram(signal, sample_rate=8000, window_size=256, hop_size=64)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_render_mel_spectrogram_returns_figure(self):
        from viz.spectrogram import render_mel_spectrogram
        signal = np.random.randn(4000)
        fig = render_mel_spectrogram(signal, sample_rate=8000, n_filters=32,
                                     window_size=256, hop_size=128)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


# ── Stream plotter ──────────────────────────────────────────────────

class TestStreamPlotter:
    def test_init(self):
        from viz.stream import StreamPlotter
        sp = StreamPlotter(window=100, n_lines=2, labels=["a", "b"])
        assert sp.window == 100
        assert sp.n_lines == 2

    def test_update_stores_data(self):
        from viz.stream import StreamPlotter
        sp = StreamPlotter(window=10, n_lines=1)
        sp.data = [[] for _ in range(sp.n_lines)]
        sp.data[0].append(1.0)
        sp.data[0].append(2.0)
        assert len(sp.data[0]) == 2


# ── Ultrasound ──────────────────────────────────────────────────────

class TestUltrasound:
    def test_dataset_to_volume_shape(self):
        from viz.ultrasound import dataset_to_volume
        data = np.random.rand(50, 5)
        vol = dataset_to_volume(data, resolution=16, sigma=0.5)
        assert vol.shape == (16, 16, 16)

    def test_dataset_to_volume_normalized(self):
        from viz.ultrasound import dataset_to_volume
        data = np.random.rand(20, 3)
        vol = dataset_to_volume(data, resolution=8, sigma=1.0)
        assert vol.min() >= 0.0
        assert vol.max() <= 1.0

    def test_dataset_to_volume_nonzero(self):
        from viz.ultrasound import dataset_to_volume
        data = np.random.rand(30, 4)
        vol = dataset_to_volume(data, resolution=8, sigma=1.0)
        assert vol.max() > 0.0

    def test_dataset_to_volume_custom_dims(self):
        from viz.ultrasound import dataset_to_volume
        data = np.random.rand(20, 6)
        vol = dataset_to_volume(data, resolution=8, feature_dims=(1, 3, 5))
        assert vol.shape == (8, 8, 8)
