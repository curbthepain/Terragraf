"""Terragraf dark theme — kohala technical identity meets Apple-style surface polish.

Palette is layered (primary → secondary → elevated → input) so the UI gets
real depth instead of two near-identical greys. UI chrome runs on Barlow with
JetBrains Mono reserved for code/log/output panels. Every legacy constant is
preserved as an importable name so callers don't break.
"""

# ── Palette ────────────────────────────────────────────────────────────

# Surface levels (darkest to lightest).
BG_PRIMARY    = "#0a0a0c"   # window background
BG_SECONDARY  = "#141418"   # chrome surfaces (sidebar, top bar, status bar, menu bar)
BG_ELEVATED   = "#1d1d22"   # cards, panels, dialogs, popups
BG_PANEL      = BG_ELEVATED  # legacy alias — old callers continue to work
BG_INPUT      = "#101014"   # inset inputs (slightly recessed)
BG_HOVER      = "#22222a"   # hover overlay tint
BG_PRESSED    = "#2c2c36"   # pressed / selected overlay

# Borders — hairlines for the most part, strong only where emphasis is needed.
BORDER        = "#26262c"
BORDER_STRONG = "#33333a"
BORDER_FOCUS  = "#5b9fff"

# Text on dark.
TEXT_PRIMARY    = "#e4e4e8"
TEXT_SECONDARY  = "#9b9ba3"
TEXT_DIM        = "#5e5e66"

# Accent + state.
ACCENT          = "#5b9fff"
ACCENT_HOVER    = "#76b1ff"
ACCENT_PRESSED  = "#3d8ce8"

# Semantic colours — kept aligned with the rest of the app.
GREEN   = "#34d399"
YELLOW  = "#fbbf24"
RED     = "#f87171"
CYAN    = "#22d3ee"
MAGENTA = "#c084fc"

# ── Sidebar / TopBar legacy aliases (do not remove — imported elsewhere) ─
SIDEBAR_BG      = BG_SECONDARY
SIDEBAR_HOVER   = BG_HOVER
SIDEBAR_ACTIVE  = BG_PRESSED
TOPBAR_BG       = BG_SECONDARY
SIDEBAR_WIDTH_COLLAPSED = 56
SIDEBAR_WIDTH_EXPANDED  = 240

# ── Typography ─────────────────────────────────────────────────────────

# UI chrome — Barlow with system fallbacks. Inherited by every QWidget that
# doesn't explicitly override its font.
FONT_UI = (
    '"Barlow", "Inter", "Segoe UI Variable", "Segoe UI", '
    '"Helvetica Neue", system-ui, sans-serif'
)
# Headers / display labels — Barlow Condensed for that distinctive squared look.
FONT_DISPLAY = (
    '"Barlow Condensed", "Barlow", "Inter", "Segoe UI Variable", '
    '"Helvetica Neue", sans-serif'
)
# Code / log / terminal output — JetBrains Mono retained.
FONT_MONO = (
    '"JetBrains Mono", "Cascadia Code", "Fira Code", '
    '"Consolas", monospace'
)


# ── Stylesheet ─────────────────────────────────────────────────────────

STYLESHEET = f"""
/* ── Base ─────────────────────────────────────────────────────── */

QMainWindow {{
    background-color: {BG_PRIMARY};
}}

QWidget {{
    color: {TEXT_PRIMARY};
    font-family: {FONT_UI};
    font-size: 14px;
}}

QDialog {{
    background-color: {BG_PRIMARY};
}}

/* Code/log surfaces always render in the mono stack — explicitly opt in
   so the Barlow inheritance from QWidget doesn't bleed in. */
QPlainTextEdit, QTextEdit,
QLabel#mono, QLabel#code, QListWidget#code {{
    font-family: {FONT_MONO};
}}

/* ── Menu bar / menus ─────────────────────────────────────────── */

QMenuBar {{
    background-color: {BG_SECONDARY};
    color: {TEXT_SECONDARY};
    border-bottom: 1px solid {BORDER};
    padding: 2px 4px;
}}

QMenuBar::item {{
    padding: 5px 12px;
    background: transparent;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    color: {TEXT_PRIMARY};
    background-color: {BG_HOVER};
}}

QMenu {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px;
    color: {TEXT_PRIMARY};
}}

QMenu::item {{
    padding: 7px 22px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {ACCENT};
    color: #ffffff;
}}

QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

/* ── Status bar ───────────────────────────────────────────────── */

QStatusBar {{
    background-color: {BG_SECONDARY};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
    font-size: 11px;
    padding: 2px 10px;
}}

QStatusBar::item {{
    border: none;
}}

/* ── Labels ───────────────────────────────────────────────────── */

QLabel#title {{
    color: {TEXT_PRIMARY};
    font-family: {FONT_DISPLAY};
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

QLabel#subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel#section_header {{
    color: {TEXT_PRIMARY};
    font-family: {FONT_DISPLAY};
    font-size: 15px;
    font-weight: 600;
    padding: 8px 0 4px 0;
    letter-spacing: 0.3px;
}}

QLabel#dim {{
    color: {TEXT_DIM};
    font-size: 12px;
}}

QLabel#mono {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

/* Semantic colour labels — used by widgets that previously inlined colour. */
QLabel#status_green   {{ color: {GREEN};   font-size: 13px; }}
QLabel#status_red     {{ color: {RED};     font-size: 13px; }}
QLabel#status_yellow  {{ color: {YELLOW};  font-size: 13px; }}
QLabel#status_cyan    {{ color: {CYAN};    font-size: 13px; }}
QLabel#status_accent  {{ color: {ACCENT};  font-size: 13px; }}
QLabel#status_magenta {{ color: {MAGENTA}; font-size: 13px; }}

QLabel#status_green_bold   {{ color: {GREEN};   font-weight: 600; }}
QLabel#status_red_bold     {{ color: {RED};     font-weight: 600; }}
QLabel#status_yellow_bold  {{ color: {YELLOW};  font-weight: 600; }}
QLabel#status_cyan_bold    {{ color: {CYAN};    font-weight: 600; }}
QLabel#status_accent_bold  {{ color: {ACCENT};  font-weight: 600; }}
QLabel#status_magenta_bold {{ color: {MAGENTA}; font-weight: 600; }}

/* Tiny detail rows used inside ContextPanel. */
QLabel#detail_yellow {{ color: {YELLOW}; font-size: 10px; }}
QLabel#detail_cyan   {{ color: {CYAN};   font-size: 10px; }}
QLabel#detail_green  {{ color: {GREEN};  font-size: 10px; }}

/* ── Legacy sidebar (#sidebar) — kept for any old callers ─────── */

QWidget#sidebar {{
    background-color: {BG_SECONDARY};
    border-right: 1px solid {BORDER};
}}

QPushButton.nav_btn {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    text-align: left;
    font-size: 13px;
}}

QPushButton.nav_btn:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

QPushButton.nav_btn[active="true"] {{
    background-color: {BG_PRESSED};
    color: {ACCENT};
    border-left: 2px solid {ACCENT};
}}

/* ── Buttons ──────────────────────────────────────────────────── */

QPushButton {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER_STRONG};
}}

QPushButton:pressed {{
    background-color: {BG_PRESSED};
}}

QPushButton:focus {{
    border: 1px solid {BORDER_FOCUS};
    outline: none;
}}

QPushButton:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_SECONDARY};
    border-color: {BORDER};
}}

QPushButton#primary {{
    background-color: {ACCENT};
    color: #ffffff;
    border: 1px solid {ACCENT};
    font-weight: 600;
}}

QPushButton#primary:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QPushButton#primary:pressed {{
    background-color: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}

QPushButton#secondary {{
    background-color: transparent;
    color: {ACCENT};
    border: 1px solid transparent;
}}

QPushButton#secondary:hover {{
    background-color: {BG_HOVER};
}}

QPushButton#danger {{
    background-color: transparent;
    color: {RED};
    border: 1px solid {RED};
}}

QPushButton#danger:hover {{
    background-color: {RED};
    color: #ffffff;
}}

/* ── Inputs ───────────────────────────────────────────────────── */

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {BORDER_FOCUS};
}}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_SECONDARY};
}}

QComboBox::drop-down {{
    border: none;
    width: 26px;
    subcontrol-position: right center;
}}

QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
    outline: none;
}}

/* ── Checkbox / radio ─────────────────────────────────────────── */

QCheckBox, QRadioButton {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_STRONG};
    background-color: {BG_INPUT};
}}

QCheckBox::indicator {{
    border-radius: 4px;
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {ACCENT};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Sliders ──────────────────────────────────────────────────── */

QSlider::groove:horizontal {{
    border: none;
    height: 6px;
    background: {BG_PRESSED};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 3px;
    height: 6px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 1px solid {BORDER_STRONG};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    border-color: {ACCENT};
}}

/* ── Scroll area / scrollbars ─────────────────────────────────── */

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {BG_HOVER};
    min-height: 32px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {BORDER_STRONG};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {BG_HOVER};
    min-width: 32px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {BORDER_STRONG};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ── Text areas / log ─────────────────────────────────────────── */

QPlainTextEdit, QTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
}}

QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

/* ── Group box ────────────────────────────────────────────────── */

QGroupBox {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 18px;
    padding: 18px 14px 14px 14px;
    font-family: {FONT_DISPLAY};
    font-size: 13px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {TEXT_SECONDARY};
    font-family: {FONT_DISPLAY};
    letter-spacing: 0.5px;
}}

/* ── Tab widget ───────────────────────────────────────────────── */

QTabWidget::pane {{
    background-color: {BG_PRIMARY};
    border: none;
    border-top: 1px solid {BORDER};
}}

QTabWidget::tab-bar {{
    alignment: left;
}}

QTabBar {{
    background: {BG_SECONDARY};
    border: none;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 18px;
    margin: 0;
    font-size: 13px;
}}

QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
    background-color: {BG_HOVER};
}}

QTabBar::tab:selected {{
    color: {TEXT_PRIMARY};
    background-color: {BG_PRIMARY};
    border-bottom: 2px solid {ACCENT};
}}

QTabBar::close-button {{
    image: none;
    subcontrol-position: right;
}}

/* ── Separators ───────────────────────────────────────────────── */

QFrame#separator {{
    background-color: {BORDER};
    max-height: 1px;
    border: none;
}}

QFrame#v_separator {{
    background-color: {BORDER};
    max-width: 1px;
    border: none;
}}

/* ── Tree / Table ─────────────────────────────────────────────── */

QTreeWidget, QTableWidget, QListWidget {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    alternate-background-color: {BG_SECONDARY};
    outline: none;
    show-decoration-selected: 1;
}}

QTreeWidget::item, QTableWidget::item, QListWidget::item {{
    padding: 6px 10px;
    border: none;
}}

QTreeWidget::item:hover, QTableWidget::item:hover, QListWidget::item:hover {{
    background-color: {BG_HOVER};
}}

QTreeWidget::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: {BG_PRESSED};
    color: {TEXT_PRIMARY};
    border-left: 2px solid {ACCENT};
}}

QHeaderView::section {{
    background-color: {BG_SECONDARY};
    color: {TEXT_DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    font-family: {FONT_DISPLAY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

/* ── Tool tip ─────────────────────────────────────────────────── */

QToolTip {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Splitter ─────────────────────────────────────────────────── */

QSplitter::handle {{
    background-color: {BG_PRIMARY};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── TopBar / chrome buttons (corner widget on the tab bar) ──── */

QWidget#top_bar {{
    background-color: {BG_SECONDARY};
}}

QToolButton#chrome_button {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 16px;
}}

QToolButton#chrome_button:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

QToolButton#chrome_button::menu-indicator {{
    image: none;
}}

/* ── Sidebar v2 (collapsible contextual rail) ─────────────────── */

QWidget#sidebar_v2 {{
    background-color: {BG_SECONDARY};
    border-right: 1px solid {BORDER};
}}

QLabel#sidebar_section {{
    color: {TEXT_DIM};
    font-family: {FONT_DISPLAY};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 14px 14px 4px 14px;
}}

QPushButton#icon_btn {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 6px;
    padding: 0 12px;
    margin: 1px 6px;
    text-align: left;
    font-size: 13px;
    qproperty-iconSize: 16px;
}}

QPushButton#icon_btn:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

QPushButton#icon_btn:pressed {{
    background-color: {BG_PRESSED};
    color: {ACCENT};
}}

QPushButton#icon_btn:focus {{
    background-color: {BG_HOVER};
    outline: none;
}}

/* ── Cards (chat / response / LLM) ────────────────────────────── */

QFrame#queryCard {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    margin: 2px 0;
}}

QFrame#responseCard, QFrame#llmCard, QFrame#noProviderCard {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px 14px;
    margin: 2px 0;
}}

QTextEdit#llmText {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 8px;
    font-family: {FONT_MONO};
    font-size: 12px;
}}

QTextEdit#llmTextError {{
    background-color: {BG_INPUT};
    color: {RED};
    border: none;
    border-radius: 6px;
    padding: 8px;
    font-family: {FONT_MONO};
    font-size: 12px;
}}

/* ── Context panel (session state rail) ───────────────────────── */

QWidget#contextPanel {{
    background-color: {BG_SECONDARY};
    border-left: 1px solid {BORDER};
}}

QLabel#contextTitle {{
    color: {ACCENT};
    font-family: {FONT_DISPLAY};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel#contextStat {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

/* ── Activity feed ────────────────────────────────────────────── */

QWidget#activityHeader {{
    background-color: {BG_SECONDARY};
    border-bottom: 1px solid {BORDER};
}}

QLabel#activityTitle {{
    color: {ACCENT};
    font-family: {FONT_DISPLAY};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QListWidget#activityList {{
    background-color: {BG_PRIMARY};
    border: none;
    border-radius: 0;
    font-family: {FONT_MONO};
    font-size: 12px;
}}

QListWidget#activityList::item {{
    padding: 4px 10px;
    border-bottom: 1px solid {BORDER};
    border-left: none;
}}

QListWidget#activityList::item:hover {{
    background-color: {BG_HOVER};
}}

QListWidget#activityList::item:selected {{
    background-color: {BG_PRESSED};
    border-left: 2px solid {ACCENT};
}}

/* ── Diff viewer ──────────────────────────────────────────────── */

QLabel#diffTitle {{
    color: {ACCENT};
    background-color: {BG_SECONDARY};
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    font-family: {FONT_DISPLAY};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QTextEdit#diffBody {{
    background-color: {BG_INPUT};
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 0;
    padding: 10px;
    font-family: {FONT_MONO};
    font-size: 11px;
}}
"""
