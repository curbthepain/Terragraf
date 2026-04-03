"""Terragraf dark theme — CI terminal aesthetic."""

# Palette
BG_PRIMARY = "#0e0e10"
BG_SECONDARY = "#161618"
BG_PANEL = "#1c1c20"
BG_INPUT = "#121214"
BORDER = "#2a2a30"
BORDER_FOCUS = "#4a9eff"

TEXT_PRIMARY = "#d4d4d8"
TEXT_SECONDARY = "#71717a"
TEXT_DIM = "#52525b"

ACCENT = "#4a9eff"
GREEN = "#34d399"
YELLOW = "#fbbf24"
RED = "#f87171"
CYAN = "#22d3ee"

STYLESHEET = f"""
QMainWindow {{
    background-color: {BG_PRIMARY};
}}

QWidget {{
    color: {TEXT_PRIMARY};
    font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 13px;
}}

QMenuBar {{
    background-color: {BG_SECONDARY};
    color: {TEXT_SECONDARY};
    border-bottom: 1px solid {BORDER};
    padding: 2px 0;
}}

QMenuBar::item {{
    padding: 4px 10px;
    background: transparent;
}}

QMenuBar::item:selected {{
    color: {TEXT_PRIMARY};
    background-color: {BG_PANEL};
}}

QMenu {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    padding: 4px 0;
}}

QMenu::item {{
    padding: 6px 24px;
}}

QMenu::item:selected {{
    background-color: {ACCENT};
    color: {BG_PRIMARY};
}}

QStatusBar {{
    background-color: {BG_SECONDARY};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 8px;
}}

QLabel#title {{
    color: {TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 600;
}}

QLabel#subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QFrame#separator {{
    background-color: {BORDER};
    max-height: 1px;
}}
"""
