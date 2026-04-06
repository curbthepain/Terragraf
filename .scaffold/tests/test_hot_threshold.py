"""Tests for the central HOT_CONTEXT threshold guard
(.scaffold/hooks/on_hot_threshold.py).

Covers all four trigger surfaces:
  - Direct API (check_threshold)
  - CLI (--json with stdin envelope)
  - Importable from terra.py main()
  - Warn-only mode for the Qt watcher path
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The hooks module patches HOT_CONTEXT/MANIFEST as module-level constants;
# we monkeypatch them per-test to avoid touching the real files.
from hooks import on_hot_threshold as hot_guard


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def fake_hot_context(tmp_path, monkeypatch):
    """Redirect the guard at a tmp HOT_CONTEXT.md and MANIFEST.toml."""
    fake_hot = tmp_path / "HOT_CONTEXT.md"
    fake_manifest = tmp_path / "MANIFEST.toml"
    fake_manifest.write_text(
        '[hot_context]\nmax_lines = 50\n', encoding="utf-8"
    )
    monkeypatch.setattr(hot_guard, "HOT_CONTEXT", fake_hot)
    monkeypatch.setattr(hot_guard, "MANIFEST", fake_manifest)
    return fake_hot


def _write_lines(path: Path, n: int):
    path.write_text("\n".join(f"line {i}" for i in range(n)), encoding="utf-8")


# ── Direct API ──────────────────────────────────────────────────────

class TestCheckThreshold:
    def test_under_threshold_no_op(self, fake_hot_context):
        _write_lines(fake_hot_context, 10)
        result = hot_guard.check_threshold(auto_decompose=True)
        assert result["over"] is False
        assert result["lines"] == 10
        assert result["threshold"] == 50
        assert result["decomposed"] is False
        assert result["moved"] == 0

    def test_over_threshold_warn_only(self, fake_hot_context):
        _write_lines(fake_hot_context, 200)
        result = hot_guard.check_threshold(auto_decompose=False)
        assert result["over"] is True
        assert result["lines"] == 200
        assert result["decomposed"] is False
        # File should be untouched
        assert fake_hot_context.read_text().count("\n") >= 199

    def test_missing_hot_context_returns_safe(self, fake_hot_context):
        # File never created
        result = hot_guard.check_threshold(auto_decompose=True)
        assert result["over"] is False
        assert result["lines"] == 0
        assert "note" in result

    def test_threshold_read_from_manifest(self, tmp_path, monkeypatch):
        fake_hot = tmp_path / "HOT_CONTEXT.md"
        fake_manifest = tmp_path / "MANIFEST.toml"
        fake_manifest.write_text(
            "[hot_context]\nmax_lines = 999\n", encoding="utf-8"
        )
        monkeypatch.setattr(hot_guard, "HOT_CONTEXT", fake_hot)
        monkeypatch.setattr(hot_guard, "MANIFEST", fake_manifest)
        _write_lines(fake_hot, 500)
        result = hot_guard.check_threshold(auto_decompose=False)
        assert result["over"] is False
        assert result["threshold"] == 999

    def test_threshold_default_when_manifest_missing(self, tmp_path, monkeypatch):
        fake_hot = tmp_path / "HOT_CONTEXT.md"
        fake_manifest = tmp_path / "no_such_manifest.toml"
        monkeypatch.setattr(hot_guard, "HOT_CONTEXT", fake_hot)
        monkeypatch.setattr(hot_guard, "MANIFEST", fake_manifest)
        _write_lines(fake_hot, 90)
        result = hot_guard.check_threshold(auto_decompose=False)
        assert result["over"] is True  # default 80
        assert result["threshold"] == 80

    def test_result_contains_harness_and_model(self, fake_hot_context):
        _write_lines(fake_hot_context, 5)
        result = hot_guard.check_threshold(auto_decompose=False)
        assert "harness" in result
        assert "model" in result


# ── PostToolUse envelope handling ───────────────────────────────────

class TestEnvelopeFiltering:
    def test_envelope_read_on_hot_context_does_not_trigger(self):
        # Read is intentionally NOT a trigger — would otherwise interfere
        # with the read-then-edit cycle. Only mutating ops trigger.
        env = {
            "tool_name": "Read",
            "tool_input": {"file_path": ".scaffold/HOT_CONTEXT.md"},
        }
        assert hot_guard._envelope_targets_hot_context(env) is False

    def test_envelope_write_on_hot_context_triggers(self):
        env = {
            "tool_name": "Write",
            "tool_input": {"file_path": ".scaffold/HOT_CONTEXT.md", "content": "x"},
        }
        assert hot_guard._envelope_targets_hot_context(env) is True

    def test_envelope_targets_other_file(self):
        env = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "src/main.py"},
        }
        assert hot_guard._envelope_targets_hot_context(env) is False

    def test_envelope_other_tool_skipped(self):
        env = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }
        assert hot_guard._envelope_targets_hot_context(env) is False

    def test_envelope_none_means_proceed(self):
        # Direct CLI invocation (no stdin envelope) — caller is non-hook
        assert hot_guard._envelope_targets_hot_context(None) is True

    def test_edit_on_hot_context_matches(self):
        env = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/d/Terragraf/.scaffold/HOT_CONTEXT.md",
                "old_string": "x",
                "new_string": "y",
            },
        }
        assert hot_guard._envelope_targets_hot_context(env) is True


# ── CLI subprocess invocation ───────────────────────────────────────

class TestCLI:
    def test_cli_with_envelope_targets_other_file(self, tmp_path):
        """Real subprocess call — verifies stdin envelope path."""
        envelope = json.dumps({
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/other.py"},
        })
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent
                    / "hooks" / "on_hot_threshold.py"),
                "--json",
            ],
            input=envelope,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        out = json.loads(result.stdout.strip())
        assert out.get("skipped") is True
