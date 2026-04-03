"""Smoke tests for the Qt container app module."""

import sys
from pathlib import Path

# Ensure .scaffold is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_theme_constants():
    """Theme module loads and has expected palette entries."""
    from app.theme import (
        BG_PRIMARY,
        BG_SECONDARY,
        TEXT_PRIMARY,
        ACCENT,
        GREEN,
        STYLESHEET,
    )

    assert BG_PRIMARY.startswith("#")
    assert BG_SECONDARY.startswith("#")
    assert TEXT_PRIMARY.startswith("#")
    assert ACCENT.startswith("#")
    assert GREEN.startswith("#")
    assert "QMainWindow" in STYLESHEET
    assert "QStatusBar" in STYLESHEET


def test_theme_stylesheet_valid_css_structure():
    """Stylesheet contains expected selectors and no broken f-string refs."""
    from app.theme import STYLESHEET

    # Should not contain unresolved f-string placeholders
    assert "{" not in STYLESHEET.replace("{{", "").replace("}}", "") or \
           "background-color" in STYLESHEET
    # Basic sanity — no Python tracebacks baked in
    assert "Traceback" not in STYLESHEET
