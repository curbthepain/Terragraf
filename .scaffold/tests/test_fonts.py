"""Tests for the bundled application fonts."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import PySide6  # noqa: F401
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

needs_qt = pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not installed")


EXPECTED_FONT_FILES = {
    "Barlow-Regular.ttf",
    "Barlow-Medium.ttf",
    "Barlow-SemiBold.ttf",
    "Barlow-Bold.ttf",
    "BarlowCondensed-Regular.ttf",
    "BarlowCondensed-SemiBold.ttf",
    "BarlowCondensed-Bold.ttf",
    "BarlowCondensed-ExtraBold.ttf",
    "BarlowCondensed-Black.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Bold.ttf",
}


def test_fonts_directory_exists():
    """The fonts/ package directory is present."""
    from app import fonts as app_fonts
    assert Path(app_fonts.__file__).parent.is_dir()


def test_all_expected_font_files_present():
    """Every TTF the QSS font stack expects is bundled."""
    from app import fonts as app_fonts
    found = {p.name for p in app_fonts.font_files()}
    missing = EXPECTED_FONT_FILES - found
    assert not missing, f"missing font files: {sorted(missing)}"


def test_font_files_are_nonempty():
    """No empty/zero-byte font files (catches failed downloads)."""
    from app import fonts as app_fonts
    for ttf in app_fonts.font_files():
        assert ttf.stat().st_size > 1000, f"{ttf.name} is suspiciously small"


def test_font_files_have_ttf_magic():
    """Each .ttf starts with a valid TrueType / OpenType signature."""
    from app import fonts as app_fonts
    valid_magics = (
        b"\x00\x01\x00\x00",  # TrueType
        b"OTTO",              # OpenType (CFF)
        b"true",              # Apple TrueType
        b"typ1",              # PostScript Type1
    )
    for ttf in app_fonts.font_files():
        with ttf.open("rb") as f:
            magic = f.read(4)
        assert magic in valid_magics, f"{ttf.name} has invalid magic: {magic!r}"


@needs_qt
def test_register_fonts_loads_all(qapp=None):
    """register_fonts() loads every bundled TTF without errors."""
    # Spin up a QApplication if one isn't already running.
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from app import fonts as app_fonts
    loaded, failed = app_fonts.register_fonts()
    assert loaded == len(EXPECTED_FONT_FILES), \
        f"loaded={loaded}, failed={failed} (expected {len(EXPECTED_FONT_FILES)})"
    assert failed == 0
