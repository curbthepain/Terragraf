"""
.scaffold/ml/models/classifier.py
Classification head template. Attach to any backbone.
"""

import torch.nn as nn
from .base_model import ScaffoldModel


class Classifier(ScaffoldModel):
    """Simple classification head. Customize layers as needed."""

    def __init__(self, input_dim, num_classes, hidden_dim=256, dropout=0.3):
        super().__init__()
        self.head = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x):
        return self.head(x)
