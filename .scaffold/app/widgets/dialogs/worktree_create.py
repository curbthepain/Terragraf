"""WorktreeCreateDialog — direct call to worktree.manager.WorktreeManager."""

from ..command_dialog import CommandDialog, FieldSpec


class WorktreeCreateDialog(CommandDialog):
    TITLE = "Create Worktree"
    FIELDS = [
        FieldSpec("task_id", "Task ID", kind="text",
                  placeholder="task_001"),
        FieldSpec("base_ref", "Base ref", kind="text", default="HEAD"),
    ]

    def run(self, values: dict) -> str:
        try:
            import sys
            from pathlib import Path as _P
            sys.path.insert(0, str(_P(__file__).resolve().parents[3]))
            from worktree.manager import WorktreeManager
        except Exception as e:
            return f"Failed to import WorktreeManager: {e}"

        try:
            mgr = WorktreeManager()
            info = mgr.create(
                task_id=values["task_id"] or "task",
                instance_id="ui",
                base_ref=values.get("base_ref") or "HEAD",
            )
            return (
                f"Created worktree:\n"
                f"  id:     {info.worktree_id}\n"
                f"  path:   {info.path}\n"
                f"  branch: {info.branch}\n"
                f"  status: {info.status}\n"
            )
        except Exception as e:
            return f"Error: {e}"
