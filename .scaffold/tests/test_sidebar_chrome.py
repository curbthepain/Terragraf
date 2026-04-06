"""Tests for Session 18 chrome — IconButton, Sidebar, TopBar, CommandDialog."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import PySide6  # noqa: F401
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

needs_qt = pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not installed")


@pytest.fixture(scope="session", autouse=True)
def _ensure_qapp():
    if not HAS_PYSIDE6:
        yield
        return
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


# ── IconButton ─────────────────────────────────────────────────────────

@needs_qt
class TestIconButton:
    def test_construct(self):
        from app.widgets.icon_button import IconButton
        btn = IconButton("⚡", "Run Skill")
        assert btn.icon_text == "⚡"
        assert btn.label == "Run Skill"
        assert btn.toolTip() == "Run Skill"

    def test_set_expanded_changes_text(self):
        from app.widgets.icon_button import IconButton
        btn = IconButton("⚡", "Run Skill")
        # Collapsed: text contains the icon but not the label
        assert "Run Skill" not in btn.text()
        assert "⚡" in btn.text()
        btn.set_expanded(True)
        assert "Run Skill" in btn.text()
        btn.set_expanded(False)
        assert "Run Skill" not in btn.text()


# ── Sidebar ────────────────────────────────────────────────────────────

@needs_qt
class TestSidebar:
    def test_default_collapsed(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        assert sb.is_expanded() is False
        assert sb.width() == Sidebar.WIDTH_COLLAPSED

    def test_set_expanded_changes_width(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_expanded(True)
        assert sb.width() == Sidebar.WIDTH_EXPANDED
        sb.set_expanded(False)
        assert sb.width() == Sidebar.WIDTH_COLLAPSED

    def test_set_active_tab_welcome(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_active_tab("welcome")
        labels = [b.label for b in sb.buttons()]
        assert "New Native" in labels
        assert "New External" in labels
        assert "Settings" in labels

    def test_set_active_tab_native(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_active_tab("native")
        labels = [b.label for b in sb.buttons()]
        assert "Train Model..." in labels
        assert "Solve Math..." in labels
        assert "Generate..." in labels

    def test_set_active_tab_external(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_active_tab("external")
        labels = [b.label for b in sb.buttons()]
        assert "Worktrees" in labels
        assert "Queue" in labels
        assert "Deps" in labels
        assert "MCP Server" in labels

    def test_action_triggered_signal(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_active_tab("welcome")
        captured = []
        sb.action_triggered.connect(lambda aid: captured.append(aid))
        first = sb.buttons()[0]
        first.click()
        assert len(captured) == 1
        # First welcome action_id is "new_native"
        assert captured[0] == "new_native"

    def test_bridge_status_updates(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_bridge_status(True)
        assert "online" in sb._bridge_label.toolTip()
        sb.set_bridge_status(False)
        assert "offline" in sb._bridge_label.toolTip()


# ── TopBar ─────────────────────────────────────────────────────────────

@needs_qt
class TestTopBar:
    def test_construct_with_menu(self):
        from PySide6.QtWidgets import QMenu
        from app.widgets.top_bar import TabCornerChrome
        menu = QMenu()
        menu.addAction("Test")
        bar = TabCornerChrome(menu)
        assert bar.hamburger_button.text() == "☰"
        assert bar.sidebar_toggle.text() == "▤"

    def test_set_sidebar_expanded_flips_icon(self):
        from PySide6.QtWidgets import QMenu
        from app.widgets.top_bar import TabCornerChrome
        menu = QMenu()
        bar = TabCornerChrome(menu)
        bar.set_sidebar_expanded(True)
        assert "◀" in bar.sidebar_toggle.text()
        bar.set_sidebar_expanded(False)
        assert "◀" not in bar.sidebar_toggle.text()


# ── CommandDialog ──────────────────────────────────────────────────────

@needs_qt
class TestCommandDialog:
    def test_field_spec_renders(self):
        from app.widgets.command_dialog import CommandDialog, FieldSpec

        class _Demo(CommandDialog):
            TITLE = "Demo"
            FIELDS = [
                FieldSpec("name", "Name", kind="text", default="x"),
                FieldSpec("count", "Count", kind="number", default=3),
                FieldSpec("rate", "Rate", kind="float", default=0.5),
                FieldSpec("mode", "Mode", kind="choice",
                          choices=["a", "b"], default="a"),
                FieldSpec("flag", "Flag", kind="checkbox", default=True),
            ]

            def run(self, values):
                return f"{values['name']}-{values['count']}"

        dlg = _Demo()
        values = dlg._collect_values()
        assert values == {
            "name": "x", "count": 3, "rate": 0.5,
            "mode": "a", "flag": True,
        }

    def test_run_captures_output(self):
        from app.widgets.command_dialog import CommandDialog, FieldSpec

        class _Demo(CommandDialog):
            TITLE = "Demo"
            FIELDS = [FieldSpec("x", "X", kind="text", default="hi")]

            def run(self, values):
                return f"got {values['x']}"

        dlg = _Demo()
        dlg._on_run_clicked()
        assert "got hi" in dlg.output.toPlainText()

    def test_normalize_paths(self):
        from app.widgets.command_dialog import CommandDialog, FieldSpec

        class _Demo(CommandDialog):
            FIELDS = [
                FieldSpec("file", "File", kind="file", default="."),
                FieldSpec("text", "Text", kind="text", default="raw"),
            ]
            def run(self, values):
                return ""

        dlg = _Demo()
        out = dlg._normalize_values({"file": ".", "text": "raw"})
        # Path normalization happened
        assert Path(out["file"]).is_absolute()
        # Text untouched
        assert out["text"] == "raw"
