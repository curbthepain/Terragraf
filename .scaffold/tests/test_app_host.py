"""Tests for the modular IDE host system (app_host + ide_host_page)."""

import os
import sys
import socket
import textwrap
from pathlib import Path

import pytest

# Ensure .scaffold is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.app_host import IDEManifest, AppHostManager

# Check PySide6 availability
try:
    import PySide6
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

needs_qt = pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not installed")


# ── Fixtures ──────────────────────────────────────────────────────────

def _write_toml(tmp_path, name, content):
    """Helper — write an app.toml into tmp_path/name/app.toml."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "app.toml").write_text(textwrap.dedent(content))
    return d


MINIMAL_TOML = """\
[ide]
name = "TestIDE"
version = "1.0"
description = "A test IDE"
license = "MIT"

[ide.display]
label = "Test"
shortcut = "Ctrl+9"

[ide.launch]
type = "webview"
command = "fake-ide-server --port {port}"
port_range = [19000, 19010]
startup_delay = 1
health_check = "http://127.0.0.1:{port}/"
"""

PROCESS_TOML = """\
[ide]
name = "NativeIDE"
version = "2.0"
description = "A native IDE"
license = "Apache-2.0"

[ide.display]
label = "Native"

[ide.launch]
type = "process"
command = "native-ide"
port_range = [19100, 19110]
"""

BARE_TOML = """\
[ide]
name = "Bare"
"""


# ── IDEManifest tests ─────────────────────────────────────────────────

class TestIDEManifest:
    def test_parse_full_manifest(self, tmp_path):
        d = _write_toml(tmp_path, "testide", MINIMAL_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        assert m.name == "TestIDE"
        assert m.version == "1.0"
        assert m.description == "A test IDE"
        assert m.license == "MIT"
        assert m.label == "Test"
        assert m.shortcut == "Ctrl+9"
        assert m.launch_type == "webview"
        assert "{port}" in m.command
        assert m.port_range == (19000, 19010)
        assert m.startup_delay == 1
        assert "{port}" in m.health_check
        assert m.app_dir == d.resolve()

    def test_parse_process_manifest(self, tmp_path):
        d = _write_toml(tmp_path, "native", PROCESS_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        assert m.name == "NativeIDE"
        assert m.launch_type == "process"
        assert m.license == "Apache-2.0"

    def test_defaults_for_missing_fields(self, tmp_path):
        d = _write_toml(tmp_path, "bare", BARE_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        assert m.name == "Bare"
        assert m.version == "0.0"
        assert m.description == ""
        assert m.license == "unknown"
        assert m.label == "Bare"
        assert m.shortcut == ""
        assert m.launch_type == "process"
        assert m.command == ""
        assert m.fallback_command == ""
        assert m.port_range == (9100, 9199)
        assert m.startup_delay == 3
        assert m.health_check == ""
        assert m.workspace == ""
        assert m.env == {}

    def test_env_vars_parsed(self, tmp_path):
        toml = MINIMAL_TOML + '\n[ide.launch.env]\nFOO = "bar"\nNUM = "42"\n'
        d = _write_toml(tmp_path, "envtest", toml)
        m = IDEManifest.from_toml(d / "app.toml")
        assert m.env == {"FOO": "bar", "NUM": "42"}

    def test_label_falls_back_to_name(self, tmp_path):
        toml = '[ide]\nname = "FallbackTest"\n'
        d = _write_toml(tmp_path, "fb", toml)
        m = IDEManifest.from_toml(d / "app.toml")
        assert m.label == "FallbackTest"

    def test_label_falls_back_to_dirname(self, tmp_path):
        toml = "[ide]\n"
        d = _write_toml(tmp_path, "mydir", toml)
        m = IDEManifest.from_toml(d / "app.toml")
        assert m.label == "mydir"
        assert m.name == "mydir"


# ── AppHostManager tests ─────────────────────────────────────────────

class TestAppHostManager:
    def test_scan_discovers_manifests(self, tmp_path):
        _write_toml(tmp_path, "alpha", MINIMAL_TOML)
        _write_toml(tmp_path, "beta", PROCESS_TOML)
        mgr = AppHostManager(apps_dir=tmp_path)
        assert "alpha" in mgr.manifests
        assert "beta" in mgr.manifests
        assert mgr.manifests["alpha"].name == "TestIDE"
        assert mgr.manifests["beta"].name == "NativeIDE"

    def test_scan_ignores_files(self, tmp_path):
        (tmp_path / "README").write_text("not an IDE")
        mgr = AppHostManager(apps_dir=tmp_path)
        assert len(mgr.manifests) == 0

    def test_scan_ignores_dirs_without_manifest(self, tmp_path):
        (tmp_path / "noide").mkdir()
        mgr = AppHostManager(apps_dir=tmp_path)
        assert len(mgr.manifests) == 0

    def test_scan_handles_missing_dir(self, tmp_path):
        mgr = AppHostManager(apps_dir=tmp_path / "nonexistent")
        assert len(mgr.manifests) == 0

    def test_scan_skips_bad_toml(self, tmp_path):
        d = tmp_path / "bad"
        d.mkdir()
        (d / "app.toml").write_text("this is not valid toml {{{{")
        mgr = AppHostManager(apps_dir=tmp_path)
        assert "bad" not in mgr.manifests

    def test_rescan_updates(self, tmp_path):
        mgr = AppHostManager(apps_dir=tmp_path)
        assert len(mgr.manifests) == 0
        _write_toml(tmp_path, "late", MINIMAL_TOML)
        mgr.scan()
        assert "late" in mgr.manifests

    def test_manifests_returns_copy(self, tmp_path):
        _write_toml(tmp_path, "x", MINIMAL_TOML)
        mgr = AppHostManager(apps_dir=tmp_path)
        m1 = mgr.manifests
        m1.pop("x")
        assert "x" in mgr.manifests  # original unchanged

    def test_apps_dir_property(self, tmp_path):
        mgr = AppHostManager(apps_dir=tmp_path)
        assert mgr.apps_dir == tmp_path

    def test_find_free_port_returns_port(self):
        port = AppHostManager.find_free_port(49100, 49110)
        assert port is not None
        assert 49100 <= port <= 49110

    def test_find_free_port_skips_occupied(self):
        """Occupy a port and verify find_free_port skips it."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 49200))
        try:
            port = AppHostManager.find_free_port(49200, 49205)
            assert port is not None
            assert port != 49200
        finally:
            s.close()

    def test_find_free_port_returns_none_when_exhausted(self):
        """All ports in range occupied → returns None."""
        sockets = []
        try:
            for p in range(49300, 49303):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(("127.0.0.1", p))
                sockets.append(s)
            result = AppHostManager.find_free_port(49300, 49302)
            assert result is None
        finally:
            for s in sockets:
                s.close()

    def test_resolve_command_system_path(self, tmp_path):
        """resolve_command finds programs on the system PATH."""
        _write_toml(tmp_path, "pyide", """\
[ide]
name = "PyIDE"
[ide.launch]
command = "python3 --version"
port_range = [19000, 19010]
""")
        mgr = AppHostManager(apps_dir=tmp_path)
        m = mgr.manifests["pyide"]
        result = mgr.resolve_command(m, 19000)
        assert result is not None
        prog, args = result
        assert "python3" in prog or "python" in prog

    def test_resolve_command_local_bin(self, tmp_path):
        """resolve_command prefers a local binary inside the app dir."""
        d = _write_toml(tmp_path, "localide", MINIMAL_TOML)
        bin_dir = d / "bin"
        bin_dir.mkdir()
        fake_bin = bin_dir / "fake-ide-server"
        fake_bin.write_text("#!/bin/sh\necho hi\n")
        fake_bin.chmod(0o755)

        # Rewrite command to use relative bin/ path
        toml_with_local = MINIMAL_TOML.replace(
            'command = "fake-ide-server', 'command = "bin/fake-ide-server'
        )
        (d / "app.toml").write_text(textwrap.dedent(toml_with_local))

        mgr = AppHostManager(apps_dir=tmp_path)
        m = mgr.manifests["localide"]
        result = mgr.resolve_command(m, 19000)
        assert result is not None
        prog, args = result
        assert "fake-ide-server" in prog

    def test_resolve_command_returns_none(self, tmp_path):
        """resolve_command returns None when no binary exists."""
        _write_toml(tmp_path, "missing", MINIMAL_TOML)
        mgr = AppHostManager(apps_dir=tmp_path)
        m = mgr.manifests["missing"]
        result = mgr.resolve_command(m, 19000)
        assert result is None

    def test_resolve_command_port_substitution(self, tmp_path):
        """Port placeholder is replaced in args."""
        _write_toml(tmp_path, "porttest", """\
[ide]
name = "PortTest"
[ide.launch]
command = "python3 -c pass --port {port}"
port_range = [19500, 19510]
""")
        mgr = AppHostManager(apps_dir=tmp_path)
        m = mgr.manifests["porttest"]
        result = mgr.resolve_command(m, 19505)
        assert result is not None
        _, args = result
        assert "19505" in " ".join(args)

    def test_resolve_command_tries_fallback(self, tmp_path):
        """Falls back to fallback_command when command binary missing."""
        _write_toml(tmp_path, "fbtest", """\
[ide]
name = "FBTest"
[ide.launch]
command = "nonexistent-binary-xyz"
fallback_command = "python3 --version"
port_range = [19000, 19010]
""")
        mgr = AppHostManager(apps_dir=tmp_path)
        m = mgr.manifests["fbtest"]
        result = mgr.resolve_command(m, 19000)
        assert result is not None
        prog, _ = result
        assert "python3" in prog or "python" in prog


# ── Real Void manifest test ───────────────────────────────────────────

class TestVoidManifest:
    def test_void_manifest_parses(self):
        """The shipped void/app.toml parses correctly."""
        void_toml = Path(__file__).resolve().parent.parent / "apps" / "void" / "app.toml"
        if not void_toml.exists():
            pytest.skip("void/app.toml not present")
        m = IDEManifest.from_toml(void_toml)
        assert m.name == "Void"
        assert m.launch_type == "webview"
        assert m.license == "MIT"
        assert "{port}" in m.command
        assert "{port}" in m.health_check
        assert m.port_range[0] < m.port_range[1]

    def test_void_discovered_by_manager(self):
        """AppHostManager finds the shipped void IDE."""
        apps_dir = Path(__file__).resolve().parent.parent / "apps"
        if not (apps_dir / "void" / "app.toml").exists():
            pytest.skip("void/app.toml not present")
        mgr = AppHostManager(apps_dir=apps_dir)
        assert "void" in mgr.manifests
        assert mgr.manifests["void"].label == "Void"


# ── IDEHostPage import & construction tests ───────────────────────────

@needs_qt
class TestIDEHostPage:
    def test_import(self):
        from app.ide_host_page import IDEHostPage
        assert IDEHostPage is not None

    def test_manifest_property(self, tmp_path):
        from app.ide_host_page import IDEHostPage
        d = _write_toml(tmp_path, "prop", MINIMAL_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        mgr = AppHostManager(apps_dir=tmp_path)
        page = IDEHostPage(m, mgr)
        assert page.manifest is m
        assert page.manifest.name == "TestIDE"

    def test_cleanup_is_safe_when_not_started(self, tmp_path):
        from app.ide_host_page import IDEHostPage
        d = _write_toml(tmp_path, "safe", MINIMAL_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        mgr = AppHostManager(apps_dir=tmp_path)
        page = IDEHostPage(m, mgr)
        page.cleanup()  # should not raise

    def test_on_page_shown_is_safe(self, tmp_path):
        from app.ide_host_page import IDEHostPage
        d = _write_toml(tmp_path, "shown", MINIMAL_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        mgr = AppHostManager(apps_dir=tmp_path)
        page = IDEHostPage(m, mgr)
        page.on_page_shown()  # should not raise

    def test_webview_type_has_ready_label(self, tmp_path):
        from app.ide_host_page import IDEHostPage
        d = _write_toml(tmp_path, "wv", MINIMAL_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        mgr = AppHostManager(apps_dir=tmp_path)
        page = IDEHostPage(m, mgr)
        assert hasattr(page, "_ready_label")
        assert page._ready_label.text() == "Not started"

    def test_process_type_no_ready_label(self, tmp_path):
        from app.ide_host_page import IDEHostPage
        d = _write_toml(tmp_path, "proc", PROCESS_TOML)
        m = IDEManifest.from_toml(d / "app.toml")
        mgr = AppHostManager(apps_dir=tmp_path)
        page = IDEHostPage(m, mgr)
        assert not hasattr(page, "_ready_label")
