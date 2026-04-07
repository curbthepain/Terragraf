"""Tests for ml/export.py — ONNX, safetensors, TorchScript round-trips."""

import pytest

torch = pytest.importorskip("torch")
import tempfile
from pathlib import Path

from ml.models.classifier import Classifier
from ml.export import (
    export_onnx, load_onnx,
    export_safetensors, load_safetensors,
    export_torchscript, load_torchscript,
)


@pytest.fixture
def model_and_input():
    model = Classifier(input_dim=16, num_classes=5)
    model.eval()
    dummy = torch.randn(1, 16)
    return model, dummy


class TestONNX:
    def test_export_creates_file(self, model_and_input):
        model, dummy = model_and_input
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.onnx"
            export_onnx(model, dummy, path)
            assert path.exists()
            assert path.stat().st_size > 0

    def test_export_load_roundtrip(self, model_and_input):
        model, dummy = model_and_input
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.onnx"
            export_onnx(model, dummy, path)
            onnx_model = load_onnx(path)
            assert onnx_model is not None


class TestSafetensors:
    def test_export_creates_file(self, model_and_input):
        model, _ = model_and_input
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.safetensors"
            export_safetensors(model, path)
            assert path.exists()

    def test_save_load_roundtrip(self, model_and_input):
        model, dummy = model_and_input
        original_out = model(dummy)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.safetensors"
            export_safetensors(model, path)

            model2 = Classifier(input_dim=16, num_classes=5)
            load_safetensors(model2, path)
            model2.eval()
            loaded_out = model2(dummy)

            assert torch.allclose(original_out, loaded_out, atol=1e-6)


class TestTorchScript:
    def test_export_creates_file(self, model_and_input):
        model, dummy = model_and_input
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.pt"
            export_torchscript(model, dummy, path)
            assert path.exists()

    def test_trace_load_roundtrip(self, model_and_input):
        model, dummy = model_and_input
        original_out = model(dummy)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.pt"
            export_torchscript(model, dummy, path)
            loaded = load_torchscript(path)
            loaded_out = loaded(dummy)

            assert torch.allclose(original_out, loaded_out, atol=1e-6)
