"""
.scaffold/ml/models/base_model.py
Base model template. All models inherit from this.

Provides:
  - Standard __init__ / forward interface
  - Parameter counting
  - Device management
  - Save/load checkpoints
  - Summary printing

Usage:
  class MyModel(ScaffoldModel):
      def __init__(self):
          super().__init__()
          self.layers = nn.Sequential(...)

      def forward(self, x):
          return self.layers(x)
"""

import torch
import torch.nn as nn
from pathlib import Path


class ScaffoldModel(nn.Module):
    """Base model with built-in checkpoint and summary support."""

    def __init__(self):
        super().__init__()

    def forward(self, x):
        raise NotImplementedError("Subclasses must implement forward()")

    @property
    def num_parameters(self):
        return sum(p.numel() for p in self.parameters())

    @property
    def num_trainable(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def summary(self):
        print(f"Model: {self.__class__.__name__}")
        print(f"  Total params:     {self.num_parameters:,}")
        print(f"  Trainable params: {self.num_trainable:,}")
        print(f"  Device: {next(self.parameters()).device}")

    def save_checkpoint(self, path, optimizer=None, epoch=None, **extra):
        checkpoint = {
            "model_state": self.state_dict(),
            "model_class": self.__class__.__name__,
            "num_parameters": self.num_parameters,
        }
        if optimizer is not None:
            checkpoint["optimizer_state"] = optimizer.state_dict()
        if epoch is not None:
            checkpoint["epoch"] = epoch
        checkpoint.update(extra)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, path)
        print(f"Checkpoint saved: {path}")

    def load_checkpoint(self, path, optimizer=None):
        checkpoint = torch.load(path, weights_only=False)
        self.load_state_dict(checkpoint["model_state"])
        if optimizer is not None and "optimizer_state" in checkpoint:
            optimizer.load_state_dict(checkpoint["optimizer_state"])
        print(f"Checkpoint loaded: {path} (epoch {checkpoint.get('epoch', '?')})")
        return checkpoint

    def to_device(self, device="auto"):
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.to(device)
        print(f"Model on: {device}")
        return self
