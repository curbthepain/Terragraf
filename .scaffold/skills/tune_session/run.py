"""
tune_session — Guided thematic calibration workflow.

Delegates to the existing tuning CLI with enhanced workflows:
calibrate (guided full session), export/import state.

Usage:
    python run.py [status|list|load|zone|set|calibrate|export|import|instructions] [args]
"""

import json
import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
TERRA_ROOT = SCAFFOLD.parent

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def _load_engine():
    sys.path.insert(0, str(SCAFFOLD))
    from tuning.engine import ThematicEngine
    engine = ThematicEngine(str(SCAFFOLD / "tuning" / "profiles"))
    # Load saved state if exists
    state_file = SCAFFOLD / "tuning" / ".tuning_state.json"
    if state_file.exists():
        try:
            engine.import_state(json.loads(state_file.read_text()))
        except Exception:
            pass
    return engine


def _save_state(engine):
    state_file = SCAFFOLD / "tuning" / ".tuning_state.json"
    state_file.write_text(json.dumps(engine.export_state(), indent=2))


def cmd_calibrate():
    """Guided full calibration — lists profiles, shows details, prints instructions."""
    engine = _load_engine()

    print(f"{BOLD}Thematic Calibration{RESET}")
    print()

    # List profiles
    profiles = engine.list_profiles()
    print(f"  {BOLD}Available Profiles:{RESET}")
    for i, p in enumerate(profiles):
        print(f"    {i+1}. {CYAN}{p}{RESET}")
    print()

    # Show current state
    if engine._profile:
        print(f"  {BOLD}Active:{RESET} {GREEN}{engine._profile.name}{RESET}")
        print(f"  Genre: {engine._profile.genre}")
        print(f"  Promise: {engine._profile.thematic_promise}")
        print()

        axes = engine.get_active_axes()
        print(f"  {BOLD}Axes:{RESET}")
        for k, v in axes.items():
            print(f"    {k}: {v}")
        print()

        knobs = engine.get_knob_state()
        if knobs:
            print(f"  {BOLD}Knobs:{RESET}")
            for k, v in knobs.items():
                print(f"    {k}: {v}")
            print()

        print(f"  {BOLD}Behavioral Instructions:{RESET}")
        instructions = engine.get_behavioral_instructions()
        for line in instructions.splitlines():
            print(f"  {line}")
    else:
        print(f"  {YELLOW}No profile loaded. Use: terra tune load <name>{RESET}")

    return 0


def cmd_export():
    """Export engine state to stdout as JSON."""
    engine = _load_engine()
    if not engine._profile:
        print(f"  {YELLOW}No profile loaded{RESET}")
        return 1
    print(json.dumps(engine.export_state(), indent=2))
    return 0


def cmd_import():
    """Import engine state from stdin."""
    engine = _load_engine()
    try:
        state = json.load(sys.stdin)
        engine.import_state(state)
        _save_state(engine)
        print(f"  {GREEN}State imported{RESET}")
        return 0
    except Exception as e:
        print(f"  {YELLOW}Import failed: {e}{RESET}")
        return 1


def cli():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    rest = sys.argv[2:]

    if action == "calibrate":
        return cmd_calibrate()
    elif action == "export":
        return cmd_export()
    elif action == "import":
        return cmd_import()
    else:
        # Delegate to existing tuning CLI
        return subprocess.run(
            [sys.executable, str(SCAFFOLD / "tuning" / "cli.py"), action] + rest
        ).returncode


if __name__ == "__main__":
    sys.exit(cli())
