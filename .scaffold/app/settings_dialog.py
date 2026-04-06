"""Settings dialog — replaces the old settings page with a modal dialog (Ctrl+,)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QGridLayout,
    QDialogButtonBox,
)

from .settings_page import _load_settings, _save_settings, _SETTINGS_FILE


class SettingsDialog(QDialog):
    """Modal settings dialog. Reads/writes the same settings file as SettingsPage."""

    def __init__(self, bridge_client=None, parent=None):
        super().__init__(parent)
        self._bridge = bridge_client
        self._settings = _load_settings()
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._init_ui()
        self._load_into_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

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

        # ── Workspace ──
        workspace_box = QGroupBox("Workspace")
        workspace_layout = QVBoxLayout(workspace_box)

        self._show_debug = QCheckBox("Show Debug panel in sidebars")
        workspace_layout.addWidget(self._show_debug)

        self._show_tuning = QCheckBox("Show Tuning panel in sidebars")
        workspace_layout.addWidget(self._show_tuning)

        layout.addWidget(workspace_box)

        # ── Info ──
        info = QLabel(f"Settings file: {_SETTINGS_FILE}")
        info.setObjectName("dim")
        info.setWordWrap(True)
        layout.addWidget(info)

        # ── Buttons ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self._do_save)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._do_reset
        )
        layout.addWidget(buttons)

    def _load_into_ui(self):
        self._host_input.setText(self._settings["bridge_host"])
        self._port_input.setValue(self._settings["bridge_port"])
        self._auto_connect_cb.setChecked(self._settings["auto_connect"])
        self._imgui_path.setText(self._settings["imgui_binary"])
        self._bridge_path.setText(self._settings["bridge_script"])
        self._auto_bridge_cb.setChecked(self._settings["auto_launch_bridge"])
        self._show_debug.setChecked(self._settings.get("show_debug", True))
        self._show_tuning.setChecked(self._settings.get("show_tuning", True))

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
        }

    def _do_save(self):
        self._settings = self._read_from_ui()
        _save_settings(self._settings)
        if self._bridge:
            self._bridge.host = self._settings["bridge_host"]
            self._bridge.port = self._settings["bridge_port"]
        self.accept()

    def _do_reset(self):
        self._settings = _load_settings.__wrapped__() if hasattr(_load_settings, '__wrapped__') else {
            "bridge_host": "127.0.0.1",
            "bridge_port": 9876,
            "auto_connect": False,
            "imgui_binary": ".scaffold/imgui/build/terragraf_imgui",
            "bridge_script": ".scaffold/imgui/bridge.py",
            "auto_launch_bridge": False,
            "show_debug": True,
            "show_tuning": True,
        }
        self._load_into_ui()

    def get_settings(self) -> dict:
        return dict(self._settings)
