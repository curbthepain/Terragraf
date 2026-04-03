"""Tests for the 3D visualization layer — mesh, nodes, scene, volume, transfer_function, export."""

import sys
import importlib
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")

# viz/3d is not a valid Python identifier, so import via importlib
_tf_mod = importlib.import_module("viz.3d.transfer_function")
_mesh_mod = importlib.import_module("viz.3d.mesh")
_nodes_mod = importlib.import_module("viz.3d.nodes")
_scene_mod = importlib.import_module("viz.3d.scene")
_volume_mod = importlib.import_module("viz.3d.volume")
_export_mod = importlib.import_module("viz.3d.export")

TransferFunction = _tf_mod.TransferFunction
preset_grayscale = _tf_mod.preset_grayscale
preset_ultrasound = _tf_mod.preset_ultrasound
preset_thermal = _tf_mod.preset_thermal
preset_ct = _tf_mod.preset_ct

generate_surface = _mesh_mod.generate_surface
generate_point_cloud = _mesh_mod.generate_point_cloud
render_surface = _mesh_mod.render_surface
render_point_cloud = _mesh_mod.render_point_cloud

NodeGraph = _nodes_mod.NodeGraph
render_node_graph = _nodes_mod.render_node_graph

Camera = _scene_mod.Camera
Light = _scene_mod.Light
Scene = _scene_mod.Scene

VolumeRenderer = _volume_mod.VolumeRenderer

export_obj = _export_mod.export_obj
export_ply = _export_mod.export_ply


# ── Transfer Function ──────────────────────────────────────────────

class TestTransferFunction:
    def test_empty_returns_identity(self):
        
        tf = TransferFunction()
        r, g, b, a = tf(0.5)
        assert r == g == b == a == 0.5

    def test_single_point_clamp(self):
        
        tf = TransferFunction()
        tf.add_point(0.5, (1, 0, 0, 1))
        assert tf(0.0) == (1, 0, 0, 1)
        assert tf(1.0) == (1, 0, 0, 1)

    def test_interpolation(self):
        
        tf = TransferFunction()
        tf.add_point(0.0, (0, 0, 0, 0))
        tf.add_point(1.0, (1, 1, 1, 1))
        r, g, b, a = tf(0.5)
        assert abs(r - 0.5) < 0.01
        assert abs(a - 0.5) < 0.01

    def test_boundary_values(self):
        
        tf = TransferFunction()
        tf.add_point(0.0, (0, 0, 0, 0))
        tf.add_point(1.0, (1, 1, 1, 1))
        assert tf(0.0) == (0, 0, 0, 0)
        assert tf(1.0) == (1, 1, 1, 1)

    def test_below_range_clamps(self):
        
        tf = TransferFunction()
        tf.add_point(0.2, (0.2, 0, 0, 0))
        tf.add_point(0.8, (0.8, 1, 1, 1))
        assert tf(0.0) == (0.2, 0, 0, 0)

    def test_above_range_clamps(self):
        
        tf = TransferFunction()
        tf.add_point(0.2, (0, 0, 0, 0))
        tf.add_point(0.8, (1, 1, 1, 1))
        assert tf(1.0) == (1, 1, 1, 1)

    def test_apply_to_volume(self):
        
        tf = TransferFunction()
        tf.add_point(0.0, (0, 0, 0, 0))
        tf.add_point(1.0, (1, 1, 1, 1))
        vol = np.array([[[0.0, 0.5], [1.0, 0.25]]])
        result = tf.apply(vol)
        assert result.shape == (1, 2, 2, 4)
        assert abs(result[0, 0, 1, 0] - 0.5) < 0.01  # density 0.5 -> r=0.5

    def test_points_sorted(self):
        
        tf = TransferFunction()
        tf.add_point(0.8, (1, 0, 0, 1))
        tf.add_point(0.2, (0, 0, 0, 0))
        assert tf.points[0][0] == 0.2
        assert tf.points[1][0] == 0.8


class TestTransferFunctionPresets:
    def test_preset_grayscale(self):
        
        tf = preset_grayscale()
        assert len(tf.points) > 0
        r, g, b, a = tf(0.5)
        assert 0 <= r <= 1

    def test_preset_ultrasound(self):
        
        tf = preset_ultrasound()
        assert len(tf.points) >= 4
        r, g, b, a = tf(0.5)
        assert 0 <= a <= 1

    def test_preset_thermal(self):
        
        tf = preset_thermal()
        assert len(tf.points) >= 4

    def test_preset_ct(self):
        
        tf = preset_ct()
        # Air should be transparent
        _, _, _, a = tf(0.0)
        assert a == 0.0


# ── Mesh ────────────────────────────────────────────────────────────

class TestMesh:
    def test_generate_surface_shape(self):
        
        z = np.random.rand(10, 20)
        X, Y, Z = generate_surface(z)
        assert X.shape == (10, 20)
        assert Y.shape == (10, 20)
        assert np.array_equal(Z, z)

    def test_generate_surface_range(self):
        
        z = np.ones((5, 5))
        X, Y, _ = generate_surface(z, x_range=(-1, 1), y_range=(0, 10))
        assert X.min() == pytest.approx(-1.0)
        assert X.max() == pytest.approx(1.0)
        assert Y.min() == pytest.approx(0.0)
        assert Y.max() == pytest.approx(10.0)

    def test_generate_point_cloud(self):
        
        data = np.random.rand(100, 3)
        cloud = generate_point_cloud(data)
        assert "vertices" in cloud
        assert cloud["vertices"].shape == (100, 3)

    def test_generate_point_cloud_with_colors(self):
        
        data = np.random.rand(50, 3)
        colors = np.random.rand(50, 4)
        cloud = generate_point_cloud(data, colors=colors)
        assert "colors" in cloud
        assert cloud["colors"].shape == (50, 4)

    def test_render_surface_returns_figure(self):
        
        import matplotlib.pyplot as plt
        z = np.random.rand(10, 10)
        fig = render_surface(z)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_render_point_cloud_returns_figure(self):
        
        import matplotlib.pyplot as plt
        data = np.random.rand(20, 3)
        fig = render_point_cloud(data)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# ── Nodes ───────────────────────────────────────────────────────────

class TestNodeGraph:
    def test_add_node(self):
        
        g = NodeGraph()
        g.add_node("a", label="Node A", group=1)
        assert "a" in g.nodes
        assert g.nodes["a"]["label"] == "Node A"
        assert g.nodes["a"]["group"] == 1

    def test_add_edge(self):
        
        g = NodeGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_edge("a", "b", weight=2.0)
        assert len(g.edges) == 1
        assert g.edges[0] == ("a", "b", 2.0)

    def test_spring_layout(self):
        
        g = NodeGraph()
        for name in ["a", "b", "c"]:
            g.add_node(name)
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.layout_spring(iterations=10)
        positions = g.get_positions()
        assert positions.shape == (3, 3)

    def test_positions_differ_after_layout(self):
        
        g = NodeGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_edge("a", "b")
        g.layout_spring(iterations=20)
        pa = g.nodes["a"]["position"]
        pb = g.nodes["b"]["position"]
        # Connected nodes should have pulled together somewhat
        assert not np.array_equal(pa, pb)

    def test_render_node_graph(self):
        import matplotlib.pyplot as plt
        g = NodeGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_edge("a", "b")
        fig = render_node_graph(g)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# ── Scene ───────────────────────────────────────────────────────────

class TestCamera:
    def test_view_matrix_shape(self):
        
        cam = Camera()
        vm = cam.view_matrix()
        assert vm.shape == (4, 4)

    def test_projection_matrix_shape(self):
        
        cam = Camera()
        pm = cam.projection_matrix(aspect=1.5)
        assert pm.shape == (4, 4)

    def test_orbit(self):
        
        cam = Camera(position=(0, 0, 5), look_at=(0, 0, 0))
        cam.orbit(90, 0)
        # After 90 degree azimuth orbit, x should be nonzero
        assert abs(cam.position[0]) > 0.1


class TestLight:
    def test_direction_to_point(self):
        
        light = Light(position=(10, 0, 0))
        direction = light.direction_to(np.array([0, 0, 0]))
        assert abs(np.linalg.norm(direction) - 1.0) < 1e-6

    def test_directional_light(self):
        
        light = Light(position=(0, 1, 0), directional=True)
        direction = light.direction_to(np.array([5, 5, 5]))
        # Directional: ignores target, uses -position
        assert direction[1] < 0


class TestScene:
    def test_add_object(self):
        
        scene = Scene()
        verts = np.random.rand(10, 3)
        scene.add_object(verts, name="test")
        assert len(scene.objects) == 1
        assert scene.objects[0]["name"] == "test"

    def test_bounds(self):
        
        scene = Scene()
        verts = np.array([[0, 0, 0], [1, 2, 3]], dtype=float)
        scene.add_object(verts)
        bmin, bmax = scene.bounds()
        assert np.allclose(bmin, [0, 0, 0])
        assert np.allclose(bmax, [1, 2, 3])

    def test_auto_camera(self):
        
        scene = Scene()
        verts = np.array([[0, 0, 0], [10, 10, 10]], dtype=float)
        scene.add_object(verts)
        scene.auto_camera()
        assert np.allclose(scene.camera.look_at, [5, 5, 5])

    def test_add_light(self):
        
        scene = Scene()
        scene.add_light(position=(1, 2, 3), intensity=0.5)
        assert len(scene.lights) == 2  # default + added

    def test_render_matplotlib(self):
        
        import matplotlib.pyplot as plt
        scene = Scene()
        verts = np.random.rand(20, 3)
        scene.add_object(verts)
        fig = scene.render_matplotlib()
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# ── Volume Renderer ─────────────────────────────────────────────────

class TestVolumeRenderer:
    def test_sample_center(self):
        
        vol = np.zeros((8, 8, 8), dtype=np.float32)
        vol[4, 4, 4] = 1.0
        renderer = VolumeRenderer(vol)
        val = renderer.sample(np.array([4.0, 4.0, 4.0]))
        assert val == pytest.approx(1.0, abs=0.01)

    def test_sample_interpolation(self):
        
        vol = np.zeros((4, 4, 4), dtype=np.float32)
        vol[1, 1, 1] = 1.0
        renderer = VolumeRenderer(vol)
        val = renderer.sample(np.array([1.0, 1.0, 1.0]))
        assert val == pytest.approx(1.0, abs=0.01)

    def test_sample_boundary(self):
        
        vol = np.ones((4, 4, 4), dtype=np.float32)
        renderer = VolumeRenderer(vol)
        val = renderer.sample(np.array([0.0, 0.0, 0.0]))
        assert val == pytest.approx(1.0, abs=0.01)

    def test_render_output_shape(self):
        vol = np.random.rand(16, 16, 16).astype(np.float32)
        renderer = VolumeRenderer(vol)
        img = renderer.render(resolution=(8, 8), camera_pos=(24, 24, 24), n_steps=8)
        assert img.shape == (8, 8, 4)

    def test_render_values_bounded(self):
        vol = np.random.rand(16, 16, 16).astype(np.float32)
        renderer = VolumeRenderer(vol)
        img = renderer.render(resolution=(8, 8), camera_pos=(24, 24, 24), n_steps=8)
        assert img.min() >= 0.0
        assert img.max() <= 1.0

    def test_render_with_transfer_fn(self):
        vol = np.random.rand(16, 16, 16).astype(np.float32)
        renderer = VolumeRenderer(vol, transfer_fn=preset_grayscale())
        img = renderer.render(resolution=(8, 8), camera_pos=(24, 24, 24), n_steps=8)
        assert img.shape == (8, 8, 4)


# ── 3D Export ───────────────────────────────────────────────────────

class TestExport3D:
    def test_export_obj_vertices(self):
        
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        with tempfile.NamedTemporaryFile(suffix=".obj", delete=False, mode="w") as f:
            path = f.name
        export_obj(path, verts)
        content = Path(path).read_text()
        assert content.count("\nv ") == 3

    def test_export_obj_faces(self):
        
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        faces = np.array([[0, 1, 2]])
        with tempfile.NamedTemporaryFile(suffix=".obj", delete=False, mode="w") as f:
            path = f.name
        export_obj(path, verts, faces=faces)
        content = Path(path).read_text()
        assert "f 1 2 3" in content  # OBJ is 1-indexed

    def test_export_obj_normals(self):
        
        verts = np.array([[0, 0, 0], [1, 0, 0]], dtype=float)
        normals = np.array([[0, 0, 1], [0, 0, 1]], dtype=float)
        with tempfile.NamedTemporaryFile(suffix=".obj", delete=False, mode="w") as f:
            path = f.name
        export_obj(path, verts, normals=normals)
        content = Path(path).read_text()
        assert "vn" in content

    def test_export_ply_vertices(self):
        
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False, mode="w") as f:
            path = f.name
        export_ply(path, verts)
        content = Path(path).read_text()
        assert "ply" in content
        assert "element vertex 3" in content

    def test_export_ply_with_colors(self):
        
        verts = np.array([[0, 0, 0], [1, 0, 0]], dtype=float)
        colors = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False, mode="w") as f:
            path = f.name
        export_ply(path, verts, colors=colors)
        content = Path(path).read_text()
        assert "property uchar red" in content

    def test_export_ply_with_faces(self):
        
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        faces = np.array([[0, 1, 2]])
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False, mode="w") as f:
            path = f.name
        export_ply(path, verts, faces=faces)
        content = Path(path).read_text()
        assert "element face 1" in content
        assert "3 0 1 2" in content
