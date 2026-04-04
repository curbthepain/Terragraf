"""
consistency_scan — Validates scaffold structural integrity.

Checks:
  1. All headers/*.h module paths exist on disk
  2. All routes/*.route targets exist
  3. All tables/deps.table modules are declared in headers
  4. All skills/registry.table entries have valid SKILL.toml
"""

import re
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent

# ANSI colors
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def scan_headers():
    """Check that all #path declarations in headers/*.h point to real dirs."""
    issues = []
    headers_dir = SCAFFOLD / "headers"
    if not headers_dir.exists():
        return [("headers", "headers/ directory not found")]

    for h_file in sorted(headers_dir.glob("*.h")):
        content = h_file.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'#path\s+"([^"]+)"', content):
            rel_path = match.group(1)
            full_path = SCAFFOLD / rel_path
            if not full_path.exists():
                issues.append(("header", f"{h_file.name}: #path \"{rel_path}\" -> not found"))
    return issues


def scan_routes():
    """Check that all route targets exist as files or directories."""
    issues = []
    routes_dir = SCAFFOLD / "routes"
    if not routes_dir.exists():
        return [("routes", "routes/ directory not found")]

    for route_file in sorted(routes_dir.glob("*.route")):
        for line in route_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "->" not in line:
                continue
            _, _, target_part = line.partition("->")
            target = target_part.split("#")[0].strip()
            if not target:
                continue
            # Target can be a file or dir, possibly with glob
            target_clean = target.rstrip("*").rstrip("/")
            full_path = SCAFFOLD / target_clean
            if not full_path.exists():
                issues.append(("route", f"{route_file.name}: {target} -> not found"))
    return issues


def scan_deps_table():
    """Check that modules listed in deps.table are declared in headers."""
    issues = []
    deps_file = SCAFFOLD / "tables" / "deps.table"
    if not deps_file.exists():
        return []

    # Collect declared module names from headers
    declared = set()
    headers_dir = SCAFFOLD / "headers"
    if headers_dir.exists():
        for h_file in headers_dir.glob("*.h"):
            content = h_file.read_text(encoding="utf-8", errors="replace")
            for match in re.finditer(r'#module\s+(\w+)', content):
                declared.add(match.group(1))

    for line in deps_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 2:
            continue
        module = parts[0].strip()
        depends_on = parts[1].strip()
        for name in [module, depends_on]:
            if name and name not in declared:
                issues.append(("deps", f"deps.table: '{name}' not declared in any header"))
    return issues


def scan_skills():
    """Check that all registry.table entries have valid SKILL.toml."""
    issues = []
    skills_dir = SCAFFOLD / "skills"
    registry = skills_dir / "registry.table"
    if not registry.exists():
        return [("skills", "skills/registry.table not found")]

    for line in registry.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        name = parts[0].strip()
        entry = parts[2].strip()
        # Entry is relative to skills/
        entry_path = skills_dir / entry
        if not entry_path.exists():
            issues.append(("skill", f"registry.table: '{name}' entry '{entry}' -> not found"))
        # Check SKILL.toml
        skill_dir = entry_path.parent if entry_path.suffix == ".py" else skills_dir / name
        manifest = skill_dir / "SKILL.toml"
        if not manifest.exists():
            issues.append(("skill", f"registry.table: '{name}' missing SKILL.toml in {skill_dir.name}/"))
    return issues


def main():
    print(f"{BOLD}Consistency Scan{RESET}")
    print()

    all_issues = []
    checks = [
        ("Headers", scan_headers),
        ("Routes", scan_routes),
        ("Dependencies", scan_deps_table),
        ("Skills", scan_skills),
    ]

    for label, check_fn in checks:
        issues = check_fn()
        if issues:
            print(f"  {YELLOW}{label}{RESET}: {len(issues)} issue(s)")
            for category, msg in issues:
                print(f"    {RED}!{RESET} {msg}")
            all_issues.extend(issues)
        else:
            print(f"  {GREEN}{label}{RESET}: OK")

    print()
    total = len(all_issues)
    if total == 0:
        print(f"  {GREEN}All checks passed.{RESET}")
    else:
        print(f"  {YELLOW}{total} issue(s) found.{RESET}")

    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
