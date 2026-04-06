"""GitFlowDialog — tabbed wrapper for branch / commit / pr."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QPushButton

from .branch import BranchDialog
from .commit import CommitDialog
from ..command_dialog import CommandDialog, FieldSpec


class _PRDialog(CommandDialog):
    TITLE = "Open PR"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("preview", "Preview only", kind="checkbox", default=True),
    ]

    def run(self, values: dict) -> str:
        args: list[str] = ["pr"]
        if values.get("preview"):
            args.append("--preview")
        return self.run_skill_streaming("git_flow", args)


class GitFlowDialog(QDialog):
    """Tabbed dialog combining branch / commit / pr."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Git Flow")
        self.setMinimumSize(600, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        tabs = QTabWidget()
        tabs.addTab(BranchDialog(self), "Branch")
        tabs.addTab(CommitDialog(self), "Commit")
        tabs.addTab(_PRDialog(self), "PR")
        layout.addWidget(tabs)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
