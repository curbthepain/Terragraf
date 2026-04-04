"""Integration tests for .scaffold/skills/signal_analyze — FFT analysis workflow."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

SCAFFOLD = Path(__file__).parent.parent
SKILL_DIR = SCAFFOLD / "skills" / "signal_analyze"
RUN_PY = SKILL_DIR / "run.py"


def run_analyze(*args):
    """Run signal_analyze skill as subprocess, return CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(RUN_PY)] + list(args),
        capture_output=True, text=True, cwd=str(SCAFFOLD.parent),
    )


class TestSyntheticSignals:
    def test_sine_440(self):
        result = run_analyze("sine:440:44100:0.5", "--no-render")
        assert result.returncode == 0
        assert "dominant" in result.stdout.lower()
        assert "440" in result.stdout  # should detect 440 Hz

    def test_chirp(self):
        result = run_analyze("chirp:200:44100:0.5", "--no-render")
        assert result.returncode == 0
        assert "Signal Analysis" in result.stdout

    def test_noise(self):
        result = run_analyze("noise:0:44100:0.5", "--no-render")
        assert result.returncode == 0
        assert "spectral" in result.stdout.lower()

    def test_square_wave(self):
        result = run_analyze("square:100:44100:0.5", "--no-render")
        assert result.returncode == 0


class TestBandpass:
    def test_bandpass_flag(self):
        result = run_analyze("sine:440:44100:0.5", "--bandpass", "200-600", "--no-render")
        assert result.returncode == 0
        assert "bandpass" in result.stdout.lower()


class TestFileInput:
    def test_csv_input(self, tmp_path):
        csv_file = tmp_path / "test_signal.csv"
        t = np.linspace(0, 1, 1000, endpoint=False)
        signal = np.sin(2 * np.pi * 100 * t)
        np.savetxt(str(csv_file), signal, delimiter=",")

        result = run_analyze(str(csv_file), "--no-render")
        assert result.returncode == 0

    def test_npy_input(self, tmp_path):
        npy_file = tmp_path / "test_signal.npy"
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 44100)).astype(np.float32)
        np.save(str(npy_file), signal)

        result = run_analyze(str(npy_file), "--no-render")
        assert result.returncode == 0


class TestOutputExport:
    def test_png_export(self, tmp_path):
        out_png = tmp_path / "spectrum.png"
        result = run_analyze("sine:440:44100:0.5", "-o", str(out_png))
        # May fail if matplotlib not installed — skip gracefully
        if "matplotlib not available" in result.stdout:
            pytest.skip("matplotlib not installed")
        assert result.returncode == 0
        assert out_png.exists()
