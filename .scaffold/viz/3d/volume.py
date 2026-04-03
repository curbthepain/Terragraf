"""
.scaffold/viz/3d/volume.py
Volumetric rendering — ray marching through 3D density fields.

Provides:
  - VolumeRenderer — CPU ray marcher for 3D data visualization
  - render_slices  — render orthogonal slices through volume
"""

import numpy as np
from typing import Tuple, Optional


class VolumeRenderer:
    """
    CPU-based volumetric ray marcher.
    Renders a 3D numpy array as if it were a density field (like CT/ultrasound).

    Usage:
        vol = np.random.rand(64, 64, 64)
        renderer = VolumeRenderer(vol)
        image = renderer.render(camera_pos=(2, 2, 2))
    """

    def __init__(self, volume: np.ndarray, transfer_fn=None):
        """
        volume:      3D numpy array (D, H, W) of density values (0-1).
        transfer_fn: callable(density) -> (r, g, b, a), or None for grayscale.
        """
        self.volume = np.asarray(volume, dtype=np.float32)
        self.shape = np.array(volume.shape, dtype=np.float32)
        self.transfer_fn = transfer_fn or self._default_transfer

    @staticmethod
    def _default_transfer(density):
        """Default grayscale transfer function."""
        return (density, density, density, density)

    def sample(self, pos: np.ndarray) -> float:
        """Trilinear interpolation sample from volume."""
        # Clamp to volume bounds
        pos = np.clip(pos, 0, self.shape - 1.001)
        i = pos.astype(int)
        f = pos - i

        # Trilinear interpolation
        c000 = self.volume[i[0], i[1], i[2]]
        c100 = self.volume[min(i[0]+1, int(self.shape[0]-1)), i[1], i[2]]
        c010 = self.volume[i[0], min(i[1]+1, int(self.shape[1]-1)), i[2]]
        c001 = self.volume[i[0], i[1], min(i[2]+1, int(self.shape[2]-1))]
        c110 = self.volume[min(i[0]+1, int(self.shape[0]-1)), min(i[1]+1, int(self.shape[1]-1)), i[2]]
        c101 = self.volume[min(i[0]+1, int(self.shape[0]-1)), i[1], min(i[2]+1, int(self.shape[2]-1))]
        c011 = self.volume[i[0], min(i[1]+1, int(self.shape[1]-1)), min(i[2]+1, int(self.shape[2]-1))]
        c111 = self.volume[min(i[0]+1, int(self.shape[0]-1)), min(i[1]+1, int(self.shape[1]-1)), min(i[2]+1, int(self.shape[2]-1))]

        return (
            c000 * (1-f[0]) * (1-f[1]) * (1-f[2]) +
            c100 * f[0] * (1-f[1]) * (1-f[2]) +
            c010 * (1-f[0]) * f[1] * (1-f[2]) +
            c001 * (1-f[0]) * (1-f[1]) * f[2] +
            c110 * f[0] * f[1] * (1-f[2]) +
            c101 * f[0] * (1-f[1]) * f[2] +
            c011 * (1-f[0]) * f[1] * f[2] +
            c111 * f[0] * f[1] * f[2]
        )

    def render(self, resolution=(256, 256), camera_pos=(2.0, 2.0, 2.0),
               look_at=None, n_steps=128, step_size=None) -> np.ndarray:
        """
        Render the volume from a given camera position.
        Returns RGBA image as (H, W, 4) numpy array.
        """
        h, w = resolution
        camera = np.array(camera_pos, dtype=np.float32)
        center = np.array(look_at or self.shape / 2, dtype=np.float32)

        if step_size is None:
            step_size = float(np.max(self.shape)) / n_steps

        # Simple orthographic-ish projection
        forward = center - camera
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, np.array([0, 1, 0]))
        if np.linalg.norm(right) < 1e-6:
            right = np.cross(forward, np.array([0, 0, 1]))
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)
        up = up / np.linalg.norm(up)

        image = np.zeros((h, w, 4), dtype=np.float32)
        extent = float(np.max(self.shape))

        for y in range(h):
            for x in range(w):
                # Normalized screen coords
                u = (x / w - 0.5) * extent
                v = (y / h - 0.5) * extent

                ray_origin = camera + right * u + up * v
                ray_dir = forward

                # March through volume
                color = np.zeros(4)
                for step in range(n_steps):
                    pos = ray_origin + ray_dir * step * step_size
                    # Check bounds
                    if np.any(pos < 0) or np.any(pos >= self.shape - 1):
                        continue
                    density = self.sample(pos)
                    if density > 0.01:
                        r, g, b, a = self.transfer_fn(density)
                        a *= step_size
                        color[0] += (1 - color[3]) * r * a
                        color[1] += (1 - color[3]) * g * a
                        color[2] += (1 - color[3]) * b * a
                        color[3] += (1 - color[3]) * a
                        if color[3] > 0.95:
                            break

                image[y, x] = np.clip(color, 0, 1)

        return image


def render_slices(volume: np.ndarray, axis=0, n_slices=4,
                  cmap="gray", title="Volume Slices", figsize=(12, 3)):
    """
    Render orthogonal slices through a 3D volume.
    axis: 0=sagittal, 1=coronal, 2=axial.
    Returns matplotlib Figure.
    """
    import matplotlib.pyplot as plt

    indices = np.linspace(0, volume.shape[axis] - 1, n_slices, dtype=int)

    fig, axes = plt.subplots(1, n_slices, figsize=figsize)
    if n_slices == 1:
        axes = [axes]

    for i, idx in enumerate(indices):
        slc = np.take(volume, idx, axis=axis)
        axes[i].imshow(slc, cmap=cmap, aspect="auto")
        axes[i].set_title(f"Slice {idx}")
        axes[i].axis("off")

    fig.suptitle(title)
    fig.tight_layout()
    return fig
