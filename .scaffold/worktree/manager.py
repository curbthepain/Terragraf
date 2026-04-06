"""
worktree/manager.py — Git worktree lifecycle management.

Creates, lists, removes, and garbage-collects git worktrees for
parallel agent isolation. Each worktree gets a branch named
worktree/{id} and lives under .scaffold/worktrees/{id}/.

Usage:
    mgr = WorktreeManager()
    info = mgr.create(task_id="fix-fft")
    worktrees = mgr.list()
    mgr.merge_back(info.worktree_id)
    mgr.remove(info.worktree_id)
    mgr.gc(max_age_hours=24)
"""

import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


BRANCH_PREFIX = "worktree/"


@dataclass
class WorktreeInfo:
    """Metadata for a single git worktree."""
    worktree_id: str = ""
    path: Path = field(default_factory=Path)
    branch: str = ""
    instance_id: str = ""
    task_id: str = ""
    created_at: float = field(default_factory=time.time)
    status: str = "active"        # "active", "stale", "merged"

    def to_dict(self) -> dict:
        return {
            "worktree_id": self.worktree_id,
            "path": str(self.path),
            "branch": self.branch,
            "instance_id": self.instance_id,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "status": self.status,
        }


class WorktreeManager:
    """
    Manages git worktrees for agent isolation.

    Creates worktrees under .scaffold/worktrees/ using
    `git worktree add`. Supports garbage collection of stale
    worktrees and merge-back of completed work.
    """

    def __init__(self, repo_root: Path = None):
        if repo_root is not None:
            self._repo_root = Path(repo_root)
        else:
            self._repo_root = self._detect_repo_root()
        self._worktrees_dir = self._repo_root / ".scaffold" / "worktrees"
        self._worktrees_dir.mkdir(parents=True, exist_ok=True)
        self._worktrees: dict[str, WorktreeInfo] = {}

        # Sync with git on init
        self._sync_from_git()

    def create(self, task_id: str = "", instance_id: str = "",
               base_ref: str = "HEAD") -> WorktreeInfo:
        """Create a new worktree with a dedicated branch."""
        wt_id = uuid.uuid4().hex[:8]
        branch = f"{BRANCH_PREFIX}{wt_id}"
        wt_path = self._worktrees_dir / wt_id

        rc, stdout, stderr = self._run_git(
            "worktree", "add", "-b", branch, str(wt_path), base_ref
        )
        if rc != 0:
            raise RuntimeError(f"git worktree add failed: {stderr}")

        info = WorktreeInfo(
            worktree_id=wt_id,
            path=wt_path,
            branch=branch,
            instance_id=instance_id,
            task_id=task_id,
        )
        self._worktrees[wt_id] = info
        return info

    def list(self) -> list[WorktreeInfo]:
        """List all managed worktrees."""
        self._sync_from_git()
        return list(self._worktrees.values())

    def get(self, worktree_id: str) -> Optional[WorktreeInfo]:
        """Get a worktree by ID."""
        return self._worktrees.get(worktree_id)

    def for_instance(self, instance_id: str) -> Optional[WorktreeInfo]:
        """Find the worktree assigned to an instance."""
        for info in self._worktrees.values():
            if info.instance_id == instance_id:
                return info
        return None

    def remove(self, worktree_id: str, force: bool = False) -> bool:
        """Remove a worktree and its branch."""
        info = self._worktrees.get(worktree_id)
        if info is None:
            # Try by path in case it exists on disk but not in our dict
            wt_path = self._worktrees_dir / worktree_id
            if not wt_path.exists():
                return False
            branch = f"{BRANCH_PREFIX}{worktree_id}"
        else:
            wt_path = info.path
            branch = info.branch

        # Remove worktree
        args = ["worktree", "remove", str(wt_path)]
        if force:
            args.append("--force")
        rc, _, stderr = self._run_git(*args)
        if rc != 0:
            if force and wt_path.exists():
                shutil.rmtree(wt_path, ignore_errors=True)
                self._run_git("worktree", "prune")
            elif not force:
                return False

        # Delete branch
        flag = "-D" if force else "-d"
        self._run_git("branch", flag, branch)

        # Remove from tracking
        self._worktrees.pop(worktree_id, None)
        return True

    def gc(self, max_age_hours: float = 24.0) -> list[str]:
        """Remove stale worktrees older than max_age_hours. Returns removed IDs."""
        self._sync_from_git()
        cutoff = time.time() - (max_age_hours * 3600)
        removed = []

        for wt_id, info in list(self._worktrees.items()):
            if info.status == "stale" and info.created_at < cutoff:
                if self.remove(wt_id, force=True):
                    removed.append(wt_id)

        # Prune any orphaned worktree entries
        self._run_git("worktree", "prune")
        return removed

    def mark_stale(self, worktree_id: str):
        """Mark a worktree as stale (no active instance)."""
        info = self._worktrees.get(worktree_id)
        if info:
            info.status = "stale"

    def merge_back(self, worktree_id: str, strategy: str = "checkout") -> bool:
        """
        Merge worktree changes back to the current branch.

        Strategies:
          - "checkout": git merge (fast-forward or merge commit)
          - "cherry-pick": cherry-pick all commits from worktree branch
          - "copy": shutil copy of modified files (no git history)
        """
        info = self._worktrees.get(worktree_id)
        if info is None:
            return False

        if strategy == "checkout":
            rc, _, stderr = self._run_git("merge", info.branch,
                                           "--no-edit",
                                           f"--message=Merge worktree {worktree_id}")
            if rc != 0:
                return False

        elif strategy == "cherry-pick":
            # Find commits unique to the worktree branch
            rc, stdout, _ = self._run_git("log", "--format=%H",
                                           f"HEAD..{info.branch}")
            if rc != 0:
                return False
            commits = [c.strip() for c in stdout.strip().splitlines() if c.strip()]
            for commit in reversed(commits):
                rc, _, _ = self._run_git("cherry-pick", commit)
                if rc != 0:
                    self._run_git("cherry-pick", "--abort")
                    return False

        elif strategy == "copy":
            # Copy all files from worktree to main repo
            for item in info.path.rglob("*"):
                if item.is_file() and ".git" not in item.parts:
                    rel = item.relative_to(info.path)
                    dest = self._repo_root / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

        else:
            return False

        info.status = "merged"
        return True

    # ── Internal ─────────────────────────────────────────────────────

    def _detect_repo_root(self) -> Path:
        """Detect git repo root."""
        rc, stdout, _ = self._run_git_raw("rev-parse", "--show-toplevel")
        if rc == 0 and stdout.strip():
            return Path(stdout.strip())
        # Fallback: walk up from this file
        return Path(__file__).resolve().parent.parent.parent

    def _run_git(self, *args) -> tuple[int, str, str]:
        """Run a git command in the repo root."""
        return self._run_git_raw(*args, cwd=str(self._repo_root))

    @staticmethod
    def _run_git_raw(*args, cwd=None) -> tuple[int, str, str]:
        """Run a git command."""
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=cwd, timeout=30
            )
            return (result.returncode, result.stdout, result.stderr)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return (1, "", str(exc))

    def _sync_from_git(self):
        """Reconcile in-memory state with git worktree list."""
        rc, stdout, _ = self._run_git("worktree", "list", "--porcelain")
        if rc != 0:
            return

        # Parse porcelain output
        git_worktrees = {}
        current = {}
        for line in stdout.splitlines():
            if line.startswith("worktree "):
                if current:
                    git_worktrees[current.get("path", "")] = current
                current = {"path": line.split(" ", 1)[1].strip()}
            elif line.startswith("HEAD "):
                current["head"] = line.split(" ", 1)[1].strip()
            elif line.startswith("branch "):
                current["branch"] = line.split(" ", 1)[1].strip()
            elif line == "bare":
                current["bare"] = True
        if current:
            git_worktrees[current.get("path", "")] = current

        # Match git worktrees to our managed ones
        wt_dir_str = str(self._worktrees_dir)
        for path_str, git_info in git_worktrees.items():
            path = Path(path_str)
            # Only track worktrees under our managed directory
            try:
                path.relative_to(self._worktrees_dir)
            except ValueError:
                continue

            wt_id = path.name
            branch_ref = git_info.get("branch", "")
            # refs/heads/worktree/xxx -> worktree/xxx
            branch = branch_ref.replace("refs/heads/", "") if branch_ref else ""

            if wt_id not in self._worktrees:
                # Discovered from git but not in our dict
                self._worktrees[wt_id] = WorktreeInfo(
                    worktree_id=wt_id,
                    path=path,
                    branch=branch,
                    status="stale",  # We don't know the instance
                )

        # Remove entries that no longer exist on disk
        to_remove = []
        for wt_id, info in self._worktrees.items():
            if not info.path.exists():
                to_remove.append(wt_id)
        for wt_id in to_remove:
            del self._worktrees[wt_id]
