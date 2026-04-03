"""Tests for mode detection — CI vs App mode."""

import sys
import os
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modes.detector import (
    Mode,
    ModeInfo,
    detect,
    require_app,
    _check_explicit_env,
    _check_ci_env,
    _has_display,
    _CI_CAPABILITIES,
    _APP_CAPABILITIES,
    _CI_BLOCKED_SYSTEMS,
)


# ── Mode Enum ──────────────────────────────────────────────────────────

class TestModeEnum:
    def test_ci_value(self):
        assert Mode.CI.value == "ci"

    def test_app_value(self):
        assert Mode.APP.value == "app"

    def test_from_string(self):
        assert Mode("ci") == Mode.CI
        assert Mode("app") == Mode.APP


# ── ModeInfo ───────────────────────────────────────────────────────────

class TestModeInfo:
    def test_is_ci(self):
        info = ModeInfo(mode=Mode.CI, source="test", capabilities=_CI_CAPABILITIES, blocked=_CI_BLOCKED_SYSTEMS)
        assert info.is_ci is True
        assert info.is_app is False

    def test_is_app(self):
        info = ModeInfo(mode=Mode.APP, source="test", capabilities=_APP_CAPABILITIES, blocked=frozenset())
        assert info.is_ci is False
        assert info.is_app is True

    def test_can_ci(self):
        info = ModeInfo(mode=Mode.CI, source="test", capabilities=_CI_CAPABILITIES, blocked=_CI_BLOCKED_SYSTEMS)
        assert info.can("tests") is True
        assert info.can("lint") is True
        assert info.can("math") is True
        assert info.can("gui") is False
        assert info.can("qt_app") is False
        assert info.can("imgui") is False

    def test_can_app(self):
        info = ModeInfo(mode=Mode.APP, source="test", capabilities=_APP_CAPABILITIES, blocked=frozenset())
        assert info.can("tests") is True
        assert info.can("gui") is True
        assert info.can("qt_app") is True
        assert info.can("imgui") is True

    def test_blocked_reason_ci(self):
        info = ModeInfo(mode=Mode.CI, source="test", capabilities=_CI_CAPABILITIES, blocked=_CI_BLOCKED_SYSTEMS)
        assert info.blocked_reason("gui") is not None
        assert "ci mode" in info.blocked_reason("gui")
        assert info.blocked_reason("tests") is None

    def test_blocked_reason_app(self):
        info = ModeInfo(mode=Mode.APP, source="test", capabilities=_APP_CAPABILITIES, blocked=frozenset())
        assert info.blocked_reason("gui") is None
        assert info.blocked_reason("anything") is None

    def test_frozen(self):
        info = ModeInfo(mode=Mode.CI, source="test")
        with pytest.raises(AttributeError):
            info.mode = Mode.APP


# ── Capability Sets ────────────────────────────────────────────────────

class TestCapabilitySets:
    def test_ci_is_subset_of_app(self):
        assert _CI_CAPABILITIES.issubset(_APP_CAPABILITIES)

    def test_blocked_not_in_ci_capabilities(self):
        assert _CI_BLOCKED_SYSTEMS.isdisjoint(_CI_CAPABILITIES)

    def test_blocked_in_app_capabilities(self):
        assert _CI_BLOCKED_SYSTEMS.issubset(_APP_CAPABILITIES)

    def test_ci_has_core_capabilities(self):
        for cap in ("tests", "lint", "generators", "routes", "tables", "math", "sharpen"):
            assert cap in _CI_CAPABILITIES

    def test_app_has_gui_capabilities(self):
        for cap in ("gui", "qt_app", "imgui", "bridge", "vulkan"):
            assert cap in _APP_CAPABILITIES


# ── Explicit Env Check ─────────────────────────────────────────────────

class TestExplicitEnv:
    def test_ci(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "ci"}):
            assert _check_explicit_env() == Mode.CI

    def test_app(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "app"}):
            assert _check_explicit_env() == Mode.APP

    def test_ci_uppercase(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "CI"}):
            assert _check_explicit_env() == Mode.CI

    def test_app_mixed_case(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "App"}):
            assert _check_explicit_env() == Mode.APP

    def test_empty(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": ""}):
            assert _check_explicit_env() is None

    def test_missing(self):
        env = os.environ.copy()
        env.pop("TERRAGRAF_MODE", None)
        with patch.dict(os.environ, env, clear=True):
            assert _check_explicit_env() is None

    def test_invalid_value(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "debug"}):
            assert _check_explicit_env() is None


# ── CI Env Check ───────────────────────────────────────────────────────

class TestCIEnvCheck:
    def test_github_actions(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            assert _check_ci_env() == "GITHUB_ACTIONS"

    def test_generic_ci(self):
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            assert _check_ci_env() == "CI"

    def test_gitlab(self):
        with patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=True):
            assert _check_ci_env() == "GITLAB_CI"

    def test_jenkins(self):
        with patch.dict(os.environ, {"JENKINS_URL": "http://localhost:8080"}, clear=True):
            assert _check_ci_env() == "JENKINS_URL"

    def test_none_set(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _check_ci_env() is None


# ── Display Check ──────────────────────────────────────────────────────

class TestHasDisplay:
    def test_x11_display(self):
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            assert _has_display() is True

    def test_wayland_display(self):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=True):
            assert _has_display() is True

    def test_offscreen(self):
        with patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"}, clear=True):
            if os.name != "nt":
                assert _has_display() is False

    def test_no_display(self):
        with patch.dict(os.environ, {}, clear=True):
            if os.name != "nt":
                assert _has_display() is False


# ── Full Detection ─────────────────────────────────────────────────────

class TestDetect:
    def test_explicit_ci(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "ci"}):
            info = detect()
            assert info.is_ci
            assert info.source == "TERRAGRAF_MODE=ci"
            assert info.can("tests")
            assert not info.can("gui")

    def test_explicit_app(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "app"}):
            info = detect()
            assert info.is_app
            assert info.source == "TERRAGRAF_MODE=app"
            assert info.can("gui")
            assert len(info.blocked) == 0

    def test_explicit_overrides_ci_env(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "app", "CI": "true", "GITHUB_ACTIONS": "true"}):
            info = detect()
            assert info.is_app
            assert info.source == "TERRAGRAF_MODE=app"

    def test_github_actions_detected(self):
        env = {"GITHUB_ACTIONS": "true", "CI": "true"}
        with patch.dict(os.environ, env, clear=True):
            info = detect()
            assert info.is_ci
            assert "CI" in info.source or "GITHUB_ACTIONS" in info.source

    def test_no_display_means_ci(self):
        with patch.dict(os.environ, {}, clear=True):
            if os.name != "nt":
                info = detect()
                assert info.is_ci
                assert "display" in info.source.lower()

    def test_display_means_app(self):
        env = {"DISPLAY": ":0"}
        with patch.dict(os.environ, env, clear=True):
            info = detect()
            assert info.is_app


# ── require_app Guard ──────────────────────────────────────────────────

class TestRequireApp:
    def test_raises_in_ci(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "ci"}):
            with pytest.raises(RuntimeError, match="qt_app.*ci mode"):
                require_app("qt_app")

    def test_passes_in_app(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "app"}):
            require_app("qt_app")  # should not raise

    def test_raises_for_gui(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "ci"}):
            with pytest.raises(RuntimeError):
                require_app("gui")

    def test_non_blocked_passes_in_ci(self):
        with patch.dict(os.environ, {"TERRAGRAF_MODE": "ci"}):
            require_app("tests")  # tests aren't blocked, should not raise
