"""App host — discovers and manages IDEs installed in .scaffold/apps/."""

import os
import socket
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11


@dataclass
class IDEManifest:
    """Parsed app.toml for a single IDE."""

    name: str
    version: str
    description: str
    license: str
    label: str
    shortcut: str
    launch_type: str          # "webview" or "process"
    command: str
    fallback_command: str
    port_range: tuple[int, int]
    startup_delay: int
    health_check: str
    workspace: str
    env: dict[str, str]
    app_dir: Path             # absolute path to this IDE's folder

    @classmethod
    def from_toml(cls, path: Path) -> "IDEManifest":
        with open(path, "rb") as f:
            data = tomllib.load(f)

        ide = data.get("ide", {})
        display = ide.get("display", {})
        launch = ide.get("launch", {})
        env = launch.get("env", {})

        port_range = launch.get("port_range", [9100, 9199])

        return cls(
            name=ide.get("name", path.parent.name),
            version=ide.get("version", "0.0"),
            description=ide.get("description", ""),
            license=ide.get("license", "unknown"),
            label=display.get("label", ide.get("name", path.parent.name)),
            shortcut=display.get("shortcut", ""),
            launch_type=launch.get("type", "process"),
            command=launch.get("command", ""),
            fallback_command=launch.get("fallback_command", ""),
            port_range=(port_range[0], port_range[1]),
            startup_delay=launch.get("startup_delay", 3),
            health_check=launch.get("health_check", ""),
            workspace=launch.get("workspace", ""),
            env={k: str(v) for k, v in env.items()},
            app_dir=path.parent.resolve(),
        )


class AppHostManager:
    """Discovers IDEs in .scaffold/apps/ and provides their manifests."""

    def __init__(self, apps_dir: Path | None = None):
        if apps_dir is None:
            apps_dir = Path(__file__).parent.parent / "apps"
        self._apps_dir = apps_dir
        self._manifests: dict[str, IDEManifest] = {}
        self.scan()

    @property
    def apps_dir(self) -> Path:
        return self._apps_dir

    @property
    def manifests(self) -> dict[str, IDEManifest]:
        return dict(self._manifests)

    def scan(self):
        """Scan the apps directory for IDE manifests."""
        self._manifests.clear()
        if not self._apps_dir.is_dir():
            return

        for entry in sorted(self._apps_dir.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "app.toml"
            if not manifest_path.exists():
                continue
            try:
                manifest = IDEManifest.from_toml(manifest_path)
                self._manifests[entry.name] = manifest
            except Exception as e:
                print(f"[app_host] failed to load {manifest_path}: {e}")

    @staticmethod
    def find_free_port(low: int, high: int) -> int | None:
        """Find a free TCP port in the given range."""
        for port in range(low, high + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    return port
            except OSError:
                continue
        return None

    def resolve_command(self, manifest: IDEManifest, port: int) -> tuple[str, list[str]] | None:
        """Resolve the launch command for an IDE, returning (program, args) or None."""
        import shutil

        for cmd_template in [manifest.command, manifest.fallback_command]:
            if not cmd_template:
                continue
            cmd = cmd_template.replace("{port}", str(port))
            parts = cmd.split()
            if not parts:
                continue
            program = parts[0]

            # Check if it's a relative path inside the app dir
            local_bin = manifest.app_dir / program
            if local_bin.exists() and os.access(local_bin, os.X_OK):
                return str(local_bin), parts[1:]

            # Check system PATH
            if shutil.which(program):
                return program, parts[1:]

        return None
