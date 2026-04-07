"""
Tests for hot_decompose skill — HOT_CONTEXT triage system.

Tests the parser, classifier, routing functions, and threshold checks
without modifying real scaffold files (uses tmp_path fixtures).
"""

import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add skills to path so we can import the module
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "hot_decompose"
sys.path.insert(0, str(SKILLS_DIR.parent.parent))

from skills.hot_decompose.run import (
    parse_blocks,
    classify_block,
    classify_all,
    Block,
    route_to_knowledge,
    route_to_routes,
    route_to_deps,
    rewrite_hot_context,
    get_max_lines,
    get_retain_sessions,
    get_hard_max_lines,
    check_threshold,
    _slugify,
)


# ── Fixtures ────────────────────────────────────────────────────────

SAMPLE_HOT_CONTEXT = textwrap.dedent("""\
    # Hot Context — Terragraf

    ## Status: Session 12 Complete — ImGui Panel Embedded

    Sessions 1-12 complete. 579 tests passing.

    ## What's Done (Session 12)

    ### ImGui as Dockable Panel
    Embedded ImGui into Qt via Win32/X11 window reparenting.

    ## Decisions Made (Session 12)

    - ImGui reparented via QWindow.fromWinId(), not a separate QProcess window
    - --embedded flag keeps ImGui borderless for clean Qt integration
    - Wayland has no reparentable handle — floating fallback is the only option

    ## ── SESSION BREAK ──────────────────────────────────────────────
    ## Everything above is Session 12.
    ## ──────────────────────────────────────────────────────────────

    ## Debug Notes

    - terra health → Grade A

    ## Backlog

    - Source all dependencies locally
    - AnthropicProvider real API integration

    ## Plan: Next Session

    FeedbackLoop + CoherenceManager + welcome tab
""")

ROUTE_BLOCK_CONTENT = textwrap.dedent("""\
    # Hot Context — Terragraf

    ## New Route Mappings

    feedback loop     -> app/feedback.py           # Cross-tab intelligence
    coherence mgr     -> app/coherence.py          # Conflict detection
    welcome tab       -> app/welcome_tab.py        # Landing tab
""")

DEP_BLOCK_CONTENT = textwrap.dedent("""\
    # Hot Context — Terragraf

    ## New Dependencies

    feedback  | workspace | events  | medium
    coherence | workspace | uses    | low
    welcome   | workspace | uses    | low
""")


# ── Parser Tests ────────────────────────────────────────────────────

class TestParser:
    def test_splits_into_correct_block_count(self):
        blocks = parse_blocks(SAMPLE_HOT_CONTEXT)
        # Status, What's Done, Decisions Made, SESSION BREAK markers (3 lines start with ##),
        # Debug Notes, Backlog, Plan
        assert len(blocks) >= 6

    def test_preserves_block_content(self):
        blocks = parse_blocks(SAMPLE_HOT_CONTEXT)
        # First block should be Status
        assert "Status:" in blocks[0].heading
        assert any("579 tests" in line for line in blocks[0].body)

    def test_handles_empty_file(self):
        blocks = parse_blocks("")
        assert blocks == []

    def test_handles_no_h2_headings(self):
        content = "# Title\nSome text\nMore text"
        blocks = parse_blocks(content)
        assert blocks == []

    def test_handles_consecutive_headings(self):
        content = "## First\n## Second\n## Third\nBody here"
        blocks = parse_blocks(content)
        assert len(blocks) == 3
        assert blocks[0].heading == "## First"
        assert blocks[0].body == []
        assert blocks[1].heading == "## Second"
        assert blocks[1].body == []
        assert blocks[2].heading == "## Third"
        assert blocks[2].body == ["Body here"]


# ── Classifier Tests ────────────────────────────────────────────────

class TestClassifier:
    def test_session_status_classified(self):
        b = Block(heading="## Status: Session 12 Complete")
        assert classify_block(b) == "session"

    def test_session_whats_done_classified(self):
        b = Block(heading="## What's Done (Session 12)")
        assert classify_block(b) == "session"

    def test_session_debug_notes_classified(self):
        b = Block(heading="## Debug Notes")
        assert classify_block(b) == "session"

    def test_session_plan_classified(self):
        b = Block(heading="## Plan: Next Session")
        assert classify_block(b) == "session"

    def test_session_backlog_classified(self):
        b = Block(heading="## Backlog")
        assert classify_block(b) == "session"

    def test_session_key_files_classified(self):
        b = Block(heading="## Key Files (Session 12)")
        assert classify_block(b) == "session"

    def test_decision_block_detected(self):
        b = Block(heading="## Decisions Made (Session 12)", body=[
            "- ImGui reparented via QWindow.fromWinId()",
        ])
        assert classify_block(b) == "decision"

    def test_pattern_block_detected(self):
        b = Block(heading="## Pattern: FFT Import Convention", body=[
            "Always use scipy.fft.rfft for real-valued signals",
        ])
        assert classify_block(b) == "pattern"

    def test_route_map_detected(self):
        b = Block(heading="## Route Mappings", body=[
            "feedback -> app/feedback.py  # Cross-tab",
            "coherence -> app/coherence.py  # Conflicts",
        ])
        assert classify_block(b) == "route_map"

    def test_dependency_lines_detected(self):
        b = Block(heading="## Dependencies", body=[
            "feedback | workspace | events | medium",
            "coherence | workspace | uses | low",
        ])
        assert classify_block(b) == "dependency"

    def test_platform_gotcha_detected(self):
        b = Block(heading="## Platform Notes", body=[
            "Win32 SetForegroundWindow requires platform-specific ctypes call",
            "This is a gotcha for cross-platform code",
        ])
        assert classify_block(b) == "platform"

    def test_session_break_discarded(self):
        b = Block(heading="## ── SESSION BREAK ──────────────────", body=[
            "## Everything above is Session 12.",
        ])
        assert classify_block(b) == "discard"


# ── Routing Tests ───────────────────────────────────────────────────

class TestRouting:
    def test_dry_run_writes_nothing(self, tmp_path, capsys):
        b = Block(heading="## Decisions Made", body=["- Chose X over Y"])
        b.block_type = "decision"
        route_to_knowledge(b, "decision", ["test"], dry_run=True)
        captured = capsys.readouterr()
        assert "KNOWLEDGE.toml" in captured.out
        assert "dry" not in captured.out.lower()  # no error about dry run

    def test_session_blocks_remain_after_decompose(self):
        blocks = parse_blocks(SAMPLE_HOT_CONTEXT)
        classify_all(blocks)
        session_blocks = [b for b in blocks if b.block_type == "session"]
        assert len(session_blocks) >= 3  # Status, What's Done, Debug Notes, Backlog, Plan

    def test_knowledge_routing_calls_writer(self, tmp_path, monkeypatch):
        """Mock subprocess to verify knowledge_writer is called correctly."""
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="Added", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Point KNOWLEDGE_WRITER to a real path so the exists() check passes
        import skills.hot_decompose.run as mod
        writer_path = tmp_path / "knowledge_writer.py"
        writer_path.write_text("# mock")
        monkeypatch.setattr(mod, "KNOWLEDGE_WRITER", writer_path)

        b = Block(heading="## Decisions Made (Session 12)", body=["- Chose X over Y"])
        result = route_to_knowledge(b, "decision", ["hot-context"], dry_run=False)
        assert result is True
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "--category" in cmd
        assert "decision" in cmd

    def test_duplicate_routes_skipped(self, tmp_path, monkeypatch, capsys):
        import skills.hot_decompose.run as mod

        route_file = tmp_path / "structure.route"
        route_file.write_text("feedback -> app/feedback.py  # existing\n")
        monkeypatch.setattr(mod, "STRUCTURE_ROUTE", route_file)

        b = Block(heading="## Routes", body=[
            "feedback -> app/feedback.py  # duplicate",
            "newroute -> app/newroute.py  # new",
        ])
        route_to_routes(b, dry_run=False)

        content = route_file.read_text()
        assert "newroute" in content
        captured = capsys.readouterr()
        assert "skip" in captured.out  # feedback was skipped

    def test_duplicate_deps_skipped(self, tmp_path, monkeypatch, capsys):
        import skills.hot_decompose.run as mod

        deps_file = tmp_path / "deps.table"
        deps_file.write_text("ml | math | uses | medium\n")
        monkeypatch.setattr(mod, "DEPS_TABLE", deps_file)

        b = Block(heading="## Deps", body=[
            "ml | math | uses | medium",
            "feedback | workspace | events | medium",
        ])
        route_to_deps(b, dry_run=False)

        content = deps_file.read_text()
        assert "feedback" in content
        captured = capsys.readouterr()
        assert "skip" in captured.out  # ml|math was skipped


# ── Threshold Tests ─────────────────────────────────────────────────

class TestThreshold:
    def test_warning_triggers_over_threshold(self, capsys):
        result = check_threshold(100, 80)
        assert result is True
        captured = capsys.readouterr()
        assert "100 lines" in captured.out

    def test_no_warning_under_threshold(self, capsys):
        result = check_threshold(50, 80)
        assert result is False
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_get_max_lines_from_manifest(self, tmp_path, monkeypatch):
        import skills.hot_decompose.run as mod
        manifest = tmp_path / "MANIFEST.toml"
        manifest.write_text('[hot_context]\nmax_lines = 120\n')
        monkeypatch.setattr(mod, "MANIFEST", manifest)
        assert get_max_lines() == 120

    def test_get_max_lines_default(self, tmp_path, monkeypatch):
        import skills.hot_decompose.run as mod
        monkeypatch.setattr(mod, "MANIFEST", tmp_path / "nonexistent.toml")
        assert get_max_lines() == 80


# ── Integration Tests ───────────────────────────────────────────────

class TestIntegration:
    def test_full_decompose_produces_valid_output(self, tmp_path, monkeypatch):
        import skills.hot_decompose.run as mod

        hot_file = tmp_path / "HOT_CONTEXT.md"
        hot_file.write_text(SAMPLE_HOT_CONTEXT, encoding="utf-8")
        monkeypatch.setattr(mod, "HOT_CONTEXT", hot_file)
        monkeypatch.setattr(mod, "MANIFEST", tmp_path / "MANIFEST.toml")

        # Mock knowledge_writer path to skip subprocess calls
        monkeypatch.setattr(mod, "KNOWLEDGE_WRITER", tmp_path / "nonexistent.py")

        result = mod.cmd_decompose(dry_run=True)
        assert result == 0

    def test_rewritten_context_under_threshold(self):
        blocks = parse_blocks(SAMPLE_HOT_CONTEXT)
        classify_all(blocks)
        session_blocks = [b for b in blocks if b.block_type == "session"]
        content = rewrite_hot_context(session_blocks, dry_run=True)
        line_count = len(content.splitlines())
        # Session-only content should be much shorter than original
        original_lines = len(SAMPLE_HOT_CONTEXT.splitlines())
        assert line_count < original_lines


# ── Slugify Tests ───────────────────────────────────────────────────

# ── Age-Out Tests ───────────────────────────────────────────────────


def _build_sessions(numbers, extra_blocks: str = "") -> str:
    """Build a HOT_CONTEXT body with one What's Done block per session number."""
    parts = ["# Hot Context — Terragraf", ""]
    for n in numbers:
        parts.append(f"## What's Done (Session {n})")
        parts.append("")
        parts.append(f"Session {n} content marker XYZ{n}")
        parts.append("")
    if extra_blocks:
        parts.append(extra_blocks)
    return "\n".join(parts) + "\n"


def _patch_hot_decompose(monkeypatch, tmp_path, hot_text: str, manifest_text: str | None = None):
    """Redirect HOT_CONTEXT, MANIFEST, and stub knowledge_writer to capture calls."""
    import skills.hot_decompose.run as mod

    hot_file = tmp_path / "HOT_CONTEXT.md"
    hot_file.write_text(hot_text, encoding="utf-8")
    monkeypatch.setattr(mod, "HOT_CONTEXT", hot_file)

    manifest_file = tmp_path / "MANIFEST.toml"
    if manifest_text is not None:
        manifest_file.write_text(manifest_text, encoding="utf-8")
    monkeypatch.setattr(mod, "MANIFEST", manifest_file)

    # Stub the knowledge writer path so route_to_knowledge passes the exists() check
    writer_path = tmp_path / "knowledge_writer.py"
    writer_path.write_text("# stub")
    monkeypatch.setattr(mod, "KNOWLEDGE_WRITER", writer_path)

    captured_calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        captured_calls.append(list(cmd))
        return MagicMock(returncode=0, stdout="Added", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return mod, hot_file, captured_calls


class TestAgeOut:
    def test_age_out_keeps_latest_3(self, tmp_path, monkeypatch):
        text = _build_sessions([10, 11, 12, 13, 14])
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text)

        assert mod.cmd_decompose(dry_run=False) == 0

        new_content = hot_file.read_text(encoding="utf-8")
        assert "XYZ12" in new_content
        assert "XYZ13" in new_content
        assert "XYZ14" in new_content
        assert "XYZ10" not in new_content
        assert "XYZ11" not in new_content

        # Exactly 2 archived sessions = 2 knowledge_writer calls
        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        assert len(writer_calls) == 2

    def test_age_out_preserves_non_session_content(self, tmp_path, monkeypatch):
        extra = (
            "## Architecture Notes\n\nWe use a layered scaffold.\n\n"
            "## Backlog\n\n- Active item one\n- Active item two\n\n"
            "## Constraints\n\nNo external network in tests.\n"
        )
        text = _build_sessions([20, 21, 22, 23], extra_blocks=extra)
        manifest = "[hot_context]\nretain_sessions = 2\n"
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text, manifest)

        assert mod.cmd_decompose(dry_run=False) == 0

        new_content = hot_file.read_text(encoding="utf-8")
        # 2 retained sessions
        assert "XYZ22" in new_content
        assert "XYZ23" in new_content
        assert "XYZ20" not in new_content
        assert "XYZ21" not in new_content
        # Non-session content all survives
        assert "Architecture Notes" in new_content
        assert "Active item one" in new_content
        assert "Constraints" in new_content

    def test_age_out_archives_to_knowledge(self, tmp_path, monkeypatch):
        text = _build_sessions([5, 6, 7, 8, 9])
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text)

        assert mod.cmd_decompose(dry_run=False) == 0

        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        assert len(writer_calls) == 2  # sessions 5 and 6 aged out

        # Check tags include session-N and "archived"
        all_tag_args: list[str] = []
        sources: list[str] = []
        for cmd in writer_calls:
            assert "--tags" in cmd
            tags_value = cmd[cmd.index("--tags") + 1]
            all_tag_args.append(tags_value)
            assert "--source" in cmd
            sources.append(cmd[cmd.index("--source") + 1])

        joined = " ".join(all_tag_args)
        assert "session-5" in joined
        assert "session-6" in joined
        assert "archived" in joined
        assert "hot-context-decompose" in sources

    def test_configurable_retention(self, tmp_path, monkeypatch):
        text = _build_sessions([1, 2, 3, 4, 5, 6, 7])
        manifest = "[hot_context]\nretain_sessions = 5\n"
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text, manifest)

        assert mod.cmd_decompose(dry_run=False) == 0

        new_content = hot_file.read_text(encoding="utf-8")
        for n in (3, 4, 5, 6, 7):
            assert f"XYZ{n}" in new_content
        for n in (1, 2):
            assert f"XYZ{n}" not in new_content

        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        assert len(writer_calls) == 2

        # Default fallback when MANIFEST missing
        import skills.hot_decompose.run as hd_mod
        monkeypatch.setattr(hd_mod, "MANIFEST", tmp_path / "no_such_manifest.toml")
        assert get_retain_sessions() == 3

    def test_decisions_route_to_correct_table(self, tmp_path, monkeypatch):
        text = (
            "# Hot Context — Terragraf\n\n"
            "## Decisions Made (Session 5)\n\n- Chose option A\n- Rejected option B\n\n"
            "## Patterns Found (Session 5)\n\n- Always use scipy.fft for real signals\n\n"
            "## What's Done (Session 10)\n\nSession 10 marker XYZ10\n\n"
            "## What's Done (Session 11)\n\nSession 11 marker XYZ11\n\n"
            "## What's Done (Session 12)\n\nSession 12 marker XYZ12\n\n"
        )
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text)
        assert mod.cmd_decompose(dry_run=False) == 0

        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        # session 5 has 2 aged-out blocks (Decisions Made + Patterns Found) → 2 calls
        assert len(writer_calls) == 2

        by_id: dict[str, str] = {}
        for cmd in writer_calls:
            entry_id = cmd[cmd.index("--id") + 1]
            category = cmd[cmd.index("--category") + 1]
            by_id[entry_id] = category

        # Decisions Made → decision (NOT pattern)
        decision_id = next(k for k in by_id if "decisions-made" in k)
        assert by_id[decision_id] == "decision"

        # Patterns Found → pattern
        pattern_id = next(k for k in by_id if "patterns-found" in k)
        assert by_id[pattern_id] == "pattern"

# ── Hard Cap (Forcer) Tests ─────────────────────────────────────────


def _build_session_with_h3s(n: int, h3_specs: list[tuple[str, int]]) -> str:
    """Build a "## What's Done (Session N)" block with multiple h3 sub-sections.

    h3_specs: list of (heading_text, body_line_count) — heading is e.g. "Key Files".
    """
    lines = [f"## What's Done (Session {n})", ""]
    for heading_text, body_count in h3_specs:
        lines.append(f"### {heading_text} (Session {n})")
        lines.append("")
        for i in range(body_count):
            lines.append(f"- session {n} {heading_text} body line {i}")
        lines.append("")
    return "\n".join(lines)


class TestHardCap:
    def test_get_hard_max_lines_default(self, tmp_path, monkeypatch):
        import skills.hot_decompose.run as mod
        monkeypatch.setattr(mod, "MANIFEST", tmp_path / "no_such.toml")
        assert get_hard_max_lines() == 1000

    def test_get_hard_max_lines_from_manifest(self, tmp_path, monkeypatch):
        import skills.hot_decompose.run as mod
        manifest = tmp_path / "MANIFEST.toml"
        manifest.write_text("[hot_context]\nhard_max_lines = 250\n")
        monkeypatch.setattr(mod, "MANIFEST", manifest)
        assert get_hard_max_lines() == 250

    def test_hard_cap_noop_when_under_limit(self, tmp_path, monkeypatch):
        # Small content, well under any reasonable cap
        text = "# Hot Context — Terragraf\n\n## What's Done (Session 12)\n\nSmall block.\n"
        manifest = "[hot_context]\nretain_sessions = 3\nhard_max_lines = 1000\n"
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text, manifest)
        assert mod.cmd_decompose(dry_run=False) == 0
        # No knowledge_writer calls — nothing was force-extracted
        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        assert writer_calls == []

    def test_hard_cap_extracts_h3_subsections(self, tmp_path, monkeypatch):
        # Build a single retained session with three large h3 sub-sections.
        # Total body ~150 lines per h3 → 450+ lines body alone.
        big_session = _build_session_with_h3s(
            12,
            [("Key Files", 60), ("Verification Results", 60), ("Decisions Made", 60)],
        )
        text = "# Hot Context — Terragraf\n\n" + big_session + "\n"
        # Set a low hard cap so the forcer must extract
        manifest = "[hot_context]\nretain_sessions = 3\nhard_max_lines = 50\n"
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text, manifest)

        assert mod.cmd_decompose(dry_run=False) == 0

        new_content = hot_file.read_text(encoding="utf-8")
        new_lines = len(new_content.splitlines())
        # File should now be at or below the hard cap (or as close as possible)
        assert new_lines <= 50, f"file is {new_lines} lines, expected <= 50"

        # The extracted h3 bodies should NO LONGER appear inline
        assert "Key Files body line 0" not in new_content
        assert "Verification Results body line 0" not in new_content
        # Wait — body lines use format "session {n} {heading_text} body line {i}"
        assert "session 12 Key Files body line 0" not in new_content

        # Knowledge writer should have been called for each extracted h3
        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        assert len(writer_calls) >= 2, f"expected >=2 force extractions, got {len(writer_calls)}"

        # Verify "hard-cap" tag is present on at least one
        all_tags = " ".join(
            cmd[cmd.index("--tags") + 1] for cmd in writer_calls if "--tags" in cmd
        )
        assert "hard-cap" in all_tags
        assert "session-12" in all_tags

    def test_hard_cap_stops_when_no_extractable(self, tmp_path, monkeypatch):
        # Session block with NO extractable h3 sub-sections (just prose body)
        text = (
            "# Hot Context — Terragraf\n\n"
            "## What's Done (Session 5)\n\n"
            + "\n".join(f"- prose line {i}" for i in range(80))
            + "\n"
        )
        manifest = "[hot_context]\nretain_sessions = 3\nhard_max_lines = 20\n"
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text, manifest)

        # Should not raise, even though file will remain over the cap
        assert mod.cmd_decompose(dry_run=False) == 0

        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        # No extractable h3s → no force extractions
        assert writer_calls == []

        # File still has the original prose (forcer didn't damage it)
        new_content = hot_file.read_text(encoding="utf-8")
        assert "prose line 0" in new_content

    def test_hard_cap_extracts_oldest_session_first(self, tmp_path, monkeypatch):
        # Two retained sessions, both with extractable h3s.
        # Forcer should drain the OLDER one first.
        old_session = _build_session_with_h3s(10, [("Key Files", 50)])
        new_session = _build_session_with_h3s(11, [("Key Files", 50)])
        text = "# Hot Context — Terragraf\n\n" + old_session + "\n" + new_session + "\n"
        # Cap that needs ONE extraction to satisfy
        manifest = "[hot_context]\nretain_sessions = 3\nhard_max_lines = 80\n"
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text, manifest)

        assert mod.cmd_decompose(dry_run=False) == 0

        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        assert len(writer_calls) >= 1

        # First force-extracted entry should be tagged session-10 (older), not session-11
        first_tags = writer_calls[0][writer_calls[0].index("--tags") + 1]
        assert "session-10" in first_tags
        assert "session-11" not in first_tags


# ── Lockfile (re-entry guard) Tests ─────────────────────────────────


class TestLockfile:
    def test_acquire_release_roundtrip(self, tmp_path, monkeypatch):
        import skills.hot_decompose.run as mod
        lock = tmp_path / ".hot_decompose.lock"
        monkeypatch.setattr(mod, "LOCKFILE", lock)

        assert mod.is_locked() is False
        assert mod._acquire_lock() is True
        assert lock.exists()
        assert mod.is_locked() is True

        # Second acquire should fail (already held)
        assert mod._acquire_lock() is False

        mod._release_lock()
        assert lock.exists() is False
        assert mod.is_locked() is False

    def test_stale_lock_is_ignored(self, tmp_path, monkeypatch):
        import os, time
        import skills.hot_decompose.run as mod
        lock = tmp_path / ".hot_decompose.lock"
        monkeypatch.setattr(mod, "LOCKFILE", lock)
        monkeypatch.setattr(mod, "LOCK_STALE_SECONDS", 1)

        lock.write_text("pid=999\n")
        # Backdate the file by 5 seconds
        old = time.time() - 5
        os.utime(lock, (old, old))

        assert mod.is_locked() is False  # stale → treated as no lock
        # Acquire should succeed despite the stale file existing
        assert mod._acquire_lock() is True
        mod._release_lock()

    def test_cmd_decompose_skips_when_locked(self, tmp_path, monkeypatch, capsys):
        text = "# Hot Context — Terragraf\n\n## What's Done (Session 12)\n\nbody\n"
        mod, hot_file, calls = _patch_hot_decompose(monkeypatch, tmp_path, text)
        lock = tmp_path / ".hot_decompose.lock"
        monkeypatch.setattr(mod, "LOCKFILE", lock)

        # Pre-create the lockfile to simulate "already in progress"
        lock.write_text(f"pid={123}\n")
        original = hot_file.read_text(encoding="utf-8")

        rc = mod.cmd_decompose(dry_run=False)
        assert rc == 0
        # File should be untouched
        assert hot_file.read_text(encoding="utf-8") == original
        # No knowledge_writer calls
        writer_calls = [c for c in calls if any("knowledge_writer" in str(p) for p in c)]
        assert writer_calls == []
        # Stdout should mention the skip
        out = capsys.readouterr().out
        assert "already in progress" in out

        # Lockfile NOT removed by the skipped invocation (caller still holds it)
        assert lock.exists()


class TestSlugify:
    def test_strips_heading_prefix(self):
        assert _slugify("## Decisions Made") == "decisions-made"

    def test_handles_special_chars(self):
        assert _slugify("## Win32 + X11 Gotcha!") == "win32-x11-gotcha"
