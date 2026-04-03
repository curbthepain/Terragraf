"""
.scaffold/ml/training/trainer.py
Training loop with logging, checkpoints, and early stopping.
Drop-in trainer — override hooks for custom behavior.
"""

import torch
import torch.nn as nn
from pathlib import Path
from time import time


class Trainer:
    """Standard training loop. Override on_epoch_end, on_batch_end for custom logic."""

    def __init__(self, model, optimizer, criterion, device="auto",
                 checkpoint_dir="checkpoints", log_dir="runs"):
        self.model = model
        self.optimizer = optimizer
        self.criterion = criterion
        self.checkpoint_dir = Path(checkpoint_dir)
        self.log_dir = Path(log_dir)

        # Device setup
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.device = torch.device(device)
        self.model.to(self.device)

        self.history = {"train_loss": [], "val_loss": []}

    def train(self, train_loader, val_loader=None, epochs=10):
        """Run the training loop."""
        print(f"Training on {self.device} for {epochs} epochs")
        best_val_loss = float("inf")

        for epoch in range(1, epochs + 1):
            t0 = time()

            # ─── Train ──────────────────────────────────────────────
            self.model.train()
            train_loss = 0.0
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(self.device), targets.to(self.device)

                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = self.criterion(outputs, targets)
                loss.backward()
                self.optimizer.step()

                train_loss += loss.item()
                self.on_batch_end(epoch, batch_idx, loss.item())

            train_loss /= len(train_loader)
            self.history["train_loss"].append(train_loss)

            # ─── Validate ───────────────────────────────────────────
            val_loss = None
            if val_loader is not None:
                val_loss = self.evaluate(val_loader)
                self.history["val_loss"].append(val_loss)

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self._save_checkpoint(epoch, "best.pt")

            # ─── Log ────────────────────────────────────────────────
            elapsed = time() - t0
            val_str = f"val_loss={val_loss:.4f}" if val_loss else ""
            print(f"Epoch {epoch}/{epochs} | loss={train_loss:.4f} {val_str} | {elapsed:.1f}s")

            self.on_epoch_end(epoch, train_loss, val_loss)

        self._save_checkpoint(epochs, "final.pt")
        return self.history

    @torch.no_grad()
    def evaluate(self, loader):
        """Run evaluation, return average loss."""
        self.model.eval()
        total_loss = 0.0
        for inputs, targets in loader:
            inputs, targets = inputs.to(self.device), targets.to(self.device)
            outputs = self.model(inputs)
            total_loss += self.criterion(outputs, targets).item()
        return total_loss / len(loader)

    def _save_checkpoint(self, epoch, filename):
        path = self.checkpoint_dir / filename
        self.model.save_checkpoint(path, optimizer=self.optimizer, epoch=epoch)

    # ─── Override these hooks ───────────────────────────────────────
    def on_batch_end(self, epoch, batch_idx, loss):
        pass

    def on_epoch_end(self, epoch, train_loss, val_loss):
        pass
