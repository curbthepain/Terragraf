#!/usr/bin/env python3
"""
.scaffold/sharpen/cli.py
CLI entry point for terra sharpen commands.

Usage:
    python cli.py status            Show analytics summary
    python cli.py run [--dry-run]   Run sharpening engine
    python cli.py reset             Clear analytics data
"""

import sys
from pathlib import Path

# Ensure scaffold is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from sharpen.tracker import load_analytics, save_analytics, _empty_analytics, ANALYTICS_FILE
from sharpen.engine import SharpenEngine
from sharpen.config import SharpenConfig


# ANSI colors
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"


def cmd_status():
    data = load_analytics()
    entries = data.get("entries", {})
    total_hits = sum(e.get("hit_count", 0) for e in entries.values())
    unmatched = data.get("unmatched_errors", [])
    outcomes = data.get("instance_outcomes", [])

    print(f"{BOLD}Sharpen Analytics{RESET}")
    print()
    print(f"  entries tracked   {len(entries)}")
    print(f"  total hits        {total_hits}")
    print(f"  instance outcomes {len(outcomes)}")
    print(f"  unmatched errors  {len(unmatched)}")
    print()

    if entries:
        # Top 5 hottest
        sorted_entries = sorted(entries.values(), key=lambda e: e.get("hit_count", 0), reverse=True)
        print(f"{BOLD}Top entries{RESET}")
        for entry in sorted_entries[:5]:
            hits = entry["hit_count"]
            color = GREEN if hits >= 5 else YELLOW if hits >= 2 else DIM
            print(f"  {color}{hits:>4}{RESET}  {entry['source_file']}::{entry['entry_key']}")
        print()

    if unmatched:
        print(f"{BOLD}Unmatched errors{RESET}")
        for err in sorted(unmatched, key=lambda e: e.get("occurrences", 0), reverse=True)[:5]:
            occ = err["occurrences"]
            color = RED if occ >= 3 else YELLOW
            print(f"  {color}{occ:>4}x{RESET}  {err['error_text'][:80]}")
        print()

    # Run a quick analysis for stale/hot counts
    engine = SharpenEngine()
    report = engine.analyze()
    if report.stale_entries or report.hot_entries or report.low_confidence:
        print(f"{BOLD}Sharpening opportunities{RESET}")
        if report.stale_entries:
            print(f"  {DIM}stale entries:{RESET}         {len(report.stale_entries)}")
        if report.hot_entries:
            print(f"  {GREEN}hot entries:{RESET}           {len(report.hot_entries)}")
        if report.new_error_rows:
            print(f"  {CYAN}new error patterns:{RESET}    {len(report.new_error_rows)}")
        if report.low_confidence:
            print(f"  {YELLOW}low-confidence routes:{RESET} {len(report.low_confidence)}")
        print()
        print(f"  Run {CYAN}terra sharpen run{RESET} to apply, or {CYAN}terra sharpen run --dry-run{RESET} to preview.")


def cmd_run(dry_run: bool = False):
    engine = SharpenEngine()
    report = engine.analyze()
    changes = engine.apply(report, dry_run=dry_run)

    if not changes:
        print(f"  {DIM}No sharpening needed. Scaffolding is up to date.{RESET}")
        return

    mode = f"{YELLOW}dry run{RESET}" if dry_run else f"{GREEN}applied{RESET}"
    print(f"{BOLD}Sharpen {mode}{RESET}")
    print()
    for change in changes:
        if change.startswith("[stale]"):
            print(f"  {DIM}{change}{RESET}")
        elif change.startswith("[hot:"):
            print(f"  {GREEN}{change}{RESET}")
        elif change.startswith("[auto-add]"):
            print(f"  {CYAN}{change}{RESET}")
        elif change.startswith("[low-confidence"):
            print(f"  {YELLOW}{change}{RESET}")
        else:
            print(f"  {change}")

    print()
    print(f"  {len(changes)} change{'s' if len(changes) != 1 else ''} {'previewed' if dry_run else 'applied'}.")


def cmd_reset():
    data = _empty_analytics()
    save_analytics(data)
    print(f"  {GREEN}Analytics reset.{RESET} {ANALYTICS_FILE}")


def main():
    args = sys.argv[1:] if len(sys.argv) > 1 else ["status"]
    action = args[0]

    if action == "status":
        cmd_status()
    elif action == "run":
        dry_run = "--dry-run" in args
        cmd_run(dry_run=dry_run)
    elif action == "reset":
        cmd_reset()
    else:
        print(f"Usage: terra sharpen <status|run [--dry-run]|reset>")
        sys.exit(1)


if __name__ == "__main__":
    main()
