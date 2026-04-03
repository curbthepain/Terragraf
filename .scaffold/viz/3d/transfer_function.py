"""
.scaffold/viz/3d/transfer_function.py
Transfer functions — map data density values to colors and opacity.

Provides:
  - TransferFunction  — piecewise-linear RGBA transfer function
  - preset_grayscale  — simple grayscale ramp
  - preset_ultrasound — blue-orange ultrasound-style palette
  - preset_thermal    — cold-to-hot thermal palette
  - preset_ct         — CT scan style (bone, tissue, air)
"""

import numpy as np
from typing import List, Tuple


class TransferFunction:
    """
    Piecewise-linear transfer function: density (0-1) → RGBA color.

    Usage:
        tf = TransferFunction()
        tf.add_point(0.0, (0, 0, 0, 0))
        tf.add_point(0.3, (0.2, 0.4, 0.8, 0.1))
        tf.add_point(0.7, (0.9, 0.6, 0.2, 0.5))
        tf.add_point(1.0, (1, 1, 1, 0.9))
        color = tf(0.5)  # interpolated RGBA
    """

    def __init__(self):
        self.points: List[Tuple[float, Tuple[float, float, float, float]]] = []

    def add_point(self, density: float, rgba: Tuple[float, float, float, float]):
        """Add a control point. Points are auto-sorted by density."""
        self.points.append((density, rgba))
        self.points.sort(key=lambda p: p[0])

    def __call__(self, density: float) -> Tuple[float, float, float, float]:
        """Evaluate transfer function at a density value."""
        if not self.points:
            return (density, density, density, density)

        if density <= self.points[0][0]:
            return self.points[0][1]
        if density >= self.points[-1][0]:
            return self.points[-1][1]

        for i in range(len(self.points) - 1):
            d0, c0 = self.points[i]
            d1, c1 = self.points[i + 1]
            if d0 <= density <= d1:
                t = (density - d0) / (d1 - d0) if d1 != d0 else 0
                return tuple(c0[j] + t * (c1[j] - c0[j]) for j in range(4))

        return self.points[-1][1]

    def apply(self, volume: np.ndarray) -> np.ndarray:
        """
        Apply transfer function to an entire volume.
        Returns RGBA volume of shape (*volume.shape, 4).
        """
        flat = volume.ravel()
        result = np.zeros((len(flat), 4), dtype=np.float32)
        for i, d in enumerate(flat):
            result[i] = self(float(d))
        return result.reshape(*volume.shape, 4)


def preset_grayscale() -> TransferFunction:
    """Simple grayscale ramp."""
    tf = TransferFunction()
    tf.add_point(0.0, (0, 0, 0, 0))
    tf.add_point(0.1, (0.1, 0.1, 0.1, 0.05))
    tf.add_point(0.5, (0.5, 0.5, 0.5, 0.3))
    tf.add_point(1.0, (1, 1, 1, 0.8))
    return tf


def preset_ultrasound() -> TransferFunction:
    """Blue-orange palette mimicking ultrasound imaging."""
    tf = TransferFunction()
    tf.add_point(0.0, (0, 0, 0, 0))
    tf.add_point(0.1, (0.0, 0.05, 0.15, 0.02))
    tf.add_point(0.25, (0.1, 0.2, 0.5, 0.08))
    tf.add_point(0.4, (0.3, 0.4, 0.7, 0.15))
    tf.add_point(0.55, (0.6, 0.5, 0.3, 0.25))
    tf.add_point(0.7, (0.85, 0.6, 0.2, 0.4))
    tf.add_point(0.85, (0.95, 0.8, 0.4, 0.6))
    tf.add_point(1.0, (1.0, 0.95, 0.7, 0.85))
    return tf


def preset_thermal() -> TransferFunction:
    """Cold-to-hot thermal color palette."""
    tf = TransferFunction()
    tf.add_point(0.0, (0, 0, 0.2, 0))
    tf.add_point(0.2, (0, 0, 0.8, 0.1))
    tf.add_point(0.4, (0, 0.7, 0.7, 0.2))
    tf.add_point(0.6, (0.8, 0.8, 0, 0.4))
    tf.add_point(0.8, (1.0, 0.4, 0, 0.6))
    tf.add_point(1.0, (1.0, 0.0, 0, 0.9))
    return tf


def preset_ct() -> TransferFunction:
    """CT scan style — air transparent, tissue gray, bone white."""
    tf = TransferFunction()
    tf.add_point(0.0, (0, 0, 0, 0))       # Air
    tf.add_point(0.15, (0, 0, 0, 0))      # Still air
    tf.add_point(0.25, (0.4, 0.3, 0.3, 0.05))  # Soft tissue start
    tf.add_point(0.45, (0.6, 0.5, 0.5, 0.15))  # Tissue
    tf.add_point(0.65, (0.8, 0.7, 0.6, 0.3))   # Dense tissue
    tf.add_point(0.8, (0.9, 0.9, 0.85, 0.6))   # Bone start
    tf.add_point(1.0, (1.0, 1.0, 0.95, 0.9))   # Dense bone
    return tf
