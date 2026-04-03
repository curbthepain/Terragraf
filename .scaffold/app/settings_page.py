"""Settings page — bridge config, paths, panel toggles."""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QFrame,
)

from . import theme

_SETTINGS_FILE = Path(__file__).parent.parent.parent / ".terragraf_settings.json"


def _load_settings() -> dict:
    defaults = {
        "bridge_host": "127.0.0.1",
        "bridge_port": 9876,
        "auto_connect": False,
        "imgui_binary": ".scaffold/imgui/build/terragraf_imgui",
        "bridge_script": ".scaffold/imgui/bridge.py",
        "auto_launch_bridge": False,
        "show_debug": True,
        "show_tuning": True,
        "show_viewer": True,
    }
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE) as f:
                saved = json.load(f)
            defaults.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


def _save_settings(data: dict):
    try:
        with open(_SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


class SettingsPage(QWidget):
    """Application settings with persistence."""

    def __init__(self, bridge_client, parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._settings = _load_settings()
        self._init_ui()
        self._load_into_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("Settings")
        header.setObjectName("section_header")
        layout.addWidget(header)

        # ── Bridge connection ──
        bridge_box = QGroupBox("Bridge Connection")
        bridge_layout = QGridLayout(bridge_box)

        bridge_layout.addWidget(QLabel("Host:"), 0, 0)
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("127.0.0.1")
        bridge_layout.addWidget(self._host_input, 0, 1)

        bridge_layout.addWidget(QLabel("Port:"), 1, 0)
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        bridge_layout.addWidget(self._port_input, 1, 1)

        self._auto_connect_cb = QCheckBox("Auto-connect on startup")
        bridge_layout.addWidget(self._auto_connect_cb, 2, 0, 1, 2)

        layout.addWidget(bridge_box)

        # ── Paths ──
        paths_box = QGroupBox("Paths")
        paths_layout = QGridLayout(paths_box)

        paths_layout.addWidget(QLabel("ImGui binary:"), 0, 0)
        self._imgui_path = QLineEdit()
        paths_layout.addWidget(self._imgui_path, 0, 1)

        paths_layout.addWidget(QLabel("Bridge script:"), 1, 0)
        self._bridge_path = QLineEdit()
        paths_layout.addWidget(self._bridge_path, 1, 1)

        self._auto_bridge_cb = QCheckBox("Auto-launch bridge on startup")
        paths_layout.addWidget(self._auto_bridge_cb, 2, 0, 1, 2)

        layout.addWidget(paths_box)

        # ── Panel visibility ──
        panels_box = QGroupBox("Panel Visibility")
        panels_layout = QVBoxLayout(panels_box)

        self._show_debug = QCheckBox("Show Debug page")
        panels_layout.addWidget(self._show_debug)

        self._show_tuning = QCheckBox("Show Tuning page")
        panels_layout.addWidget(self._show_tuning)

        self._show_viewer = QCheckBox("Show Viewer page")
        panels_layout.addWidget(self._show_viewer)

        layout.addWidget(panels_box)

        # ── Actions ──
        btn_row = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._do_save)
        btn_row.addWidget(save_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._do_apply)
        btn_row.addWidget(apply_btn)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("danger")
        reset_btn.clicked.connect(self._do_reset)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Info ──
        info_box = QGroupBox("About")
        info_layout = QVBoxLayout(info_box)
        info = QLabel(
            "Terragraf — scaffolding system\n"
            "Qt container + ImGui viewer + Python bridge\n\n"
            f"Settings file: {_SETTINGS_FILE}"
        )
        info.setObjectName("mono")
        info.setWordWrap(True)
        info_layout.addWidget(info)
        layout.addWidget(info_box)

        layout.addStretch()

    def _load_into_ui(self):
        self._host_input.setText(self._settings["bridge_host"])
        self._port_input.setValue(self._settings["bridge_port"])
        self._auto_connect_cb.setChecked(self._settings["auto_connect"])
        self._imgui_path.setText(self._settings["imgui_binary"])
        self._bridge_path.setText(self._settings["bridge_script"])
        self._auto_bridge_cb.setChecked(self._settings["auto_launch_bridge"])
        self._show_debug.setChecked(self._settings["show_debug"])
        self._show_tuning.setChecked(self._settings["show_tuning"])
        self._show_viewer.setChecked(self._settings["show_viewer"])

    def _read_from_ui(self) -> dict:
        return {
            "bridge_host": self._host_input.text().strip() or "127.0.0.1",
            "bridge_port": self._port_input.value(),
            "auto_connect": self._auto_connect_cb.isChecked(),
            "imgui_binary": self._imgui_path.text().strip(),
            "bridge_script": self._bridge_path.text().strip(),
            "auto_launch_bridge": self._auto_bridge_cb.isChecked(),
            "show_debug": self._show_debug.isChecked(),
            "show_tuning": self._show_tuning.isChecked(),
            "show_viewer": self._show_viewer.isChecked(),
        }

    def _do_save(self):
        self._settings = self._read_from_ui()
        _save_settings(self._settings)
        self._do_apply()

    def _do_apply(self):
        data = self._read_from_ui()
        self._bridge.host = data["bridge_host"]
        self._bridge.port = data["bridge_port"]

    def _do_reset(self):
        self._settings = {
            "bridge_host": "127.0.0.1",
            "bridge_port": 9876,
            "auto_connect": False,
            "imgui_binary": ".scaffold/imgui/build/terragraf_imgui",
            "bridge_script": ".scaffold/imgui/bridge.py",
            "auto_launch_bridge": False,
            "show_debug": True,
            "show_tuning": True,
            "show_viewer": True,
        }
        self._load_into_ui()

    def get_settings(self) -> dict:
        return dict(self._settings)
