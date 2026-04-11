"""Terragraf Kohala theme — terra-sufimorphic warm-glass red/navy.

The full QSS now lives in :mod:`app.themes` (kohala.qss + a legacy
objectName compat block). This module keeps the palette constants other
modules import (``theme.RED``, ``theme.BG_PRIMARY`` etc.) and exposes
``STYLESHEET`` as the concatenated string for ``MainWindow.setStyleSheet``.

Migration note (Session 26): the palette constants below now hold the
Kohala palette values, not the old cool-blue ones. Every module that
imports ``theme.RED`` etc. picks up the new values automatically — no
call-site changes needed for color references.
"""

from . import themes as _themes


# ── Palette ────────────────────────────────────────────────────────────
# Surface levels (darkest → lightest). Kohala leans dark navy with a
# warm-glass card material on top. Hex constants are kept opaque so
# legacy callers that interpolate them into inline f-strings still work;
# the QSS itself uses semi-transparent rgba() for the warm-glass look.

BG_PRIMARY    = "#060D17"   # main window background (sunset gradient base)
BG_SECONDARY  = "#0E1A2E"   # chrome surfaces (sidebar, top bar, panels)
BG_ELEVATED   = "#1A2A40"   # cards, dialogs, popups
BG_PANEL      = BG_ELEVATED  # legacy alias
BG_INPUT      = "#06121E"   # inset inputs (slightly recessed)
BG_HOVER      = "#172841"   # hover overlay
BG_PRESSED    = "#22344F"   # pressed / selected overlay

# Borders — hairlines, the warm top edge of the glass effect lives in
# the QSS itself.
BORDER        = "#1F2A3C"
BORDER_STRONG = "#2C3A52"
BORDER_FOCUS  = "#E83030"

# Text on dark.
TEXT_PRIMARY    = "#F0EDE6"
TEXT_SECONDARY  = "#B6C3D2"
TEXT_DIM        = "#6B7D90"

# Accent + state — Kohala's signature red.
ACCENT          = "#E83030"
ACCENT_HOVER    = "#FF5040"
ACCENT_PRESSED  = "#C0221F"

# Semantic colours.
GREEN   = "#6EE0B0"
YELLOW  = "#fbbf24"
RED     = "#E83030"
CYAN    = "#22d3ee"
MAGENTA = "#c084fc"

# ── Sidebar / TopBar legacy aliases (preserved for older callers) ─────
SIDEBAR_BG      = BG_SECONDARY
SIDEBAR_HOVER   = BG_HOVER
SIDEBAR_ACTIVE  = BG_PRESSED
TOPBAR_BG       = BG_SECONDARY
SIDEBAR_WIDTH_COLLAPSED = 56
SIDEBAR_WIDTH_EXPANDED  = 240


# ── Typography ─────────────────────────────────────────────────────────
# Same font stacks as before; the actual TTF files are bundled under
# app/fonts/ and registered at startup via fonts.register_fonts().

FONT_UI = (
    '"Barlow", "Inter", "Segoe UI Variable", "Segoe UI", '
    '"Helvetica Neue", system-ui, sans-serif'
)
FONT_DISPLAY = (
    '"Barlow Condensed", "Barlow", "Inter", "Segoe UI Variable", '
    '"Helvetica Neue", sans-serif'
)
FONT_MONO = (
    '"JetBrains Mono", "Cascadia Code", "Fira Code", '
    '"Consolas", monospace'
)


# ── Stylesheet ─────────────────────────────────────────────────────────
# Loaded at import time from app/themes/ (kohala.qss + legacy compat).
# MainWindow does setStyleSheet(theme.STYLESHEET) — single application
# point, the contents just changed from a giant f-string to a file load.

STYLESHEET = _themes.load_stylesheet()
