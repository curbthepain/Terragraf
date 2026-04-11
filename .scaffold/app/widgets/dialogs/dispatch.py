"""DispatchDialog — terra dispatch -> instance_dispatch skill."""

from ..command_dialog import CommandDialog, FieldSpec


class DispatchDialog(CommandDialog):
    TITLE = "Dispatch Task"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("task", "Task description", kind="multiline",
                  placeholder="What should be done?"),
        FieldSpec("instance_count", "Instance count",
                  kind="number", default=1, minimum=1, maximum=16),
        FieldSpec("use_worktree", "Isolate in worktree",
                  kind="checkbox", default=True),
    ]

    def run(self, values: dict) -> str:
        task = (values.get("task") or "").strip()
        if not task:
            return "Task description is required."
        args: list[str] = ["enqueue", task]
        args += ["--count", str(values["instance_count"])]
        if values.get("use_worktree"):
            args.append("--worktree")
        return self.run_skill_streaming("instance_dispatch", args)
