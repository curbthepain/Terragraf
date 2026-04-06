"""Form dialogs that surface terra commands as proper UI."""

from .generate import GenerateDialog
from .train import TrainDialog
from .solve import SolveDialog
from .analyze import AnalyzeDialog
from .render import RenderDialog
from .branch import BranchDialog
from .commit import CommitDialog
from .git_flow import GitFlowDialog
from .knowledge_add import KnowledgeAddDialog
from .project_new import ProjectNewDialog
from .worktree_create import WorktreeCreateDialog
from .dispatch import DispatchDialog

__all__ = [
    "GenerateDialog",
    "TrainDialog",
    "SolveDialog",
    "AnalyzeDialog",
    "RenderDialog",
    "BranchDialog",
    "CommitDialog",
    "GitFlowDialog",
    "KnowledgeAddDialog",
    "ProjectNewDialog",
    "WorktreeCreateDialog",
    "DispatchDialog",
]
