"""
.scaffold/ml/config.py
Training configuration loader. Reads config.toml and provides TrainConfig dataclass.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TrainConfig:
    # Model
    model_name: str = ""

    # Training
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    optimizer: str = "adam"
    scheduler: str = "cosine"
    max_grad_norm: float = 0.0
    early_stopping_patience: int = 0

    # Data
    dataset: str = ""
    root_dir: str = "data/"
    val_split: float = 0.2
    num_workers: int = 4
    augment: bool = True

    # Checkpoint
    save_dir: str = "checkpoints/"
    save_best: bool = True
    save_every: int = 0

    # Logging
    log_backend: str = "console"
    log_dir: str = "runs/"
    log_every: int = 10


def load_config(path=None):
    """Load TrainConfig from a TOML file. Returns defaults if path is None or missing."""
    config = TrainConfig()
    if path is None:
        return config

    path = Path(path)
    if not path.exists():
        return config

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open(path, "rb") as f:
        data = tomllib.load(f)

    # Map TOML sections to flat dataclass fields
    model = data.get("model", {})
    training = data.get("training", {})
    data_sec = data.get("data", {})
    checkpoint = data.get("checkpoint", {})
    logging = data.get("logging", {})

    if model.get("name"):
        config.model_name = model["name"]
    if training.get("epochs"):
        config.epochs = int(training["epochs"])
    if training.get("batch_size"):
        config.batch_size = int(training["batch_size"])
    if training.get("learning_rate"):
        config.learning_rate = float(training["learning_rate"])
    if training.get("weight_decay"):
        config.weight_decay = float(training["weight_decay"])
    if training.get("optimizer"):
        config.optimizer = training["optimizer"]
    if training.get("scheduler"):
        config.scheduler = training["scheduler"]

    if data_sec.get("dataset"):
        config.dataset = data_sec["dataset"]
    if data_sec.get("root_dir"):
        config.root_dir = data_sec["root_dir"]
    if "val_split" in data_sec:
        config.val_split = float(data_sec["val_split"])
    if "num_workers" in data_sec:
        config.num_workers = int(data_sec["num_workers"])
    if "augment" in data_sec:
        config.augment = bool(data_sec["augment"])

    if checkpoint.get("save_dir"):
        config.save_dir = checkpoint["save_dir"]
    if "save_best" in checkpoint:
        config.save_best = bool(checkpoint["save_best"])
    if "save_every" in checkpoint:
        config.save_every = int(checkpoint["save_every"])

    if logging.get("backend"):
        config.log_backend = logging["backend"]
    if logging.get("log_dir"):
        config.log_dir = logging["log_dir"]
    if "log_every" in logging:
        config.log_every = int(logging["log_every"])

    return config
