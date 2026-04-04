"""Tests for .scaffold/skills/runner.py — skill discovery, matching, execution."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.runner import list_skills, match_skill, run_skill, _load_manifest, SKILLS_DIR


class TestListSkills:
    def test_returns_all_registered(self):
        skills = list_skills()
        names = [name for name, _ in skills]
        assert len(skills) >= 15
        # Spot-check a few known skills
        assert "signal_analyze" in names
        assert "math_solve" in names
        assert "health_check" in names
        assert "consistency_scan" in names
        assert "scaffold_project" in names

    def test_each_has_valid_manifest(self):
        for name, manifest in list_skills():
            assert "skill" in manifest
            info = manifest["skill"]
            assert "name" in info
            assert "description" in info

    def test_each_has_entry_point(self):
        for name, manifest in list_skills():
            entry = manifest["skill"].get("entry", "run.py")
            entry_path = SKILLS_DIR / name / entry
            assert entry_path.exists(), f"{name}: entry {entry} not found"


class TestMatchSkill:
    def test_exact_intent(self):
        result = match_skill("analyze signal")
        assert result is not None
        name, _ = result
        assert name == "signal_analyze"

    def test_partial_intent(self):
        result = match_skill("analyze signal please")
        assert result is not None
        name, _ = result
        assert name == "signal_analyze"

    def test_math_intent(self):
        result = match_skill("eigenvalues")
        assert result is not None
        name, _ = result
        assert name == "math_solve"

    def test_case_insensitive(self):
        result = match_skill("ANALYZE SIGNAL")
        assert result is not None

    def test_no_match(self):
        result = match_skill("completely unrelated gibberish xyz123")
        assert result is None


class TestLoadManifest:
    def test_valid_skill_dir(self):
        manifest = _load_manifest(SKILLS_DIR / "signal_analyze")
        assert manifest is not None
        assert "skill" in manifest

    def test_nonexistent_dir(self):
        manifest = _load_manifest(SKILLS_DIR / "does_not_exist")
        assert manifest is None


class TestRunSkill:
    def test_nonexistent_skill(self, capsys):
        rc = run_skill("nonexistent_skill_xyz")
        assert rc == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "error" in captured.out.lower()
