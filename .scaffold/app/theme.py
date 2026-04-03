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

/* ── Menu bar ─────────────────────────────────────────────────── */

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

/* ── Status bar ───────────────────────────────────────────────── */

QStatusBar {{
    background-color: {BG_SECONDARY};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 8px;
}}

/* ── Labels ───────────────────────────────────────────────────── */

QLabel#title {{
    color: {TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 600;
}}

QLabel#subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel#section_header {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 600;
    padding: 8px 0 4px 0;
}}

QLabel#status_green {{
    color: {GREEN};
    font-size: 13px;
}}

QLabel#status_red {{
    color: {RED};
    font-size: 13px;
}}

QLabel#status_yellow {{
    color: {YELLOW};
    font-size: 13px;
}}

QLabel#dim {{
    color: {TEXT_DIM};
    font-size: 12px;
}}

QLabel#mono {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

/* ── Sidebar ──────────────────────────────────────────────────── */

QWidget#sidebar {{
    background-color: {BG_SECONDARY};
    border-right: 1px solid {BORDER};
}}

QPushButton.nav_btn {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 4px;
    padding: 8px 14px;
    text-align: left;
    font-size: 13px;
}}

QPushButton.nav_btn:hover {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
}}

QPushButton.nav_btn[active="true"] {{
    background-color: {BG_PANEL};
    color: {ACCENT};
    border-left: 2px solid {ACCENT};
}}

/* ── Buttons ──────────────────────────────────────────────────── */

QPushButton {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {BORDER};
}}

QPushButton:pressed {{
    background-color: {ACCENT};
    color: {BG_PRIMARY};
}}

QPushButton#primary {{
    background-color: {ACCENT};
    color: {BG_PRIMARY};
    border: none;
}}

QPushButton#primary:hover {{
    background-color: #5aafff;
}}

QPushButton#danger {{
    background-color: transparent;
    color: {RED};
    border: 1px solid {RED};
}}

QPushButton#danger:hover {{
    background-color: {RED};
    color: {BG_PRIMARY};
}}

/* ── Inputs ───────────────────────────────────────────────────── */

QLineEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {ACCENT};
}}

QLineEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {BORDER_FOCUS};
}}

QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 10px;
}}

QComboBox:hover {{
    border-color: {BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: {BG_PRIMARY};
}}

QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {BG_INPUT};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Sliders ──────────────────────────────────────────────────── */

QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: #5aafff;
}}

/* ── Scroll area ──────────────────────────────────────────────── */

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background-color: {BG_PRIMARY};
    width: 8px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER};
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_DIM};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {BG_PRIMARY};
    height: 8px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    min-width: 24px;
    border-radius: 4px;
}}

/* ── Text areas / log ─────────────────────────────────────────── */

QPlainTextEdit, QTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px;
    font-size: 12px;
}}

QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

/* ── Group box ────────────────────────────────────────────────── */

QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-size: 13px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {TEXT_SECONDARY};
}}

/* ── Tab widget ───────────────────────────────────────────────── */

QTabWidget::pane {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER};
    border-top: none;
}}

QTabBar::tab {{
    background-color: {BG_SECONDARY};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-bottom: none;
    padding: 6px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {BG_PRIMARY};
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}

QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}

/* ── Separators ───────────────────────────────────────────────── */

QFrame#separator {{
    background-color: {BORDER};
    max-height: 1px;
}}

QFrame#v_separator {{
    background-color: {BORDER};
    max-width: 1px;
}}

/* ── Table / Tree ─────────────────────────────────────────────── */

QTreeWidget, QTableWidget {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    alternate-background-color: {BG_PANEL};
}}

QTreeWidget::item, QTableWidget::item {{
    padding: 4px 8px;
}}

QTreeWidget::item:selected, QTableWidget::item:selected {{
    background-color: {ACCENT};
    color: {BG_PRIMARY};
}}

QHeaderView::section {{
    background-color: {BG_SECONDARY};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    padding: 4px 8px;
    font-size: 12px;
}}
"""
