"""
.scaffold/ml/models/transformer.py
Transformer block template. Standard multi-head self-attention + FFN.
"""

import torch
import torch.nn as nn
import math
from .base_model import ScaffoldModel


class TransformerBlock(nn.Module):
    """Single transformer block: attention + feed-forward + residual + norm."""

    def __init__(self, d_model, n_heads, d_ff=None, dropout=0.1):
        super().__init__()
        d_ff = d_ff or 4 * d_model
        self.attention = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x, mask=None):
        attended, _ = self.attention(x, x, x, attn_mask=mask)
        x = self.norm1(x + attended)
        x = self.norm2(x + self.ffn(x))
        return x


class Transformer(ScaffoldModel):
    """Stack of transformer blocks with positional encoding."""

    def __init__(self, d_model=512, n_heads=8, n_layers=6, d_ff=2048,
                 max_seq_len=512, vocab_size=None, dropout=0.1):
        super().__init__()

        self.d_model = d_model

        if vocab_size is not None:
            self.embedding = nn.Embedding(vocab_size, d_model)
        else:
            self.embedding = None

        self.pos_encoding = self._make_positional_encoding(max_seq_len, d_model)
        self.dropout = nn.Dropout(dropout)
        self.layers = nn.ModuleList([
            TransformerBlock(d_model, n_heads, d_ff, dropout)
            for _ in range(n_layers)
        ])
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x, mask=None):
        if self.embedding is not None:
            x = self.embedding(x) * math.sqrt(self.d_model)

        seq_len = x.size(1)
        x = x + self.pos_encoding[:, :seq_len, :].to(x.device)
        x = self.dropout(x)

        for layer in self.layers:
            x = layer(x, mask)

        return self.norm(x)

    @staticmethod
    def _make_positional_encoding(max_len, d_model):
        pe = torch.zeros(1, max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[0, :, 0::2] = torch.sin(position * div_term)
        pe[0, :, 1::2] = torch.cos(position * div_term)
        return nn.Parameter(pe, requires_grad=False)
