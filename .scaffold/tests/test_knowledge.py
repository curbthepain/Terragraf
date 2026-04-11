"""
Tests for the Knowledge Registry — writer and reader utilities.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TERRA_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTS = TERRA_ROOT / "projects"
WRITER = PROJECTS / "knowledge_writer.py"
READER = PROJECTS / "knowledge_reader.py"


def run_writer(*args):
    """Run knowledge_writer.py as subprocess."""
    return subprocess.run(
        [sys.executable, str(WRITER)] + list(args),
        capture_output=True, text=True, cwd=str(TERRA_ROOT),
    )


def run_reader(*args):
    """Run knowledge_reader.py as subprocess."""
    return subprocess.run(
        [sys.executable, str(READER)] + list(args),
        capture_output=True, text=True, cwd=str(TERRA_ROOT),
    )


# ── Writer Tests ─────────────────────────────────────────────────────


class TestWriterAdd:
    """Test adding entries to a temporary KNOWLEDGE.toml."""

    def test_add_entry(self, tmp_path):
        toml_file = tmp_path / "KNOWLEDGE.toml"
        toml_file.write_text("# test\n", encoding="utf-8")

        sys.path.insert(0, str(PROJECTS))
        import knowledge_writer
        original_file = knowledge_writer.KNOWLEDGE_FILE
        knowledge_writer.KNOWLEDGE_FILE = toml_file

        rc = knowledge_writer.append_entry(
            "test-add", "unit-test", "pattern",
            "A test pattern", "Detail here", "tag1,tag2",
        )
        assert rc == 0
        content = toml_file.read_text(encoding="utf-8")
        assert 'id = "test-add"' in content
        assert 'category = "pattern"' in content
        assert '"tag1"' in content

        # Restore
        knowledge_writer.KNOWLEDGE_FILE = original_file

    def test_deduplicate(self, tmp_path):
        toml_file = tmp_path / "KNOWLEDGE.toml"
        toml_file.write_text(textwrap.dedent("""\
            [[knowledge]]
            id = "existing-id"
            source = "test"
            category = "pattern"
            summary = "Exists"
            detail = "Already here"
            tags = []
            created = "2026-01-01"
        """), encoding="utf-8")

        sys.path.insert(0, str(PROJECTS))
        import knowledge_writer
        original_file = knowledge_writer.KNOWLEDGE_FILE
        knowledge_writer.KNOWLEDGE_FILE = toml_file

        rc = knowledge_writer.append_entry(
            "existing-id", "test", "pattern",
            "Duplicate", "Should fail", "",
        )
        assert rc == 1

        # Restore
        knowledge_writer.KNOWLEDGE_FILE = original_file

    def test_invalid_category(self, tmp_path):
        toml_file = tmp_path / "KNOWLEDGE.toml"
        toml_file.write_text("# test\n", encoding="utf-8")

        sys.path.insert(0, str(PROJECTS))
        import knowledge_writer
        original_file = knowledge_writer.KNOWLEDGE_FILE
        knowledge_writer.KNOWLEDGE_FILE = toml_file

        rc = knowledge_writer.append_entry(
            "bad-cat", "test", "invalid_category",
            "Bad", "Bad detail", "",
        )
        assert rc == 1

        # Restore
        knowledge_writer.KNOWLEDGE_FILE = original_file


class TestWriterCLI:
    """Test writer CLI via subprocess against real KNOWLEDGE.toml."""

    def test_missing_required_args(self):
        result = run_writer()
        assert result.returncode != 0

    def test_help(self):
        result = run_writer("--help")
        assert result.returncode == 0
        assert "--id" in result.stdout


# ── Reader Tests ─────────────────────────────────────────────────────


class TestReaderList:
    """Test reader listing from the real KNOWLEDGE.toml."""

    def test_list_all(self):
        result = run_reader()
        assert result.returncode == 0
        assert "fft-import-pattern" in result.stdout
        assert "pydub-fallback" in result.stdout
        assert "opengl-theme-colors" in result.stdout

    def test_count_header(self):
        result = run_reader()
        assert "Knowledge Registry" in result.stdout
        # Should show at least 3 entries
        assert "3 entries" in result.stdout or "entries" in result.stdout


class TestReaderFilterTag:
    def test_filter_by_tag(self):
        result = run_reader("--tag", "fft")
        assert result.returncode == 0
        assert "fft-import-pattern" in result.stdout
        assert "pydub-fallback" not in result.stdout

    def test_filter_by_tag_no_match(self):
        result = run_reader("--tag", "nonexistent_tag_xyz")
        assert result.returncode == 0
        assert "No entries found" in result.stdout


class TestReaderFilterCategory:
    def test_filter_by_category(self):
        result = run_reader("--category", "caveat")
        assert result.returncode == 0
        assert "pydub-fallback" in result.stdout
        assert "fft-import-pattern" not in result.stdout


class TestReaderFilterSource:
    def test_filter_by_source(self):
        result = run_reader("--source", "music-viz")
        assert result.returncode == 0
        assert "fft-import-pattern" in result.stdout


class TestReaderSearch:
    def test_search_text(self):
        result = run_reader("--search", "ffmpeg")
        assert result.returncode == 0
        assert "pydub-fallback" in result.stdout
        assert "fft-import-pattern" not in result.stdout

    def test_search_no_match(self):
        result = run_reader("--search", "nonexistent_query_xyz")
        assert result.returncode == 0
        assert "No entries found" in result.stdout


class TestReaderCombined:
    def test_tag_and_source(self):
        result = run_reader("--tag", "fft", "--source", "music-viz")
        assert result.returncode == 0
        assert "fft-import-pattern" in result.stdout

    def test_conflicting_filters(self):
        result = run_reader("--tag", "fft", "--category", "caveat")
        assert result.returncode == 0
        assert "No entries found" in result.stdout
