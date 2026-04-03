"""Tests for the self-sharpening engine — config, tracker, engine, cli."""

import sys
import json
import os
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Config ──────────────────────────────────────────────────────────

class TestSharpenConfig:
    def test_defaults(self):
        from sharpen.config import SharpenConfig
        cfg = SharpenConfig()
        assert cfg.stale_threshold_days == 30
        assert cfg.hot_threshold_multiplier == 3.0
        assert cfg.min_hits_for_hot == 5
        assert cfg.min_error_occurrences == 3
        assert cfg.max_instance_outcomes == 200
        assert cfg.max_queries_per_entry == 20
        assert cfg.lock_timeout_seconds == 5.0

    def test_custom_values(self):
        from sharpen.config import SharpenConfig
        cfg = SharpenConfig(stale_threshold_days=7, min_hits_for_hot=10)
        assert cfg.stale_threshold_days == 7
        assert cfg.min_hits_for_hot == 10


# ── Tracker ─────────────────────────────────────────────────────────

class TestTrackerHelpers:
    def test_normalize_error_strips_paths(self):
        from sharpen.tracker import _normalize_error
        result = _normalize_error("FileNotFoundError: /home/user/foo.py not found")
        assert "<path>" in result
        assert "/home/user" not in result

    def test_normalize_error_strips_line_numbers(self):
        from sharpen.tracker import _normalize_error
        result = _normalize_error("Error at line 42 in module")
        assert "line N" in result
        assert "42" not in result

    def test_normalize_error_strips_hex(self):
        from sharpen.tracker import _normalize_error
        result = _normalize_error("Object at 0xdeadbeef crashed")
        assert "0xN" in result
        assert "0xdeadbeef" not in result

    def test_normalize_error_strips_windows_paths(self):
        from sharpen.tracker import _normalize_error
        result = _normalize_error("Error in C:\\Users\\admin\\file.py")
        assert "<path>" in result
        assert "C:\\Users" not in result

    def test_empty_analytics(self):
        from sharpen.tracker import _empty_analytics
        data = _empty_analytics()
        assert data["version"] == 1
        assert "created_at" in data
        assert "updated_at" in data
        assert data["entries"] == {}
        assert data["unmatched_errors"] == []
        assert data["instance_outcomes"] == []


class TestTrackerIO:
    def setup_method(self):
        import sharpen.tracker as tracker
        self._orig_analytics = tracker.ANALYTICS_FILE
        self._orig_lock = tracker.LOCK_FILE
        self._tmpdir = Path(tempfile.mkdtemp())
        tracker.ANALYTICS_FILE = self._tmpdir / "analytics.json"
        tracker.LOCK_FILE = self._tmpdir / "analytics.lock"

    def teardown_method(self):
        import sharpen.tracker as tracker
        tracker.ANALYTICS_FILE = self._orig_analytics
        tracker.LOCK_FILE = self._orig_lock
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_load_empty(self):
        from sharpen.tracker import load_analytics
        data = load_analytics()
        assert data["version"] == 1
        assert data["entries"] == {}

    def test_save_and_load(self):
        from sharpen.tracker import load_analytics, save_analytics
        data = load_analytics()
        data["entries"]["test::key"] = {"hit_count": 5}
        save_analytics(data)

        loaded = load_analytics()
        assert loaded["entries"]["test::key"]["hit_count"] == 5

    def test_record_hit(self):
        from sharpen.tracker import record_hit, load_analytics
        record_hit("routes/test.route", "bug", "fix a bug")
        data = load_analytics()
        key = "routes/test.route::bug"
        assert key in data["entries"]
        assert data["entries"][key]["hit_count"] == 1
        assert "fix a bug" in data["entries"][key]["queries"]

    def test_record_hit_increments(self):
        from sharpen.tracker import record_hit, load_analytics
        record_hit("routes/test.route", "bug", "q1")
        record_hit("routes/test.route", "bug", "q2")
        data = load_analytics()
        key = "routes/test.route::bug"
        assert data["entries"][key]["hit_count"] == 2

    def test_record_hit_deduplicates_queries(self):
        from sharpen.tracker import record_hit, load_analytics
        record_hit("routes/test.route", "bug", "same query")
        record_hit("routes/test.route", "bug", "same query")
        data = load_analytics()
        key = "routes/test.route::bug"
        assert data["entries"][key]["queries"].count("same query") == 1

    def test_record_outcome(self):
        from sharpen.tracker import record_outcome, load_analytics
        record_outcome("inst-1", "task-1", "completed", ["routes/test.route"])
        data = load_analytics()
        assert len(data["instance_outcomes"]) == 1
        assert data["instance_outcomes"][0]["status"] == "completed"

    def test_record_outcome_tracks_unmatched_error(self):
        from sharpen.tracker import record_outcome, load_analytics
        record_outcome("inst-1", "task-1", "failed", [],
                       error_text="KeyError: 'missing_key'")
        data = load_analytics()
        assert len(data["unmatched_errors"]) == 1
        assert data["unmatched_errors"][0]["occurrences"] == 1

    def test_record_outcome_increments_unmatched(self):
        from sharpen.tracker import record_outcome, load_analytics
        for i in range(3):
            record_outcome(f"inst-{i}", f"task-{i}", "failed", [],
                           error_text="KeyError: 'missing_key'")
        data = load_analytics()
        assert len(data["unmatched_errors"]) == 1
        assert data["unmatched_errors"][0]["occurrences"] == 3

    def test_lock_acquire_release(self):
        from sharpen.tracker import _acquire_lock, _release_lock, LOCK_FILE
        import sharpen.tracker as tracker
        assert _acquire_lock()
        assert tracker.LOCK_FILE.exists()
        _release_lock()
        assert not tracker.LOCK_FILE.exists()

    def test_stale_lock_cleanup(self):
        from sharpen.tracker import _acquire_lock, _release_lock
        import sharpen.tracker as tracker
        # Create stale lock
        tracker.LOCK_FILE.write_text("99999")
        # Backdate it
        os.utime(str(tracker.LOCK_FILE), (0, 0))
        # Should succeed by cleaning stale lock
        assert _acquire_lock()
        _release_lock()


# ── Engine ──────────────────────────────────────────────────────────

class TestSharpenEngine:
    def setup_method(self):
        import sharpen.tracker as tracker
        self._orig_analytics = tracker.ANALYTICS_FILE
        self._orig_lock = tracker.LOCK_FILE
        self._tmpdir = Path(tempfile.mkdtemp())
        tracker.ANALYTICS_FILE = self._tmpdir / "analytics.json"
        tracker.LOCK_FILE = self._tmpdir / "analytics.lock"

    def teardown_method(self):
        import sharpen.tracker as tracker
        tracker.ANALYTICS_FILE = self._orig_analytics
        tracker.LOCK_FILE = self._orig_lock
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_analyze_empty(self):
        from sharpen.engine import SharpenEngine
        engine = SharpenEngine()
        report = engine.analyze()
        assert report.total_entries_tracked == 0
        assert report.total_hits == 0

    def test_report_fields(self):
        from sharpen.engine import SharpenReport
        report = SharpenReport()
        assert report.stale_entries == []
        assert report.hot_entries == []
        assert report.new_error_rows == []
        assert report.low_confidence == []

    def test_pass_hot_detects_hot_entries(self):
        from sharpen.engine import SharpenEngine, SharpenReport
        from sharpen.tracker import save_analytics, _empty_analytics
        from sharpen.config import SharpenConfig

        data = _empty_analytics()
        # One entry with many hits, others with few
        for i in range(5):
            data["entries"][f"routes/test.route::entry{i}"] = {
                "source_file": "routes/test.route",
                "entry_key": f"entry{i}",
                "hit_count": 2,
                "first_hit": data["created_at"],
                "last_hit": data["created_at"],
                "queries": [],
                "outcomes": {"completed": 0, "failed": 0},
            }
        # Make one entry hot
        data["entries"]["routes/test.route::entry0"]["hit_count"] = 50
        save_analytics(data)

        engine = SharpenEngine(config=SharpenConfig(min_hits_for_hot=5))
        report = SharpenReport()
        engine._pass_hot(data, report)
        assert len(report.hot_entries) >= 1
        assert report.hot_entries[0]["entry_key"] == "entry0"

    def test_pass_new_errors(self):
        from sharpen.engine import SharpenEngine, SharpenReport
        from sharpen.config import SharpenConfig

        data = {
            "unmatched_errors": [
                {"error_text": "ImportError: no module", "occurrences": 5},
                {"error_text": "rare error", "occurrences": 1},
            ]
        }
        engine = SharpenEngine(config=SharpenConfig(min_error_occurrences=3))
        report = SharpenReport()
        engine._pass_new_errors(data, report)
        assert len(report.new_error_rows) == 1
        assert report.new_error_rows[0]["pattern"] == "ImportError: no module"

    def test_pass_low_confidence(self):
        from sharpen.engine import SharpenEngine, SharpenReport

        data = {
            "entries": {
                "routes/bad.route::flaky": {
                    "source_file": "routes/bad.route",
                    "entry_key": "flaky",
                    "hit_count": 10,
                    "outcomes": {"completed": 1, "failed": 9},
                },
                "routes/good.route::solid": {
                    "source_file": "routes/good.route",
                    "entry_key": "solid",
                    "hit_count": 10,
                    "outcomes": {"completed": 9, "failed": 1},
                },
            }
        }
        engine = SharpenEngine()
        report = SharpenReport()
        engine._pass_low_confidence(data, report)
        assert len(report.low_confidence) == 1
        assert report.low_confidence[0]["entry_key"] == "flaky"

    def test_apply_dry_run(self):
        from sharpen.engine import SharpenEngine, SharpenReport
        engine = SharpenEngine()
        report = SharpenReport()
        report.stale_entries.append({
            "source_file": "routes/test.route",
            "entry_key": "old_entry",
            "is_route": True,
            "reason": "never hit",
        })
        changes = engine.apply(report, dry_run=True)
        assert len(changes) == 1
        assert "[stale]" in changes[0]

    def test_comment_out_entry(self):
        from sharpen.engine import SharpenEngine
        engine = SharpenEngine(scaffold_dir=self._tmpdir)
        routes_dir = self._tmpdir / "routes"
        routes_dir.mkdir()
        route_file = routes_dir / "test.route"
        route_file.write_text("bug -> routes/bugs.route\nfeature -> headers/project.h\n")

        engine._comment_out_entry(route_file, "bug", is_route=True)
        content = route_file.read_text()
        assert "# [stale]" in content
        assert "feature -> headers/project.h" in content

    def test_annotate_hot(self):
        from sharpen.engine import SharpenEngine
        engine = SharpenEngine(scaffold_dir=self._tmpdir)
        routes_dir = self._tmpdir / "routes"
        routes_dir.mkdir()
        route_file = routes_dir / "test.route"
        route_file.write_text("bug -> routes/bugs.route\n")

        engine._annotate_hot(route_file, "bug", 42, is_route=True)
        content = route_file.read_text()
        assert "# [hot: 42 hits]" in content

    def test_add_error_entry(self):
        from sharpen.engine import SharpenEngine
        engine = SharpenEngine(scaffold_dir=self._tmpdir)
        tables_dir = self._tmpdir / "tables"
        tables_dir.mkdir()
        errors_table = tables_dir / "errors.table"
        errors_table.write_text("# Errors table\nKeyError | fix | check keys | docs\n")

        engine._add_error_entry("ImportError: no module", 5)
        content = errors_table.read_text()
        assert "ImportError: no module" in content
        assert "[auto-added" in content

    def test_parse_route_keys(self):
        from sharpen.engine import SharpenEngine
        engine = SharpenEngine(scaffold_dir=self._tmpdir)
        routes_dir = self._tmpdir / "routes"
        routes_dir.mkdir()
        route_file = routes_dir / "test.route"
        route_file.write_text("# comment\nbug -> routes/bugs.route\nfeature -> headers/project.h\n")

        keys = engine._parse_route_keys(route_file)
        assert keys == ["bug", "feature"]

    def test_parse_table_keys(self):
        from sharpen.engine import SharpenEngine
        engine = SharpenEngine(scaffold_dir=self._tmpdir)
        tables_dir = self._tmpdir / "tables"
        tables_dir.mkdir()
        table_file = tables_dir / "errors.table"
        table_file.write_text("# Errors\nKeyError | fix it | do thing\nTypeError | cast | type check\n")

        keys = engine._parse_table_keys(table_file)
        assert keys == ["KeyError", "TypeError"]

    def test_parse_iso_valid(self):
        from sharpen.engine import _parse_iso
        dt = _parse_iso("2025-01-15T10:30:00+00:00")
        assert dt is not None
        assert dt.year == 2025

    def test_parse_iso_invalid(self):
        from sharpen.engine import _parse_iso
        assert _parse_iso("") is None
        assert _parse_iso("not a date") is None
