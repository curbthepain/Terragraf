"""
.scaffold/viz/heatmap.py
Generic 2D heatmap renderer.

Provides:
  - heatmap           — render a 2D array as a heatmap
  - annotated_heatmap — heatmap with cell value annotations
"""

import numpy as np


def heatmap(data, x_labels=None, y_labels=None, cmap="viridis",
            title="Heatmap", figsize=(8, 6)):
    """
    Render a 2D numpy array as a heatmap.
    Returns a matplotlib Figure object.
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    im = ax.imshow(data, cmap=cmap, aspect="auto")
    fig.colorbar(im, ax=ax)

    if x_labels is not None:
        ax.set_xticks(np.arange(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    if y_labels is not None:
        ax.set_yticks(np.arange(len(y_labels)))
        ax.set_yticklabels(y_labels)

    ax.set_title(title)
    fig.tight_layout()
    return fig


def annotated_heatmap(data, x_labels=None, y_labels=None, cmap="viridis",
                       fmt=".2f", title="Heatmap", figsize=(8, 6)):
    """
    Heatmap with numeric annotations in each cell.
    Good for correlation matrices, confusion matrices.
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    im = ax.imshow(data, cmap=cmap, aspect="auto")
    fig.colorbar(im, ax=ax)

    rows, cols = data.shape
    for i in range(rows):
        for j in range(cols):
            val = data[i, j]
            color = "white" if val < (data.max() + data.min()) / 2 else "black"
            ax.text(j, i, format(val, fmt), ha="center", va="center", color=color)

    if x_labels is not None:
        ax.set_xticks(np.arange(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    if y_labels is not None:
        ax.set_yticks(np.arange(len(y_labels)))
        ax.set_yticklabels(y_labels)

    ax.set_title(title)
    fig.tight_layout()
    return fig
