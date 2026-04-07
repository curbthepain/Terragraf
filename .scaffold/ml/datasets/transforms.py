"""
.scaffold/ml/datasets/transforms.py
Standard transform pipelines for image and audio data.
"""


def image_train_transforms(size=224):
    """Training transforms: augmentation + normalization (ImageNet stats)."""
    from torchvision import transforms
    return transforms.Compose([
        transforms.Resize(size + 32),
        transforms.RandomCrop(size),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def image_eval_transforms(size=224):
    """Evaluation transforms: resize + center crop + normalization."""
    from torchvision import transforms
    return transforms.Compose([
        transforms.Resize(size + 32),
        transforms.CenterCrop(size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def cifar_transforms(train=True):
    """CIFAR-10/100 transforms (32x32 images)."""
    from torchvision import transforms
    if train:
        return transforms.Compose([
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.4914, 0.4822, 0.4465], std=[0.2470, 0.2435, 0.2616]),
        ])
    return transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.4914, 0.4822, 0.4465], std=[0.2470, 0.2435, 0.2616]),
    ])


def audio_mel_transforms(sample_rate=16000, n_mels=64):
    """Audio to mel spectrogram transform."""
    import torchaudio.transforms as T
    return T.MelSpectrogram(sample_rate=sample_rate, n_mels=n_mels)
