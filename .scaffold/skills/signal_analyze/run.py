"""
signal_analyze — End-to-end signal/audio analysis workflow.

Pipeline: load/generate signal → FFT → spectral features → optional bandpass
         → spectrogram → export PNG.

Usage:
    python run.py <input> [options]
    python run.py --synthetic sine:440:44100:1.0
    python run.py audio.wav --mel --bandpass 200-4000 --output spec.png
"""

import argparse
import sys
from pathlib import Path

import numpy as np

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCAFFOLD))

from compute.fft.fft import rfft, magnitude, fft1d, power_spectrum
from compute.fft.spectral import (
    spectrogram, spectral_centroid, spectral_rolloff,
    dominant_frequency, bandpass_filter,
)

# ANSI
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def generate_synthetic(spec):
    """Parse synthetic spec: type:freq:sr:duration."""
    parts = spec.split(":")
    sig_type = parts[0]
    freq = float(parts[1]) if len(parts) > 1 else 440.0
    sr = float(parts[2]) if len(parts) > 2 else 44100.0
    duration = float(parts[3]) if len(parts) > 3 else 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    if sig_type == "sine":
        signal = np.sin(2 * np.pi * freq * t)
    elif sig_type == "chirp":
        signal = np.sin(2 * np.pi * freq * t * (1 + t))
    elif sig_type == "noise":
        signal = np.random.randn(len(t))
    elif sig_type == "square":
        signal = np.sign(np.sin(2 * np.pi * freq * t))
    else:
        print(f"  {RED}Unknown signal type: {sig_type}{RESET}")
        print(f"  {DIM}Available: sine, chirp, noise, square{RESET}")
        sys.exit(1)
    return signal.astype(np.float32), sr


def load_signal(path):
    """Load signal from WAV or CSV."""
    path = Path(path)
    if path.suffix in (".wav", ".flac", ".ogg"):
        try:
            import soundfile as sf
            data, sr = sf.read(str(path), dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            return data, sr
        except ImportError:
            print(f"  {RED}soundfile not installed (pip install soundfile){RESET}")
            sys.exit(1)
    elif path.suffix == ".csv":
        data = np.loadtxt(str(path), delimiter=",", dtype=np.float32)
        if data.ndim > 1:
            data = data[:, 0]
        return data, 1.0
    elif path.suffix == ".npy":
        data = np.load(str(path)).astype(np.float32)
        return data, 1.0
    else:
        print(f"  {RED}Unsupported format: {path.suffix}{RESET}")
        print(f"  {DIM}Supported: .wav, .flac, .ogg, .csv, .npy{RESET}")
        sys.exit(1)


def run_analysis(signal, sr, args):
    """Run the full analysis pipeline."""
    print(f"{BOLD}Signal Analysis{RESET}")
    print(f"  samples    {len(signal)}")
    print(f"  rate       {sr:.0f} Hz")
    print(f"  duration   {len(signal)/sr:.3f} s")
    print()

    # Optional bandpass
    if args.bandpass:
        low, high = map(float, args.bandpass.split("-"))
        signal = bandpass_filter(signal, low, high, sr)
        print(f"  {GREEN}bandpass{RESET}  {low:.0f}-{high:.0f} Hz")

    # FFT
    spectrum = rfft(signal)
    mag = magnitude(spectrum)

    # Spectral features
    dom_freq, dom_mag = dominant_frequency(signal, sr)
    centroid = spectral_centroid(mag)
    rolloff = spectral_rolloff(mag)

    print(f"{BOLD}Spectral Features{RESET}")
    print(f"  dominant   {dom_freq:.1f} Hz (mag: {dom_mag:.4f})")
    print(f"  centroid   bin {centroid:.1f}")
    print(f"  rolloff    bin {rolloff:.1f}")
    print()

    # Power spectrum
    psd = power_spectrum(signal)
    print(f"  PSD bins   {len(psd)}")
    print(f"  PSD max    {np.max(psd):.6f}")
    print()

    # Spectrogram + render
    output = args.output
    if output or not args.no_render:
        try:
            from viz.spectrogram import render_spectrogram, render_mel_spectrogram
            from viz.export import save_figure

            if args.mel:
                fig = render_mel_spectrogram(signal, sample_rate=sr)
                label = "mel spectrogram"
            else:
                fig = render_spectrogram(signal, sample_rate=sr)
                label = "spectrogram"

            if output:
                save_figure(fig, output)
                print(f"  {GREEN}saved{RESET}    {output} ({label})")
            else:
                import matplotlib.pyplot as plt
                plt.show()
        except ImportError as e:
            print(f"  {YELLOW}matplotlib not available for rendering: {e}{RESET}")

    return 0


def cli():
    parser = argparse.ArgumentParser(description="Signal analysis workflow")
    parser.add_argument("input", help="Input file (WAV/CSV/NPY) or --synthetic spec")
    parser.add_argument("--synthetic", action="store_true",
                        help="Treat input as synthetic spec (type:freq:sr:dur)")
    parser.add_argument("--bandpass", metavar="LOW-HIGH",
                        help="Bandpass filter range in Hz (e.g., 200-4000)")
    parser.add_argument("--mel", action="store_true", help="Use mel spectrogram")
    parser.add_argument("--output", "-o", help="Output PNG path")
    parser.add_argument("--no-render", action="store_true",
                        help="Skip spectrogram rendering")
    args = parser.parse_args()

    if args.synthetic or (":" in args.input and not Path(args.input).exists()):
        signal, sr = generate_synthetic(args.input)
    else:
        signal, sr = load_signal(args.input)

    return run_analysis(signal, sr, args)


if __name__ == "__main__":
    sys.exit(cli())
