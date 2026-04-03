"""
.scaffold/ml/models/cnn.py
Convolutional neural network template. Image classification baseline.
"""

import torch.nn as nn
from .base_model import ScaffoldModel


class CNN(ScaffoldModel):
    """Configurable CNN. Adjust channels, layers, kernel sizes as needed."""

    def __init__(self, in_channels=3, num_classes=10, base_channels=32):
        super().__init__()
        c = base_channels
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(in_channels, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.ReLU(),
            nn.MaxPool2d(2),
            # Block 2
            nn.Conv2d(c, c * 2, 3, padding=1),
            nn.BatchNorm2d(c * 2),
            nn.ReLU(),
            nn.MaxPool2d(2),
            # Block 3
            nn.Conv2d(c * 2, c * 4, 3, padding=1),
            nn.BatchNorm2d(c * 4),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(c * 4, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)
