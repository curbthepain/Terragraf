"""
worktree/context.py — Worktree-scoped instance context.

Wraps InstanceContext with worktree path and branch, providing
path resolution relative to the worktree root.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from instances.instance import InstanceContext


@dataclass
class WorktreeContext:
    """
    Instance context scoped to a git worktree.

    Uses composition (not inheritance) to wrap InstanceContext,
    matching how Session uses InstanceContext as a field.
    """
    base: InstanceContext = field(default_factory=InstanceContext)
    worktree_id: str = ""
    worktree_path: Optional[Path] = None
    worktree_branch: str = ""

    @property
    def scaffold_dir(self) -> Optional[Path]:
        """The .scaffold directory inside the worktree, if set."""
        if self.worktree_path:
            return self.worktree_path / ".scaffold"
        return None

    def resolve_path(self, relative: str) -> Path:
        """
        Resolve a relative path against the worktree root.
        Falls back to the main repo if no worktree is set.
        """
        if self.worktree_path:
            return self.worktree_path / relative
        # Fallback: resolve relative to .scaffold parent
        from instances.instance import SCAFFOLD_DIR
        return SCAFFOLD_DIR.parent / relative

    def scaffold_state_for_worktree(self):
        """
        Create a ScaffoldState pointing at the worktree's .scaffold/.

        Returns None if no worktree path is set or the directory
        doesn't exist.
        """
        scaffold = self.scaffold_dir
        if scaffold is None or not scaffold.exists():
            return None

        from app.scaffold_state import ScaffoldState
        state = ScaffoldState(scaffold_dir=scaffold)
        state.load_all()
        return state
