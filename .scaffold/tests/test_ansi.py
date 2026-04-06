"""Tests for app.widgets.ansi — SGR escape sequence helpers."""

from app.widgets.ansi import ansi_to_html, strip_ansi
from app import theme


def test_strip_ansi_removes_sgr():
    raw = "\x1b[1mhi\x1b[0m \x1b[32mok\x1b[0m"
    assert strip_ansi(raw) == "hi ok"


def test_strip_ansi_removes_other_csi():
    raw = "abc\x1b[2Kdef"
    assert strip_ansi(raw) == "abcdef"


def test_ansi_to_html_bold_and_color():
    html = ansi_to_html("\x1b[1mhi\x1b[0m \x1b[32mok\x1b[0m")
    assert "\x1b" not in html
    assert "[1m" not in html
    assert "[0m" not in html
    assert "[32m" not in html
    assert "font-weight:bold" in html
    assert "hi" in html
    assert "ok" in html
    # Green colour from theme should appear as the SGR-32 mapping.
    assert theme.GREEN.lower() in html.lower()


def test_ansi_to_html_html_escapes_payload():
    html = ansi_to_html("a < b & c > d")
    assert "&lt;" in html
    assert "&amp;" in html
    assert "&gt;" in html
    assert "<pre" in html
