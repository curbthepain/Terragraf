"""DPI scaling helper.

Under the PassThrough rounding policy, Qt treats every `px` value as a
logical pixel and multiplies for device pixels at draw time. The few cases
that need explicit clamps (initial window size, screen-relative geometry)
go through this module so they read the OS-reported scale factor in one
consistent place.
"""

from PySide6.QtWidgets import QApplication

_scale: float = 1.0


def init(app: QApplication) -> None:
    """Initialise the scale factor from the primary screen's logical DPI."""
    global _scale
    screen = app.primaryScreen()
    if screen is not None:
        _scale = max(1.0, screen.logicalDotsPerInch() / 96.0)


def s(px: int) -> int:
    """Scale a logical pixel value by the current factor."""
    return int(round(px * _scale))


def factor() -> float:
    """Return the current scale factor (1.0 if uninitialised)."""
    return _scale
