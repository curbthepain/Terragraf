"""Tuning page — Qt-native thematic calibration controls via bridge."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QComboBox,
    QSlider,
    QLineEdit,
    QCheckBox,
    QPlainTextEdit,
    QScrollArea,
    QFrame,
    QGridLayout,
    QSizePolicy,
)

from . import theme


class TuningPage(QWidget):
    """Qt-native tuning panel that mirrors the ImGui tuning_panel via bridge."""

    def __init__(self, bridge_client, parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._profiles = []
        self._active_profile = None
        self._zones = []
        self._active_zone = None
        self._knobs = {}          # {domain: [knob_data, ...]}
        self._knob_widgets = {}   # {knob_id: widget}
        self._instructions = ""

        self._init_ui()
        self._register_handlers()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("Thematic Calibration")
        header.setObjectName("section_header")
        layout.addWidget(header)

        # ── Profile selector ──
        profile_box = QGroupBox("Universe Profile")
        profile_layout = QHBoxLayout(profile_box)

        self._profile_combo = QComboBox()
        self._profile_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        profile_layout.addWidget(self._profile_combo)

        self._load_btn = QPushButton("Load")
        self._load_btn.setObjectName("primary")
        self._load_btn.clicked.connect(self._do_load_profile)
        profile_layout.addWidget(self._load_btn)

        self._refresh_btn = QPushButton("Refresh List")
        self._refresh_btn.clicked.connect(self._do_request_profiles)
        profile_layout.addWidget(self._refresh_btn)

        layout.addWidget(profile_box)

        # ── Profile metadata ──
        self._meta_box = QGroupBox("Profile Info")
        meta_layout = QGridLayout(self._meta_box)

        self._meta_name = QLabel("—")
        self._meta_name.setObjectName("section_header")
        meta_layout.addWidget(self._meta_name, 0, 0, 1, 2)

        self._meta_genre = QLabel("")
        self._meta_genre.setObjectName("dim")
        meta_layout.addWidget(self._meta_genre, 1, 0, 1, 2)

        self._meta_desc = QLabel("")
        self._meta_desc.setWordWrap(True)
        meta_layout.addWidget(self._meta_desc, 2, 0, 1, 2)

        self._meta_promise = QLabel("")
        self._meta_promise.setWordWrap(True)
        self._meta_promise.setObjectName("mono")
        meta_layout.addWidget(QLabel("Promise:"), 3, 0)
        meta_layout.addWidget(self._meta_promise, 3, 1)

        # Axes
        self._axes_labels = {}
        for i, axis in enumerate(["mortality_weight", "power_fantasy", "shitpost_tolerance"]):
            label = QLabel(axis.replace("_", " ").title() + ":")
            val = QLabel("—")
            val.setObjectName("mono")
            meta_layout.addWidget(label, 4 + i, 0)
            meta_layout.addWidget(val, 4 + i, 1)
            self._axes_labels[axis] = val

        self._meta_box.setVisible(False)
        layout.addWidget(self._meta_box)

        # ── Zone selector ──
        self._zone_box = QGroupBox("Zones")
        self._zone_layout = QHBoxLayout(self._zone_box)

        self._zone_btns = []
        self._exit_zone_btn = QPushButton("Exit Zone")
        self._exit_zone_btn.setObjectName("danger")
        self._exit_zone_btn.clicked.connect(self._do_exit_zone)
        self._exit_zone_btn.setEnabled(False)

        self._zone_box.setVisible(False)
        layout.addWidget(self._zone_box)

        # ── Knobs (scrollable) ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._knobs_container = QWidget()
        self._knobs_layout = QVBoxLayout(self._knobs_container)
        self._knobs_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._knobs_container)
        layout.addWidget(scroll, stretch=1)

        # ── Reset + Instructions ──
        bottom = QHBoxLayout()
        self._reset_btn = QPushButton("Reset All Knobs")
        self._reset_btn.clicked.connect(self._do_reset_knobs)
        self._reset_btn.setEnabled(False)
        bottom.addWidget(self._reset_btn)

        self._instr_btn = QPushButton("Refresh Instructions")
        self._instr_btn.clicked.connect(self._do_get_instructions)
        self._instr_btn.setEnabled(False)
        bottom.addWidget(self._instr_btn)
        bottom.addStretch()
        layout.addLayout(bottom)

        self._instructions_box = QGroupBox("Behavioral Instructions")
        instr_layout = QVBoxLayout(self._instructions_box)
        self._instructions_view = QPlainTextEdit()
        self._instructions_view.setReadOnly(True)
        self._instructions_view.setMinimumHeight(100)
        instr_layout.addWidget(self._instructions_view)
        self._instructions_box.setVisible(False)
        layout.addWidget(self._instructions_box)

    # ── Bridge handlers ─────────────────────────────────────────────

    def _register_handlers(self):
        self._bridge.on("tune_profiles", self._handle_profiles)
        self._bridge.on("tune_profile_data", self._handle_profile_data)
        self._bridge.on("tune_state_update", self._handle_state_update)
        self._bridge.on("tune_instructions", self._handle_instructions)

    def _handle_profiles(self, msg):
        data = msg.get("data", {})
        self._profiles = data.get("profiles", [])
        self._profile_combo.clear()
        for name in self._profiles:
            self._profile_combo.addItem(name)

    def _handle_profile_data(self, msg):
        data = msg.get("data", msg)
        self._active_profile = data

        # Metadata
        self._meta_name.setText(data.get("name", ""))
        self._meta_genre.setText(data.get("genre", ""))
        self._meta_desc.setText(data.get("description", ""))
        self._meta_promise.setText(data.get("thematic_promise", ""))
        self._meta_box.setVisible(True)

        # Axes
        for axis, label in self._axes_labels.items():
            val = data.get(axis, "—")
            if isinstance(val, (int, float)):
                label.setText(f"{val:.2f}")
            else:
                label.setText(str(val))

        # Zones
        self._zones = data.get("zones", [])
        self._rebuild_zone_buttons()
        self._zone_box.setVisible(len(self._zones) > 0)

        # Knobs
        self._build_knob_widgets(data.get("knobs", []))

        # Instructions
        instr = data.get("instructions", "")
        if instr:
            self._instructions_view.setPlainText(instr)
            self._instructions_box.setVisible(True)

        self._reset_btn.setEnabled(True)
        self._instr_btn.setEnabled(True)

    def _handle_state_update(self, msg):
        data = msg.get("data", {})

        # Update axes
        axes = data.get("axes", {})
        for axis, label in self._axes_labels.items():
            val = axes.get(axis)
            if val is not None:
                label.setText(f"{val:.2f}" if isinstance(val, (int, float)) else str(val))

        # Update active zone
        self._active_zone = data.get("zone")
        self._update_zone_highlight()

        # Update knob values
        knob_state = data.get("knobs", {})
        for knob_id, value in knob_state.items():
            widget = self._knob_widgets.get(knob_id)
            if widget and hasattr(widget, 'set_value'):
                widget.set_value(value)

        # Update instructions
        instr = data.get("instructions", "")
        if instr:
            self._instructions_view.setPlainText(instr)
            self._instructions_box.setVisible(True)

    def _handle_instructions(self, msg):
        data = msg.get("data", {})
        text = data.get("text", "")
        self._instructions_view.setPlainText(text)
        self._instructions_box.setVisible(bool(text))

    # ── Actions ─────────────────────────────────────────────────────

    def _do_request_profiles(self):
        self._bridge.send("tune_list")

    def _do_load_profile(self):
        name = self._profile_combo.currentText()
        if name:
            self._bridge.send("tune_load", {"name": name})

    def _do_enter_zone(self, zone_name):
        self._bridge.send("tune_zone", {"zone": zone_name})

    def _do_exit_zone(self):
        self._bridge.send("tune_zone_exit")

    def _do_reset_knobs(self):
        self._bridge.send("tune_reset_knobs")

    def _do_get_instructions(self):
        self._bridge.send("tune_get_instructions")

    def _do_set_knob(self, knob_id, value):
        self._bridge.send("tune_set_knob", {"id": knob_id, "value": value})

    # ── Zone UI ─────────────────────────────────────────────────────

    def _rebuild_zone_buttons(self):
        # Clear existing
        for btn in self._zone_btns:
            self._zone_layout.removeWidget(btn)
            btn.deleteLater()
        self._zone_btns.clear()

        for zone in self._zones:
            name = zone["name"] if isinstance(zone, dict) else zone
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, n=name: self._do_enter_zone(n))
            self._zone_layout.addWidget(btn)
            self._zone_btns.append(btn)

        self._zone_layout.addWidget(self._exit_zone_btn)
        self._zone_layout.addStretch()

    def _update_zone_highlight(self):
        for btn in self._zone_btns:
            is_active = (btn.text() == self._active_zone)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._exit_zone_btn.setEnabled(self._active_zone is not None)

    # ── Knob UI ─────────────────────────────────────────────────────

    def _build_knob_widgets(self, knobs):
        # Clear existing
        self._knob_widgets.clear()
        while self._knobs_layout.count():
            item = self._knobs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Group by domain
        domains = {}
        for k in knobs:
            domain = k.get("domain", "general")
            domains.setdefault(domain, []).append(k)

        for domain, domain_knobs in domains.items():
            group = QGroupBox(domain.replace("_", " ").title())
            group_layout = QVBoxLayout(group)

            for k in domain_knobs:
                row = QHBoxLayout()
                label = QLabel(k.get("label", k.get("id", "")))
                label.setMinimumWidth(140)
                label.setToolTip(k.get("description", ""))
                row.addWidget(label)

                knob_type = k.get("knob_type", "slider")
                knob_id = k.get("id", "")

                if knob_type == "slider":
                    widget = _SliderKnob(k, self._do_set_knob)
                elif knob_type == "dropdown":
                    widget = _DropdownKnob(k, self._do_set_knob)
                elif knob_type == "toggle":
                    widget = _ToggleKnob(k, self._do_set_knob)
                elif knob_type == "text":
                    widget = _TextKnob(k, self._do_set_knob)
                else:
                    widget = QLabel(f"[{knob_type}]")
                    widget.set_value = lambda v: None

                row.addWidget(widget, stretch=1)
                group_layout.addLayout(row)
                self._knob_widgets[knob_id] = widget

            self._knobs_layout.addWidget(group)

    def on_page_shown(self):
        """Called when page becomes visible — request profile list."""
        if self._bridge.connected and not self._profiles:
            self._do_request_profiles()


# ── Knob widgets ────────────────────────────────────────────────────

class _SliderKnob(QWidget):
    def __init__(self, knob_data, on_change, parent=None):
        super().__init__(parent)
        self._id = knob_data["id"]
        self._on_change = on_change
        self._min = knob_data.get("min_val", 0.0)
        self._max = knob_data.get("max_val", 1.0)
        self._step = knob_data.get("step", 0.01)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        initial = knob_data.get("value", knob_data.get("default", self._min))
        self._slider.setValue(self._val_to_pos(initial))
        self._slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self._slider, stretch=1)

        self._label = QLabel(f"{initial:.2f}")
        self._label.setFixedWidth(50)
        self._label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._label.setObjectName("mono")
        layout.addWidget(self._label)

    def _val_to_pos(self, val):
        if self._max == self._min:
            return 0
        return int((val - self._min) / (self._max - self._min) * 1000)

    def _pos_to_val(self, pos):
        return self._min + (pos / 1000.0) * (self._max - self._min)

    def _on_slider(self, pos):
        val = self._pos_to_val(pos)
        self._label.setText(f"{val:.2f}")
        self._on_change(self._id, val)

    def set_value(self, val):
        self._slider.blockSignals(True)
        self._slider.setValue(self._val_to_pos(float(val)))
        self._label.setText(f"{float(val):.2f}")
        self._slider.blockSignals(False)


class _DropdownKnob(QWidget):
    def __init__(self, knob_data, on_change, parent=None):
        super().__init__(parent)
        self._id = knob_data["id"]
        self._on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._combo = QComboBox()
        for opt in knob_data.get("options", []):
            self._combo.addItem(str(opt))

        current = knob_data.get("value", knob_data.get("default", ""))
        idx = self._combo.findText(str(current))
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

        self._combo.currentTextChanged.connect(
            lambda text: self._on_change(self._id, text)
        )
        layout.addWidget(self._combo, stretch=1)

    def set_value(self, val):
        self._combo.blockSignals(True)
        idx = self._combo.findText(str(val))
        if idx >= 0:
            self._combo.setCurrentIndex(idx)
        self._combo.blockSignals(False)


class _ToggleKnob(QWidget):
    def __init__(self, knob_data, on_change, parent=None):
        super().__init__(parent)
        self._id = knob_data["id"]
        self._on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._cb = QCheckBox()
        self._cb.setChecked(bool(knob_data.get("value", knob_data.get("default", False))))
        self._cb.toggled.connect(lambda v: self._on_change(self._id, v))
        layout.addWidget(self._cb)

    def set_value(self, val):
        self._cb.blockSignals(True)
        self._cb.setChecked(bool(val))
        self._cb.blockSignals(False)


class _TextKnob(QWidget):
    def __init__(self, knob_data, on_change, parent=None):
        super().__init__(parent)
        self._id = knob_data["id"]
        self._on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._input = QLineEdit()
        self._input.setMaxLength(knob_data.get("max_length", 256))
        self._input.setText(str(knob_data.get("value", knob_data.get("default", ""))))
        self._input.editingFinished.connect(
            lambda: self._on_change(self._id, self._input.text())
        )
        layout.addWidget(self._input, stretch=1)

    def set_value(self, val):
        self._input.blockSignals(True)
        self._input.setText(str(val))
        self._input.blockSignals(False)
