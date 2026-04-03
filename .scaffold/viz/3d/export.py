"""
.scaffold/viz/3d/export.py
3D export utilities — OBJ, PLY, GLTF.

Provides:
  - export_obj  — export mesh to Wavefront OBJ format
  - export_ply  — export mesh/point cloud to PLY format
  - export_gltf — export mesh to GLTF format (requires trimesh)
"""

import numpy as np
from typing import Optional


def export_obj(path: str, vertices: np.ndarray,
               faces: Optional[np.ndarray] = None,
               normals: Optional[np.ndarray] = None):
    """
    Export mesh to Wavefront OBJ format.
    vertices: (N, 3) array of vertex positions.
    faces: (M, 3) array of triangle indices (0-based).
    normals: optional (N, 3) array of vertex normals.
    """
    with open(path, "w") as f:
        f.write("# Exported by Terragraf\n")

        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        if normals is not None:
            for n in normals:
                f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")

        if faces is not None:
            for face in faces:
                # OBJ is 1-indexed
                indices = " ".join(str(i + 1) for i in face)
                f.write(f"f {indices}\n")


def export_ply(path: str, vertices: np.ndarray,
               faces: Optional[np.ndarray] = None,
               colors: Optional[np.ndarray] = None):
    """
    Export mesh or point cloud to PLY format.
    vertices: (N, 3) array.
    faces: optional (M, 3) array.
    colors: optional (N, 3) array of RGB values (0-255 uint8 or 0-1 float).
    """
    n_verts = len(vertices)
    has_faces = faces is not None
    has_colors = colors is not None

    if has_colors and colors.max() <= 1.0:
        colors = (colors * 255).astype(np.uint8)

    with open(path, "w") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {n_verts}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        if has_colors:
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
        if has_faces:
            f.write(f"element face {len(faces)}\n")
            f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")

        for i in range(n_verts):
            line = f"{vertices[i, 0]:.6f} {vertices[i, 1]:.6f} {vertices[i, 2]:.6f}"
            if has_colors:
                line += f" {colors[i, 0]} {colors[i, 1]} {colors[i, 2]}"
            f.write(line + "\n")

        if has_faces:
            for face in faces:
                indices = " ".join(str(i) for i in face)
                f.write(f"{len(face)} {indices}\n")


def export_gltf(path: str, vertices: np.ndarray,
                faces: Optional[np.ndarray] = None):
    """
    Export mesh to GLTF format using trimesh.
    Requires: pip install trimesh
    """
    import trimesh

    if faces is not None:
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    else:
        mesh = trimesh.PointCloud(vertices)

    mesh.export(path)
