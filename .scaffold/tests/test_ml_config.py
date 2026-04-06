"""Tests for ml/config.py — TrainConfig and load_config."""

import pytest
from pathlib import Path
from ml.config import TrainConfig, load_config


class TestTrainConfig:
    def test_defaults(self):
        c = TrainConfig()
        assert c.epochs == 10
        assert c.batch_size == 32
        assert c.learning_rate == 1e-3
        assert c.optimizer == "adam"
        assert c.scheduler == "cosine"
        assert c.log_backend == "console"

    def test_custom_values(self):
        c = TrainConfig(epochs=50, learning_rate=1e-4, scheduler="plateau")
        assert c.epochs == 50
        assert c.learning_rate == 1e-4
        assert c.scheduler == "plateau"


class TestLoadConfig:
    def test_load_none_returns_defaults(self):
        c = load_config(None)
        assert isinstance(c, TrainConfig)
        assert c.epochs == 10

    def test_load_missing_file_returns_defaults(self):
        c = load_config("/nonexistent/path.toml")
        assert c.epochs == 10

    def test_load_real_config(self):
        config_path = Path(__file__).parent.parent / "ml" / "training" / "config.toml"
        if config_path.exists():
            c = load_config(config_path)
            assert c.epochs == 10
            assert c.optimizer == "adam"
            assert c.scheduler == "cosine"
            assert c.batch_size == 32

    def test_load_config_training_section(self):
        config_path = Path(__file__).parent.parent / "ml" / "training" / "config.toml"
        if config_path.exists():
            c = load_config(config_path)
            assert c.weight_decay == 1e-4
            assert c.val_split == 0.2
