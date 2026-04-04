"""
Mode detection for Terragraf scaffolding.

Detects whether the current session is running in CI mode (headless,
background, limited to tests/lint) or App mode (interactive, GUI-capable,
full system access).

Priority order:
  1. Explicit TERRAGRAF_MODE env var ("ci" or "app")
  2. Standard CI env vars (CI, GITHUB_ACTIONS, JENKINS_URL, etc.)
  3. Capability heuristics (display server, PySide6 availability)
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Mode(Enum):
    CI = "ci"
    APP = "app"


# What each mode is allowed to do
_CI_CAPABILITIES = frozenset({
    "tests",
    "lint",
    "syntax_check",
    "generators",
    "routes",
    "tables",
    "sharpen",
    "math",
    "queue",
    "hooks",
})

_APP_CAPABILITIES = frozenset({
    "tests",
    "lint",
    "syntax_check",
    "generators",
    "routes",
    "tables",
    "sharpen",
    "math",
    "queue",
    "hooks",
    # App-only capabilities
    "gui",
    "qt_app",
    "imgui",
    "bridge",
    "viz_interactive",
    "vulkan",
    "tuning_ui",
    "settings_ui",
    "instances_socket",
})

# Systems that should NOT be built/modified in CI mode
_CI_BLOCKED_SYSTEMS = frozenset({
    "gui",
    "qt_app",
    "imgui",
    "bridge",
    "viz_interactive",
    "vulkan",
    "tuning_ui",
    "settings_ui",
})

# Known CI environment variables
_CI_ENV_VARS = (
    "CI",
    "GITHUB_ACTIONS",
    "JENKINS_URL",
    "GITLAB_CI",
    "CIRCLECI",
    "TRAVIS",
    "BUILDKITE",
    "TF_BUILD",
    "CODEBUILD_BUILD_ID",
)


@dataclass(frozen=True)
class ModeInfo:
    """Result of mode detection."""
    mode: Mode
    source: str                          # How the mode was determined
    capabilities: frozenset = field(default_factory=frozenset)
    blocked: frozenset = field(default_factory=frozenset)

    @property
    def is_ci(self) -> bool:
        return self.mode == Mode.CI

    @property
    def is_app(self) -> bool:
        return self.mode == Mode.APP

    def can(self, capability: str) -> bool:
        """Check if a capability is allowed in the current mode."""
        return capability in self.capabilities

    def blocked_reason(self, system: str) -> Optional[str]:
        """Return a reason string if the system is blocked, else None."""
        if system in self.blocked:
            return f"'{system}' is not available in {self.mode.value} mode"
        return None


def _check_explicit_env() -> Optional[Mode]:
    """Check for explicit TERRAGRAF_MODE env var."""
    val = os.environ.get("TERRAGRAF_MODE", "").strip().lower()
    if val == "ci":
        return Mode.CI
    if val == "app":
        return Mode.APP
    return None


def _check_ci_env() -> Optional[str]:
    """Check for standard CI environment variables. Returns the var name if found."""
    for var in _CI_ENV_VARS:
        if os.environ.get(var):
            return var
    return None


def _is_wsl() -> bool:
    """Check if running under Windows Subsystem for Linux."""
    try:
        from pathlib import Path
        proc_version = Path("/proc/version")
        if proc_version.exists():
            text = proc_version.read_text().lower()
            return "microsoft" in text or "wsl" in text
    except Exception:
        pass
    return False


def _has_display() -> bool:
    """Check if a display server is available."""
    # QT_QPA_PLATFORM=offscreen means headless (check first)
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return False
    # Windows always has a display in interactive sessions
    if os.name == "nt":
        return True
    # X11 or Wayland display
    if os.environ.get("DISPLAY"):
        return True
    if os.environ.get("WAYLAND_DISPLAY"):
        return True
    # WSL without X11 forwarding has no display
    if _is_wsl():
        return False
    return False


def _has_pyside6() -> bool:
    """Check if PySide6 is importable."""
    try:
        import PySide6  # noqa: F401
        return True
    except ImportError:
        return False


def detect() -> ModeInfo:
    """Detect the current operational mode.

    Returns a ModeInfo with the detected mode, how it was determined,
    and what capabilities/blocks apply.
    """
    # 1. Explicit env var takes priority
    explicit = _check_explicit_env()
    if explicit is not None:
        if explicit == Mode.CI:
            return ModeInfo(
                mode=Mode.CI,
                source="TERRAGRAF_MODE=ci",
                capabilities=_CI_CAPABILITIES,
                blocked=_CI_BLOCKED_SYSTEMS,
            )
        return ModeInfo(
            mode=Mode.APP,
            source="TERRAGRAF_MODE=app",
            capabilities=_APP_CAPABILITIES,
            blocked=frozenset(),
        )

    # 2. Standard CI env vars
    ci_var = _check_ci_env()
    if ci_var:
        return ModeInfo(
            mode=Mode.CI,
            source=f"env:{ci_var}",
            capabilities=_CI_CAPABILITIES,
            blocked=_CI_BLOCKED_SYSTEMS,
        )

    # 3. Capability heuristics — no display = likely CI
    if not _has_display():
        return ModeInfo(
            mode=Mode.CI,
            source="no display server detected",
            capabilities=_CI_CAPABILITIES,
            blocked=_CI_BLOCKED_SYSTEMS,
        )

    # 4. Default: App mode (interactive session with display)
    return ModeInfo(
        mode=Mode.APP,
        source="display available (interactive session)",
        capabilities=_APP_CAPABILITIES,
        blocked=frozenset(),
    )


def require_app(system: str) -> None:
    """Guard: raise RuntimeError if not in app mode.

    Use at the top of functions/modules that must not run in CI.
    Example:
        from modes.detector import require_app
        require_app("qt_app")
    """
    info = detect()
    reason = info.blocked_reason(system)
    if reason:
        raise RuntimeError(reason)
