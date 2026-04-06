"""
.scaffold/worktree — Git worktree isolation for parallel agents.

Each agent (instance) can get its own git worktree with an independent
copy of the scaffold, preventing file conflicts between parallel agents.

Worktrees live under .scaffold/worktrees/ with branch prefix worktree/.
"""

from .manager import WorktreeManager, WorktreeInfo
from .context import WorktreeContext

__all__ = [
    "WorktreeManager",
    "WorktreeInfo",
    "WorktreeContext",
]
