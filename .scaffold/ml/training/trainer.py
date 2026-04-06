"""
.scaffold/ml/training/trainer.py
Training loop with LR scheduling, early stopping, gradient clipping, and logging.
"""

import torch
import torch.nn as nn
from pathlib import Path
from time import time


class EarlyStopping:
    """Stop training when validation loss stops improving."""

    def __init__(self, patience=5, min_delta=0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.best_score = None
        self.counter = 0
        self.should_stop = False

    def step(self, val_loss):
        if self.patience <= 0:
            return
        if self.best_score is None:
            self.best_score = val_loss
        elif val_loss < self.best_score - self.min_delta:
            self.best_score = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True


def create_scheduler(optimizer, name="cosine", epochs=10, **kwargs):
    """Factory for LR schedulers."""
    if name is None or name == "none":
        return None
    if name == "cosine":
        return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    elif name == "step":
        return torch.optim.lr_scheduler.StepLR(optimizer, step_size=kwargs.get("step_size", max(1, epochs // 3)))
    elif name == "plateau":
        return torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=kwargs.get("patience", 3))
    return None


def create_optimizer(model, name="adam", lr=1e-3, weight_decay=1e-4, **kwargs):
    """Factory for optimizers: adam, adamw, sgd."""
    name = name.lower()
    params = model.parameters()
    if name == "adam":
        return torch.optim.Adam(params, lr=lr, weight_decay=weight_decay)
    elif name == "adamw":
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    elif name == "sgd":
        momentum = kwargs.get("momentum", 0.9)
        return torch.optim.SGD(params, lr=lr, weight_decay=weight_decay, momentum=momentum)
    raise ValueError(f"Unknown optimizer: {name} (expected adam/adamw/sgd)")


class Trainer:
    """Training loop with scheduling, early stopping, gradient clipping, and logging."""

    def __init__(self, model, optimizer, criterion, device="auto",
                 checkpoint_dir="checkpoints", log_dir="runs",
                 scheduler=None, logger=None, max_grad_norm=0.0,
                 early_stopping_patience=0):
        self.model = model
        self.optimizer = optimizer
        self.criterion = criterion
        self.checkpoint_dir = Path(checkpoint_dir)
        self.log_dir = Path(log_dir)
        self.scheduler = scheduler
        self.max_grad_norm = max_grad_norm

        # Logging
        if logger is None:
            from .loggers import ConsoleLogger
            logger = ConsoleLogger()
        self.logger = logger

        # Early stopping
        self.early_stopping = EarlyStopping(patience=early_stopping_patience) if early_stopping_patience > 0 else None

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

        self.history = {"train_loss": [], "val_loss": [], "lr": []}

    def train(self, train_loader, val_loader=None, epochs=10, start_epoch=0):
        """Run the training loop."""
        print(f"Training on {self.device} for {epochs} epochs (start={start_epoch})")
        best_val_loss = float("inf")

        for epoch in range(start_epoch + 1, epochs + 1):
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

                if self.max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)

                self.optimizer.step()

                train_loss += loss.item()
                self.on_batch_end(epoch, batch_idx, loss.item())

            train_loss /= len(train_loader)
            self.history["train_loss"].append(train_loss)

            # ─── Validate ───────────────────────────────────────────
            val_loss = None
            if val_loader is not None:
                val_loss = self._evaluate_loss(val_loader)
                self.history["val_loss"].append(val_loss)

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self._save_checkpoint(epoch, "best.pt")

            # ─── Scheduler step ─────────────────────────────────────
            current_lr = self.optimizer.param_groups[0]["lr"]
            self.history["lr"].append(current_lr)
            if self.scheduler is not None:
                if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                    if val_loss is not None:
                        self.scheduler.step(val_loss)
                else:
                    self.scheduler.step()

            # ─── Log ────────────────────────────────────────────────
            elapsed = time() - t0
            val_str = f"val_loss={val_loss:.4f}" if val_loss is not None else ""
            print(f"Epoch {epoch}/{epochs} | loss={train_loss:.4f} {val_str} lr={current_lr:.2e} | {elapsed:.1f}s")

            self.logger.log_scalar("train/loss", train_loss, epoch)
            if val_loss is not None:
                self.logger.log_scalar("val/loss", val_loss, epoch)
            self.logger.log_scalar("train/lr", current_lr, epoch)

            self.on_epoch_end(epoch, train_loss, val_loss)

            # ─── Early stopping ─────────────────────────────────────
            if self.early_stopping is not None and val_loss is not None:
                self.early_stopping.step(val_loss)
                if self.early_stopping.should_stop:
                    print(f"Early stopping at epoch {epoch}")
                    break

        self._save_checkpoint(epochs, "final.pt")
        self.logger.close()
        return self.history

    @torch.no_grad()
    def _evaluate_loss(self, loader):
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
