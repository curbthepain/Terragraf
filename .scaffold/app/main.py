#!/usr/bin/env python3
"""Terragraf — Qt container application."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from . import scaling
from . import fonts as app_fonts
from .window import MainWindow


def main():
    # Pass the OS-reported scale factor through unmodified. Qt 6 + PySide6
    # handles fractional scales correctly; every `px` value in code and the
    # stylesheet is treated as a logical pixel and Qt multiplies for device
    # pixels at draw time.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    scaling.init(app)
    app.setApplicationName("Terragraf")
    app.setOrganizationName("Terragraf")

    # Register bundled Barlow + JetBrains Mono fonts so the Kohala theme
    # font stack resolves consistently regardless of system installs.
    app_fonts.register_fonts()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
