"""
.scaffold/viz/3d/scene.py
3D scene manager — camera, lighting, coordinate systems.

Provides:
  - Scene   — manages camera, lights, and renderable objects
  - Camera  — perspective/orthographic camera
  - Light   — point/directional light
"""

import numpy as np
from typing import List, Optional, Tuple


class Camera:
    """3D camera with perspective or orthographic projection."""

    def __init__(self, position=(0, 0, 5), look_at=(0, 0, 0),
                 up=(0, 1, 0), fov=60.0, near=0.1, far=100.0):
        self.position = np.array(position, dtype=np.float32)
        self.look_at = np.array(look_at, dtype=np.float32)
        self.up = np.array(up, dtype=np.float32)
        self.fov = fov
        self.near = near
        self.far = far

    def view_matrix(self) -> np.ndarray:
        """Compute the 4x4 view matrix (world → camera space)."""
        forward = self.look_at - self.position
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, self.up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        view = np.eye(4, dtype=np.float32)
        view[0, :3] = right
        view[1, :3] = up
        view[2, :3] = -forward
        view[0, 3] = -np.dot(right, self.position)
        view[1, 3] = -np.dot(up, self.position)
        view[2, 3] = np.dot(forward, self.position)
        return view

    def projection_matrix(self, aspect=1.0) -> np.ndarray:
        """Compute 4x4 perspective projection matrix."""
        fov_rad = np.radians(self.fov)
        f = 1.0 / np.tan(fov_rad / 2)
        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = f / aspect
        proj[1, 1] = f
        proj[2, 2] = (self.far + self.near) / (self.near - self.far)
        proj[2, 3] = (2 * self.far * self.near) / (self.near - self.far)
        proj[3, 2] = -1.0
        return proj

    def orbit(self, azimuth: float, elevation: float, radius: Optional[float] = None):
        """Orbit the camera around look_at point."""
        if radius is None:
            radius = np.linalg.norm(self.position - self.look_at)
        az = np.radians(azimuth)
        el = np.radians(elevation)
        self.position = self.look_at + np.array([
            radius * np.cos(el) * np.sin(az),
            radius * np.sin(el),
            radius * np.cos(el) * np.cos(az),
        ], dtype=np.float32)


class Light:
    """Point or directional light source."""

    def __init__(self, position=(5, 5, 5), color=(1, 1, 1),
                 intensity=1.0, directional=False):
        self.position = np.array(position, dtype=np.float32)
        self.color = np.array(color, dtype=np.float32)
        self.intensity = intensity
        self.directional = directional

    def direction_to(self, point: np.ndarray) -> np.ndarray:
        """Get normalized direction from light to a point."""
        if self.directional:
            d = -self.position
        else:
            d = self.position - point
        return d / max(np.linalg.norm(d), 1e-8)


class Scene:
    """
    3D scene container. Holds camera, lights, and objects to render.
    Coordinates rendering pipeline.
    """

    def __init__(self):
        self.camera = Camera()
        self.lights: List[Light] = [Light()]
        self.objects: List[dict] = []

    def add_object(self, vertices: np.ndarray, faces: np.ndarray = None,
                   colors: np.ndarray = None, name: str = "object"):
        """Add a renderable object to the scene."""
        self.objects.append({
            "name": name,
            "vertices": np.asarray(vertices, dtype=np.float32),
            "faces": faces,
            "colors": colors,
        })

    def add_light(self, position=(5, 5, 5), color=(1, 1, 1), intensity=1.0):
        """Add a light source."""
        self.lights.append(Light(position, color, intensity))

    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get the axis-aligned bounding box of all objects."""
        all_verts = np.concatenate([o["vertices"] for o in self.objects])
        return all_verts.min(axis=0), all_verts.max(axis=0)

    def auto_camera(self):
        """Position camera to frame all objects."""
        if not self.objects:
            return
        bmin, bmax = self.bounds()
        center = (bmin + bmax) / 2
        extent = np.linalg.norm(bmax - bmin)
        self.camera.look_at = center
        self.camera.position = center + np.array([0, 0, extent * 1.5])

    def render_matplotlib(self, figsize=(10, 8), title="Scene"):
        """Render scene using matplotlib 3D. Returns Figure."""
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection="3d")

        for obj in self.objects:
            verts = obj["vertices"]
            colors = obj["colors"]
            if obj["faces"] is not None:
                from mpl_toolkits.mplot3d.art3d import Poly3DCollection
                polys = verts[obj["faces"]]
                collection = Poly3DCollection(polys, alpha=0.7, edgecolor="gray")
                ax.add_collection3d(collection)
            else:
                ax.scatter(verts[:, 0], verts[:, 1], verts[:, 2],
                          c=colors, s=1, alpha=0.6)

        ax.set_title(title)
        fig.tight_layout()
        return fig
