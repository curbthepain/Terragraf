"""
.scaffold/tuning/cli.py
CLI entry point for `terra tune`.

Usage:
    terra tune                    — show active profile + current axes
    terra tune list               — list available universe profiles
    terra tune load <universe>    — load a universe profile
    terra tune zone <name>        — enter a zone (shift axes)
    terra tune zone --exit        — return to base profile
    terra tune set <knob> <val>   — adjust a custom knob
    terra tune axes               — print current thematic axes
    terra tune directive          — print current bot/behavior directive
    terra tune instructions       — print full behavioral instruction block
    terra tune promise            — print the thematic promise
"""

import json
import sys
from pathlib import Path

# Add scaffold to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tuning.engine import ThematicEngine
from tuning.tracker import record_profile_load, record_knob_adjustment

# Persistent state file for CLI sessions
STATE_FILE = Path(__file__).parent / ".tuning_state.json"


# ── Colors ───────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def _load_engine() -> ThematicEngine:
    """Load engine with persisted state if available."""
    engine = ThematicEngine()
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            profile_name = state.get("profile")
            if profile_name:
                engine.load(profile_name)
                engine.import_state(state)
        except Exception:
            pass
    return engine


def _save_state(engine: ThematicEngine):
    """Persist engine state for CLI sessions."""
    state = engine.export_state()
    if state:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)


def cmd_status(engine: ThematicEngine):
    """Show active profile and current axes."""
    if engine.profile is None:
        print(f"  {DIM}no profile loaded{RESET}")
        print(f"  {DIM}use: terra tune load <name>{RESET}")
        return

    p = engine.profile
    print(f"  {BOLD}{p.name}{RESET}  {DIM}{p.genre}{RESET}")
    print(f"  {CYAN}promise{RESET}  {p.thematic_promise}")
    if p.register:
        print(f"  {CYAN}register{RESET} {p.register}")
    print()

    axes = engine.get_active_axes()
    zone = engine.active_zone
    if zone:
        print(f"  {YELLOW}zone{RESET}     {zone.name}")
    for name, value in axes.items():
        print(f"  {GREEN}{name}{RESET}  {value}")
    print()

    if p.knobs:
        for domain in p.knob_domains():
            print(f"  {DIM}[{domain}]{RESET}")
            for knob in p.knobs_by_domain(domain):
                print(f"    {knob.label}: {knob.value}")


def cmd_list(engine: ThematicEngine):
    """List available universe profiles."""
    profiles = engine.list_profiles()
    if not profiles:
        print(f"  {DIM}no profiles found{RESET}")
        return
    print(f"  {BOLD}Available profiles:{RESET}")
    for name in profiles:
        marker = " *" if engine.profile and engine.profile.name == name else ""
        print(f"    {CYAN}{name}{RESET}{marker}")


def cmd_load(engine: ThematicEngine, name: str):
    """Load a universe profile."""
    try:
        profile = engine.load(name)
        record_profile_load(profile.name)
        _save_state(engine)
        print(f"  {GREEN}loaded{RESET}  {profile.name}")
        print(f"  {CYAN}promise{RESET} {profile.thematic_promise}")
        print()
        cmd_status(engine)
    except FileNotFoundError:
        print(f"  {RED}not found:{RESET} {name}")
        print(f"  {DIM}use: terra tune list{RESET}")
    except ValueError as e:
        print(f"  {RED}invalid:{RESET} {e}")


def cmd_zone(engine: ThematicEngine, args: list[str]):
    """Enter or exit a zone."""
    if not args or args[0] == "--exit":
        if engine.profile is None:
            print(f"  {RED}no profile loaded{RESET}")
            return
        old_zone = engine.active_zone
        engine.exit_zone()
        _save_state(engine)
        if old_zone:
            print(f"  {GREEN}exited{RESET}  {old_zone.name} -> base")
        else:
            print(f"  {DIM}already at base{RESET}")
        return

    zone_name = args[0]
    try:
        zone = engine.enter_zone(zone_name)
        _save_state(engine)
        print(f"  {GREEN}entered{RESET} {zone.name}")
        if zone.override_directive:
            print(f"  {CYAN}directive{RESET} {zone.override_directive}")
        axes = engine.get_active_axes()
        for name, value in axes.items():
            print(f"  {GREEN}{name}{RESET}  {value}")
    except (RuntimeError, ValueError) as e:
        print(f"  {RED}error:{RESET} {e}")


def cmd_set(engine: ThematicEngine, knob_id: str, raw_value: str):
    """Set a custom knob value."""
    if engine.profile is None:
        print(f"  {RED}no profile loaded{RESET}")
        return

    knob = engine.profile.get_knob(knob_id)
    if knob is None:
        print(f"  {RED}knob not found:{RESET} {knob_id}")
        return

    # Parse value based on knob type
    try:
        if knob.knob_type == "slider":
            value = float(raw_value)
        elif knob.knob_type == "toggle":
            value = raw_value.lower() in ("true", "1", "yes", "on")
        elif knob.knob_type == "dropdown":
            value = raw_value
        elif knob.knob_type == "text":
            value = raw_value
        else:
            value = raw_value

        old_value = knob.value
        engine.set_knob(knob_id, value)
        record_knob_adjustment(engine.profile.name, knob_id, old_value, value)
        _save_state(engine)

        instruction = engine.get_knob_instruction(knob_id)
        print(f"  {GREEN}set{RESET}  {knob.label}: {old_value} -> {value}")
        if instruction:
            print(f"  {CYAN}->{RESET}   {instruction}")
    except ValueError as e:
        print(f"  {RED}invalid:{RESET} {e}")


def cmd_axes(engine: ThematicEngine):
    """Print current thematic axes."""
    if engine.profile is None:
        print(f"  {RED}no profile loaded{RESET}")
        return
    axes = engine.get_active_axes()
    for name, value in axes.items():
        print(f"  {GREEN}{name}{RESET}  {value}")


def cmd_directive(engine: ThematicEngine):
    """Print current bot/behavior directive."""
    directive = engine.get_directive()
    if directive:
        print(directive)
    else:
        print(f"  {DIM}no directive{RESET}")


def cmd_instructions(engine: ThematicEngine):
    """Print full behavioral instruction block."""
    instructions = engine.get_behavioral_instructions()
    if instructions:
        print(instructions)
    else:
        print(f"  {DIM}no profile loaded{RESET}")


def cmd_promise(engine: ThematicEngine):
    """Print the thematic promise."""
    promise = engine.get_promise()
    if promise:
        print(f"  {BOLD}{promise}{RESET}")
    else:
        print(f"  {DIM}no profile loaded{RESET}")


# ── Dispatch ─────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    action = args[0] if args else "status"
    rest = args[1:]

    engine = _load_engine()

    if action in ("status", "show"):
        cmd_status(engine)
    elif action == "list":
        cmd_list(engine)
    elif action == "load":
        if not rest:
            print(f"  {RED}usage:{RESET} terra tune load <name>")
            return
        cmd_load(engine, rest[0])
    elif action == "zone":
        cmd_zone(engine, rest)
    elif action == "set":
        if len(rest) < 2:
            print(f"  {RED}usage:{RESET} terra tune set <knob_id> <value>")
            return
        cmd_set(engine, rest[0], " ".join(rest[1:]))
    elif action == "axes":
        cmd_axes(engine)
    elif action == "directive":
        cmd_directive(engine)
    elif action == "instructions":
        cmd_instructions(engine)
    elif action == "promise":
        cmd_promise(engine)
    else:
        print(f"  {RED}unknown:{RESET} {action}")
        print(f"  {DIM}commands: list, load, zone, set, axes, directive, instructions, promise{RESET}")


if __name__ == "__main__":
    main()
