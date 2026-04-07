"""
.scaffold/ml/model_io.py

Unified model serialization safety layer.

ALL model save/load goes through this module. Never call torch.jit.save,
torch.jit.load, torch.save, torch.load, torch.onnx.export, or
safetensors.torch.{save_file,load_file} directly from anywhere else in the
codebase — route through save_model/load_model/save_checkpoint/load_checkpoint.

Backends (auto fallback order for save, format="auto"):
  1. "export"     — torch.export -> .pt2  (preferred when available + dummy_input given)
  2. "jit"        — torch.jit.trace + ScriptModule.save -> .pt
  3. "state_dict" — torch.save({"model_state": ...}) -> .pt  (last resort, always works)

Explicit-only backends (never picked by auto):
  4. "onnx"        — torch.onnx.export -> .onnx
  5. "safetensors" — safetensors.torch.save_file -> .safetensors

Format detection (load, format="auto"):
  - Extension first: .pt2 / .onnx / .safetensors / .pt / .pth
  - For .pt/.pth: read first 8 bytes. ZIP magic (PK\\x03\\x04) -> try jit, fall
    back to state_dict on failure. Otherwise -> state_dict.

Every save/load logs "backend=<name> path=<p>" at INFO. Fallback events at DEBUG.
Errors raise ModelIOError with the path, requested/detected format, available
backends, and an install hint where applicable.
"""

from __future__ import annotations

import logging
from pathlib import Path

import torch

logger = logging.getLogger("terragraf.ml.model_io")


class ModelIOError(RuntimeError):
    """Raised when a model cannot be saved or loaded with any available backend."""


# ── backend probes ────────────────────────────────────────────────────────

def _has_torch_export() -> bool:
    try:
        from torch.export import export  # noqa: F401
        return True
    except Exception:
        return False


def _has_safetensors() -> bool:
    try:
        import safetensors.torch  # noqa: F401
        return True
    except Exception:
        return False


def _has_onnx() -> bool:
    try:
        import onnx  # noqa: F401
        return True
    except Exception:
        return False


def available_backends() -> list[str]:
    """Return the list of backends that can be used in this environment."""
    backends = ["state_dict", "jit"]  # always available with torch
    if _has_torch_export():
        backends.insert(0, "export")
    if _has_onnx():
        backends.append("onnx")
    if _has_safetensors():
        backends.append("safetensors")
    return backends


# ── format detection ──────────────────────────────────────────────────────

_EXT_TO_FORMAT = {
    ".pt2": "export",
    ".onnx": "onnx",
    ".safetensors": "safetensors",
}

_ZIP_MAGIC = b"PK\x03\x04"


def detect_format(path) -> str:
    """Detect serialization format from path.

    Uses extension first, then sniffs the file header for .pt/.pth.
    Raises ModelIOError if the format cannot be determined.
    """
    p = Path(path)
    ext = p.suffix.lower()

    if ext in _EXT_TO_FORMAT:
        return _EXT_TO_FORMAT[ext]

    if ext in (".pt", ".pth"):
        # Need to sniff header — ZIP magic = jit or torch-2.x pickled state_dict.
        if not p.exists():
            # No file yet (e.g. called during save planning) — default to state_dict
            # for a generic .pt path.
            return "state_dict"
        try:
            with open(p, "rb") as f:
                head = f.read(8)
        except OSError as e:
            raise ModelIOError(
                f"cannot read {p}: {e}"
            ) from e
        if head.startswith(_ZIP_MAGIC):
            return "jit_or_state_dict"  # caller probes jit first
        return "state_dict"

    raise ModelIOError(
        f"unknown model format for {p} (extension {ext!r}). "
        f"Supported extensions: .pt2, .pt, .pth, .onnx, .safetensors. "
        f"Available backends: {available_backends()}"
    )


# ── save ──────────────────────────────────────────────────────────────────

def save_model(model, path, format: str = "auto", *, dummy_input=None, meta=None) -> str:
    """Save a model. Returns the backend name used.

    format:
      "auto"        — pick best available (export > jit > state_dict)
      "export"      — torch.export -> .pt2
      "jit"         — torch.jit.trace -> .pt
      "state_dict"  — torch.save({"model_state": ...}) -> .pt
      "onnx"        — torch.onnx.export -> .onnx (requires dummy_input)
      "safetensors" — safetensors.torch.save_file -> .safetensors

    dummy_input is required for "export", "jit", and "onnx".
    meta is an optional dict — currently only "opset_version" (onnx) is honoured.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    meta = meta or {}

    if format == "auto":
        backend = _pick_auto_save_backend(dummy_input)
    else:
        backend = format

    if backend == "export":
        _save_export(model, p, dummy_input)
    elif backend == "jit":
        _save_jit(model, p, dummy_input)
    elif backend == "state_dict":
        _save_state_dict(model, p)
    elif backend == "onnx":
        _save_onnx(model, p, dummy_input, meta.get("opset_version", 17))
    elif backend == "safetensors":
        _save_safetensors(model, p)
    else:
        raise ModelIOError(
            f"unknown save backend {backend!r}. "
            f"Available: {available_backends()}"
        )

    logger.info("save_model: backend=%s path=%s", backend, p)
    return backend


def _pick_auto_save_backend(dummy_input) -> str:
    if dummy_input is not None and _has_torch_export():
        return "export"
    if dummy_input is not None and _has_torch_export() is False:
        logger.debug("torch.export unavailable, falling back to jit")
    if dummy_input is not None:
        return "jit"
    logger.debug("no dummy_input provided, falling back to state_dict")
    return "state_dict"


def _save_export(model, path: Path, dummy_input) -> None:
    if dummy_input is None:
        raise ModelIOError(
            f"save_model(format='export') requires dummy_input for {path}"
        )
    try:
        from torch.export import export as torch_export
    except ImportError as e:
        raise ModelIOError(
            f"torch.export unavailable (upgrade torch to >=2.3): {e}"
        ) from e
    model.eval()
    try:
        exported = torch_export(model, (dummy_input,))
    except Exception as e:
        raise ModelIOError(
            f"torch.export failed for {path}: {e}. "
            f"Try format='jit' or format='state_dict'."
        ) from e
    # torch.export provides a .save helper on ExportedProgram in recent versions;
    # otherwise fall back to torch.save on the exported program object.
    if hasattr(exported, "save"):
        exported.save(str(path))
    else:
        torch.save(exported, str(path))


def _save_jit(model, path: Path, dummy_input) -> None:
    if dummy_input is None:
        raise ModelIOError(
            f"save_model(format='jit') requires dummy_input for {path}"
        )
    model.eval()
    try:
        traced = torch.jit.trace(model, dummy_input)
    except Exception as e:
        raise ModelIOError(
            f"torch.jit.trace failed for {path}: {e}. "
            f"Try format='state_dict'."
        ) from e
    traced.save(str(path))


def _save_state_dict(model, path: Path) -> None:
    payload = {"model_state": model.state_dict()}
    torch.save(payload, str(path))


def _save_onnx(model, path: Path, dummy_input, opset_version: int) -> None:
    if dummy_input is None:
        raise ModelIOError(
            f"save_model(format='onnx') requires dummy_input for {path}"
        )
    model.eval()
    kwargs = dict(
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        opset_version=opset_version,
    )
    # Try dynamo exporter first (torch >=2.5 default); fall back to legacy on
    # ImportError for onnxscript or any other exporter failure. This keeps the
    # ONNX path functional without onnxscript installed.
    try:
        torch.onnx.export(model, dummy_input, str(path), **kwargs)
        logger.debug("onnx export used default exporter")
        return
    except ImportError as e:
        logger.debug("dynamo onnx exporter unavailable (%s), falling back to legacy", e)
    except Exception as e:
        logger.debug("default onnx exporter failed (%s), falling back to legacy", e)

    try:
        torch.onnx.export(
            model, dummy_input, str(path), dynamo=False, **kwargs
        )
        logger.debug("onnx export used legacy (dynamo=False) exporter")
    except TypeError:
        # Very old torch — no dynamo kwarg at all; retry without it.
        try:
            torch.onnx.export(model, dummy_input, str(path), **kwargs)
        except Exception as e:
            raise ModelIOError(
                f"torch.onnx.export failed for {path}: {e}. "
                f"Install `onnxscript` for the dynamo exporter, "
                f"or upgrade torch."
            ) from e
    except Exception as e:
        raise ModelIOError(
            f"torch.onnx.export failed for {path}: {e}. "
            f"Install `onnxscript` for the dynamo exporter."
        ) from e


def _save_safetensors(model, path: Path) -> None:
    try:
        from safetensors.torch import save_file
    except ImportError as e:
        raise ModelIOError(
            f"safetensors not installed: {e}. Run `pip install safetensors`."
        ) from e
    save_file(model.state_dict(), str(path))


# ── load ──────────────────────────────────────────────────────────────────

def load_model(path, model=None, format: str = "auto"):
    """Load a model.

    For backends that return a standalone object (export, jit, onnx), the
    returned object is that object. For weights-only backends (state_dict,
    safetensors), a model instance must be supplied via the `model=` keyword
    and the loaded state_dict is applied in-place; the same model is returned.
    """
    p = Path(path)
    if not p.exists():
        raise ModelIOError(f"model file does not exist: {p}")

    if format == "auto":
        detected = detect_format(p)
        backend = detected
    else:
        backend = format

    # Resolve jit-or-state_dict probe from detect_format
    if backend == "jit_or_state_dict":
        try:
            result = torch.jit.load(str(p))
            backend = "jit"
            logger.info("load_model: backend=%s path=%s", backend, p)
            return result
        except Exception as e:
            logger.debug("jit load failed (%s), falling back to state_dict", e)
            backend = "state_dict"

    if backend == "export":
        result = _load_export(p)
    elif backend == "jit":
        result = torch.jit.load(str(p))
    elif backend == "state_dict":
        result = _load_state_dict(p, model)
    elif backend == "onnx":
        result = _load_onnx(p)
    elif backend == "safetensors":
        result = _load_safetensors(p, model)
    else:
        raise ModelIOError(
            f"unknown load backend {backend!r}. "
            f"Available: {available_backends()}"
        )

    logger.info("load_model: backend=%s path=%s", backend, p)
    return result


def _load_export(path: Path):
    try:
        from torch.export import load as torch_export_load
    except ImportError as e:
        raise ModelIOError(
            f"torch.export unavailable, cannot load {path}: {e}"
        ) from e
    try:
        return torch_export_load(str(path))
    except Exception:
        # Some torch versions stored via torch.save(exported, ...)
        return torch.load(str(path), weights_only=False)


def _load_state_dict(path: Path, model):
    payload = torch.load(str(path), weights_only=False)
    if model is None:
        # Return the raw payload — caller can extract state themselves
        return payload
    if isinstance(payload, dict) and "model_state" in payload:
        model.load_state_dict(payload["model_state"])
    else:
        model.load_state_dict(payload)
    return model


def _load_onnx(path: Path):
    try:
        import onnx
    except ImportError as e:
        raise ModelIOError(
            f"onnx not installed: {e}. Run `pip install onnx`."
        ) from e
    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    return model


def _load_safetensors(path: Path, model):
    try:
        from safetensors.torch import load_file
    except ImportError as e:
        raise ModelIOError(
            f"safetensors not installed: {e}. Run `pip install safetensors`."
        ) from e
    state_dict = load_file(str(path))
    if model is None:
        return state_dict
    model.load_state_dict(state_dict)
    return model


# ── checkpoint helpers ────────────────────────────────────────────────────

def save_checkpoint(model, path, optimizer=None, epoch=None, **extra) -> str:
    """Save a training checkpoint (model + optimizer + epoch + extras).

    Preserves the dict schema from base_model.save_checkpoint so Trainer's
    call graph is unchanged.
    """
    checkpoint = {
        "model_state": model.state_dict(),
        "model_class": model.__class__.__name__,
        "num_parameters": getattr(model, "num_parameters",
                                  sum(p.numel() for p in model.parameters())),
    }
    if optimizer is not None:
        checkpoint["optimizer_state"] = optimizer.state_dict()
    if epoch is not None:
        checkpoint["epoch"] = epoch
    checkpoint.update(extra)

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, str(p))
    logger.info("save_checkpoint: backend=state_dict path=%s", p)
    return "state_dict"


def load_checkpoint(path, model, optimizer=None) -> dict:
    """Load a training checkpoint into a model (and optionally optimizer).

    Returns the full checkpoint dict so callers can inspect epoch / extras.
    """
    p = Path(path)
    if not p.exists():
        raise ModelIOError(f"checkpoint does not exist: {p}")
    checkpoint = torch.load(str(p), weights_only=False)
    if not isinstance(checkpoint, dict) or "model_state" not in checkpoint:
        raise ModelIOError(
            f"not a terragraf checkpoint: {p} "
            f"(missing 'model_state' key)"
        )
    model.load_state_dict(checkpoint["model_state"])
    if optimizer is not None and "optimizer_state" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer_state"])
    logger.info("load_checkpoint: backend=state_dict path=%s", p)
    return checkpoint
