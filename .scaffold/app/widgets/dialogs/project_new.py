"""ProjectNewDialog — terra project new <name> -> scaffold_project skill."""

from ..command_dialog import CommandDialog, FieldSpec


class ProjectNewDialog(CommandDialog):
    TITLE = "New Project"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("name", "Project name", kind="text",
                  placeholder="my_project"),
        FieldSpec("type", "Type", kind="choice",
                  choices=["qt-app", "cli", "lib", "test"],
                  default="cli"),
    ]

    def run(self, values: dict) -> str:
        name = (values.get("name") or "").strip()
        if not name:
            return "Project name is required."
        args = [name, "--type", values["type"]]
        return self.run_skill_streaming("scaffold_project", args)
