"""BranchDialog — terra branch <type> <name> -> git_flow skill."""

from ..command_dialog import CommandDialog, FieldSpec


class BranchDialog(CommandDialog):
    TITLE = "Create Branch"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("branch_type", "Type", kind="choice",
                  choices=["feature", "fix", "refactor", "docs",
                           "ci", "test", "chore"],
                  default="feature"),
        FieldSpec("name", "Branch name", kind="text",
                  placeholder="my-cool-feature"),
    ]

    def run(self, values: dict) -> str:
        args = ["branch", values["branch_type"], values["name"]]
        return self.run_skill_streaming("git_flow", args)
