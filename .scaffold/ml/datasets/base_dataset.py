"""
.scaffold/ml/datasets/base_dataset.py
Dataset template. Subclass and implement __getitem__.
"""

from torch.utils.data import Dataset
from pathlib import Path


class ScaffoldDataset(Dataset):
    """Base dataset with standard split support and path management."""

    def __init__(self, root_dir, split="train", transform=None):
        self.root = Path(root_dir)
        self.split = split
        self.transform = transform
        self.samples = self._load_samples()

    def _load_samples(self):
        """Override: return list of (input, target) or file paths."""
        raise NotImplementedError

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        """Override if samples aren't directly usable tensors."""
        sample = self.samples[idx]
        if self.transform:
            sample = self.transform(sample)
        return sample

    def summary(self):
        print(f"Dataset: {self.__class__.__name__}")
        print(f"  Split: {self.split}")
        print(f"  Samples: {len(self)}")
        print(f"  Root: {self.root}")
