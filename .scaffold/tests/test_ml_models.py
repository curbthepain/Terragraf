"""Tests for ml/models/ — forward pass, checkpointing, parameter counting."""

import pytest

torch = pytest.importorskip("torch")
import tempfile
from pathlib import Path

from ml.models.classifier import Classifier
from ml.models.cnn import CNN
from ml.models.transformer import Transformer
from ml.models.base_model import ScaffoldModel


class TestClassifier:
    def test_forward_shape(self):
        model = Classifier(input_dim=128, num_classes=10)
        x = torch.randn(4, 128)
        out = model(x)
        assert out.shape == (4, 10)

    def test_parameter_count(self):
        model = Classifier(input_dim=64, num_classes=5)
        assert model.num_parameters > 0
        assert model.num_trainable > 0


class TestCNN:
    def test_forward_shape(self):
        model = CNN(in_channels=3, num_classes=10, base_channels=16)
        x = torch.randn(2, 3, 32, 32)
        out = model(x)
        assert out.shape == (2, 10)

    def test_different_input_channels(self):
        model = CNN(in_channels=1, num_classes=5, base_channels=8)
        x = torch.randn(2, 1, 32, 32)
        out = model(x)
        assert out.shape == (2, 5)


class TestTransformer:
    def test_forward_shape(self):
        model = Transformer(d_model=64, n_layers=2, n_heads=4)
        x = torch.randn(2, 16, 64)
        out = model(x)
        assert out.shape == (2, 16, 64)

    def test_with_vocab(self):
        model = Transformer(d_model=64, n_layers=2, n_heads=4, vocab_size=100)
        x = torch.randint(0, 100, (2, 16))
        out = model(x)
        assert out.shape == (2, 16, 64)


class TestCheckpointing:
    def test_save_load_roundtrip(self):
        model = Classifier(input_dim=32, num_classes=5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.pt"
            model.save_checkpoint(path, epoch=1)
            assert path.exists()

            model2 = Classifier(input_dim=32, num_classes=5)
            checkpoint = model2.load_checkpoint(path)
            assert checkpoint["epoch"] == 1
            assert checkpoint["model_class"] == "Classifier"

            # Weights should match
            for (n1, p1), (n2, p2) in zip(model.named_parameters(), model2.named_parameters()):
                assert torch.allclose(p1, p2), f"Mismatch in {n1}"

    def test_device_movement(self):
        model = CNN(in_channels=3, num_classes=10, base_channels=8)
        model = model.to_device("cpu")
        assert next(model.parameters()).device == torch.device("cpu")
