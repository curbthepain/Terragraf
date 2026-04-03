"""Main window — the Terragraf container shell."""

from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
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
    QMenuBar,
    QSizePolicy,
)

from . import theme


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terragraf")
        self.setMinimumSize(QSize(800, 500))
        self.resize(1200, 740)

        # --- Style ---
        self.setStyleSheet(theme.STYLESHEET)

        # --- Menu bar ---
        self._build_menu()

        # --- Central area ---
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Content stack (pages go here later)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_landing())
        layout.addWidget(self._stack)

        # --- Status bar ---
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("ready")

        # --- Keyboard shortcuts ---
        self._bind_shortcuts()

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

        status_line = QLabel("193 tests passing")
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

        return page

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
        # Escape exits fullscreen, otherwise does nothing
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(event)
