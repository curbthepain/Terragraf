"""Tests for .scaffold/generators/gen_model.py and gen_shader.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.gen_model import generate_model
from generators.gen_shader import generate_shader


class TestGenModel:
    def test_base_model(self):
        code = generate_model("TestModel", "base")
        assert "class TestModel(ScaffoldModel)" in code
        assert "Base: base" in code

    def test_classifier(self):
        code = generate_model("MyClassifier", "classifier", num_classes=5)
        assert "class MyClassifier(Classifier)" in code
        assert "num_classes=5" in code

    def test_transformer(self):
        code = generate_model("MyTransformer", "transformer",
                              d_model=256, n_layers=4)
        assert "class MyTransformer(Transformer)" in code
        assert "d_model=256" in code
        assert "n_layers=4" in code
        assert "import torch.nn as nn" in code

    def test_cnn(self):
        code = generate_model("MyCNN", "cnn", num_classes=20)
        assert "class MyCNN(CNN)" in code
        assert "num_classes=20" in code

    def test_contains_import(self):
        code = generate_model("Foo", "base")
        assert "from scaffold.ml.models import ScaffoldModel" in code


class TestGenShader:
    def test_basic_shader(self):
        code = generate_shader("test_compute", n_buffers=2, workgroup_x=256)
        assert "#version 450" in code
        assert "local_size_x = 256" in code
        assert "InputBuffer" in code
        assert "OutputBuffer" in code

    def test_custom_buffers(self):
        code = generate_shader("multi_buf", n_buffers=4)
        assert "InputBuffer" in code
        assert "Buffer1" in code
        assert "Buffer2" in code
        assert "OutputBuffer" in code

    def test_push_constants(self):
        code = generate_shader("pc_shader", push_constants="uint n, uint stage")
        assert "PushConstants" in code
        assert "uint n, uint stage" in code

    def test_workgroup_size(self):
        code = generate_shader("wg", workgroup_x=512)
        assert "local_size_x = 512" in code

    def test_compile_comment(self):
        code = generate_shader("my_shader")
        assert "glslangValidator -V my_shader.comp" in code
