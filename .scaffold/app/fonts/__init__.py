"""Bundled application fonts (Barlow + Barlow Condensed + JetBrains Mono).

Walks the package directory at startup and registers every ``.ttf`` it
finds with ``QFontDatabase.addApplicationFont`` so the QSS font stack
("Barlow", "Barlow Condensed", "JetBrains Mono") resolves consistently
on every machine — Windows, Linux (CI xvfb), macOS — without depending
on system installs.

All bundled fonts are SIL Open Font License (OFL):
- Barlow + Barlow Condensed: https://github.com/jpt/barlow
- JetBrains Mono: https://github.com/JetBrains/JetBrainsMono
"""

from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).resolve().parent


def font_files() -> list[Path]:
    """Return every bundled ``.ttf`` file under this package."""
    return sorted(_HERE.glob("*.ttf"))


def register_fonts() -> tuple[int, int]:
    """Register every bundled font with the running QApplication.

    Must be called AFTER ``QApplication`` has been constructed (the font
    database is per-application). Returns ``(loaded, failed)`` counts.
    """
    # Imported lazily so this module is importable without Qt for the
    # file-presence test.
    from PySide6.QtGui import QFontDatabase

    loaded = 0
    failed = 0
    for ttf in font_files():
        font_id = QFontDatabase.addApplicationFont(str(ttf))
        if font_id == -1:
            failed += 1
        else:
            loaded += 1
    return loaded, failed
