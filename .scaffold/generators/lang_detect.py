"""
.scaffold/generators/lang_detect.py
Detect the primary language of a project by inspecting file patterns.

Used by generators to adapt output conventions (naming, structure,
test frameworks, imports) without requiring explicit --lang flags.

Usage:
    from generators.lang_detect import detect_language, LanguageInfo
    info = detect_language("/path/to/project")
    print(info.primary)       # "python"
    print(info.test_framework) # "pytest"
    print(info.naming)         # "snake_case"
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LanguageInfo:
    """Detected language profile for a project."""
    primary: str                        # e.g. "python", "javascript", "cpp", "rust", "go"
    secondary: list[str] = field(default_factory=list)  # other languages present
    naming: str = "snake_case"          # snake_case, camelCase, PascalCase, kebab-case
    test_framework: str = ""            # pytest, jest, gtest, cargo-test, go-test
    test_pattern: str = ""              # test_*.py, *.test.js, *_test.go, etc.
    entry_file: str = ""                # __init__.py, index.js, main.rs, main.go
    import_style: str = ""              # "from x import y", "import x", "require", "#include"
    file_ext: str = ""                  # .py, .js, .rs, .go, .cpp
    confidence: float = 0.0             # 0.0–1.0


# Language signatures: (glob_pattern, weight)
_SIGNATURES = {
    "python": [
        ("*.py", 1.0),
        ("setup.py", 3.0),
        ("pyproject.toml", 3.0),
        ("setup.cfg", 2.0),
        ("requirements*.txt", 2.0),
        ("Pipfile", 2.0),
        ("poetry.lock", 2.0),
        ("tox.ini", 1.5),
        ("pytest.ini", 2.0),
        (".flake8", 1.0),
        ("mypy.ini", 1.0),
    ],
    "javascript": [
        ("*.js", 1.0),
        ("*.jsx", 1.0),
        ("*.ts", 1.0),
        ("*.tsx", 1.0),
        ("package.json", 3.0),
        ("package-lock.json", 2.0),
        ("yarn.lock", 2.0),
        ("tsconfig.json", 2.0),
        (".eslintrc*", 1.5),
        ("webpack.config.*", 1.5),
        ("vite.config.*", 1.5),
        ("next.config.*", 1.5),
    ],
    "cpp": [
        ("*.cpp", 1.0),
        ("*.cc", 1.0),
        ("*.cxx", 1.0),
        ("*.h", 0.8),
        ("*.hpp", 1.0),
        ("CMakeLists.txt", 3.0),
        ("Makefile", 1.5),
        ("*.cmake", 1.5),
        ("conanfile.*", 2.0),
        ("vcpkg.json", 2.0),
    ],
    "rust": [
        ("*.rs", 1.0),
        ("Cargo.toml", 3.0),
        ("Cargo.lock", 2.0),
    ],
    "go": [
        ("*.go", 1.0),
        ("go.mod", 3.0),
        ("go.sum", 2.0),
    ],
    "java": [
        ("*.java", 1.0),
        ("pom.xml", 3.0),
        ("build.gradle", 3.0),
        ("build.gradle.kts", 3.0),
        ("settings.gradle*", 1.5),
    ],
    "csharp": [
        ("*.cs", 1.0),
        ("*.csproj", 3.0),
        ("*.sln", 3.0),
        ("nuget.config", 1.5),
    ],
}

# Language-specific conventions
_CONVENTIONS = {
    "python": {
        "naming": "snake_case",
        "test_framework": "pytest",
        "test_pattern": "test_*.py",
        "entry_file": "__init__.py",
        "import_style": "from x import y",
        "file_ext": ".py",
    },
    "javascript": {
        "naming": "camelCase",
        "test_framework": "jest",
        "test_pattern": "*.test.js",
        "entry_file": "index.js",
        "import_style": "import/require",
        "file_ext": ".js",
    },
    "cpp": {
        "naming": "snake_case",
        "test_framework": "gtest",
        "test_pattern": "test_*.cpp",
        "entry_file": "main.cpp",
        "import_style": "#include",
        "file_ext": ".cpp",
    },
    "rust": {
        "naming": "snake_case",
        "test_framework": "cargo-test",
        "test_pattern": "*_test.rs",
        "entry_file": "main.rs",
        "import_style": "use",
        "file_ext": ".rs",
    },
    "go": {
        "naming": "camelCase",
        "test_framework": "go-test",
        "test_pattern": "*_test.go",
        "entry_file": "main.go",
        "import_style": "import",
        "file_ext": ".go",
    },
    "java": {
        "naming": "camelCase",
        "test_framework": "junit",
        "test_pattern": "*Test.java",
        "entry_file": "Main.java",
        "import_style": "import",
        "file_ext": ".java",
    },
    "csharp": {
        "naming": "PascalCase",
        "test_framework": "xunit",
        "test_pattern": "*Tests.cs",
        "entry_file": "Program.cs",
        "import_style": "using",
        "file_ext": ".cs",
    },
}


def detect_language(project_dir: str | Path, max_depth: int = 3) -> LanguageInfo:
    """
    Detect the primary language of a project.

    Walks the project directory (up to max_depth), counts file pattern
    matches weighted by significance, and returns a LanguageInfo with
    the primary language and its conventions.

    Args:
        project_dir: Root of the project to analyze.
        max_depth: How deep to walk (default 3, avoids node_modules etc.)

    Returns:
        LanguageInfo with detected language and conventions.
    """
    project_dir = Path(project_dir)
    scores: dict[str, float] = {lang: 0.0 for lang in _SIGNATURES}

    # Directories to skip
    skip_dirs = {
        ".git", ".scaffold", "node_modules", "__pycache__", ".venv",
        "venv", "env", ".env", "build", "dist", "target", ".tox",
        ".mypy_cache", ".pytest_cache", "vendor", "third_party",
    }

    for root, dirs, files in os.walk(project_dir):
        # Prune skipped and deep directories
        rel = Path(root).relative_to(project_dir)
        depth = len(rel.parts) if str(rel) != "." else 0
        if depth >= max_depth:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for lang, patterns in _SIGNATURES.items():
            for pattern, weight in patterns:
                for f in files:
                    if _matches(f, pattern):
                        scores[lang] += weight

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ranked = [(lang, score) for lang, score in ranked if score > 0]

    if not ranked:
        return LanguageInfo(primary="unknown", confidence=0.0)

    primary_lang, primary_score = ranked[0]
    total = sum(s for _, s in ranked)
    confidence = primary_score / total if total > 0 else 0.0

    secondary = [lang for lang, score in ranked[1:] if score > 0]

    conv = _CONVENTIONS.get(primary_lang, {})
    return LanguageInfo(
        primary=primary_lang,
        secondary=secondary,
        naming=conv.get("naming", "snake_case"),
        test_framework=conv.get("test_framework", ""),
        test_pattern=conv.get("test_pattern", ""),
        entry_file=conv.get("entry_file", ""),
        import_style=conv.get("import_style", ""),
        file_ext=conv.get("file_ext", ""),
        confidence=round(confidence, 2),
    )


def read_project_lang(scaffold_dir: str | Path) -> Optional[str]:
    """
    Read the primary language from project.h if it exists.

    Parses the #project { lang: "..." } block.
    """
    project_h = Path(scaffold_dir) / "headers" / "project.h"
    if not project_h.exists():
        return None
    text = project_h.read_text()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("lang:"):
            # Extract first language from the list
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            return val.split(",")[0].strip()
    return None


def _matches(filename: str, pattern: str) -> bool:
    """Simple glob match for file names (not paths)."""
    import fnmatch
    return fnmatch.fnmatch(filename, pattern)
