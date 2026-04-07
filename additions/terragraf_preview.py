"""
Terragraf workspace — Kohala theme preview.

Loads `theme/kohala_theme.qss` and renders a window styled after the
Terragraf workspace screenshot, but pushed harder toward the
Project Kohala website's flair: warm-glass cards, mono red eyebrows,
condensed display titles, and a glowing red workspace tab.

Run from anywhere:
    python "D:/QSS THEME/preview/terragraf_preview.py"
Output:
    D:/QSS THEME/preview/terragraf_preview.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QStatusBar, QToolButton, QSizePolicy,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
QSS_PATH = ROOT / "theme" / "kohala_theme.qss"
PNG_PATH = HERE / "terragraf_preview.png"


def tag(widget: QWidget, cls: str) -> QWidget:
    """Set a `class` property and re-polish so the QSS rule applies."""
    widget.setProperty("class", cls)
    s = widget.style()
    s.unpolish(widget)
    s.polish(widget)
    return widget


def label(text: str, cls: str | None = None,
          align: Qt.AlignmentFlag | None = None) -> QLabel:
    lbl = QLabel(text)
    lbl.setTextFormat(Qt.PlainText)
    if cls:
        tag(lbl, cls)
    if align is not None:
        lbl.setAlignment(align)
    return lbl


def nav_button(icon: str, text: str, checked: bool = False) -> QPushButton:
    # Use an inner layout so the icon lives in a fixed-width column at a
    # uniform font size. Different unicode glyphs (♥, ◉, ▢, ✓, ⚙) have
    # very different natural widths/weights when embedded in button text;
    # rendering them in their own QLabel column normalizes that.
    btn = QPushButton("")
    tag(btn, "nav-item")
    btn.setCheckable(True)
    btn.setChecked(checked)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(36)

    inner = QHBoxLayout(btn)
    inner.setContentsMargins(14, 0, 14, 0)
    inner.setSpacing(12)

    icon_lbl = QLabel(icon)
    icon_lbl.setFixedWidth(18)
    icon_lbl.setAlignment(Qt.AlignCenter)
    # Explicit color — Qt QSS doesn't support `color: inherit`, so the
    # inner labels can't follow the parent button's :hover/:checked state.
    # Static slate reads fine on both hover (navy) and checked (red) bg.
    icon_lbl.setStyleSheet(
        "color: #C6D2E0; background: transparent; border: none;"
        " font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;"
        " font-size: 15px;"
    )
    text_lbl = QLabel(text.upper())
    text_lbl.setStyleSheet(
        "color: #C6D2E0; background: transparent; border: none;"
        " font-family: 'Barlow', 'Segoe UI', sans-serif;"
        " font-size: 12px; font-weight: 600; letter-spacing: 0.4px;"
    )
    inner.addWidget(icon_lbl, 0, Qt.AlignVCenter)
    inner.addWidget(text_lbl, 1, Qt.AlignVCenter)

    return btn


def stat_tile(key: str, val: str) -> QFrame:
    f = QFrame()
    tag(f, "stat-tile")
    v = QVBoxLayout(f)
    v.setContentsMargins(14, 12, 14, 12)
    v.setSpacing(4)
    v.addWidget(label(f"— {key.upper()}", "stat-key"))
    v.addWidget(label(val, "stat-val"))
    return f


def icon_button(text: str) -> QToolButton:
    b = QToolButton()
    b.setText(text)
    tag(b, "iconbtn")
    b.setFixedSize(38, 32)
    return b


def divider() -> QFrame:
    f = QFrame()
    tag(f, "ws-divider")
    f.setFixedHeight(1)
    return f


class TerragrafWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Terragraf")
        self.resize(1200, 640)

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        # Outer margins so the sidebar/content read as floating cards
        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 14, 16, 6)
        outer.setSpacing(10)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(14)

        # ── LEFT SIDEBAR (floating card) ────────────────────
        sidebar = QFrame()
        tag(sidebar, "sidebar")
        sidebar.setFixedWidth(258)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(18, 22, 18, 18)
        sb.setSpacing(2)

        sb.addWidget(label("— WELCOME —", "sidebar-header"))
        sb.addSpacing(10)

        sb.addWidget(nav_button("+", "New Native"))
        sb.addWidget(nav_button("▢", "New External"))
        sb.addWidget(nav_button("▢", "New Project…"))
        sb.addSpacing(8)
        sb.addWidget(nav_button("♥", "Health Check"))
        sb.addWidget(nav_button("◉", "Status"))
        sb.addWidget(nav_button("◉", "Mode"))
        sb.addWidget(nav_button("✓", "Scan"))
        sb.addWidget(nav_button("≡", "Knowledge"))
        sb.addSpacing(8)
        sb.addWidget(nav_button("⚙", "Settings"))

        sb.addStretch(1)
        sb.addWidget(divider())
        sb.addSpacing(10)

        # Workspace minor details — moved here from the top, replacing
        # the duplicate BRIDGE OFFLINE indicator (already in the footer).
        ws_row = QHBoxLayout()
        ws_row.setContentsMargins(2, 0, 2, 0)
        ws_row.setSpacing(8)
        ws_row.addWidget(label("— WORKSPACE //", "sidebar-header"))
        ws_row.addStretch(1)
        ws_row.addWidget(label("v0.4.2", "hint"))
        ws_wrap = QWidget()
        ws_wrap.setLayout(ws_row)
        sb.addWidget(ws_wrap)

        body.addWidget(sidebar)

        # ── RIGHT SIDE (top bar + content) ──────────────────
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(12)

        # Top bar — floating card
        topbar = QFrame()
        tag(topbar, "topbar")
        topbar.setFixedHeight(58)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(14, 10, 24, 10)
        tb.setSpacing(10)

        tb.addWidget(icon_button("≡"))
        tb.addWidget(icon_button("▣"))

        # Welcome workspace tab — glowing red pill
        ws_tab = QPushButton("WELCOME")
        tag(ws_tab, "ws-tab")
        ws_tab.setMinimumHeight(34)
        tb.addWidget(ws_tab)

        tb.addStretch(1)

        # TERRAGRAF wordmark on the upper-right half (mirrors the sidebar mark)
        tb.addWidget(label("TERRA", "brand-mark"))
        tb.addWidget(label("GRAF", "brand-mark-red"))

        right.addWidget(topbar)

        # ── Health + Sessions side-by-side ──────────────────
        hs_row = QHBoxLayout()
        hs_row.setContentsMargins(0, 0, 0, 0)
        hs_row.setSpacing(14)

        # Scaffold Health — single unified panel, compact key:value rows
        health = QFrame()
        tag(health, "panel")
        hv = QVBoxLayout(health)
        hv.setContentsMargins(24, 20, 24, 20)
        hv.setSpacing(8)

        hv.addWidget(label("— SCAFFOLD HEALTH", "section-sub"))
        hv.addWidget(divider())
        hv.addSpacing(4)

        stats_grid = QGridLayout()
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setHorizontalSpacing(28)
        stats_grid.setVerticalSpacing(8)
        stats = [
            ("Header files",      "12"),
            ("Modules",           "23"),
            ("Route files",       "3"),
            ("Routes",            "204"),
            ("Table files",       "3"),
            ("Queue pending",     "0"),
            ("Queue running",     "1"),
            ("HOT_CONTEXT lines", "457"),
            ("Recent events",     "0"),
        ]
        for i, (k, v) in enumerate(stats):
            r, c = divmod(i, 3)
            cell = QHBoxLayout()
            cell.setContentsMargins(0, 0, 0, 0)
            cell.setSpacing(10)
            k_lbl = label(f"— {k.upper()}", "stat-key")
            v_lbl = label(v, "stat-compact")
            cell.addWidget(k_lbl, 0, Qt.AlignLeft | Qt.AlignVCenter)
            cell.addStretch(1)
            cell.addWidget(v_lbl, 0, Qt.AlignRight | Qt.AlignVCenter)
            wrap = QWidget()
            wrap.setLayout(cell)
            stats_grid.addWidget(wrap, r, c)
        for c in range(3):
            stats_grid.setColumnStretch(c, 1)
        grid_wrap = QWidget()
        grid_wrap.setLayout(stats_grid)
        hv.addWidget(grid_wrap)
        hv.addStretch(1)

        hs_row.addWidget(health, 3)

        # Recent Sessions — a panel of session rows
        sessions = QFrame()
        tag(sessions, "panel")
        sv = QVBoxLayout(sessions)
        sv.setContentsMargins(24, 20, 24, 20)
        sv.setSpacing(8)

        sv.addWidget(label("— RECENT TABS", "section-sub"))
        sv.addWidget(divider())
        sv.addSpacing(4)

        def tab_row(name: str, slug: str, state: str,
                    dot_color: str = "#8FA0B6") -> QWidget:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 4, 0, 4)
            rl.setSpacing(12)
            d = QLabel("●")
            d.setStyleSheet(
                f"color: {dot_color}; font-size: 11px;"
                " background: transparent; border: none;"
            )
            rl.addWidget(d)
            rl.addWidget(label(name.upper(), "stat-compact"))
            rl.addWidget(label(slug, "hint"))
            rl.addStretch(1)
            rl.addWidget(label(state, "stat-key"))
            return row

        # Mirrors the open + recently-closed tabs in the topbar.
        sv.addWidget(tab_row("Welcome", "welcome · 523434", "ACTIVE", "#6EE0B0"))
        sv.addWidget(tab_row("Modules", "modules · 511298", "RECENT"))
        sv.addWidget(tab_row("Routes",  "routes · 488221",  "RECENT"))
        sv.addStretch(1)

        hs_row.addWidget(sessions, 2)

        hs_wrap = QWidget()
        hs_wrap.setLayout(hs_row)
        right.addWidget(hs_wrap, 1)

        right_wrap = QWidget()
        right_wrap.setLayout(right)
        body.addWidget(right_wrap, 1)

        body_wrap = QWidget()
        body_wrap.setLayout(body)
        outer.addWidget(body_wrap, 1)

        # ── FOOTER ──────────────────────────────────────────
        # Custom footer instead of QStatusBar so we get true centering
        # without fighting QStatusBar's left/permanent split.
        footer = QFrame()
        tag(footer, "topbar")  # reuse the warm-glass topbar look
        footer.setFixedHeight(44)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 8, 24, 8)
        fl.setSpacing(0)
        fl.addStretch(1)
        center_lbl = QLabel("BRIDGE: OFFLINE   ·   1 SESSION   ·   PATENT PENDING")
        center_lbl.setStyleSheet(
            "color: #E83030; font-family: 'JetBrains Mono', 'Consolas', monospace;"
            " font-size: 10px; font-weight: 700; letter-spacing: 1.5px;"
            " background: transparent; border: none;"
        )
        center_lbl.setAlignment(Qt.AlignCenter)
        fl.addWidget(center_lbl, 0, Qt.AlignCenter)
        fl.addStretch(1)
        outer.addWidget(footer)

    def save_screenshot(self) -> None:
        pix = self.grab()
        ok = pix.save(str(PNG_PATH), "PNG")
        print(f"saved={ok} -> {PNG_PATH}")


def main() -> int:
    if not QSS_PATH.exists():
        print(f"ERROR: QSS not found at {QSS_PATH}", file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    win = TerragrafWindow()
    win.show()
    QTimer.singleShot(450, lambda: (win.save_screenshot(), app.quit()))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
