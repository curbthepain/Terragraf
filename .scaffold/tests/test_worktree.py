"""Tests for Session 15 — Worktree isolation backend.

25 tests covering:
  - WorktreeInfo (3)
  - WorktreeManager lifecycle (14)
  - Merge-back strategies (4)
  - WorktreeContext (4)
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure .scaffold is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worktree.manager import WorktreeInfo, WorktreeManager, BRANCH_PREFIX
from worktree.context import WorktreeContext
from instances.instance import InstanceContext


# ── Helpers ──────────────────────────────────────────────────────────

HAS_GIT = shutil.which("git") is not None
needs_git = pytest.mark.skipif(not HAS_GIT, reason="git not available")


def _init_repo(tmp_path):
    """Create a minimal git repo with one commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"],
                   cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                   cwd=str(repo), capture_output=True)
    # Create initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True)
    # Create .scaffold dir
    (repo / ".scaffold").mkdir()
    (repo / ".scaffold" / "worktrees").mkdir()
    return repo


@pytest.fixture
def repo(tmp_path):
    return _init_repo(tmp_path)


@pytest.fixture
def mgr(repo):
    return WorktreeManager(repo_root=repo)


# ── TestWorktreeInfo ────────────────────────────────────────────────

class TestWorktreeInfo:
    def test_defaults(self):
        info = WorktreeInfo()
        assert info.worktree_id == ""
        assert info.status == "active"

    def test_to_dict(self):
        info = WorktreeInfo(worktree_id="abc123", branch="worktree/abc123",
                            status="active")
        d = info.to_dict()
        assert d["worktree_id"] == "abc123"
        assert d["branch"] == "worktree/abc123"
        assert d["status"] == "active"

    def test_branch_prefix(self):
        assert BRANCH_PREFIX == "worktree/"


# ── TestWorktreeManager ─────────────────────────────────────────────

class TestWorktreeManager:
    @needs_git
    def test_create(self, mgr):
        info = mgr.create()
        assert info.worktree_id
        assert info.path.exists()
        assert info.branch.startswith(BRANCH_PREFIX)
        assert info.status == "active"

    @needs_git
    def test_create_with_task_id(self, mgr):
        info = mgr.create(task_id="fix-fft")
        assert info.task_id == "fix-fft"

    @needs_git
    def test_create_with_instance_id(self, mgr):
        info = mgr.create(instance_id="inst-001")
        assert info.instance_id == "inst-001"

    @needs_git
    def test_list(self, mgr):
        mgr.create()
        mgr.create()
        worktrees = mgr.list()
        assert len(worktrees) == 2

    @needs_git
    def test_list_empty(self, mgr):
        worktrees = mgr.list()
        assert len(worktrees) == 0

    @needs_git
    def test_remove(self, mgr):
        info = mgr.create()
        assert mgr.remove(info.worktree_id)
        assert not info.path.exists()
        assert mgr.list() == []

    @needs_git
    def test_remove_nonexistent(self, mgr):
        assert mgr.remove("nonexistent") is False

    @needs_git
    def test_remove_force(self, mgr):
        info = mgr.create()
        # Create a dirty file
        (info.path / "dirty.txt").write_text("uncommitted")
        assert mgr.remove(info.worktree_id, force=True)

    @needs_git
    def test_get_by_id(self, mgr):
        info = mgr.create()
        found = mgr.get(info.worktree_id)
        assert found is not None
        assert found.worktree_id == info.worktree_id

    @needs_git
    def test_for_instance(self, mgr):
        info = mgr.create(instance_id="inst-42")
        found = mgr.for_instance("inst-42")
        assert found is not None
        assert found.worktree_id == info.worktree_id

    @needs_git
    def test_for_instance_not_found(self, mgr):
        assert mgr.for_instance("nonexistent") is None

    @needs_git
    def test_mark_stale(self, mgr):
        info = mgr.create()
        mgr.mark_stale(info.worktree_id)
        found = mgr.get(info.worktree_id)
        assert found.status == "stale"

    @needs_git
    def test_gc_removes_stale(self, mgr):
        info = mgr.create()
        mgr.mark_stale(info.worktree_id)
        # Backdate the created_at to make it look old
        info.created_at = time.time() - (48 * 3600)
        removed = mgr.gc(max_age_hours=24)
        assert info.worktree_id in removed

    @needs_git
    def test_gc_preserves_active(self, mgr):
        info = mgr.create()
        # Active worktree should not be removed
        removed = mgr.gc(max_age_hours=0)
        assert info.worktree_id not in removed
        assert info.path.exists()


# ── TestWorktreeMergeBack ───────────────────────────────────────────

class TestWorktreeMergeBack:
    @needs_git
    def test_checkout_strategy(self, mgr, repo):
        info = mgr.create()
        # Add a commit in the worktree
        (info.path / "feature.txt").write_text("new feature")
        subprocess.run(["git", "add", "feature.txt"],
                       cwd=str(info.path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "add feature"],
                       cwd=str(info.path), capture_output=True)
        assert mgr.merge_back(info.worktree_id, strategy="checkout")
        assert (repo / "feature.txt").exists()
        assert info.status == "merged"

    @needs_git
    def test_copy_strategy(self, mgr, repo):
        info = mgr.create()
        (info.path / "copied.txt").write_text("copied content")
        assert mgr.merge_back(info.worktree_id, strategy="copy")
        assert (repo / "copied.txt").exists()
        assert info.status == "merged"

    @needs_git
    def test_marks_merged(self, mgr, repo):
        info = mgr.create()
        (info.path / "file.txt").write_text("data")
        subprocess.run(["git", "add", "file.txt"],
                       cwd=str(info.path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "commit"],
                       cwd=str(info.path), capture_output=True)
        mgr.merge_back(info.worktree_id, strategy="checkout")
        assert info.status == "merged"

    @needs_git
    def test_nonexistent_returns_false(self, mgr):
        assert mgr.merge_back("nonexistent") is False


# ── TestWorktreeContext ─────────────────────────────────────────────

class TestWorktreeContext:
    def test_delegates_to_base(self):
        base = InstanceContext(instance_id="inst-1", task_id="task-1")
        ctx = WorktreeContext(base=base, worktree_id="wt-1")
        assert ctx.base.instance_id == "inst-1"
        assert ctx.base.task_id == "task-1"

    def test_resolve_path_in_worktree(self, tmp_path):
        wt_path = tmp_path / "worktree"
        wt_path.mkdir()
        ctx = WorktreeContext(worktree_path=wt_path)
        resolved = ctx.resolve_path("src/main.py")
        assert resolved == wt_path / "src" / "main.py"

    def test_resolve_path_without_worktree(self):
        ctx = WorktreeContext()
        resolved = ctx.resolve_path("src/main.py")
        # Should fallback to main repo
        assert "src" in str(resolved)

    def test_scaffold_dir(self, tmp_path):
        wt_path = tmp_path / "worktree"
        wt_path.mkdir()
        ctx = WorktreeContext(worktree_path=wt_path)
        assert ctx.scaffold_dir == wt_path / ".scaffold"
