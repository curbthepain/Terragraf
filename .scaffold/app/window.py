"""Main window — tabbed workspace with native + external sessions.

Session 27 chrome rework: replaced the ``QSplitter`` + ``QStatusBar`` shell
with a floating-card layout (sidebar + top bar + tab content + footer) that
matches ``additions/terragraf_preview.py``. See
``.scaffold/app/widgets/top_bar.py`` for ``TopBar`` / ``Footer``, and
``tab_strip.py`` for the ws-tab pill strip that replaces ``QTabBar``.
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QMenu,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from .bridge_client import BridgeClient
from .coherence import CoherenceManager
from .external_detector import ExternalDetector
from .external_tab import ExternalTab
from .feedback import FeedbackLoop
from .imgui_dock import ImGuiDock
from .imgui_panel import ImGuiPanel
from .widgets.graph_panel import GraphPanel
from .native_tab import NativeTab
from .session import SessionManager
from .scaffold_watcher import ScaffoldWatcher
from .scaffold_state import ScaffoldState
from .tab_widget import WorkspaceTabWidget
from .welcome_tab import WelcomeTab
from .settings_page import _load_settings, _save_settings
from .widgets.sidebar import Sidebar
from .widgets.top_bar import Footer, TopBar
from . import theme


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terragraf")
        self.setMinimumSize(QSize(1024, 640))
        # Adaptive initial size — clamps to a sensible range relative to the
        # primary screen's available area. Logical px under PassThrough, so
        # Qt scales for the user's DPI automatically.
        screen = QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableSize()
            w = max(1024, min(1600, int(avail.width() * 0.80)))
            h = max(640, min(1000, int(avail.height() * 0.85)))
            self.resize(w, h)
        else:
            self.resize(1440, 900)

        # --- Style ---
        self.setStyleSheet(theme.STYLESHEET)

        # --- Bridge client (shared) ---
        self._bridge = BridgeClient()

        # --- Session manager ---
        self._session_mgr = SessionManager()

        # --- Scaffold state + watcher ---
        self._scaffold_state = ScaffoldState()
        self._scaffold_watcher = ScaffoldWatcher()
        self._scaffold_state.connect_watcher(self._scaffold_watcher)
        self._scaffold_watcher.watch_defaults()
        self._scaffold_state.load_all()

        # HOT_CONTEXT threshold guard — warn-only inside the Qt app
        # (we never auto-rewrite a file the user might be staring at)
        self._scaffold_watcher.hot_context_changed.connect(
            self._maybe_warn_hot_context
        )

        # --- Menu bar ---
        self._build_menu()

        # --- External detector ---
        self._external_detector = ExternalDetector(
            self._scaffold_state, self._session_mgr
        )

        # --- Feedback loop ---
        self._feedback = FeedbackLoop(
            self._scaffold_state, self._session_mgr, self._external_detector
        )

        # --- Coherence manager ---
        self._coherence = CoherenceManager(
            self._session_mgr, self._scaffold_state
        )

        # --- Central: splitter [tabs | imgui panel] ---
        self._tabs = WorkspaceTabWidget(self._session_mgr)
        self._tabs.register_tab_type(
            "native",
            lambda session: NativeTab(session, self._scaffold_state),
        )
        self._tabs.register_tab_type(
            "external",
            lambda session: ExternalTab(session, self._scaffold_state),
        )
        self._tabs.register_tab_type(
            "welcome",
            lambda session: WelcomeTab(
                session, self._scaffold_state, self._session_mgr
            ),
        )

        # ImGuiPanel lives inside a QDockWidget on the right edge. The
        # dock is hidden by default; Ctrl+I toggles its visibility. The
        # user can float (tear off) the dock via its titlebar for a
        # multi-monitor workflow. `ImGuiDock` below is the unrelated
        # ImGui-backend routing object — different concept from the Qt
        # QDockWidget we build here.
        self._imgui_panel = ImGuiPanel(self._bridge)
        self._imgui_dock_widget = QDockWidget("ImGui Viewer", self)
        self._imgui_dock_widget.setObjectName("imguiDock")
        self._imgui_dock_widget.setWidget(self._imgui_panel)
        self._imgui_dock_widget.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._imgui_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._imgui_dock_widget
        )
        self._imgui_dock_widget.setVisible(False)

        # GraphPanel lives in its own QDockWidget, same pattern as ImGui.
        # Ctrl+G toggles; hidden by default.
        self._graph_panel = GraphPanel()
        self._graph_dock_widget = QDockWidget("Graph Viewer", self)
        self._graph_dock_widget.setObjectName("graphDock")
        self._graph_dock_widget.setWidget(self._graph_panel)
        self._graph_dock_widget.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._graph_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._graph_dock_widget
        )
        self._graph_dock_widget.setVisible(False)

        # --- Sidebar (collapsible contextual rail) ---
        self._sidebar = Sidebar()
        settings = _load_settings()
        self._sidebar.set_expanded(settings.get("sidebar_expanded", True))

        # --- Top bar (hamburger + sidebar toggle + ws-tab strip + brand) ---
        self._hamburger_menu = self._build_hamburger_menu()
        self._top_bar = TopBar(self._hamburger_menu)
        self._top_bar.set_sidebar_expanded(self._sidebar.is_expanded())
        self._top_bar.sidebar_toggle_clicked.connect(self._toggle_sidebar)

        # Wire WorkspaceTabWidget <-> TopBar.tab_strip
        self._tab_strip = self._top_bar.tab_strip
        self._tabs.tab_added.connect(self._on_tab_added_to_strip)
        self._tabs.tab_removed.connect(self._tab_strip.remove_tab)
        self._tabs.tab_label_changed.connect(self._tab_strip.set_label)
        self._tabs.current_changed.connect(self._tab_strip.set_current)
        self._tab_strip.current_changed.connect(self._tabs.setCurrentIndex)
        self._tab_strip.close_requested.connect(self._tabs._on_close_tab)

        # Hide the standard menu bar — hamburger replaces it
        self.menuBar().setVisible(False)

        # --- Floating-card central layout ---
        # objectName="centralWidget" makes the QMainWindow's sunset gradient
        # show through (see kohala.qss `QMainWindow > QWidget#centralWidget`).
        central = QWidget()
        central.setObjectName("centralWidget")

        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 14, 16, 6)
        outer.setSpacing(10)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(14)
        body.addWidget(self._sidebar)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(12)
        right_col.addWidget(self._top_bar)
        right_col.addWidget(self._tabs, 1)

        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        body.addWidget(right_wrap, 1)

        body_wrap = QWidget()
        body_wrap.setLayout(body)
        outer.addWidget(body_wrap, 1)

        # --- Footer (replaces QStatusBar) ---
        self._footer = Footer()
        outer.addWidget(self._footer)

        self.setCentralWidget(central)

        # --- Lazy dialog cache (sidebar action_id -> instance) ---
        self._dialogs: dict = {}

        # --- ImGui dock (routes tab data to ImGui) ---
        self._imgui_dock = ImGuiDock(
            self._bridge, self._scaffold_state, self._session_mgr
        )

        # Route external events to all external tabs
        self._external_detector.external_change.connect(
            self._on_external_change
        )

        # Wire tab signals to status bar updates + ImGui dock + sidebar context
        self._tabs.tab_session_activated.connect(self._on_tab_activated)
        self._tabs.tab_session_activated.connect(
            self._imgui_dock.on_tab_activated
        )
        self._tabs.tab_session_activated.connect(self._on_tab_activated_for_sidebar)
        self._tabs.tab_session_created.connect(self._on_tab_created)
        self._tabs.tab_session_closed.connect(self._on_tab_closed)

        # Sidebar action dispatch
        self._sidebar.action_triggered.connect(self._on_sidebar_action)

        # --- Footer state wiring (replaces the S26 QStatusBar) ---
        self._bridge.connection_changed.connect(self._on_bridge_status)
        self._footer.set_bridge_state(False)

        self._coherence.conflict_detected.connect(self._on_conflict_detected)
        self._coherence.conflict_cleared.connect(self._on_conflict_cleared)

        # Feedback sharpen -> forward to active external tab
        self._feedback.sharpen_suggested.connect(self._on_sharpen_suggested)

        # --- Create initial welcome tab ---
        self._tabs.create_tab(tab_type="welcome", label="Welcome")
        self._update_session_count()

        # --- Auto-connect if configured ---
        settings = _load_settings()
        if settings.get("auto_connect"):
            self._bridge.host = settings.get("bridge_host", "127.0.0.1")
            self._bridge.port = settings.get("bridge_port", 9876)
            self._bridge.connect_to_bridge()

    # ── Menu ────────────────────────────────────────────────────────

    def _build_menu(self):
        bar = self.menuBar()

        # File menu
        file_menu = bar.addMenu("&File")

        self._action_new_native = QAction("New &Native Tab", self)
        self._action_new_native.setShortcut(QKeySequence("Ctrl+N"))
        self._action_new_native.triggered.connect(lambda: self._tabs.create_tab("native"))
        file_menu.addAction(self._action_new_native)

        self._action_new_external = QAction("New &External Tab", self)
        self._action_new_external.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self._action_new_external.triggered.connect(lambda: self._tabs.create_tab("external"))
        file_menu.addAction(self._action_new_external)

        file_menu.addSeparator()

        self._action_settings = QAction("&Settings...", self)
        self._action_settings.setShortcut(QKeySequence("Ctrl+,"))
        self._action_settings.triggered.connect(self._open_settings)
        file_menu.addAction(self._action_settings)

        file_menu.addSeparator()

        self._action_quit = QAction("&Quit", self)
        self._action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self._action_quit.triggered.connect(self.close)
        file_menu.addAction(self._action_quit)

        # View menu
        view_menu = bar.addMenu("&View")

        self._action_toggle_imgui = QAction("Toggle &ImGui Panel", self)
        self._action_toggle_imgui.setShortcut(QKeySequence("Ctrl+I"))
        self._action_toggle_imgui.triggered.connect(self._toggle_imgui_panel)
        view_menu.addAction(self._action_toggle_imgui)

        self._action_toggle_graph = QAction("Toggle &Graph Panel", self)
        self._action_toggle_graph.setShortcut(QKeySequence("Ctrl+G"))
        self._action_toggle_graph.triggered.connect(self._toggle_graph_panel)
        view_menu.addAction(self._action_toggle_graph)

        self._action_toggle_sidebar = QAction("Toggle &Sidebar", self)
        self._action_toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        self._action_toggle_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(self._action_toggle_sidebar)

        view_menu.addSeparator()

        self._action_fullscreen = QAction("Toggle &Fullscreen", self)
        self._action_fullscreen.setShortcut(QKeySequence("F11"))
        self._action_fullscreen.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(self._action_fullscreen)

        self._action_maximize = QAction("Toggle &Maximize", self)
        self._action_maximize.setShortcut(QKeySequence("F10"))
        self._action_maximize.triggered.connect(self._toggle_maximize)
        view_menu.addAction(self._action_maximize)

        # Make all actions effective even when the menu bar is hidden
        for act in (
            self._action_new_native, self._action_new_external,
            self._action_settings, self._action_quit,
            self._action_toggle_imgui, self._action_toggle_sidebar,
            self._action_fullscreen, self._action_maximize,
        ):
            act.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
            self.addAction(act)

        self._view_menu = view_menu

    def _build_hamburger_menu(self) -> QMenu:
        """Construct the popup menu used by the TopBar's hamburger button.

        Reuses the same QAction instances built in `_build_menu`, so all
        shortcuts continue to work and there is no duplication.
        """
        menu = QMenu(self)
        menu.addAction(self._action_new_native)
        menu.addAction(self._action_new_external)
        menu.addSeparator()
        menu.addAction(self._action_toggle_sidebar)
        menu.addAction(self._action_toggle_imgui)
        menu.addAction(self._action_fullscreen)
        menu.addAction(self._action_maximize)
        menu.addSeparator()
        menu.addAction(self._action_settings)
        menu.addSeparator()
        menu.addAction(self._action_quit)
        return menu

    # ── Settings dialog ─────────────────────────────────────────────

    def _open_settings(self):
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(bridge_client=self._bridge, parent=self)
        dlg.exec()

    # ── Tab event handlers ──────────────────────────────────────────

    def _on_tab_activated(self, session_id: str):
        # Footer doesn't carry a "current tab" segment — the active ws-tab
        # pill in the top bar handles that. Hook kept for future use.
        return

    def _on_tab_created(self, session_id: str):
        self._update_session_count()

    def _on_tab_closed(self, session_id: str):
        self._update_session_count()

    def _update_session_count(self):
        self._footer.set_session_count(self._session_mgr.count)

    def _on_tab_added_to_strip(self, index: int, label: str):
        """Bridge WorkspaceTabWidget.tab_added to the ws-tab pill strip.

        Welcome tabs are non-closable; everything else gets an inline ×.
        """
        session_id = self._tabs.session_for_tab(index)
        session = self._session_mgr.get(session_id) if session_id else None
        closable = not (session and session.tab_type == "welcome")
        self._tab_strip.add_tab(index, label, closable=closable)
        # If the new tab is the current one, highlight its pill immediately.
        self._tab_strip.set_current(self._tabs.currentIndex())

    def _on_external_change(self, event):
        """Forward external events to all open ExternalTab widgets."""
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if isinstance(widget, ExternalTab):
                widget.add_external_event(event)

    # ── HOT_CONTEXT threshold guard ─────────────────────────────────

    def _maybe_warn_hot_context(self):
        """
        Watcher saw HOT_CONTEXT.md change. Run the central threshold guard
        in warn-only mode (auto_decompose=False) so we never rewrite a file
        the user might be editing in another window. Surface the result in
        the footer as a transient coherence warning so the user sees it
        without the old QStatusBar round-trip.
        """
        try:
            import sys as _sys
            from pathlib import Path as _Path
            scaffold_root = _Path(__file__).resolve().parent.parent
            if str(scaffold_root) not in _sys.path:
                _sys.path.insert(0, str(scaffold_root))
            from hooks.on_hot_threshold import check_threshold
            result = check_threshold(auto_decompose=False)
        except Exception:
            return
        if result.get("over"):
            self._footer.set_coherence_warning(
                f"HOT_CONTEXT {result['lines']}/{result['threshold']} — "
                f"run terra hot decompose"
            )

    # ── Bridge status ───────────────────────────────────────────────

    def _on_bridge_status(self, connected: bool):
        self._footer.set_bridge_state(connected)
        if hasattr(self, "_sidebar"):
            self._sidebar.set_bridge_status(connected)

    # ── Coherence + feedback handlers ───────────────────────────────

    def _on_conflict_detected(self, session_id: str, conflict_type: str, detail: str):
        n = self._coherence.active_conflict_count
        self._footer.set_coherence_warning(
            f"CONFLICTS: {n} ({conflict_type})"
        )

    def _on_conflict_cleared(self, session_id: str):
        if self._coherence.active_conflict_count == 0:
            self._footer.set_coherence_warning(None)
        else:
            n = self._coherence.active_conflict_count
            self._footer.set_coherence_warning(f"CONFLICTS: {n}")

    def _on_sharpen_suggested(self, route_path: str):
        # Sharpen hints used to flash in the status bar. The footer is a
        # persistent brand line now; just log and let ActivityFeed surface
        # the event instead.
        return

    # ── ImGui panel ──────────────────────────────────────────────────

    def _toggle_imgui_panel(self):
        visible = not self._imgui_dock_widget.isVisible()
        self._imgui_dock_widget.setVisible(visible)

    # ── Graph panel ─────────────────────────────────────────────────

    def _toggle_graph_panel(self):
        visible = not self._graph_dock_widget.isVisible()
        self._graph_dock_widget.setVisible(visible)
        if visible:
            self._graph_panel.refresh()

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

    def resizeEvent(self, event):
        """Force repaint on resize to clear stale pixels (DPI artifact fix)."""
        super().resizeEvent(event)
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(event)

    # ── Sidebar dispatch ────────────────────────────────────────────

    def _toggle_sidebar(self):
        new_state = not self._sidebar.is_expanded()
        self._sidebar.set_expanded(new_state, animated=True)
        self._top_bar.set_sidebar_expanded(new_state)
        # No splitter anymore — the sidebar is a fixed-width floating card,
        # set_expanded() already updates its width.
        s = _load_settings()
        s["sidebar_expanded"] = new_state
        _save_settings(s)

    def _on_tab_activated_for_sidebar(self, session_id: str):
        session = self._session_mgr.get(session_id)
        if session:
            self._sidebar.set_active_tab(session.tab_type)

    def _dialog(self, key: str, factory):
        """Lazy-instantiate and cache dialogs."""
        if key not in self._dialogs:
            try:
                if isinstance(factory, type):
                    self._dialogs[key] = factory(parent=self)
                else:
                    self._dialogs[key] = factory()
            except Exception as e:
                self._footer.set_coherence_warning(f"failed to open {key}: {e}")
                return None
        return self._dialogs[key]

    def _run_skill_quietly(self, name: str):
        """Run a skill in-process. Errors surface as a coherence warning."""
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from skills.runner import run_skill_capture
            rc, stdout, stderr = run_skill_capture(name, [])
            if rc != 0:
                text = (stderr or stdout or "").strip().split("\n", 1)[0]
                self._footer.set_coherence_warning(f"{name}: {text or 'failed'}")
        except Exception as e:
            self._footer.set_coherence_warning(f"{name}: error {e}")

    def _clear_active_activity_feed(self):
        widget = self._tabs.currentWidget()
        feed = getattr(widget, "_activity_feed", None) or getattr(widget, "activity_feed", None)
        if feed and hasattr(feed, "clear"):
            feed.clear()

    def _on_sidebar_action(self, action_id: str):
        # Imports are local to keep window.py startup fast and avoid
        # pulling Qt widget classes that may transitively touch Qt before
        # MainWindow construction.
        from .widgets.dialogs import (
            GenerateDialog, TrainDialog, SolveDialog, AnalyzeDialog,
            RenderDialog, GitFlowDialog, ProjectNewDialog, DispatchDialog,
        )
        from .widgets.browsers import (
            RoutesBrowser, HeadersBrowser, KnowledgeBrowser,
            SkillPicker, WorktreeManagerDialog,
            LookupBrowser, PatternBrowser,
        )
        from .widgets.panels import (
            HealthPanel, QueuePanel, DepsPanel, MCPServerPanel,
            SharpenPanel, HotContextEditor,
            TunePanel, ModePanel, StatusPanel, ViewerPanel,
        )

        # Tab creation
        if action_id == "new_native":
            self._tabs.create_tab("native"); return
        if action_id == "new_external":
            self._tabs.create_tab("external"); return

        # Direct actions
        if action_id == "settings":
            self._open_settings(); return
        if action_id == "refresh_snapshot":
            self._scaffold_state.load_all(); return
        if action_id == "clear_activity":
            self._clear_active_activity_feed(); return
        if action_id == "toggle_graph_panel":
            self._toggle_graph_panel(); return
        if action_id.startswith("skill:"):
            self._run_skill_quietly(action_id.split(":", 1)[1]); return
        if action_id == "route_jump":
            dlg = self._dialog(
                "browse_routes",
                lambda: RoutesBrowser(self._scaffold_state, parent=self),
            )
            if dlg is not None:
                dlg.filter_edit.setFocus()
                dlg.filter_edit.selectAll()
                dlg.exec()
            return

        # Form dialogs
        dialog_map = {
            "dlg_generate":     lambda: GenerateDialog(parent=self),
            "dlg_train":        lambda: TrainDialog(parent=self),
            "dlg_solve":        lambda: SolveDialog(parent=self),
            "dlg_analyze":      lambda: AnalyzeDialog(parent=self),
            "dlg_render":       lambda: RenderDialog(parent=self),
            "dlg_git_flow":     lambda: GitFlowDialog(parent=self),
            "dlg_project_new":  lambda: ProjectNewDialog(parent=self),
            "dlg_dispatch":     lambda: DispatchDialog(parent=self),
        }
        if action_id in dialog_map:
            dlg = self._dialog(action_id, dialog_map[action_id])
            if dlg is not None:
                dlg.exec()
            return

        # Browsers
        browser_map = {
            "browse_routes":    lambda: RoutesBrowser(self._scaffold_state, parent=self),
            "browse_headers":   lambda: HeadersBrowser(self._scaffold_state, parent=self),
            "browse_knowledge": lambda: KnowledgeBrowser(parent=self),
            "browse_skills":    lambda: SkillPicker(parent=self),
            "browse_worktrees": lambda: WorktreeManagerDialog(parent=self),
            "browse_lookup":    lambda: LookupBrowser(parent=self),
            "browse_patterns":  lambda: PatternBrowser(parent=self),
        }
        if action_id in browser_map:
            dlg = self._dialog(action_id, browser_map[action_id])
            if dlg is not None:
                dlg.exec()
            return

        # Status panels
        panel_map = {
            "panel_health":      lambda: HealthPanel(parent=self),
            "panel_queue":       lambda: QueuePanel(self._scaffold_state, parent=self),
            "panel_deps":        lambda: DepsPanel(parent=self),
            "panel_mcp":         lambda: MCPServerPanel(parent=self),
            "panel_sharpen":     lambda: SharpenPanel(parent=self),
            "panel_hot_context": lambda: HotContextEditor(parent=self),
            "panel_tune":        lambda: TunePanel(parent=self),
            "panel_mode":        lambda: ModePanel(parent=self),
            "panel_status":      lambda: StatusPanel(parent=self),
            "panel_viewer":      lambda: ViewerPanel(parent=self),
        }
        if action_id in panel_map:
            dlg = self._dialog(action_id, panel_map[action_id])
            if dlg is not None:
                dlg.exec()
            return

        self._footer.set_coherence_warning(f"unknown sidebar action: {action_id}")

    def closeEvent(self, event):
        # Cleanup coherence timer
        self._coherence.stop()
        # Cleanup ImGui panel
        self._imgui_panel.cleanup()
        # Cleanup watcher
        self._scaffold_watcher.cleanup()
        # Cleanup bridge
        self._bridge.disconnect_from_bridge()
        super().closeEvent(event)

    # ── Public accessors ────────────────────────────────────────────

    @property
    def session_manager(self) -> SessionManager:
        return self._session_mgr

    @property
    def scaffold_state(self) -> ScaffoldState:
        return self._scaffold_state

    @property
    def scaffold_watcher(self) -> ScaffoldWatcher:
        return self._scaffold_watcher

    @property
    def bridge(self) -> BridgeClient:
        return self._bridge

    @property
    def tabs(self) -> WorkspaceTabWidget:
        return self._tabs

    @property
    def imgui_panel(self) -> ImGuiPanel:
        return self._imgui_panel

    @property
    def imgui_dock(self) -> ImGuiDock:
        return self._imgui_dock
