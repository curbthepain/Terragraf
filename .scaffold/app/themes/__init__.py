"""Theme stylesheet loader.

Concatenates the canonical Kohala QSS with a legacy objectName compat
block so widgets that still use ``setObjectName("status_red")`` etc.
keep rendering correctly while the layout migration is in flight.
"""

from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).resolve().parent
_KOHALA = _HERE / "kohala.qss"
_LEGACY = _HERE / "legacy_objectnames.qss"


def load_stylesheet() -> str:
    """Return the full QSS string applied to the QApplication.

    Reads ``kohala.qss`` (the new property-class-based base theme) and
    appends ``legacy_objectnames.qss`` (compat rules for the existing
    ``#objectName`` selectors that 47 tests + many widgets still rely on).
    """
    parts: list[str] = []
    if _KOHALA.exists():
        parts.append(_KOHALA.read_text(encoding="utf-8"))
    if _LEGACY.exists():
        parts.append(_LEGACY.read_text(encoding="utf-8"))
    return "\n\n".join(parts)
