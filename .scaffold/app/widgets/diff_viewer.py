"""
Diff viewer — read-only unified diff display with color-coded additions/removals.

Used by ExternalTab to show before/after changes when scaffold files are modified.
"""

import difflib

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from .. import theme


class DiffViewer(QWidget):
    """Read-only unified diff viewer with syntax coloring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._title = QLabel("")
        self._title.setObjectName("diffTitle")
        self._title.hide()
        layout.addWidget(self._title)

        self._text = QTextEdit()
        self._text.setObjectName("diffBody")
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("No changes to display")
        layout.addWidget(self._text, 1)

    def show_diff(self, old_text: str, new_text: str, title: str = ""):
        """Generate and display a unified diff between two texts."""
        if title:
            self._title.setText(title)
            self._title.show()
        else:
            self._title.hide()

        if old_text == new_text:
            self._text.setHtml(
                f'<span style="color: {theme.TEXT_DIM};">No changes</span>'
            )
            return

        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, lineterm="")

        html_parts = []
        for line in diff:
            escaped = (
                line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .rstrip("\n")
            )
            if line.startswith("+++") or line.startswith("---"):
                html_parts.append(
                    f'<span style="color: {theme.CYAN};">{escaped}</span>'
                )
            elif line.startswith("@@"):
                html_parts.append(
                    f'<span style="color: {theme.CYAN};">{escaped}</span>'
                )
            elif line.startswith("+"):
                html_parts.append(
                    f'<span style="color: {theme.GREEN};">{escaped}</span>'
                )
            elif line.startswith("-"):
                html_parts.append(
                    f'<span style="color: {theme.RED};">{escaped}</span>'
                )
            else:
                html_parts.append(
                    f'<span style="color: {theme.TEXT_SECONDARY};">{escaped}</span>'
                )

        self._text.setHtml("<pre>" + "<br>".join(html_parts) + "</pre>")

    def show_snapshot_diff(self, before: dict, after: dict, path: str):
        """Compare a specific path between two take_snapshot() results."""
        old = before.get(path, "")
        new = after.get(path, "")
        self.show_diff(old, new, title=path)

    def clear(self):
        """Reset to empty state."""
        self._title.hide()
        self._text.clear()
