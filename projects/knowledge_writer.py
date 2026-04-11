"""
knowledge_writer — Append entries to the Knowledge Registry (KNOWLEDGE.toml).

Usage:
    python knowledge_writer.py --id <slug> --source <project> --category <cat>
                               --summary "..." --detail "..." --tags "t1,t2"

Categories: pattern | decision | integration | domain | caveat
Deduplicates by id — rejects if an entry with the same id already exists.
"""

import argparse
import sys
import tomllib
from datetime import date
from pathlib import Path

KNOWLEDGE_FILE = Path(__file__).resolve().parent / "KNOWLEDGE.toml"

VALID_CATEGORIES = {"pattern", "decision", "integration", "domain", "caveat"}


def load_existing_ids():
    """Return set of existing knowledge entry ids."""
    if not KNOWLEDGE_FILE.exists():
        return set()
    data = tomllib.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    return {entry["id"] for entry in data.get("knowledge", [])}


def format_tags(tags_str):
    """Convert comma-separated string to TOML array literal."""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    return "[" + ", ".join(f'"{t}"' for t in tags) + "]"


def append_entry(entry_id, source, category, summary, detail, tags_str):
    """Append a new [[knowledge]] block to KNOWLEDGE.toml."""
    existing = load_existing_ids()

    if entry_id in existing:
        print(f"Error: knowledge entry '{entry_id}' already exists. Use a unique id.")
        return 1

    if category not in VALID_CATEGORIES:
        print(f"Error: invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
        return 1

    tags_toml = format_tags(tags_str) if tags_str else '[]'
    today = date.today().isoformat()

    # Use TOML triple-quoted basic strings for summary/detail so newlines
    # and most quotes survive without escaping. Triple-double-quote sequences
    # in the content are escaped to avoid prematurely ending the string.
    def _ts(s: str) -> str:
        return s.replace('"""', '\\"\\"\\"')

    block = f'''
[[knowledge]]
id = "{entry_id}"
source = "{source}"
category = "{category}"
summary = """{_ts(summary)}"""
detail = """{_ts(detail)}"""
tags = {tags_toml}
created = "{today}"
'''

    # Create file with header if it doesn't exist
    if not KNOWLEDGE_FILE.exists():
        KNOWLEDGE_FILE.write_text(
            "# Knowledge Registry — reusable patterns, decisions, and caveats from project work.\n",
            encoding="utf-8",
        )

    with open(KNOWLEDGE_FILE, "a", encoding="utf-8") as f:
        f.write(block)

    print(f"Added knowledge entry: {entry_id}")
    return 0


def cli():
    parser = argparse.ArgumentParser(description="Append an entry to the Knowledge Registry")
    parser.add_argument("--id", required=True, help="Unique slug for this entry")
    parser.add_argument("--source", required=True, help="Project or context that produced this knowledge")
    parser.add_argument("--category", required=True, choices=sorted(VALID_CATEGORIES),
                        help="Entry category")
    parser.add_argument("--summary", required=True, help="One-line summary")
    parser.add_argument("--detail", required=True, help="Full explanation")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    args = parser.parse_args()
    sys.exit(append_entry(args.id, args.source, args.category, args.summary, args.detail, args.tags))


if __name__ == "__main__":
    cli()
