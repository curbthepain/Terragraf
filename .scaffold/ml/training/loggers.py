"""
.scaffold/ml/training/loggers.py
Logging backends for training — TensorBoard, Wandb, Console.
"""

from abc import ABC, abstractmethod


class Logger(ABC):
    @abstractmethod
    def log_scalar(self, tag, value, step):
        pass

    def log_model(self, model, step):
        pass

    def close(self):
        pass


class ConsoleLogger(Logger):
    """Default logger — prints to stdout."""

    def log_scalar(self, tag, value, step):
        pass  # Trainer already prints per-epoch; avoid duplication

    def close(self):
        pass


class TensorBoardLogger(Logger):
    """Wraps torch.utils.tensorboard.SummaryWriter."""

    def __init__(self, log_dir="runs/"):
        from torch.utils.tensorboard import SummaryWriter
        self._writer = SummaryWriter(log_dir=log_dir)

    def log_scalar(self, tag, value, step):
        self._writer.add_scalar(tag, value, step)

    def close(self):
        self._writer.close()


class WandbLogger(Logger):
    """Wraps wandb logging."""

    def __init__(self, project="terragraf", **kwargs):
        import wandb
        self._run = wandb.init(project=project, **kwargs)

    def log_scalar(self, tag, value, step):
        import wandb
        wandb.log({tag: value}, step=step)

    def close(self):
        import wandb
        wandb.finish()


def create_logger(backend="console", **kwargs):
    """Factory for logging backends."""
    if backend == "tensorboard":
        return TensorBoardLogger(**kwargs)
    elif backend == "wandb":
        return WandbLogger(**kwargs)
    else:
        return ConsoleLogger()
