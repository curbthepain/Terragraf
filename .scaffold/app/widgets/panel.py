"""Panel helpers for the workspace content area.

Small utilities used by ``WelcomeTab`` (and anything else that wants the
preview's warm-glass card look). Factored out so the welcome layout code
reads closer to the structure in ``additions/terragraf_preview.py``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


def _apply_class(widget: QWidget, cls: str) -> None:
    widget.setProperty("class", cls)
    s = widget.style()
    s.unpolish(widget)
    s.polish(widget)


def make_panel(title: str) -> tuple[QFrame, QVBoxLayout]:
    """Return a ``QFrame[class="panel"]`` with a section header + divider.

    The caller gets back the frame (to add to its parent layout) and the
    inner ``QVBoxLayout`` (to populate with content below the divider).

    Matches the preview's section card: margins ``(24,20,24,20)``, spacing
    8, a monospace red ``— TITLE`` header, and a red ``ws-divider`` rule.
    """
    frame = QFrame()
    _apply_class(frame, "panel")

    inner = QVBoxLayout(frame)
    inner.setContentsMargins(24, 20, 24, 20)
    inner.setSpacing(8)

    header = QLabel(f"— {title.upper()}")
    _apply_class(header, "section-sub")
    inner.addWidget(header)

    divider = QFrame()
    _apply_class(divider, "ws-divider")
    divider.setFixedHeight(1)
    inner.addWidget(divider)
    inner.addSpacing(4)

    return frame, inner


def stat_row(key_text: str, value_text: str = "—") -> tuple[QWidget, QLabel]:
    """Return a compact ``— KEY`` / ``value`` row and the value label.

    Caller keeps a reference to the value label so it can be updated
    in place (e.g. by ``WelcomeTab._refresh``).
    """
    row = QWidget()
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 0, 0, 0)
    rl.setSpacing(10)

    k = QLabel(f"— {key_text.upper()}")
    _apply_class(k, "stat-key")
    v = QLabel(value_text)
    _apply_class(v, "stat-compact")

    rl.addWidget(k, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    rl.addStretch(1)
    rl.addWidget(v, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return row, v
