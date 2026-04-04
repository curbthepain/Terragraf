"""Main window — the Terragraf container shell with sidebar navigation."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QStackedWidget,
    QStatusBar,
    QPushButton,
    QSizePolicy,
)

from . import theme
from .bridge_client import BridgeClient
from .debug_page import DebugPage
from .tuning_page import TuningPage
from .viewer_page import ViewerPage
from .settings_page import SettingsPage, _load_settings
from .app_host import AppHostManager
from .ide_host_page import IDEHostPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terragraf")
        self.setMinimumSize(QSize(900, 560))
        self.resize(1280, 780)

        # --- Style ---
        self.setStyleSheet(theme.STYLESHEET)

        # --- Bridge client (shared) ---
        self._bridge = BridgeClient()

        # --- Menu bar ---
        self._build_menu()

        # --- Central area: sidebar + stack ---
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self._sidebar = self._build_sidebar()
        root.addWidget(self._sidebar)

        # Page stack
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        # --- Pages ---
        self._pages = {}
        self._nav_btns = {}

        self._add_page("home", "Home", self._build_landing())
        self._add_page("viewer", "Viewer", ViewerPage(self._bridge))
        self._add_page("tuning", "Tuning", TuningPage(self._bridge))
        self._add_page("debug", "Debug", DebugPage(self._bridge))
        self._add_page("settings", "Settings", SettingsPage(self._bridge))

        # --- Status bar (must exist before _select_page) ---
        self._status = QStatusBar()
        self.setStatusBar(self._status)

        # --- Discover and add installed IDEs ---
        self._app_host = AppHostManager()
        self._ide_pages = {}
        for ide_key, manifest in self._app_host.manifests.items():
            page = IDEHostPage(manifest, self._app_host)
            page_key = f"ide_{ide_key}"
            self._add_page(page_key, manifest.label, page)
            self._ide_pages[page_key] = page

        self._select_page("home")

        # Add IDE buttons to landing page
        for page_key, page in self._ide_pages.items():
            btn = QPushButton(page.manifest.label)
            btn.setFixedWidth(100)
            btn.clicked.connect(
                lambda checked, k=page_key: self._select_page(k)
            )
            self._landing_ide_nav.addWidget(btn)

        # Add IDE shortcuts to View menu
        if self._ide_pages:
            self._view_menu.addSeparator()
            for page_key, page in self._ide_pages.items():
                m = page.manifest
                action = QAction(f"&{m.label}", self)
                if m.shortcut:
                    action.setShortcut(QKeySequence(m.shortcut))
                action.triggered.connect(
                    lambda checked, k=page_key: self._select_page(k)
                )
                self._view_menu.addAction(action)

        # --- Status bar ready message ---
        self._status.showMessage("ready")

        # --- Bridge status in statusbar ---
        self._bridge_indicator = QLabel("bridge: offline")
        self._bridge_indicator.setObjectName("dim")
        self._status.addPermanentWidget(self._bridge_indicator)
        self._bridge.connection_changed.connect(self._on_bridge_status)

        # --- Keyboard shortcuts ---
        self._bind_shortcuts()

        # --- Auto-connect if configured ---
        settings = _load_settings()
        if settings.get("auto_connect"):
            self._bridge.host = settings.get("bridge_host", "127.0.0.1")
            self._bridge.port = settings.get("bridge_port", 9876)
            self._bridge.connect_to_bridge()

    # ── Sidebar ─────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(160)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("Terragraf")
        logo.setObjectName("title")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        layout.addSpacing(16)

        # Nav buttons are added by _add_page
        self._nav_layout = layout

        layout.addStretch()

        # Version
        ver = QLabel("v0.1")
        ver.setObjectName("dim")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        return sidebar

    def _add_page(self, key: str, label: str, widget: QWidget):
        idx = self._stack.addWidget(widget)
        self._pages[key] = (idx, widget)

        btn = QPushButton(label)
        btn.setProperty("class", "nav_btn")
        btn.setProperty("active", "false")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked, k=key: self._select_page(k))

        # Insert before the stretch
        count = self._nav_layout.count()
        self._nav_layout.insertWidget(count - 1, btn)
        self._nav_btns[key] = btn

    def _select_page(self, key: str):
        if key not in self._pages:
            return
        idx, widget = self._pages[key]
        self._stack.setCurrentIndex(idx)

        # Update active state
        for k, btn in self._nav_btns.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Notify page
        if hasattr(widget, 'on_page_shown'):
            widget.on_page_shown()

        self._status.showMessage(f"{key}")

    # ── Menu ────────────────────────────────────────────────────────

    def _build_menu(self):
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = bar.addMenu("&View")

        fullscreen_action = QAction("Toggle &Fullscreen", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        maximize_action = QAction("Toggle &Maximize", self)
        maximize_action.setShortcut(QKeySequence("F10"))
        maximize_action.triggered.connect(self._toggle_maximize)
        view_menu.addAction(maximize_action)

        view_menu.addSeparator()

        # Page navigation shortcuts
        for i, (key, label) in enumerate([
            ("home", "&Home"),
            ("viewer", "&Viewer"),
            ("tuning", "&Tuning"),
            ("debug", "&Debug"),
            ("settings", "&Settings"),
        ]):
            action = QAction(label, self)
            action.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            action.triggered.connect(lambda checked, k=key: self._select_page(k))
            view_menu.addAction(action)

        # IDE shortcuts (added after IDEs are discovered)
        self._view_menu = view_menu

    # ── Landing page ────────────────────────────────────────────────

    def _build_landing(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Terragraf")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("scaffolding system")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedWidth(200)

        status_line = QLabel("302 tests passing")
        status_line.setObjectName("subtitle")
        status_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_line.setStyleSheet(f"color: {theme.GREEN};")

        outer.addWidget(title)
        outer.addSpacing(4)
        outer.addWidget(subtitle)
        outer.addSpacing(16)
        outer.addWidget(sep, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addSpacing(16)
        outer.addWidget(status_line)

        # Quick nav
        outer.addSpacing(32)
        nav = QHBoxLayout()
        nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for key, label in [("viewer", "Viewer"), ("tuning", "Tuning"),
                           ("debug", "Debug"), ("settings", "Settings")]:
            btn = QPushButton(label)
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda checked, k=key: self._select_page(k))
            nav.addWidget(btn)
        outer.addLayout(nav)

        # IDE quick nav (populated after discovery)
        self._landing_ide_nav = QHBoxLayout()
        self._landing_ide_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addSpacing(8)
        outer.addLayout(self._landing_ide_nav)

        return page

    # ── Bridge status ───────────────────────────────────────────────

    def _on_bridge_status(self, connected: bool):
        if connected:
            self._bridge_indicator.setText("bridge: online")
            self._bridge_indicator.setStyleSheet(f"color: {theme.GREEN};")
        else:
            self._bridge_indicator.setText("bridge: offline")
            self._bridge_indicator.setStyleSheet(f"color: {theme.RED};")

    # ── Window controls ─────────────────────────────────────────────

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _bind_shortcuts(self):
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        # Cleanup child processes
        viewer_page = self._pages.get("viewer")
        if viewer_page:
            _, widget = viewer_page
            if hasattr(widget, 'cleanup'):
                widget.cleanup()
        # Cleanup IDE host pages
        for page in self._ide_pages.values():
            page.cleanup()
        self._bridge.disconnect_from_bridge()
        super().closeEvent(event)
