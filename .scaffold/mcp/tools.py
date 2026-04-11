"""
mcp/tools.py — Skill-to-tool adapter.

Wraps Terragraf skills as MCP tool definitions so external tools can
discover and invoke them via the MCP protocol.
"""

import sys
from pathlib import Path


SCAFFOLD_DIR = Path(__file__).resolve().parent.parent


def _ensure_path():
    """Ensure .scaffold is on sys.path for skill imports."""
    scaffold_str = str(SCAFFOLD_DIR)
    if scaffold_str not in sys.path:
        sys.path.insert(0, scaffold_str)


class SkillToolAdapter:
    """
    Translates Terragraf skills into MCP tool descriptors and handles
    tool invocations via run_skill_capture.

    Usage:
        adapter = SkillToolAdapter()
        tools = adapter.list_tools()
        result = adapter.call_tool("health_check", {"args": ["--quick"]})
    """

    def __init__(self, skills_dir: Path = None):
        self._skills_dir = skills_dir or (SCAFFOLD_DIR / "skills")

    def list_tools(self) -> list[dict]:
        """Return MCP tool descriptors for all registered skills."""
        _ensure_path()
        from skills.runner import list_skills

        tools = []
        for name, manifest in list_skills():
            info = manifest.get("skill", {})
            triggers = manifest.get("triggers", {})
            tools.append({
                "name": name,
                "description": info.get("description", ""),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command-line arguments for the skill",
                        },
                    },
                },
            })
        return tools

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        """
        Execute a skill and return MCP tool result.

        Returns:
            {"content": [{"type": "text", "text": ...}], "isError": bool}
        """
        _ensure_path()
        from skills.runner import run_skill_capture

        arguments = arguments or {}
        args = arguments.get("args", [])

        rc, stdout, stderr = run_skill_capture(name, args)
        is_error = rc != 0
        text = stdout if not is_error else (stderr or f"Skill exited with code {rc}")

        return {
            "content": [{"type": "text", "text": text}],
            "isError": is_error,
        }
