"""Tests for ml/training/ — Trainer, EarlyStopping, scheduling, metrics."""

import pytest

torch = pytest.importorskip("torch")
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from ml.training.trainer import Trainer, EarlyStopping, create_scheduler, create_optimizer
from ml.training.metrics import accuracy, precision_recall_f1, MetricsTracker
from ml.training.loggers import create_logger, ConsoleLogger
from ml.models.classifier import Classifier
from ml.models.transformer import Transformer


def _make_tiny_loaders(n=20, features=16, classes=3):
    """Create tiny synthetic train/val loaders."""
    x = torch.randn(n, features)
    y = torch.randint(0, classes, (n,))
    dataset = TensorDataset(x, y)
    train_loader = DataLoader(dataset[:15], batch_size=5)
    val_loader = DataLoader(dataset[15:], batch_size=5)
    # DataLoader needs a dataset, not a list — rebuild properly
    train_ds = TensorDataset(x[:15], y[:15])
    val_ds = TensorDataset(x[15:], y[15:])
    return DataLoader(train_ds, batch_size=5), DataLoader(val_ds, batch_size=5)


class TestTrainer:
    def test_train_basic(self):
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.CrossEntropyLoss()
        trainer = Trainer(model, optimizer, criterion, device="cpu")
        train_loader, val_loader = _make_tiny_loaders()
        history = trainer.train(train_loader, val_loader, epochs=2)
        assert len(history["train_loss"]) == 2
        assert len(history["val_loss"]) == 2

    def test_train_no_val(self):
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.CrossEntropyLoss()
        trainer = Trainer(model, optimizer, criterion, device="cpu")
        train_loader, _ = _make_tiny_loaders()
        history = trainer.train(train_loader, epochs=2)
        assert len(history["train_loss"]) == 2
        assert len(history["val_loss"]) == 0

    def test_gradient_clipping(self):
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.CrossEntropyLoss()
        trainer = Trainer(model, optimizer, criterion, device="cpu", max_grad_norm=1.0)
        train_loader, _ = _make_tiny_loaders()
        history = trainer.train(train_loader, epochs=1)
        assert len(history["train_loss"]) == 1


class TestEarlyStopping:
    def test_no_stop_when_improving(self):
        es = EarlyStopping(patience=3)
        for val in [1.0, 0.9, 0.8, 0.7]:
            es.step(val)
        assert not es.should_stop

    def test_stops_after_patience(self):
        es = EarlyStopping(patience=3)
        es.step(0.5)  # new best
        es.step(0.6)  # worse
        es.step(0.6)  # worse
        es.step(0.6)  # worse — patience exhausted
        assert es.should_stop

    def test_zero_patience_never_stops(self):
        es = EarlyStopping(patience=0)
        for _ in range(10):
            es.step(1.0)
        assert not es.should_stop


class TestScheduler:
    def test_cosine(self):
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        sched = create_scheduler(optimizer, "cosine", epochs=10)
        assert sched is not None

    def test_step(self):
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        sched = create_scheduler(optimizer, "step", epochs=10)
        assert sched is not None

    def test_plateau(self):
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        sched = create_scheduler(optimizer, "plateau", epochs=10)
        assert sched is not None

    def test_none_scheduler(self):
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        sched = create_scheduler(optimizer, "none", epochs=10)
        assert sched is None


class TestMetrics:
    def test_accuracy(self):
        preds = torch.tensor([0, 1, 2, 0, 1])
        labels = torch.tensor([0, 1, 2, 1, 1])
        assert accuracy(preds, labels) == pytest.approx(0.8)

    def test_precision_recall_f1(self):
        preds = torch.tensor([0, 1, 2, 0, 1])
        labels = torch.tensor([0, 1, 2, 1, 1])
        result = precision_recall_f1(preds, labels)
        assert "precision" in result
        assert "recall" in result
        assert "f1" in result

    def test_metrics_tracker(self):
        tracker = MetricsTracker()
        tracker.update(torch.tensor([0, 1]), torch.tensor([0, 1]))
        tracker.update(torch.tensor([2, 0]), torch.tensor([2, 0]))
        result = tracker.compute()
        assert result["accuracy"] == 1.0


class TestLoggers:
    def test_console_logger(self):
        logger = create_logger("console")
        assert isinstance(logger, ConsoleLogger)
        logger.log_scalar("test", 1.0, 1)
        logger.close()

    def test_create_logger_default(self):
        logger = create_logger()
        assert isinstance(logger, ConsoleLogger)


class TestCreateOptimizer:
    def test_adam(self):
        model = Classifier(input_dim=8, num_classes=2)
        opt = create_optimizer(model, name="adam", lr=1e-3)
        assert isinstance(opt, torch.optim.Adam)
        assert opt.param_groups[0]["lr"] == 1e-3

    def test_adamw(self):
        model = Classifier(input_dim=8, num_classes=2)
        opt = create_optimizer(model, name="adamw", lr=5e-4, weight_decay=0.01)
        assert isinstance(opt, torch.optim.AdamW)
        assert opt.param_groups[0]["weight_decay"] == 0.01

    def test_sgd(self):
        model = Classifier(input_dim=8, num_classes=2)
        opt = create_optimizer(model, name="sgd", lr=0.1)
        assert isinstance(opt, torch.optim.SGD)
        assert opt.param_groups[0]["momentum"] == 0.9

    def test_invalid_raises(self):
        model = Classifier(input_dim=8, num_classes=2)
        with pytest.raises(ValueError):
            create_optimizer(model, name="nope")


class TestTransformerClassification:
    def test_no_num_classes(self):
        """Without num_classes, Transformer returns sequence output."""
        t = Transformer(d_model=32, n_heads=4, n_layers=2, d_ff=64, max_seq_len=16)
        x = torch.randn(2, 10, 32)
        out = t(x)
        assert out.shape == (2, 10, 32)

    def test_with_num_classes(self):
        """With num_classes, Transformer returns (B, num_classes) logits."""
        t = Transformer(
            d_model=32, n_heads=4, n_layers=2, d_ff=64,
            max_seq_len=16, num_classes=5,
        )
        x = torch.randn(2, 10, 32)
        out = t(x)
        assert out.shape == (2, 5)


class TestTrainerStartEpoch:
    def test_start_epoch_offset(self):
        """start_epoch skips earlier iterations."""
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = create_optimizer(model, name="adam", lr=1e-3)
        criterion = nn.CrossEntropyLoss()
        trainer = Trainer(model, optimizer, criterion, device="cpu")

        train_loader, val_loader = _make_tiny_loaders()
        history = trainer.train(train_loader, val_loader, epochs=5, start_epoch=3)
        # epochs 4 and 5 -> 2 entries
        assert len(history["train_loss"]) == 2

    def test_end_to_end_pipeline(self, tmp_path):
        """create_optimizer + create_scheduler + Trainer + train."""
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = create_optimizer(model, name="adamw", lr=1e-3)
        scheduler = create_scheduler(optimizer, name="cosine", epochs=2)
        criterion = nn.CrossEntropyLoss()
        trainer = Trainer(
            model, optimizer, criterion, device="cpu",
            scheduler=scheduler, checkpoint_dir=str(tmp_path),
        )
        train_loader, val_loader = _make_tiny_loaders()
        history = trainer.train(train_loader, val_loader, epochs=2)
        assert len(history["train_loss"]) == 2
        assert len(history["lr"]) == 2

    def test_resume_checkpoint(self, tmp_path):
        """Save a checkpoint, load it, continue training."""
        model = Classifier(input_dim=16, num_classes=3)
        optimizer = create_optimizer(model, name="adam", lr=1e-3)
        criterion = nn.CrossEntropyLoss()
        trainer = Trainer(
            model, optimizer, criterion, device="cpu",
            checkpoint_dir=str(tmp_path),
        )
        train_loader, val_loader = _make_tiny_loaders()
        trainer.train(train_loader, val_loader, epochs=2)

        # Load into a new model
        model2 = Classifier(input_dim=16, num_classes=3)
        opt2 = create_optimizer(model2, name="adam", lr=1e-3)
        ckpt = model2.load_checkpoint(str(tmp_path / "final.pt"), optimizer=opt2)
        assert ckpt["epoch"] == 2
