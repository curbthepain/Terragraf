"""Tests for Session 27 — layout rework.

Covers the new TopBar / Footer / WorkspaceTabStrip chrome, the
WelcomeTab two-panel rewrite, the Sidebar class-property migration, and
the rewired signal path between ``WorkspaceTabWidget`` and the pill strip.
"""

from __future__ import annotations

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


# ── TopBar ─────────────────────────────────────────────────────────────

@needs_qt
class TestTopBarLayout:
    def test_topbar_fixed_height_and_class(self):
        from PySide6.QtWidgets import QMenu
        from app.widgets.top_bar import TopBar
        menu = QMenu()
        bar = TopBar(menu)
        assert bar.height() == 58
        assert bar.property("class") == "topbar"

    def test_topbar_contains_expected_widgets(self):
        from PySide6.QtWidgets import QMenu, QToolButton, QLabel
        from app.widgets.top_bar import TopBar
        from app.widgets.tab_strip import WorkspaceTabStrip
        menu = QMenu()
        bar = TopBar(menu)

        iconbtns = [
            b for b in bar.findChildren(QToolButton)
            if b.property("class") == "iconbtn"
        ]
        # TopBar itself owns exactly two iconbtns (hamburger + sidebar toggle).
        # The ws-tab strip may spawn more inside its pill children later, so
        # we restrict the search to direct children.
        direct_icons = [b for b in iconbtns if b.parent() is bar]
        assert len(direct_icons) == 2

        assert isinstance(bar.tab_strip, WorkspaceTabStrip)

        brand_labels = [
            l for l in bar.findChildren(QLabel)
            if l.property("class") in ("brand-mark", "brand-mark-red")
        ]
        brand_texts = {l.text() for l in brand_labels}
        assert "TERRA" in brand_texts
        assert "GRAF" in brand_texts


# ── Footer ─────────────────────────────────────────────────────────────

@needs_qt
class TestFooter:
    def test_footer_fixed_height_and_class(self):
        from app.widgets.top_bar import Footer
        f = Footer()
        assert f.height() == 44
        assert f.property("class") == "topbar"

    def test_footer_default_text(self):
        from app.widgets.top_bar import Footer
        f = Footer()
        text = f.center_label.text()
        assert "BRIDGE: OFFLINE" in text
        assert "0 SESSIONS" in text
        assert "PATENT PENDING" in text

    def test_footer_bridge_state_updates(self):
        from app.widgets.top_bar import Footer
        f = Footer()
        f.set_bridge_state(True)
        assert "BRIDGE: ONLINE" in f.center_label.text()
        f.set_bridge_state("connecting")
        assert "CONNECTING" in f.center_label.text()

    def test_footer_session_count_pluralizes(self):
        from app.widgets.top_bar import Footer
        f = Footer()
        f.set_session_count(1)
        assert "1 SESSION " in f.center_label.text() + " "  # singular
        assert "1 SESSIONS" not in f.center_label.text()
        f.set_session_count(3)
        assert "3 SESSIONS" in f.center_label.text()

    def test_footer_coherence_replaces_tail(self):
        from app.widgets.top_bar import Footer
        f = Footer()
        f.set_coherence_warning("conflict: routes")
        assert "CONFLICT: ROUTES" in f.center_label.text()
        assert "PATENT PENDING" not in f.center_label.text()
        f.set_coherence_warning(None)
        assert "PATENT PENDING" in f.center_label.text()

    def test_footer_brand_footer_label_class(self):
        from app.widgets.top_bar import Footer
        f = Footer()
        assert f.center_label.property("class") == "brand-footer"


# ── WorkspaceTabStrip ──────────────────────────────────────────────────

@needs_qt
class TestTabStrip:
    def test_add_and_remove(self):
        from app.widgets.tab_strip import WorkspaceTabStrip
        s = WorkspaceTabStrip()
        s.add_tab(0, "Welcome", closable=False)
        s.add_tab(1, "Native")
        assert s.count() == 2
        s.remove_tab(0)
        assert s.count() == 1

    def test_set_current_emits(self):
        from app.widgets.tab_strip import WorkspaceTabStrip
        s = WorkspaceTabStrip()
        s.add_tab(0, "A")
        s.add_tab(1, "B")
        captured: list[int] = []
        s.current_changed.connect(lambda i: captured.append(i))
        s._pills[1].button.click()
        assert captured == [1]

    def test_close_clicked_emits(self):
        from app.widgets.tab_strip import WorkspaceTabStrip
        s = WorkspaceTabStrip()
        s.add_tab(0, "A")
        captured: list[int] = []
        s.close_requested.connect(lambda i: captured.append(i))
        s._pills[0].close_btn.click()
        assert captured == [0]

    def test_set_label_updates(self):
        from app.widgets.tab_strip import WorkspaceTabStrip
        s = WorkspaceTabStrip()
        s.add_tab(0, "a")
        s.set_label(0, "renamed")
        assert s._pills[0].button.text() == "RENAMED"


# ── Sidebar class/width ────────────────────────────────────────────────

@needs_qt
class TestSidebarS27:
    def test_sidebar_class_property(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        assert sb.property("class") == "sidebar"

    def test_sidebar_expanded_width_is_258(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_expanded(True)
        assert sb.width() == 258

    def test_nav_items_tagged(self):
        from app.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_active_tab("welcome")
        tagged = [b for b in sb.buttons() if b.property("class") == "nav-item"]
        assert len(tagged) == len(sb.buttons())
        assert len(tagged) > 0

    def test_version_label_in_footer(self):
        from app.widgets.sidebar import Sidebar
        from PySide6.QtWidgets import QLabel
        sb = Sidebar()
        texts = [l.text() for l in sb.findChildren(QLabel)]
        assert any(t.startswith("v") and "." in t for t in texts)
        assert any("WORKSPACE" in t for t in texts)


# ── WelcomeTab two-panel layout ────────────────────────────────────────

def _make_state_and_mgr():
    """Minimal ScaffoldState + SessionManager for welcome tab tests."""
    import tempfile
    from pathlib import Path as _P
    from app.scaffold_state import ScaffoldState
    from app.session import SessionManager

    tmp = _P(tempfile.mkdtemp())
    (tmp / "headers").mkdir()
    (tmp / "routes").mkdir()
    (tmp / "tables").mkdir()
    (tmp / "instances" / "shared" / "locks").mkdir(parents=True)
    (tmp / "HOT_CONTEXT.md").write_text("# Test\n")
    (tmp / "instances" / "shared" / "queue.json").write_text("[]")
    state = ScaffoldState(scaffold_dir=tmp)
    state.load_all()
    return state, SessionManager()


@needs_qt
class TestWelcomeTabS27:
    def test_two_panels(self):
        from PySide6.QtWidgets import QFrame
        from app.session import Session
        from app.welcome_tab import WelcomeTab
        state, mgr = _make_state_and_mgr()
        tab = WelcomeTab(Session(tab_type="welcome", label="W"), state, mgr)
        panels = [
            f for f in tab.findChildren(QFrame)
            if f.property("class") == "panel"
        ]
        assert len(panels) == 2

    def test_health_labels_populated(self):
        from app.session import Session
        from app.welcome_tab import WelcomeTab, _HEALTH_KEYS
        state, mgr = _make_state_and_mgr()
        tab = WelcomeTab(Session(tab_type="welcome", label="W"), state, mgr)
        assert set(tab._health_labels.keys()) == {k for k, _ in _HEALTH_KEYS}
        assert len(tab._health_labels) == 12

    def test_root_layout_stretch_ratio(self):
        from app.session import Session
        from app.welcome_tab import WelcomeTab
        state, mgr = _make_state_and_mgr()
        tab = WelcomeTab(Session(tab_type="welcome", label="W"), state, mgr)
        root = tab.layout()
        # Two items: health (stretch 3) + sessions (stretch 2)
        assert root.count() == 2
        assert root.stretch(0) == 3
        assert root.stretch(1) == 2


# ── WorkspaceTabWidget <-> WorkspaceTabStrip mirroring ─────────────────

@needs_qt
class TestTabStripMirroring:
    # Class-level refs keep Qt widgets alive across the test body. Local
    # variables get GC'd the moment the helper returns, which under
    # shiboken deletes the underlying C++ object and the strip along with
    # it — that's what caused the first run on CI to blow up with
    # "Internal C++ object (WorkspaceTabStrip) already deleted".
    _alive: list = []

    def _make(self):
        from app.session import SessionManager
        from app.tab_widget import WorkspaceTabWidget
        from app.widgets.tab_strip import WorkspaceTabStrip
        mgr = SessionManager()
        tabs = WorkspaceTabWidget(mgr)
        strip = WorkspaceTabStrip()
        # Pin both objects so Python (and shiboken) don't collect them
        # mid-test.
        self._alive.extend([mgr, tabs, strip])

        # Wire the same signals MainWindow wires.
        tabs.tab_added.connect(lambda i, lbl: strip.add_tab(i, lbl))
        tabs.tab_removed.connect(strip.remove_tab)
        tabs.tab_label_changed.connect(strip.set_label)
        tabs.current_changed.connect(strip.set_current)
        strip.current_changed.connect(tabs.setCurrentIndex)
        strip.close_requested.connect(tabs._on_close_tab)
        return tabs, strip

    def test_topbar_owns_tab_strip(self):
        """Sanity: the TopBar exposes the same WorkspaceTabStrip type used
        above, so MainWindow's wiring targets the same signal surface."""
        from PySide6.QtWidgets import QMenu
        from app.widgets.tab_strip import WorkspaceTabStrip
        from app.widgets.top_bar import TopBar
        bar = TopBar(QMenu())
        self._alive.append(bar)
        assert isinstance(bar.tab_strip, WorkspaceTabStrip)

    def test_create_tab_adds_pill(self):
        tabs, strip = self._make()
        tabs.create_tab("native", "Alpha")
        assert strip.count() == 1

    def test_close_pill_removes_tab(self):
        tabs, strip = self._make()
        tabs.create_tab("native", "Alpha")
        tabs.create_tab("native", "Beta")
        assert strip.count() == 2
        strip.close_requested.emit(1)
        assert tabs.count() == 1
        assert strip.count() == 1

    def test_click_pill_activates_session(self):
        tabs, strip = self._make()
        s1 = tabs.create_tab("native", "A")
        s2 = tabs.create_tab("native", "B")
        tabs.setCurrentIndex(1)
        assert tabs.active_session_id() == s2.id
        strip.current_changed.emit(0)
        assert tabs.active_session_id() == s1.id


# ── MainWindow chrome smoke test ───────────────────────────────────────

@needs_qt
class TestMainWindowChrome:
    def _make_window(self):
        from app.window import MainWindow
        return MainWindow()

    def test_central_widget_margins(self):
        win = self._make_window()
        central = win.centralWidget()
        lay = central.layout()
        m = lay.contentsMargins()
        assert (m.left(), m.top(), m.right(), m.bottom()) == (16, 14, 16, 6)
        win.close()
        win.deleteLater()

    def test_has_top_bar_and_footer(self):
        from app.widgets.top_bar import Footer, TopBar
        win = self._make_window()
        assert isinstance(win._top_bar, TopBar)
        assert isinstance(win._footer, Footer)
        win.close()
        win.deleteLater()

    def test_no_status_bar_content(self):
        win = self._make_window()
        # QMainWindow always has a status bar object lazily; we just make
        # sure the S26 indicator widgets no longer exist.
        assert not hasattr(win, "_bridge_indicator")
        assert not hasattr(win, "_session_indicator")
        assert not hasattr(win, "_coherence_indicator")
        assert not hasattr(win, "_splitter")
        win.close()
        win.deleteLater()

    def test_footer_reflects_session_count(self):
        win = self._make_window()
        # MainWindow creates an initial welcome tab — that counts as 1.
        assert "1 SESSION" in win._footer.center_label.text()
        win._tabs.create_tab("native", "X")
        assert "2 SESSIONS" in win._footer.center_label.text()
        win.close()
        win.deleteLater()

    def test_tab_strip_mirrors_welcome(self):
        win = self._make_window()
        # Welcome tab was created in __init__; its pill should be there.
        assert win._tab_strip.count() == 1
        win.close()
        win.deleteLater()


# ── ImGui QDockWidget (S31) ────────────────────────────────────────────

@needs_qt
class TestImGuiDock:
    def _make_window(self):
        from app.window import MainWindow
        return MainWindow()

    def test_imgui_dock_exists(self):
        from PySide6.QtWidgets import QDockWidget
        from app.imgui_panel import ImGuiPanel
        win = self._make_window()
        assert isinstance(win._imgui_dock_widget, QDockWidget)
        assert win._imgui_dock_widget.widget() is win._imgui_panel
        assert isinstance(win._imgui_panel, ImGuiPanel)
        win.close()
        win.deleteLater()

    def test_imgui_dock_starts_hidden(self):
        win = self._make_window()
        assert win._imgui_dock_widget.isVisible() is False
        win.close()
        win.deleteLater()

    def test_imgui_toggle_flips_dock_visibility(self):
        win = self._make_window()
        # MainWindow must be shown for child visibility to resolve to True.
        win.show()
        assert win._imgui_dock_widget.isVisible() is False
        win._toggle_imgui_panel()
        assert win._imgui_dock_widget.isVisible() is True
        win._toggle_imgui_panel()
        assert win._imgui_dock_widget.isVisible() is False
        win.close()
        win.deleteLater()

    def test_imgui_dock_right_area(self):
        from PySide6.QtCore import Qt
        win = self._make_window()
        area = win.dockWidgetArea(win._imgui_dock_widget)
        assert area == Qt.DockWidgetArea.RightDockWidgetArea
        win.close()
        win.deleteLater()


@needs_qt
class TestGraphDock:
    def _make_window(self):
        from app.window import MainWindow
        return MainWindow()

    def test_graph_dock_exists(self):
        from PySide6.QtWidgets import QDockWidget
        from app.widgets.graph_panel import GraphPanel
        win = self._make_window()
        assert isinstance(win._graph_dock_widget, QDockWidget)
        assert win._graph_dock_widget.widget() is win._graph_panel
        assert isinstance(win._graph_panel, GraphPanel)
        win.close()
        win.deleteLater()

    def test_graph_dock_starts_hidden(self):
        win = self._make_window()
        assert win._graph_dock_widget.isVisible() is False
        win.close()
        win.deleteLater()

    def test_graph_toggle_flips_dock_visibility(self):
        win = self._make_window()
        win.show()
        assert win._graph_dock_widget.isVisible() is False
        win._toggle_graph_panel()
        assert win._graph_dock_widget.isVisible() is True
        win._toggle_graph_panel()
        assert win._graph_dock_widget.isVisible() is False
        win.close()
        win.deleteLater()

    def test_graph_dock_right_area(self):
        from PySide6.QtCore import Qt
        win = self._make_window()
        area = win.dockWidgetArea(win._graph_dock_widget)
        assert area == Qt.DockWidgetArea.RightDockWidgetArea
        win.close()
        win.deleteLater()
