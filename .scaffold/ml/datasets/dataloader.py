"""
.scaffold/ml/datasets/dataloader.py
DataLoader factory with sensible defaults.
"""

from torch.utils.data import DataLoader, random_split


def create_loaders(dataset, batch_size=32, val_split=0.2, num_workers=4, seed=42):
    """Split a dataset and return train/val DataLoaders."""
    import torch

    total = len(dataset)
    val_size = int(total * val_split)
    train_size = total - val_size

    generator = torch.Generator().manual_seed(seed)
    train_set, val_set = random_split(dataset, [train_size, val_size], generator=generator)

    train_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    print(f"Train: {train_size} samples, Val: {val_size} samples")
    print(f"Batch size: {batch_size}, Workers: {num_workers}")

    return train_loader, val_loader
