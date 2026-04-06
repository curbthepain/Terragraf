"""KnowledgeAddDialog — terra knowledge add via knowledge_writer.py."""

import subprocess
import sys
from pathlib import Path

from ..command_dialog import CommandDialog, FieldSpec


WRITER = Path(__file__).resolve().parents[4] / "projects" / "knowledge_writer.py"


class KnowledgeAddDialog(CommandDialog):
    TITLE = "Add Knowledge Entry"
    FIELDS = [
        FieldSpec("id", "ID", kind="text", placeholder="entry_id"),
        FieldSpec("summary", "Summary", kind="text",
                  placeholder="One-line summary"),
        FieldSpec("type", "Type", kind="choice",
                  choices=["pattern", "decision", "caveat", "incident"],
                  default="pattern"),
        FieldSpec("content", "Content", kind="multiline"),
        FieldSpec("tags", "Tags (comma-separated)", kind="text"),
    ]

    def run(self, values: dict) -> str:
        if not WRITER.exists():
            return f"knowledge_writer.py not found at {WRITER}"
        args = [
            sys.executable, str(WRITER),
            "--id", values["id"],
            "--summary", values["summary"],
            "--type", values["type"],
        ]
        if values.get("content"):
            args += ["--content", values["content"]]
        if values.get("tags"):
            args += ["--tags", values["tags"]]
        try:
            result = subprocess.run(args, capture_output=True, text=True)
            out = result.stdout + (result.stderr or "")
            if result.returncode != 0:
                out += f"\n[exit {result.returncode}]"
            return out
        except OSError as e:
            return f"Error: {e}"
