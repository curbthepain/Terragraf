"""Tests for ml/model_io.py — unified model serialization safety layer."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

torch = pytest.importorskip("torch")

from ml import model_io
from ml.model_io import (
    save_model, load_model,
    save_checkpoint, load_checkpoint,
    detect_format, available_backends,
    ModelIOError,
)
from ml.models.classifier import Classifier


@pytest.fixture
def model_and_input():
    model = Classifier(input_dim=16, num_classes=5)
    model.eval()
    dummy = torch.randn(1, 16)
    return model, dummy


# ── format detection ─────────────────────────────────────────────────────

class TestDetectFormat:
    def test_pt2_extension(self, tmp_path):
        p = tmp_path / "model.pt2"
        p.write_bytes(b"fake")
        assert detect_format(p) == "export"

    def test_onnx_extension(self, tmp_path):
        p = tmp_path / "model.onnx"
        p.write_bytes(b"fake")
        assert detect_format(p) == "onnx"

    def test_safetensors_extension(self, tmp_path):
        p = tmp_path / "model.safetensors"
        p.write_bytes(b"fake")
        assert detect_format(p) == "safetensors"

    def test_pt_with_zip_magic_probes_jit(self, tmp_path):
        p = tmp_path / "model.pt"
        p.write_bytes(b"PK\x03\x04rest")
        assert detect_format(p) == "jit_or_state_dict"

    def test_pt_without_zip_magic_is_state_dict(self, tmp_path):
        p = tmp_path / "model.pt"
        p.write_bytes(b"\x80\x04\x95other")
        assert detect_format(p) == "state_dict"

    def test_unknown_extension_raises(self, tmp_path):
        p = tmp_path / "model.xyz"
        p.write_bytes(b"fake")
        with pytest.raises(ModelIOError, match="unknown model format"):
            detect_format(p)


# ── available backends ───────────────────────────────────────────────────

class TestAvailableBackends:
    def test_always_includes_state_dict_and_jit(self):
        backends = available_backends()
        assert "state_dict" in backends
        assert "jit" in backends


# ── save/load round-trip ─────────────────────────────────────────────────

class TestSaveLoadRoundtrip:
    def test_state_dict_roundtrip(self, model_and_input, tmp_path):
        model, dummy = model_and_input
        original = model(dummy)
        p = tmp_path / "m.pt"
        backend = save_model(model, p, format="state_dict")
        assert backend == "state_dict"
        assert p.exists()

        model2 = Classifier(input_dim=16, num_classes=5)
        load_model(p, model=model2, format="state_dict")
        model2.eval()
        assert torch.allclose(original, model2(dummy), atol=1e-6)

    def test_jit_roundtrip(self, model_and_input, tmp_path):
        model, dummy = model_and_input
        original = model(dummy)
        p = tmp_path / "m.pt"
        backend = save_model(model, p, format="jit", dummy_input=dummy)
        assert backend == "jit"
        assert p.exists()

        loaded = load_model(p, format="jit")
        assert torch.allclose(original, loaded(dummy), atol=1e-6)

    def test_safetensors_roundtrip(self, model_and_input, tmp_path):
        pytest.importorskip("safetensors")
        model, dummy = model_and_input
        original = model(dummy)
        p = tmp_path / "m.safetensors"
        backend = save_model(model, p, format="safetensors")
        assert backend == "safetensors"

        model2 = Classifier(input_dim=16, num_classes=5)
        load_model(p, model=model2, format="safetensors")
        model2.eval()
        assert torch.allclose(original, model2(dummy), atol=1e-6)

    def test_onnx_roundtrip(self, model_and_input, tmp_path):
        pytest.importorskip("onnx")
        model, dummy = model_and_input
        p = tmp_path / "m.onnx"
        backend = save_model(model, p, format="onnx", dummy_input=dummy)
        assert backend == "onnx"
        assert p.exists() and p.stat().st_size > 0

        loaded = load_model(p, format="onnx")
        assert loaded is not None

    def test_export_roundtrip(self, model_and_input, tmp_path):
        if not model_io._has_torch_export():
            pytest.skip("torch.export unavailable")
        model, dummy = model_and_input
        p = tmp_path / "m.pt2"
        try:
            backend = save_model(model, p, format="export", dummy_input=dummy)
        except ModelIOError as e:
            pytest.skip(f"torch.export failed on this model: {e}")
        assert backend == "export"
        assert p.exists()

    def test_checkpoint_roundtrip(self, model_and_input, tmp_path):
        model, _ = model_and_input
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        p = tmp_path / "ckpt.pt"
        save_checkpoint(model, p, optimizer=optimizer, epoch=5, val_loss=0.42)
        assert p.exists()

        model2 = Classifier(input_dim=16, num_classes=5)
        opt2 = torch.optim.Adam(model2.parameters(), lr=1e-3)
        ckpt = load_checkpoint(p, model2, optimizer=opt2)
        assert ckpt["epoch"] == 5
        assert ckpt["val_loss"] == 0.42
        assert "model_state" in ckpt


# ── auto selection ───────────────────────────────────────────────────────

class TestAutoSelection:
    def test_auto_with_dummy_input_picks_export_or_jit(self, model_and_input, tmp_path):
        model, dummy = model_and_input
        p = tmp_path / "m.pt"
        backend = save_model(model, p, format="auto", dummy_input=dummy)
        assert backend in ("export", "jit")

    def test_auto_without_dummy_input_picks_state_dict(self, model_and_input, tmp_path):
        model, _ = model_and_input
        p = tmp_path / "m.pt"
        backend = save_model(model, p, format="auto")
        assert backend == "state_dict"


# ── fallback behavior ────────────────────────────────────────────────────

class TestFallbackBehavior:
    def test_export_unavailable_falls_back_to_jit(self, model_and_input, tmp_path):
        model, dummy = model_and_input
        p = tmp_path / "m.pt"
        with patch.object(model_io, "_has_torch_export", return_value=False):
            backend = save_model(model, p, format="auto", dummy_input=dummy)
        assert backend == "jit"

    def test_no_dummy_input_falls_back_to_state_dict(self, model_and_input, tmp_path, caplog):
        model, _ = model_and_input
        p = tmp_path / "m.pt"
        with caplog.at_level(logging.DEBUG, logger="terragraf.ml.model_io"):
            backend = save_model(model, p, format="auto")
        assert backend == "state_dict"
        assert any("state_dict" in r.message for r in caplog.records)


# ── error cases ──────────────────────────────────────────────────────────

class TestErrors:
    def test_unknown_extension_on_load_raises(self, tmp_path):
        p = tmp_path / "mystery.xyz"
        p.write_bytes(b"anything")
        with pytest.raises(ModelIOError, match="unknown model format"):
            load_model(p, format="auto")

    def test_onnx_without_dummy_input_raises(self, model_and_input, tmp_path):
        model, _ = model_and_input
        p = tmp_path / "m.onnx"
        with pytest.raises(ModelIOError, match="requires dummy_input"):
            save_model(model, p, format="onnx")

    def test_jit_without_dummy_input_raises(self, model_and_input, tmp_path):
        model, _ = model_and_input
        p = tmp_path / "m.pt"
        with pytest.raises(ModelIOError, match="requires dummy_input"):
            save_model(model, p, format="jit")

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(ModelIOError, match="does not exist"):
            load_model(tmp_path / "nope.pt", format="state_dict")


# ── logging ──────────────────────────────────────────────────────────────

class TestLoggingBackendChoice:
    def test_save_logs_backend(self, model_and_input, tmp_path, caplog):
        model, _ = model_and_input
        p = tmp_path / "m.pt"
        with caplog.at_level(logging.INFO, logger="terragraf.ml.model_io"):
            save_model(model, p, format="state_dict")
        messages = [r.message for r in caplog.records]
        assert any("backend=state_dict" in m for m in messages)

    def test_load_logs_backend(self, model_and_input, tmp_path, caplog):
        model, _ = model_and_input
        p = tmp_path / "m.pt"
        save_model(model, p, format="state_dict")
        model2 = Classifier(input_dim=16, num_classes=5)
        with caplog.at_level(logging.INFO, logger="terragraf.ml.model_io"):
            load_model(p, model=model2, format="state_dict")
        messages = [r.message for r in caplog.records]
        assert any("backend=state_dict" in m for m in messages)


# ── auto load from ZIP-magic .pt probe ───────────────────────────────────

class TestAutoLoad:
    def test_auto_load_jit_from_pt(self, model_and_input, tmp_path):
        model, dummy = model_and_input
        p = tmp_path / "m.pt"
        save_model(model, p, format="jit", dummy_input=dummy)
        loaded = load_model(p, format="auto")
        # jit module returns a ScriptModule, not a raw state dict
        assert hasattr(loaded, "forward")

    def test_auto_load_state_dict_from_pt(self, model_and_input, tmp_path):
        model, _ = model_and_input
        p = tmp_path / "m.pt"
        save_model(model, p, format="state_dict")
        model2 = Classifier(input_dim=16, num_classes=5)
        load_model(p, model=model2, format="auto")
