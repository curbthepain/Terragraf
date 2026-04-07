"""Tests for ml/datasets/ — dataloader factory, transforms."""

import pytest

torch = pytest.importorskip("torch")
from torch.utils.data import TensorDataset

from ml.datasets.dataloader import create_dataloader, create_loaders
from ml.datasets.base_dataset import ScaffoldDataset


class TestCreateDataloader:
    def test_basic_split(self):
        x = torch.randn(100, 16)
        y = torch.randint(0, 5, (100,))
        dataset = TensorDataset(x, y)
        train_loader, val_loader = create_dataloader(dataset, batch_size=10, val_split=0.2, num_workers=0)
        assert len(train_loader.dataset) == 80
        assert len(val_loader.dataset) == 20

    def test_batch_iteration(self):
        x = torch.randn(50, 8)
        y = torch.randint(0, 3, (50,))
        dataset = TensorDataset(x, y)
        train_loader, val_loader = create_dataloader(dataset, batch_size=10, num_workers=0)
        batch = next(iter(train_loader))
        assert batch[0].shape[0] == 10
        assert batch[0].shape[1] == 8

    def test_backward_compat_alias(self):
        """create_loaders should still work as an alias."""
        x = torch.randn(20, 4)
        y = torch.randint(0, 2, (20,))
        dataset = TensorDataset(x, y)
        train_loader, val_loader = create_loaders(dataset, batch_size=5, num_workers=0)
        assert len(train_loader.dataset) + len(val_loader.dataset) == 20


class TestTransforms:
    def test_cifar_transforms_shape(self):
        from ml.datasets.transforms import cifar_transforms
        transform = cifar_transforms(train=True)
        # Simulate a PIL image-like input
        from PIL import Image
        import numpy as np
        img = Image.fromarray(np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8))
        tensor = transform(img)
        assert tensor.shape == (3, 32, 32)

    def test_image_train_transforms(self):
        from ml.datasets.transforms import image_train_transforms
        transform = image_train_transforms(size=64)
        from PIL import Image
        import numpy as np
        img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        tensor = transform(img)
        assert tensor.shape == (3, 64, 64)

    def test_image_eval_transforms(self):
        from ml.datasets.transforms import image_eval_transforms
        transform = image_eval_transforms(size=64)
        from PIL import Image
        import numpy as np
        img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        tensor = transform(img)
        assert tensor.shape == (3, 64, 64)


class TestScaffoldDataset:
    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ScaffoldDataset()
