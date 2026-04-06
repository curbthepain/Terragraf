"""
skills/runner.py — Skill discovery, matching, and execution.

Lists registered skills, matches intents to skills, and runs skill entry points.
"""

import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python < 3.11

SKILLS_DIR = Path(__file__).parent.resolve()
SCAFFOLD = SKILLS_DIR.parent
TERRA_ROOT = SCAFFOLD.parent


def _load_manifest(skill_dir):
    """Load and return a SKILL.toml manifest dict, or None on failure."""
    manifest_path = skill_dir / "SKILL.toml"
    if not manifest_path.exists():
        return None
    return tomllib.loads(manifest_path.read_text(encoding="utf-8"))


def list_skills():
    """Return list of (name, manifest_dict) for all valid skills."""
    skills = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        manifest = _load_manifest(child)
        if manifest and "skill" in manifest:
            skills.append((child.name, manifest))
    return skills


def match_skill(intent):
    """Match an intent string to a skill name. Returns (name, manifest) or None."""
    intent_lower = intent.lower().strip()
    for name, manifest in list_skills():
        triggers = manifest.get("triggers", {})
        intents = triggers.get("intents", [])
        for trigger in intents:
            if trigger.lower() in intent_lower or intent_lower in trigger.lower():
                return (name, manifest)
    return None


def run_skill(name, args=None):
    """Execute a skill by name. Returns subprocess return code."""
    skill_dir = SKILLS_DIR / name
    manifest = _load_manifest(skill_dir)
    if not manifest:
        print(f"Error: skill '{name}' not found or missing SKILL.toml")
        return 1

    entry = manifest["skill"].get("entry", "run.py")
    entry_path = skill_dir / entry
    if not entry_path.exists():
        print(f"Error: entry point '{entry}' not found for skill '{name}'")
        return 1

    cmd = [sys.executable, str(entry_path)] + (args or [])
    result = subprocess.run(cmd, cwd=str(TERRA_ROOT))
    return result.returncode


def run_skill_capture(name, args=None):
    """Execute a skill and capture output. Returns (returncode, stdout, stderr)."""
    skill_dir = SKILLS_DIR / name
    manifest = _load_manifest(skill_dir)
    if not manifest:
        return (1, "", f"Error: skill '{name}' not found or missing SKILL.toml")

    entry = manifest["skill"].get("entry", "run.py")
    entry_path = skill_dir / entry
    if not entry_path.exists():
        return (1, "", f"Error: entry point '{entry}' not found for skill '{name}'")

    cmd = [sys.executable, str(entry_path)] + (args or [])
    result = subprocess.run(cmd, cwd=str(TERRA_ROOT), capture_output=True, text=True)
    return (result.returncode, result.stdout, result.stderr)


def run_skill_stream(name, args=None, on_line=None):
    """Execute a skill and stream stdout line-by-line via on_line(line).

    stderr is merged into stdout so callers see everything in order.
    Returns the subprocess return code after wait().
    """
    skill_dir = SKILLS_DIR / name
    manifest = _load_manifest(skill_dir)
    if not manifest:
        if on_line:
            on_line(f"Error: skill '{name}' not found or missing SKILL.toml")
        return 1

    entry = manifest["skill"].get("entry", "run.py")
    entry_path = skill_dir / entry
    if not entry_path.exists():
        if on_line:
            on_line(f"Error: entry point '{entry}' not found for skill '{name}'")
        return 1

    cmd = [sys.executable, "-u", str(entry_path)] + (args or [])
    proc = subprocess.Popen(
        cmd,
        cwd=str(TERRA_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
    )
    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                if on_line:
                    on_line(line.rstrip("\n"))
    finally:
        proc.wait()
    return proc.returncode


def print_skills():
    """Print a formatted list of all registered skills."""
    skills = list_skills()
    if not skills:
        print("  No skills registered.")
        return

    for name, manifest in skills:
        info = manifest.get("skill", {})
        desc = info.get("description", "")
        stype = info.get("type", "")
        version = info.get("version", "")
        triggers = manifest.get("triggers", {})
        commands = triggers.get("commands", [])
        print(f"  {name}")
        print(f"    {desc}")
        if commands:
            print(f"    commands: {', '.join(commands)}")
        print()
