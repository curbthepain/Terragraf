"""
knowledge_reader — Query the Knowledge Registry (KNOWLEDGE.toml).

Usage:
    python knowledge_reader.py                          # list all (summaries)
    python knowledge_reader.py --tag fft                # filter by tag
    python knowledge_reader.py --category pattern       # filter by category
    python knowledge_reader.py --source music-viz       # filter by source
    python knowledge_reader.py --search "query"         # free-text search
    python knowledge_reader.py --tag fft --source x     # multiple filters AND together
"""

import argparse
import sys
import tomllib
from pathlib import Path

KNOWLEDGE_FILE = Path(__file__).resolve().parent / "KNOWLEDGE.toml"

# ANSI colors
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def load_entries():
    """Load all knowledge entries from KNOWLEDGE.toml."""
    if not KNOWLEDGE_FILE.exists():
        return []
    data = tomllib.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    return data.get("knowledge", [])


def filter_entries(entries, tag=None, category=None, source=None, search=None):
    """Apply filters (AND logic). Returns filtered list."""
    result = entries

    if tag:
        result = [e for e in result if tag.lower() in [t.lower() for t in e.get("tags", [])]]

    if category:
        result = [e for e in result if e.get("category", "").lower() == category.lower()]

    if source:
        result = [e for e in result if e.get("source", "").lower() == source.lower()]

    if search:
        q = search.lower()
        result = [e for e in result
                  if q in e.get("summary", "").lower()
                  or q in e.get("detail", "").lower()
                  or q in e.get("id", "").lower()]

    return result


def print_summary(entries):
    """Print entries as compact summaries."""
    if not entries:
        print("  No entries found.")
        return

    for entry in entries:
        eid = entry.get("id", "?")
        cat = entry.get("category", "")
        summary = entry.get("summary", "")
        print(f"  {BOLD}{eid}{RESET}  {DIM}[{cat}]{RESET}")
        print(f"    {summary}")
        print()


def print_detail(entries):
    """Print entries with full detail."""
    if not entries:
        print("  No entries found.")
        return

    for entry in entries:
        eid = entry.get("id", "?")
        cat = entry.get("category", "")
        src = entry.get("source", "")
        summary = entry.get("summary", "")
        detail = entry.get("detail", "")
        tags = ", ".join(entry.get("tags", []))
        created = entry.get("created", "")

        print(f"  {BOLD}{CYAN}{eid}{RESET}  {DIM}[{cat}]{RESET}  {DIM}from {src}{RESET}")
        print(f"    {summary}")
        if detail:
            print(f"    {YELLOW}{detail}{RESET}")
        if tags:
            print(f"    tags: {tags}")
        if created:
            print(f"    created: {created}")
        print()


def cli():
    parser = argparse.ArgumentParser(description="Query the Knowledge Registry")
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--source", help="Filter by source project")
    parser.add_argument("--search", help="Free-text search across summary and detail")
    args = parser.parse_args()

    entries = load_entries()
    has_filter = any([args.tag, args.category, args.source, args.search])

    filtered = filter_entries(entries, tag=args.tag, category=args.category,
                              source=args.source, search=args.search)

    print(f"\n{BOLD}Knowledge Registry{RESET}  ({len(filtered)} entries)\n")

    if has_filter:
        print_detail(filtered)
    else:
        print_summary(filtered)


if __name__ == "__main__":
    cli()
