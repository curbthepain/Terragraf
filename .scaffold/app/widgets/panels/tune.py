"""TunePanel — controls for `terra tune`.

Reads profile schema (knob types, domains, options) and computes per-knob
behavioral instructions through a local `ThematicEngine` instance, which
also restores any persisted state from `.tuning_state.json`. All mutations
(load profile, enter zone, set knob) still go through `tuning/cli.py` as
a subprocess so the on-disk state file remains the single source of truth
across CLI and panel sessions.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


_SCAFFOLD = Path(__file__).resolve().parents[3]
_TUNING_CLI = _SCAFFOLD / "tuning" / "cli.py"
_PROFILES_DIR = _SCAFFOLD / "tuning" / "profiles"
_TERRA_ROOT = _SCAFFOLD.parent
_STATE_FILE = Path(os.environ.get(
    "TUNING_STATE_FILE", str(_SCAFFOLD / "tuning" / ".tuning_state.json")
))

# Make `tuning` importable. .scaffold is a sibling of widgets/panels — adding
# it to sys.path is the same trick test_tuning.py uses. This does NOT pull in
# terra.py, so the StatusPanel/DepsPanel src/python sys.path trap doesn't apply.
if str(_SCAFFOLD) not in sys.path:
    sys.path.insert(0, str(_SCAFFOLD))


def _run_tune(args: list[str]) -> str:
    """Shell out to tuning/cli.py and capture output."""
    if not _TUNING_CLI.exists():
        return f"tuning/cli.py not found at {_TUNING_CLI}"
    cmd = [sys.executable, str(_TUNING_CLI)] + args
    try:
        result = subprocess.run(
            cmd, cwd=str(_TERRA_ROOT), capture_output=True, text=True, timeout=30
        )
    except Exception as e:
        return f"tuning subprocess failed: {e}"
    out = result.stdout or ""
    if result.stderr:
        out += ("\n" if out else "") + result.stderr
    if result.returncode != 0:
        out += f"\n[exit {result.returncode}]"
    return out or "(no output)"


class TunePanel(QDialog):
    """Status + control panel for `terra tune` with typed knob editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tuning")
        self.setMinimumSize(720, 680)

        # Track widgets per knob_id so we can read/write them programmatically.
        self._knob_widgets: dict[str, QWidget] = {}
        self._instruction_labels: dict[str, QLabel] = {}
        # Domain → (groupbox, content widget) for collapse toggling.
        self._domain_groups: dict[str, tuple[QGroupBox, QWidget]] = {}
        self._engine = None  # ThematicEngine instance once a profile is loaded
        self._suppress_signals = False  # block knob change handlers during rebuild

        self._build_ui()
        self._discover_profiles()
        # If a profile is already persisted, load it into the panel so the
        # editor reflects on-disk state on first open.
        if self.profile_combo.count() > 0 and self.profile_combo.currentText():
            self._load_profile_schema(self.profile_combo.currentText())
        self._refresh_zone_indicator()
        self._run([])  # initial status

    # ── UI construction ───────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Tuning")
        header.setObjectName("section_header")
        layout.addWidget(header)

        info = QLabel("Profile, zone, and typed knob editor. Wraps `terra tune`.")
        info.setObjectName("dim")
        layout.addWidget(info)

        # ── Profile row ───────────────────────────────────────────
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(180)
        profile_row.addWidget(self.profile_combo, 1)
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._load_profile_clicked)
        profile_row.addWidget(load_btn)
        reload_btn = QPushButton("Reload")
        reload_btn.setToolTip("Re-scan profiles directory")
        reload_btn.clicked.connect(self._discover_profiles)
        profile_row.addWidget(reload_btn)
        layout.addLayout(profile_row)

        self.active_label = QLabel("(no profile loaded)")
        self.active_label.setObjectName("dim")
        layout.addWidget(self.active_label)

        self.zone_label = QLabel("Zone: (none)")
        self.zone_label.setObjectName("dim")
        layout.addWidget(self.zone_label)

        # ── Zone row ──────────────────────────────────────────────
        zone_row = QHBoxLayout()
        zone_row.addWidget(QLabel("Zone:"))
        self.zone_combo = QComboBox()
        self.zone_combo.setMinimumWidth(160)
        zone_row.addWidget(self.zone_combo, 1)
        enter_btn = QPushButton("Enter")
        enter_btn.clicked.connect(self._enter_zone_clicked)
        zone_row.addWidget(enter_btn)
        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(self._exit_zone_clicked)
        zone_row.addWidget(exit_btn)
        layout.addLayout(zone_row)

        # ── Knob editor (scroll area) ─────────────────────────────
        self.knob_scroll = QScrollArea()
        self.knob_scroll.setWidgetResizable(True)
        self.knob_container = QWidget()
        self.knob_layout = QVBoxLayout(self.knob_container)
        self.knob_layout.setContentsMargins(4, 4, 4, 4)
        self.knob_layout.setSpacing(6)
        self.knob_layout.addStretch(1)
        self.knob_scroll.setWidget(self.knob_container)
        layout.addWidget(self.knob_scroll, 2)

        # ── Output area ───────────────────────────────────────────
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(200)
        layout.addWidget(self.output, 1)

        # ── Footer ────────────────────────────────────────────────
        footer = QHBoxLayout()
        for label, args in (
            ("Axes", ["axes"]),
            ("Directive", ["directive"]),
            ("Promise", ["promise"]),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _checked=False, a=args: self._run(a))
            footer.addWidget(btn)
        status_btn = QPushButton("Status")
        status_btn.setObjectName("primary")
        status_btn.clicked.connect(lambda: self._run([]))
        footer.addWidget(status_btn)
        footer.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    # ── Profile discovery & loading ───────────────────────────────

    def _discover_profiles(self):
        """Populate profile_combo from tuning.loader.list_profiles()."""
        try:
            from tuning.loader import list_profiles
            names = list_profiles()
        except Exception as e:  # noqa: BLE001 — surface any import/scan failure
            self.output.setPlainText(f"Failed to list profiles: {e}")
            return
        self._suppress_signals = True
        self.profile_combo.clear()
        self.profile_combo.addItems(names)
        self._suppress_signals = False
        # Mark active profile from `tune list` output if possible
        active = self._detect_active_profile()
        if active and active in names:
            self.profile_combo.setCurrentText(active)

    def _detect_active_profile(self) -> str | None:
        """Parse `tune list` output for the line with a trailing '*'."""
        text = _run_tune(["list"])
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.endswith("*"):
                return stripped.rstrip("*").strip()
        return None

    def _load_profile_clicked(self):
        name = self.profile_combo.currentText().strip()
        if not name:
            self.output.setPlainText("Pick a profile first.")
            return
        # Mutation through subprocess (state file is authoritative)
        self._run(["load", name])
        # Schema + engine read directly for the editor
        self._load_profile_schema(name)

    def _load_profile_schema(self, name: str):
        """Spin up a ThematicEngine, load the profile, restore state,
        rebuild the knob editor."""
        try:
            from tuning.engine import ThematicEngine
            engine = ThematicEngine()
            engine.load(name)
            # Restore on-disk state so the editor matches what `terra tune`
            # would show. Mirrors tuning/cli.py:_load_engine().
            if _STATE_FILE.exists():
                try:
                    with open(_STATE_FILE) as f:
                        state = json.load(f)
                    if state.get("profile") == name:
                        engine.import_state(state)
                except Exception:  # noqa: BLE001 — fall through to defaults
                    pass
        except Exception as e:  # noqa: BLE001
            self.output.appendPlainText(f"\n[schema load failed: {e}]")
            self._engine = None
            self._rebuild_knob_editor(None)
            return
        self._engine = engine
        profile = engine.profile
        self.active_label.setText(
            f"Active: {profile.name}  ({profile.genre})  — {profile.thematic_promise}"
        )
        self._populate_zone_combo(profile)
        self._rebuild_knob_editor(profile)
        self._refresh_zone_indicator()

    @property
    def _current_profile(self):
        """Backwards-compat handle to the loaded profile (used by tests)."""
        return self._engine.profile if self._engine else None

    def _populate_zone_combo(self, profile):
        self._suppress_signals = True
        self.zone_combo.clear()
        for zone in profile.zones:
            self.zone_combo.addItem(zone.name)
        self._suppress_signals = False

    # ── Knob editor ───────────────────────────────────────────────

    def _clear_knob_editor(self):
        """Remove every widget from the knob_layout (except the trailing stretch)."""
        while self.knob_layout.count() > 1:
            item = self.knob_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._knob_widgets.clear()
        self._instruction_labels.clear()
        self._domain_groups.clear()

    def _make_collapsible_group(self, title: str) -> tuple[QGroupBox, QWidget]:
        """Build a checkable QGroupBox whose checkbox toggles content visibility.

        Returns (group, content) — caller owns the content widget and adds
        rows to its layout. Starts expanded (checked).
        """
        group = QGroupBox(title)
        group.setCheckable(True)
        group.setChecked(True)
        outer = QVBoxLayout(group)
        outer.setContentsMargins(8, 4, 8, 8)
        outer.setSpacing(0)
        content = QWidget()
        outer.addWidget(content)
        # Hide / show the content widget when the user toggles the title.
        group.toggled.connect(content.setVisible)
        return group, content

    def _rebuild_knob_editor(self, profile):
        self._clear_knob_editor()
        if profile is None:
            return
        self._suppress_signals = True
        try:
            for domain in profile.knob_domains():
                group, content = self._make_collapsible_group(f"[{domain}]")
                form = QFormLayout(content)
                form.setSpacing(6)
                form.setContentsMargins(0, 0, 0, 0)
                for knob in profile.knobs_by_domain(domain):
                    self._add_knob_row(form, knob)
                self._domain_groups[domain] = (group, content)
                # Insert before the trailing stretch
                self.knob_layout.insertWidget(self.knob_layout.count() - 1, group)
        finally:
            self._suppress_signals = False

    def _add_knob_row(self, form: QFormLayout, knob):
        """Add a labelled knob widget plus an instruction-preview row to the form."""
        widget = self._build_knob_widget(knob)
        label = QLabel(knob.label)
        if knob.description:
            label.setToolTip(knob.description)
        form.addRow(label, widget)

        instruction = QLabel(self._compute_instruction(knob.id))
        instruction.setObjectName("dim")
        instruction.setWordWrap(True)
        instruction.setContentsMargins(12, 0, 0, 6)
        # Empty label cell so the instruction lines up under the value
        form.addRow("", instruction)
        self._instruction_labels[knob.id] = instruction

    def _compute_instruction(self, knob_id: str) -> str:
        """Look up the live behavioral instruction for a knob via the engine."""
        if self._engine is None:
            return ""
        try:
            text = self._engine.get_knob_instruction(knob_id)
        except Exception:  # noqa: BLE001
            return ""
        if not text:
            return ""
        return f"→ {text.strip()}"

    def _build_knob_widget(self, knob) -> QWidget:
        kt = knob.knob_type
        widget: QWidget

        if kt == "slider":
            widget = QDoubleSpinBox()
            widget.setRange(float(knob.min_val), float(knob.max_val))
            widget.setSingleStep(float(knob.step or 0.1))
            widget.setDecimals(6)
            widget.setValue(float(knob.value if knob.value is not None else knob.default))
            widget.valueChanged.connect(
                lambda v, k=knob.id: self._on_knob_changed(k, v)
            )

        elif kt == "toggle":
            widget = QCheckBox()
            widget.setChecked(bool(knob.value if knob.value is not None else knob.default))
            widget.toggled.connect(
                lambda v, k=knob.id: self._on_knob_changed(k, v)
            )

        elif kt == "dropdown":
            widget = QComboBox()
            widget.addItems(knob.options or [])
            current = knob.value if knob.value is not None else knob.default
            if current in (knob.options or []):
                widget.setCurrentText(str(current))
            widget.currentTextChanged.connect(
                lambda v, k=knob.id: self._on_knob_changed(k, v)
            )

        elif kt == "text":
            widget = QLineEdit()
            widget.setText(str(knob.value if knob.value is not None else knob.default))
            if knob.pattern:
                widget.setToolTip(f"pattern: {knob.pattern}")
            widget.editingFinished.connect(
                lambda k=knob.id, w=None: self._on_knob_changed(k, self._knob_widgets[k].text())
            )

        elif kt == "curve":
            widget = QLabel("(curve editing not supported in panel)")
            widget.setObjectName("dim")

        else:
            widget = QLabel(f"(unknown knob type: {kt})")

        self._knob_widgets[knob.id] = widget
        return widget

    def _on_knob_changed(self, knob_id: str, value):
        if self._suppress_signals:
            return
        # Update the in-memory engine first so the instruction preview reflects
        # the new value immediately, even before the subprocess returns.
        if self._engine is not None:
            try:
                self._engine.set_knob(knob_id, value)
            except Exception:  # noqa: BLE001 — engine validation may reject
                pass
        # Refresh the instruction label for this knob
        label = self._instruction_labels.get(knob_id)
        if label is not None:
            label.setText(self._compute_instruction(knob_id))
        # Bool needs to render as "true"/"false" for the CLI parser
        if isinstance(value, bool):
            value_str = "true" if value else "false"
        else:
            value_str = str(value)
        self._run(["set", knob_id, value_str])

    # ── Zone control ──────────────────────────────────────────────

    def _enter_zone_clicked(self):
        name = self.zone_combo.currentText().strip()
        if not name:
            self.output.setPlainText("Pick a zone first.")
            return
        self._run(["zone", name])
        if self._engine is not None:
            try:
                self._engine.enter_zone(name)
            except Exception:  # noqa: BLE001 — engine may reject unknown zone
                pass
        self._refresh_zone_indicator()

    def _exit_zone_clicked(self):
        self._run(["zone", "--exit"])
        if self._engine is not None:
            try:
                self._engine.exit_zone()
            except Exception:  # noqa: BLE001
                pass
        self._refresh_zone_indicator()

    def _refresh_zone_indicator(self):
        """Update the zone label from the in-memory engine state."""
        if self._engine is None:
            self.zone_label.setText("Zone: (no profile)")
            return
        zone = self._engine.active_zone
        if zone is None:
            self.zone_label.setText("Zone: (none)")
        else:
            self.zone_label.setText(f"Zone: {zone.name}")

    # ── Subprocess runner ─────────────────────────────────────────

    def _run(self, args: list[str]):
        self.output.setPlainText(f"$ tune {' '.join(args)}\n")
        text = _run_tune(args)
        self.output.appendPlainText(text)
