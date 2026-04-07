"""Tests for Session 18 browsers and status panels."""

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


# ── Helpers ────────────────────────────────────────────────────────────

def _make_state():
    """Build a real ScaffoldState loaded from the actual scaffold tree."""
    from app.scaffold_state import ScaffoldState
    s = ScaffoldState()
    s.load_all()
    return s


# ── Browsers ───────────────────────────────────────────────────────────

@needs_qt
class TestBrowsers:
    def test_routes_browser_lists_routes(self):
        from app.widgets.browsers.routes import RoutesBrowser
        state = _make_state()
        dlg = RoutesBrowser(state)
        assert dlg.visible_row_count() > 0

    def test_routes_browser_filter_narrows(self):
        from app.widgets.browsers.routes import RoutesBrowser
        state = _make_state()
        dlg = RoutesBrowser(state)
        before = dlg.visible_row_count()
        dlg.filter_edit.setText("zzznevermatchesanything")
        after = dlg.visible_row_count()
        assert after <= before
        # And should equal zero for an obviously bad needle
        assert after == 0

    def test_headers_browser_constructs(self):
        from app.widgets.browsers.headers import HeadersBrowser
        state = _make_state()
        dlg = HeadersBrowser(state)
        # Tree has at least one top-level item (header file)
        assert dlg.tree.topLevelItemCount() > 0

    def test_skill_picker_lists_real_skills(self):
        from app.widgets.browsers.skill_picker import SkillPicker
        dlg = SkillPicker()
        assert dlg.visible_count() > 0

    def test_skill_picker_filter(self):
        from app.widgets.browsers.skill_picker import SkillPicker
        dlg = SkillPicker()
        dlg.filter_edit.setText("zzznever")
        assert dlg.visible_count() == 0

    def test_knowledge_browser_constructs(self):
        from app.widgets.browsers.knowledge import KnowledgeBrowser
        dlg = KnowledgeBrowser()
        assert dlg.windowTitle() == "Knowledge"

    def test_worktree_manager_constructs(self):
        from app.widgets.browsers.worktree_manager import WorktreeManagerDialog
        dlg = WorktreeManagerDialog()
        assert dlg.windowTitle() == "Worktree Manager"

    def test_routes_browser_set_filter(self):
        from app.widgets.browsers.routes import RoutesBrowser
        state = _make_state()
        dlg = RoutesBrowser(state)
        dlg.set_filter("zzznevermatchesanything")
        assert dlg.visible_row_count() == 0

    def test_lookup_browser_lists_errors(self):
        from app.widgets.browsers.lookup import LookupBrowser
        dlg = LookupBrowser()
        # errors.table is non-empty in the repo
        assert dlg.visible_row_count() > 0
        assert dlg.windowTitle() == "Error Lookup"

    def test_lookup_browser_filter_narrows(self):
        from app.widgets.browsers.lookup import LookupBrowser
        dlg = LookupBrowser()
        before = dlg.visible_row_count()
        dlg.filter_edit.setText("zzznevermatchesanything")
        after = dlg.visible_row_count()
        assert after <= before
        assert after == 0

    def test_pattern_browser_lists_patterns(self):
        from app.widgets.browsers.patterns import PatternBrowser
        dlg = PatternBrowser()
        assert dlg.visible_row_count() > 0
        assert dlg.windowTitle() == "Design Patterns"

    def test_pattern_browser_filter_narrows(self):
        from app.widgets.browsers.patterns import PatternBrowser
        dlg = PatternBrowser()
        dlg.filter_edit.setText("zzznevermatchesanything")
        assert dlg.visible_row_count() == 0


# ── Panels ─────────────────────────────────────────────────────────────

@needs_qt
class TestPanels:
    def test_health_panel_constructs(self):
        from app.widgets.panels.health import HealthPanel
        dlg = HealthPanel()
        assert dlg.windowTitle() == "System Health"
        # HealthPanel runs the health skill in __init__, output should not be empty
        # (we just check it has output - could be error or actual)
        assert dlg.output.toPlainText() != ""

    def test_queue_panel_constructs(self):
        from app.widgets.panels.queue import QueuePanel
        dlg = QueuePanel()
        # Two tabs: Pending + Completed
        assert dlg.tabs.count() == 2

    def test_deps_panel_constructs(self):
        from app.widgets.panels.deps import DepsPanel
        dlg = DepsPanel()
        assert dlg.tabs.count() == 2  # Python + C++

    def test_mcp_server_panel_constructs(self):
        from app.widgets.panels.mcp_server import MCPServerPanel
        dlg = MCPServerPanel()
        assert dlg.start_btn.isEnabled()
        assert not dlg.stop_btn.isEnabled()

    def test_sharpen_panel_constructs(self):
        from app.widgets.panels.sharpen import SharpenPanel
        dlg = SharpenPanel()
        assert dlg.analyze_btn.isEnabled()

    def test_hot_context_editor_loads_file(self):
        from app.widgets.panels.hot_context import HotContextEditor
        dlg = HotContextEditor()
        # Editor populated with the real HOT_CONTEXT.md content
        text = dlg.editor.toPlainText()
        assert text  # Non-empty

    def test_tune_panel_constructs(self):
        from app.widgets.panels.tune import TunePanel
        dlg = TunePanel()
        assert dlg.windowTitle() == "Tuning"
        # Status was loaded into the output area
        assert dlg.output.toPlainText() != ""

    def test_tune_panel_has_profile_combo(self):
        """Profile selection is now a populated dropdown, not free text."""
        from PySide6.QtWidgets import QComboBox
        from app.widgets.panels.tune import TunePanel
        dlg = TunePanel()
        assert isinstance(dlg.profile_combo, QComboBox)
        assert dlg.profile_combo.count() > 0  # at least one profile discovered

    def test_tune_panel_builds_typed_knob_widgets(self):
        """Loading a profile rebuilds the editor with one QGroupBox per
        knob domain and one typed widget per knob."""
        from PySide6.QtWidgets import QGroupBox
        from app.widgets.panels.tune import TunePanel
        dlg = TunePanel()
        # Pick the first profile that actually has knobs
        for i in range(dlg.profile_combo.count()):
            dlg.profile_combo.setCurrentIndex(i)
            dlg._load_profile_schema(dlg.profile_combo.currentText())
            if dlg._knob_widgets:
                break
        assert dlg._current_profile is not None
        assert dlg._knob_widgets, "expected at least one knob widget"
        groups = dlg.knob_container.findChildren(QGroupBox)
        assert len(groups) >= 1

    def test_tune_panel_does_not_import_terra(self):
        """Mirror the StatusPanel guard: TunePanel must not pull terra.py
        (which prepends src/python to sys.path and breaks torchvision)."""
        for key in list(sys.modules.keys()):
            if key == "terra":
                del sys.modules[key]
        from app.widgets.panels.tune import TunePanel
        _ = TunePanel()
        assert "terra" not in sys.modules

    def test_tune_panel_domain_groups_are_collapsible(self):
        """Each domain group is a checkable QGroupBox; toggling the title
        hides the form rows underneath."""
        from app.widgets.panels.tune import TunePanel
        dlg = TunePanel()
        for i in range(dlg.profile_combo.count()):
            dlg.profile_combo.setCurrentIndex(i)
            dlg._load_profile_schema(dlg.profile_combo.currentText())
            if dlg._domain_groups:
                break
        assert dlg._domain_groups, "expected at least one domain group"
        domain, (group, content) = next(iter(dlg._domain_groups.items()))
        assert group.isCheckable()
        assert group.isChecked()
        assert content.isVisible() is True or content.isVisibleTo(group)
        # Collapse and confirm content is hidden
        group.setChecked(False)
        assert content.isVisible() is False

    def test_tune_panel_instruction_preview_matches_engine(self):
        """Each knob row carries an instruction label whose text reflects
        ThematicEngine.get_knob_instruction at the current value."""
        from app.widgets.panels.tune import TunePanel
        dlg = TunePanel()
        # Pick the first profile that exposes a parseable behavior knob
        for i in range(dlg.profile_combo.count()):
            dlg.profile_combo.setCurrentIndex(i)
            dlg._load_profile_schema(dlg.profile_combo.currentText())
            if dlg._instruction_labels and dlg._engine is not None:
                break
        assert dlg._instruction_labels, "expected instruction labels"
        assert dlg._engine is not None
        for knob_id, label in dlg._instruction_labels.items():
            engine_text = dlg._engine.get_knob_instruction(knob_id)
            if engine_text:
                # Label is prefixed with an arrow; engine text appears verbatim
                assert engine_text.strip() in label.text(), (
                    f"knob {knob_id}: label={label.text()!r} engine={engine_text!r}"
                )

    def test_tune_panel_zone_indicator_reflects_engine(self):
        """Zone label updates when a zone is entered and cleared on exit."""
        from app.widgets.panels.tune import TunePanel
        dlg = TunePanel()
        # Find a profile that has at least one zone
        for i in range(dlg.profile_combo.count()):
            dlg.profile_combo.setCurrentIndex(i)
            dlg._load_profile_schema(dlg.profile_combo.currentText())
            if dlg._engine and dlg._engine.profile.zones:
                break
        assert dlg._engine is not None
        assert dlg._engine.profile.zones, "need a profile with zones"
        # Initial label always carries the "Zone:" prefix
        assert "Zone:" in dlg.zone_label.text()
        # Enter a zone directly on the engine + refresh
        zone_name = dlg._engine.profile.zones[0].name
        dlg._engine.enter_zone(zone_name)
        dlg._refresh_zone_indicator()
        assert zone_name in dlg.zone_label.text()
        # Exit
        dlg._engine.exit_zone()
        dlg._refresh_zone_indicator()
        assert "(none)" in dlg.zone_label.text()

    def test_mode_panel_constructs(self):
        from app.widgets.panels.mode import ModePanel
        dlg = ModePanel()
        assert dlg.windowTitle() == "Mode"
        text = dlg.output.toPlainText()
        # mode line is always present
        assert "mode" in text.lower()

    def test_status_panel_constructs(self):
        from app.widgets.panels.status import StatusPanel
        dlg = StatusPanel()
        assert dlg.windowTitle() == "Status"
        text = dlg.output.toPlainText()
        assert "Terragraf" in text
        assert "platform" in text

    def test_status_panel_does_not_import_terra(self):
        """Guard against the DepsPanel trap: terra.py prepends src/python to
        sys.path, which clobbers the system torchvision install."""
        # Wipe terra from sys.modules first so we test fresh import
        for key in list(sys.modules.keys()):
            if key == "terra":
                del sys.modules[key]
        from app.widgets.panels.status import StatusPanel
        dlg = StatusPanel()  # noqa: F841
        assert "terra" not in sys.modules

    def test_viewer_panel_constructs(self):
        from app.widgets.panels.viewer import ViewerPanel
        dlg = ViewerPanel()
        assert dlg.windowTitle() == "Viewer"
        # All control buttons exist
        assert dlg.launch_btn is not None
        assert dlg.build_btn is not None
        assert dlg.bridge_btn is not None
        assert dlg.status_btn is not None
