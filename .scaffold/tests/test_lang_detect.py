"""
Tests for .scaffold/generators/lang_detect.py
Language detection for project-aware generators.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add .scaffold to path for imports
_SCAFFOLD_DIR = Path(__file__).parent.parent
if str(_SCAFFOLD_DIR) not in sys.path:
    sys.path.insert(0, str(_SCAFFOLD_DIR))

from generators.lang_detect import detect_language, read_project_lang, LanguageInfo


class TestDetectLanguage:
    """Test language detection from file patterns."""

    def test_python_project(self, tmp_path):
        """Detects Python from .py files and requirements.txt."""
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()
        (tmp_path / "requirements.txt").touch()
        (tmp_path / "setup.py").touch()
        info = detect_language(tmp_path)
        assert info.primary == "python"
        assert info.naming == "snake_case"
        assert info.test_framework == "pytest"
        assert info.file_ext == ".py"

    def test_javascript_project(self, tmp_path):
        """Detects JavaScript from package.json and .js files."""
        (tmp_path / "index.js").touch()
        (tmp_path / "app.js").touch()
        (tmp_path / "package.json").touch()
        (tmp_path / "package-lock.json").touch()
        info = detect_language(tmp_path)
        assert info.primary == "javascript"
        assert info.naming == "camelCase"
        assert info.test_framework == "jest"

    def test_typescript_detected_as_javascript(self, tmp_path):
        """TypeScript files count toward JavaScript."""
        (tmp_path / "app.ts").touch()
        (tmp_path / "tsconfig.json").touch()
        (tmp_path / "package.json").touch()
        info = detect_language(tmp_path)
        assert info.primary == "javascript"

    def test_cpp_project(self, tmp_path):
        """Detects C++ from .cpp files and CMakeLists.txt."""
        (tmp_path / "main.cpp").touch()
        (tmp_path / "utils.cpp").touch()
        (tmp_path / "utils.h").touch()
        (tmp_path / "CMakeLists.txt").touch()
        info = detect_language(tmp_path)
        assert info.primary == "cpp"
        assert info.import_style == "#include"

    def test_rust_project(self, tmp_path):
        """Detects Rust from .rs files and Cargo.toml."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.rs").touch()
        (src / "lib.rs").touch()
        (tmp_path / "Cargo.toml").touch()
        info = detect_language(tmp_path)
        assert info.primary == "rust"
        assert info.test_framework == "cargo-test"

    def test_go_project(self, tmp_path):
        """Detects Go from .go files and go.mod."""
        (tmp_path / "main.go").touch()
        (tmp_path / "handler.go").touch()
        (tmp_path / "go.mod").touch()
        info = detect_language(tmp_path)
        assert info.primary == "go"
        assert info.test_pattern == "*_test.go"

    def test_java_project(self, tmp_path):
        """Detects Java from .java files and pom.xml."""
        src = tmp_path / "src" / "main" / "java"
        src.mkdir(parents=True)
        (src / "App.java").touch()
        (tmp_path / "pom.xml").touch()
        info = detect_language(tmp_path)
        assert info.primary == "java"

    def test_csharp_project(self, tmp_path):
        """Detects C# from .cs files and .csproj."""
        (tmp_path / "Program.cs").touch()
        (tmp_path / "MyApp.csproj").touch()
        info = detect_language(tmp_path)
        assert info.primary == "csharp"
        assert info.naming == "PascalCase"

    def test_empty_project(self, tmp_path):
        """Empty directory returns unknown."""
        info = detect_language(tmp_path)
        assert info.primary == "unknown"
        assert info.confidence == 0.0

    def test_mixed_project_picks_dominant(self, tmp_path):
        """Mixed project picks the dominant language."""
        # More Python than JS
        for i in range(5):
            (tmp_path / f"mod{i}.py").touch()
        (tmp_path / "requirements.txt").touch()
        (tmp_path / "helper.js").touch()
        info = detect_language(tmp_path)
        assert info.primary == "python"
        assert "javascript" in info.secondary

    def test_confidence_higher_for_clear_projects(self, tmp_path):
        """Pure single-language project has high confidence."""
        for i in range(10):
            (tmp_path / f"mod{i}.py").touch()
        (tmp_path / "setup.py").touch()
        info = detect_language(tmp_path)
        assert info.confidence > 0.8

    def test_skips_node_modules(self, tmp_path):
        """Doesn't scan node_modules."""
        (tmp_path / "main.py").touch()
        (tmp_path / "requirements.txt").touch()
        nm = tmp_path / "node_modules" / "some_pkg"
        nm.mkdir(parents=True)
        for i in range(100):
            (nm / f"file{i}.js").touch()
        info = detect_language(tmp_path)
        assert info.primary == "python"

    def test_skips_venv(self, tmp_path):
        """Doesn't scan .venv or venv."""
        (tmp_path / "main.go").touch()
        (tmp_path / "go.mod").touch()
        venv = tmp_path / "venv" / "lib"
        venv.mkdir(parents=True)
        for i in range(50):
            (venv / f"mod{i}.py").touch()
        info = detect_language(tmp_path)
        assert info.primary == "go"

    def test_max_depth_limits_walk(self, tmp_path):
        """Respects max_depth parameter."""
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        for i in range(20):
            (deep / f"file{i}.rs").touch()
        (deep / "Cargo.toml").touch()
        # Default max_depth=3, deep is at depth 4
        info = detect_language(tmp_path, max_depth=3)
        assert info.primary == "unknown"

    def test_secondary_languages(self, tmp_path):
        """Reports secondary languages found."""
        (tmp_path / "main.py").touch()
        (tmp_path / "setup.py").touch()
        (tmp_path / "helper.cpp").touch()
        (tmp_path / "CMakeLists.txt").touch()
        info = detect_language(tmp_path)
        assert info.primary == "python"
        assert "cpp" in info.secondary

    def test_entry_file_set(self, tmp_path):
        """Entry file matches language conventions."""
        (tmp_path / "main.rs").touch()
        (tmp_path / "Cargo.toml").touch()
        info = detect_language(tmp_path)
        assert info.entry_file == "main.rs"


class TestReadProjectLang:
    """Test reading language from project.h."""

    def test_reads_from_project_h(self, tmp_path):
        """Reads first language from project.h lang field."""
        headers = tmp_path / "headers"
        headers.mkdir()
        (headers / "project.h").write_text(
            '#project {\n    name: "test",\n    lang: "python, c++"\n}\n'
        )
        result = read_project_lang(tmp_path)
        assert result == "python"

    def test_returns_none_if_missing(self, tmp_path):
        """Returns None if project.h doesn't exist."""
        result = read_project_lang(tmp_path)
        assert result is None

    def test_returns_none_if_no_lang(self, tmp_path):
        """Returns None if project.h has no lang field."""
        headers = tmp_path / "headers"
        headers.mkdir()
        (headers / "project.h").write_text('#project {\n    name: "test"\n}\n')
        result = read_project_lang(tmp_path)
        assert result is None

    def test_single_language(self, tmp_path):
        """Works with a single language."""
        headers = tmp_path / "headers"
        headers.mkdir()
        (headers / "project.h").write_text(
            '#project {\n    lang: "rust"\n}\n'
        )
        result = read_project_lang(tmp_path)
        assert result == "rust"


class TestLanguageInfo:
    """Test LanguageInfo dataclass."""

    def test_defaults(self):
        info = LanguageInfo(primary="python")
        assert info.secondary == []
        assert info.naming == "snake_case"
        assert info.confidence == 0.0

    def test_all_fields(self):
        info = LanguageInfo(
            primary="go",
            secondary=["python"],
            naming="camelCase",
            test_framework="go-test",
            test_pattern="*_test.go",
            entry_file="main.go",
            import_style="import",
            file_ext=".go",
            confidence=0.85,
        )
        assert info.primary == "go"
        assert info.confidence == 0.85
