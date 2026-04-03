"""
.scaffold/viz/3d/mesh.py
Mesh generation from data — surface plots, point clouds.

Provides:
  - generate_surface     — create mesh vertices/faces from a 2D height map
  - generate_point_cloud — create point cloud from 3D data
  - render_surface       — render surface as matplotlib 3D plot
  - render_point_cloud   — render point cloud as matplotlib 3D scatter
"""

import numpy as np
from typing import Tuple


def generate_surface(z: np.ndarray, x_range=(0, 1), y_range=(0, 1)) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate surface mesh from a 2D height map.
    z: 2D array of height values (rows=y, cols=x).
    Returns (X, Y, Z) meshgrid arrays for plotting.
    """
    rows, cols = z.shape
    x = np.linspace(x_range[0], x_range[1], cols)
    y = np.linspace(y_range[0], y_range[1], rows)
    X, Y = np.meshgrid(x, y)
    return X, Y, z


def generate_point_cloud(data: np.ndarray, colors: np.ndarray = None) -> dict:
    """
    Create a point cloud structure from Nx3 data.
    data: (N, 3) array of XYZ coordinates.
    colors: optional (N, 3) or (N, 4) array of RGB(A) values (0-1 range).
    Returns dict with 'vertices' and optionally 'colors'.
    """
    result = {"vertices": np.asarray(data, dtype=np.float32)}
    if colors is not None:
        result["colors"] = np.asarray(colors, dtype=np.float32)
    return result


def render_surface(z: np.ndarray, x_range=(0, 1), y_range=(0, 1),
                   cmap="viridis", title="Surface", figsize=(10, 7)):
    """Render a 2D height map as a 3D surface. Returns matplotlib Figure."""
    import matplotlib.pyplot as plt

    X, Y, Z = generate_surface(z, x_range, y_range)

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, Z, cmap=cmap, edgecolor="none", alpha=0.9)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def render_point_cloud(data: np.ndarray, colors=None, size=1,
                        title="Point Cloud", figsize=(10, 7)):
    """Render Nx3 point cloud as 3D scatter. Returns matplotlib Figure."""
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    if colors is not None:
        ax.scatter(data[:, 0], data[:, 1], data[:, 2], c=colors, s=size)
    else:
        ax.scatter(data[:, 0], data[:, 1], data[:, 2], s=size, alpha=0.6)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(title)
    fig.tight_layout()
    return fig
