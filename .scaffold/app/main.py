#!/usr/bin/env python3
"""Terragraf — Qt container application."""

import sys

from PySide6.QtWidgets import QApplication
from .window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Terragraf")
    app.setOrganizationName("Terragraf")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
