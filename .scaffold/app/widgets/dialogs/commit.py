"""CommitDialog — terra commit <msg> -> git_flow skill."""

from ..command_dialog import CommandDialog, FieldSpec


class CommitDialog(CommandDialog):
    TITLE = "Commit Changes"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("message", "Commit message", kind="multiline",
                  placeholder="Describe the change..."),
        FieldSpec("auto", "Auto (AI message)", kind="checkbox", default=False),
    ]

    def run(self, values: dict) -> str:
        args: list[str] = ["commit"]
        if values.get("auto"):
            args.append("--auto")
        msg = (values.get("message") or "").strip()
        if msg:
            args.append(msg)
        return self.run_skill_streaming("git_flow", args)
