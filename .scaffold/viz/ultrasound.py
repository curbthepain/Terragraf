"""
.scaffold/viz/ultrasound.py
Ultrasound-style dataset imaging — treat feature spaces as 3D density fields.

High-level API: dataset in, image out.

Provides:
  - dataset_to_volume     — convert dataset features to 3D density field
  - render_ultrasound     — render dataset as ultrasound-style image
  - render_ct             — render dataset as CT-style image
  - render_thermal        — render dataset with thermal colormap
"""

import numpy as np
from typing import Tuple


def dataset_to_volume(data: np.ndarray, resolution: int = 64,
                       feature_dims: Tuple[int, int, int] = (0, 1, 2),
                       sigma: float = 1.0) -> np.ndarray:
    """
    Convert a dataset's feature space into a 3D density volume.

    data:         (N, D) array of data points (N samples, D features).
    resolution:   size of output volume (res x res x res).
    feature_dims: which 3 feature dimensions to use as XYZ axes.
    sigma:        Gaussian kernel width for density estimation.

    Returns: (resolution, resolution, resolution) density array (0-1).
    """
    n_samples = data.shape[0]
    d0, d1, d2 = feature_dims

    # Extract and copy the 3 feature columns
    x = data[:, d0].copy()
    y = data[:, d1].copy()
    z = data[:, d2].copy()

    # Normalize to [0, resolution-1]
    for arr in [x, y, z]:
        arr_min, arr_max = arr.min(), arr.max()
        if arr_max > arr_min:
            arr[:] = (arr - arr_min) / (arr_max - arr_min) * (resolution - 1)

    # Build density volume via Gaussian splatting
    volume = np.zeros((resolution, resolution, resolution), dtype=np.float32)
    for i in range(n_samples):
        ix, iy, iz = int(x[i]), int(y[i]), int(z[i])
        r = int(np.ceil(sigma * 3))
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    px, py, pz = ix + dx, iy + dy, iz + dz
                    if 0 <= px < resolution and 0 <= py < resolution and 0 <= pz < resolution:
                        dist2 = dx*dx + dy*dy + dz*dz
                        volume[px, py, pz] += np.exp(-dist2 / (2 * sigma * sigma))

    # Normalize to [0, 1]
    vmax = volume.max()
    if vmax > 0:
        volume /= vmax
    return volume


def render_ultrasound(data: np.ndarray, resolution: int = 64,
                       feature_dims: Tuple[int, int, int] = (0, 1, 2),
                       image_size: Tuple[int, int] = (256, 256),
                       camera_pos: Tuple[float, float, float] = (2.0, 2.0, 2.0)) -> np.ndarray:
    """
    Render a dataset as an ultrasound-style volume image.

    data:         (N, D) array of data points.
    resolution:   voxel grid resolution.
    feature_dims: which 3 features map to XYZ.
    image_size:   output image resolution.

    Returns: RGBA image as (H, W, 4) numpy array.
    """
    import importlib
    vol_mod = importlib.import_module(".3d.volume", package=__package__)
    tf_mod = importlib.import_module(".3d.transfer_function", package=__package__)

    volume = dataset_to_volume(data, resolution, feature_dims)
    tf = tf_mod.preset_ultrasound()
    renderer = vol_mod.VolumeRenderer(volume, transfer_fn=tf)
    return renderer.render(resolution=image_size, camera_pos=camera_pos)


def render_ct(data: np.ndarray, resolution: int = 64,
               feature_dims: Tuple[int, int, int] = (0, 1, 2),
               image_size: Tuple[int, int] = (256, 256)) -> np.ndarray:
    """Render dataset as CT-style volume image."""
    import importlib
    vol_mod = importlib.import_module(".3d.volume", package=__package__)
    tf_mod = importlib.import_module(".3d.transfer_function", package=__package__)

    volume = dataset_to_volume(data, resolution, feature_dims)
    tf = tf_mod.preset_ct()
    renderer = vol_mod.VolumeRenderer(volume, transfer_fn=tf)
    return renderer.render(resolution=image_size)


def render_thermal(data: np.ndarray, resolution: int = 64,
                    feature_dims: Tuple[int, int, int] = (0, 1, 2),
                    image_size: Tuple[int, int] = (256, 256)) -> np.ndarray:
    """Render dataset with thermal colormap."""
    import importlib
    vol_mod = importlib.import_module(".3d.volume", package=__package__)
    tf_mod = importlib.import_module(".3d.transfer_function", package=__package__)

    volume = dataset_to_volume(data, resolution, feature_dims)
    tf = tf_mod.preset_thermal()
    renderer = vol_mod.VolumeRenderer(volume, transfer_fn=tf)
    return renderer.render(resolution=image_size)
