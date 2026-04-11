"""
.scaffold/ml/export.py
Model export — ONNX, safetensors, TorchScript.

This module is a thin backwards-compatible shim over ml.model_io. All
serialization work happens in model_io; never add raw torch.save / torch.jit
calls here. See ml/model_io.py for the safety-layer contract.
"""

from pathlib import Path

from . import model_io


def export_onnx(model, dummy_input, path, opset_version=17):
    """Export model to ONNX format (via model_io)."""
    model_io.save_model(
        model, path, format="onnx",
        dummy_input=dummy_input,
        meta={"opset_version": opset_version},
    )
    print(f"ONNX exported: {Path(path)}")


def load_onnx(path):
    """Load and validate an ONNX model (via model_io)."""
    return model_io.load_model(path, format="onnx")


def export_safetensors(model, path):
    """Export model weights to safetensors format (via model_io)."""
    model_io.save_model(model, path, format="safetensors")
    print(f"Safetensors exported: {Path(path)}")


def load_safetensors(model, path):
    """Load model weights from safetensors format (via model_io)."""
    result = model_io.load_model(path, model=model, format="safetensors")
    print(f"Safetensors loaded: {Path(path)}")
    return result


def export_torchscript(model, dummy_input, path):
    """Export model to TorchScript via tracing (via model_io)."""
    model_io.save_model(model, path, format="jit", dummy_input=dummy_input)
    print(f"TorchScript exported: {Path(path)}")


def load_torchscript(path):
    """Load a TorchScript model (via model_io)."""
    return model_io.load_model(path, format="jit")
