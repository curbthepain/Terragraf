"""
.scaffold/ml/datasets/vision.py
Built-in vision dataset loaders using torchvision.
"""

from torch.utils.data import DataLoader


def cifar10_loaders(root="data/", batch_size=32, num_workers=4, download=True):
    """CIFAR-10 train/test loaders with standard augmentation."""
    from torchvision.datasets import CIFAR10
    from .transforms import cifar_transforms

    train_set = CIFAR10(root=root, train=True, download=download, transform=cifar_transforms(train=True))
    test_set = CIFAR10(root=root, train=False, download=download, transform=cifar_transforms(train=False))

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    return train_loader, test_loader


def image_folder_loaders(root, batch_size=32, val_split=0.2, num_workers=4, size=224):
    """ImageFolder train/val loaders from a directory with class subfolders."""
    import torch
    from torch.utils.data import random_split
    from torchvision.datasets import ImageFolder
    from .transforms import image_train_transforms, image_eval_transforms

    full_dataset = ImageFolder(root, transform=image_train_transforms(size))
    total = len(full_dataset)
    val_size = int(total * val_split)
    train_size = total - val_size

    train_set, val_set = random_split(full_dataset, [train_size, val_size],
                                      generator=torch.Generator().manual_seed(42))
    # Override transform for val set (no augmentation)
    val_set.dataset = ImageFolder(root, transform=image_eval_transforms(size))

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    return train_loader, val_loader
