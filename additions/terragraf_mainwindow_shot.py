"""
Render the real Terragraf MainWindow to a PNG for visual verification.

This is the S27 counterpart to ``additions/terragraf_preview.py`` — that
file renders a standalone mock of the Kohala layout; this file spins up
the actual ``app.window.MainWindow`` (with a fresh welcome tab) so we
can confirm the shipped chrome matches the preview.

Run from the repo root:
    QT_QPA_PLATFORM=offscreen python additions/terragraf_mainwindow_shot.py

Output:
    additions/terragraf_mainwindow.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCAFFOLD = ROOT / ".scaffold"
PNG_PATH = HERE / "terragraf_mainwindow.png"

# Make `import app....` resolve against .scaffold/ the same way the CI
# suite does (working-directory: .scaffold).
sys.path.insert(0, str(SCAFFOLD))

# Use offscreen by default so this works on any headless machine. The
# caller can override with QT_QPA_PLATFORM= if they want a real display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("TERRAGRAF_MODE", "ci")


def main() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    # Load bundled fonts before any widget is constructed — same thing
    # `app/main.py` does at startup.
    try:
        from app.fonts import load_bundled_fonts
    except Exception:
        load_bundled_fonts = None  # type: ignore

    app = QApplication.instance() or QApplication(sys.argv)
    if load_bundled_fonts is not None:
        try:
            load_bundled_fonts()
        except Exception as exc:
            print(f"font load warning: {exc}", file=sys.stderr)

    from app.window import MainWindow

    win = MainWindow()
    win.resize(1200, 640)  # match the preview's reference size
    win.show()

    exit_code = {"rc": 0}

    def _grab_and_quit() -> None:
        try:
            pix = win.grab()
            ok = pix.save(str(PNG_PATH), "PNG")
            print(f"saved={ok} size={pix.width()}x{pix.height()} -> {PNG_PATH}")
            if not ok:
                exit_code["rc"] = 2
        except Exception as exc:
            print(f"grab failed: {exc}", file=sys.stderr)
            exit_code["rc"] = 3
        finally:
            app.quit()

    # Give Qt a couple of event-loop turns so the stylesheet polishes,
    # fonts resolve, and the initial welcome tab finishes laying out
    # before we snapshot.
    QTimer.singleShot(500, _grab_and_quit)
    app.exec()
    return exit_code["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
