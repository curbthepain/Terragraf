"""
.scaffold/sharpen/engine.py
Self-sharpening engine — analyzes route/table usage and updates scaffolding.

Four passes:
  1. Stale: entries with no hits or last_hit > threshold → comment out
  2. Hot: entries with disproportionately high hits → annotate
  3. New errors: recurring unmatched errors → add to errors.table
  4. Low-confidence: routes with poor success rate → flag in report
"""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .config import SharpenConfig
from .tracker import load_analytics, save_analytics, _acquire_lock, _release_lock


SCAFFOLD_DIR = Path(__file__).parent.parent


@dataclass
class SharpenReport:
    stale_entries: list = field(default_factory=list)
    hot_entries: list = field(default_factory=list)
    new_error_rows: list = field(default_factory=list)
    low_confidence: list = field(default_factory=list)
    total_entries_tracked: int = 0
    total_hits: int = 0


class SharpenEngine:
    def __init__(self, scaffold_dir: Path = None, config: SharpenConfig = None):
        self.scaffold_dir = scaffold_dir or SCAFFOLD_DIR
        self.config = config or SharpenConfig()

    def analyze(self) -> SharpenReport:
        data = load_analytics()
        report = SharpenReport()
        report.total_entries_tracked = len(data.get("entries", {}))
        report.total_hits = sum(e.get("hit_count", 0) for e in data.get("entries", {}).values())

        self._pass_stale(data, report)
        self._pass_hot(data, report)
        self._pass_new_errors(data, report)
        self._pass_low_confidence(data, report)

        return report

    def apply(self, report: SharpenReport, dry_run: bool = False) -> list:
        changes = []

        for entry in report.stale_entries:
            desc = f"[stale] {entry['source_file']}: {entry['entry_key']}"
            if not dry_run:
                self._comment_out_entry(
                    self.scaffold_dir / entry["source_file"],
                    entry["entry_key"],
                    entry["is_route"],
                )
            changes.append(desc)

        for entry in report.hot_entries:
            desc = f"[hot: {entry['hit_count']} hits] {entry['source_file']}: {entry['entry_key']}"
            if not dry_run:
                self._annotate_hot(
                    self.scaffold_dir / entry["source_file"],
                    entry["entry_key"],
                    entry["hit_count"],
                    entry["is_route"],
                )
            changes.append(desc)

        for row in report.new_error_rows:
            desc = f"[auto-add] errors.table: {row['pattern']}"
            if not dry_run:
                self._add_error_entry(row["pattern"], row["occurrences"])
                self._clear_matched_unmatched(row["pattern"])
            changes.append(desc)

        for entry in report.low_confidence:
            total = entry["completed"] + entry["failed"]
            rate = entry["completed"] / total * 100 if total else 0
            changes.append(
                f"[low-confidence: {rate:.0f}% success] {entry['source_file']}: {entry['entry_key']}"
            )

        return changes

    # ── Pass 1: Stale ────────────────────────────────────────────────

    def _pass_stale(self, data: dict, report: SharpenReport):
        now = datetime.now(timezone.utc)
        threshold = timedelta(days=self.config.stale_threshold_days)
        analytics_age = now - _parse_iso(data.get("created_at", ""))

        # Only flag stale entries if analytics has been running long enough
        if analytics_age < threshold:
            return

        all_file_entries = self._scan_all_entries()

        for source_file, entry_key, is_route in all_file_entries:
            key = f"{source_file}::{entry_key}"
            tracked = data.get("entries", {}).get(key)

            if tracked is None:
                # Never hit at all
                report.stale_entries.append({
                    "source_file": source_file,
                    "entry_key": entry_key,
                    "is_route": is_route,
                    "reason": "never hit",
                })
            else:
                last_hit = _parse_iso(tracked.get("last_hit", ""))
                if last_hit and (now - last_hit) > threshold:
                    report.stale_entries.append({
                        "source_file": source_file,
                        "entry_key": entry_key,
                        "is_route": is_route,
                        "reason": f"last hit {tracked['last_hit']}",
                    })

    # ── Pass 2: Hot ──────────────────────────────────────────────────

    def _pass_hot(self, data: dict, report: SharpenReport):
        entries = data.get("entries", {})
        if not entries:
            return

        # Group by source file
        by_file: dict[str, list] = {}
        for key, entry in entries.items():
            sf = entry["source_file"]
            by_file.setdefault(sf, []).append(entry)

        for source_file, file_entries in by_file.items():
            counts = sorted(e["hit_count"] for e in file_entries)
            if len(counts) < 2:
                continue

            # Use median-based threshold: entry is hot if hits > multiplier * median
            # and meets minimum hit count. More robust than mean+stddev with outliers.
            median = counts[len(counts) // 2]
            threshold = max(
                self.config.min_hits_for_hot,
                median * self.config.hot_threshold_multiplier,
            )

            is_route = source_file.startswith("routes/")
            for entry in file_entries:
                if entry["hit_count"] >= threshold:
                    report.hot_entries.append({
                        "source_file": source_file,
                        "entry_key": entry["entry_key"],
                        "hit_count": entry["hit_count"],
                        "is_route": is_route,
                    })

    # ── Pass 3: New errors ───────────────────────────────────────────

    def _pass_new_errors(self, data: dict, report: SharpenReport):
        for err in data.get("unmatched_errors", []):
            if err.get("occurrences", 0) >= self.config.min_error_occurrences:
                report.new_error_rows.append({
                    "pattern": err["error_text"],
                    "occurrences": err["occurrences"],
                })

    # ── Pass 4: Low confidence ───────────────────────────────────────

    def _pass_low_confidence(self, data: dict, report: SharpenReport):
        for key, entry in data.get("entries", {}).items():
            outcomes = entry.get("outcomes", {})
            completed = outcomes.get("completed", 0)
            failed = outcomes.get("failed", 0)
            total = completed + failed
            if total >= 4 and completed / total < 0.25:
                report.low_confidence.append({
                    "source_file": entry["source_file"],
                    "entry_key": entry["entry_key"],
                    "completed": completed,
                    "failed": failed,
                })

    # ── File scanning ────────────────────────────────────────────────

    def _scan_all_entries(self) -> list:
        """Scan all .route and .table files, return (source_file, entry_key, is_route) tuples."""
        results = []

        # Scan routes
        routes_dir = self.scaffold_dir / "routes"
        if routes_dir.exists():
            for f in routes_dir.glob("*.route"):
                for entry_key in self._parse_route_keys(f):
                    results.append((f"routes/{f.name}", entry_key, True))

        # Scan tables
        tables_dir = self.scaffold_dir / "tables"
        if tables_dir.exists():
            for f in tables_dir.glob("*.table"):
                for entry_key in self._parse_table_keys(f):
                    results.append((f"tables/{f.name}", entry_key, False))

        return results

    def _parse_route_keys(self, path: Path) -> list:
        keys = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "->" in line:
                    key = line.split("->")[0].strip()
                    keys.append(key)
        return keys

    def _parse_table_keys(self, path: Path) -> list:
        keys = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    key = line.split("|")[0].strip()
                    keys.append(key)
        return keys

    # ── File modification ────────────────────────────────────────────

    def _comment_out_entry(self, file_path: Path, entry_key: str, is_route: bool):
        if not file_path.exists():
            return
        lines = file_path.read_text().splitlines(keepends=True)
        sep = "->" if is_route else "|"
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if (not stripped.startswith("#") and sep in stripped and
                    stripped.split(sep)[0].strip() == entry_key):
                new_lines.append(f"# [stale] {line.lstrip()}" if line.endswith("\n")
                                 else f"# [stale] {line.lstrip()}\n")
            else:
                new_lines.append(line)
        file_path.write_text("".join(new_lines))

    def _annotate_hot(self, file_path: Path, entry_key: str, hit_count: int, is_route: bool):
        if not file_path.exists():
            return
        lines = file_path.read_text().splitlines(keepends=True)
        sep = "->" if is_route else "|"
        annotation = f"# [hot: {hit_count} hits]\n"
        new_lines = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()

            # Remove existing hot annotation
            if stripped.startswith("# [hot:"):
                if i + 1 < len(lines):
                    next_stripped = lines[i + 1].strip()
                    if (not next_stripped.startswith("#") and sep in next_stripped and
                            next_stripped.split(sep)[0].strip() == entry_key):
                        i += 1  # skip old annotation, will re-add below
                        continue

            if (not stripped.startswith("#") and sep in stripped and
                    stripped.split(sep)[0].strip() == entry_key):
                new_lines.append(annotation)
                new_lines.append(lines[i])
            else:
                new_lines.append(lines[i])
            i += 1
        file_path.write_text("".join(new_lines))

    def _add_error_entry(self, pattern: str, occurrences: int):
        errors_table = self.scaffold_dir / "tables" / "errors.table"
        if not errors_table.exists():
            return
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = f"\n# [auto-added {today}, {occurrences} occurrences]\n"
        entry += f"{pattern} | (unknown cause) | (investigate) | (see instance reports)\n"
        with open(errors_table, "a") as f:
            f.write(entry)

    def _clear_matched_unmatched(self, pattern: str):
        """Remove processed unmatched errors from analytics."""
        if not _acquire_lock():
            return
        try:
            data = load_analytics()
            data["unmatched_errors"] = [
                e for e in data["unmatched_errors"]
                if e["error_text"] != pattern
            ]
            save_analytics(data)
        finally:
            _release_lock()


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
