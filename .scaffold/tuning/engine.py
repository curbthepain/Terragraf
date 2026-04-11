"""
.scaffold/tuning/engine.py
Thematic Tension Calibration Engine.

Loads a universe profile, tracks the active zone, generates behavioral
instructions the AI reads on session entry or zone transition.

The key method is get_behavioral_instructions() — it produces a full
text block containing: thematic promise, active axes, bot directive,
custom knob states, and reaction signature.
"""

import re
from pathlib import Path
from typing import Optional

from .config import TuningConfig
from .schema import UniverseProfile, Knob, Zone, THEMATIC_AXES
from .loader import load_profile, list_profiles, DEFAULT_PROFILES_DIR


class ThematicEngine:
    """Evaluate a universe profile and generate behavioral instructions."""

    def __init__(self, config: TuningConfig = None):
        self.config = config or TuningConfig()
        self._profile: Optional[UniverseProfile] = None
        self._active_zone: Optional[Zone] = None
        self._profiles_dir = Path(__file__).parent.parent / self.config.profiles_dir

    # ── Profile Management ───────────────────────────────────────────

    @property
    def profile(self) -> Optional[UniverseProfile]:
        return self._profile

    @property
    def active_zone(self) -> Optional[Zone]:
        return self._active_zone

    def load(self, name_or_path: str) -> UniverseProfile:
        """Load a universe profile by name or path.

        Args:
            name_or_path: Profile name (without .toml) or full path.

        Returns:
            The loaded UniverseProfile.
        """
        path = Path(name_or_path)
        if not path.exists():
            path = self._profiles_dir / f"{name_or_path}.toml"
        self._profile = load_profile(path)
        self._active_zone = None
        return self._profile

    def list_profiles(self) -> list[str]:
        """List available universe profile names."""
        return list_profiles(self._profiles_dir)

    # ── Zone Management ──────────────────────────────────────────────

    def enter_zone(self, zone_name: str) -> Zone:
        """Enter a zone, shifting thematic axes.

        Raises:
            RuntimeError: If no profile is loaded.
            ValueError: If zone doesn't exist.
        """
        if self._profile is None:
            raise RuntimeError("No profile loaded")
        zone = self._profile.get_zone(zone_name)
        if zone is None:
            available = ", ".join(self._profile.zone_names())
            raise ValueError(
                f"Zone '{zone_name}' not found. Available: {available}"
            )
        self._active_zone = zone
        return zone

    def exit_zone(self):
        """Exit the current zone, returning to base profile axes."""
        self._active_zone = None

    # ── Axis Queries ─────────────────────────────────────────────────

    def get_active_axes(self) -> dict[str, str]:
        """Get current thematic axis values, zone-aware.

        Zone overrides take precedence over base profile values.
        """
        if self._profile is None:
            return {}

        axes = {
            "mortality_weight": self._profile.mortality_weight,
            "power_fantasy": self._profile.power_fantasy,
            "shitpost_tolerance": self._profile.shitpost_tolerance,
        }

        if self._active_zone:
            if self._active_zone.mortality_weight:
                axes["mortality_weight"] = self._active_zone.mortality_weight
            if self._active_zone.power_fantasy:
                axes["power_fantasy"] = self._active_zone.power_fantasy
            if self._active_zone.shitpost_tolerance:
                axes["shitpost_tolerance"] = self._active_zone.shitpost_tolerance

        return axes

    def get_directive(self) -> str:
        """Get current bot/behavior directive, zone-aware."""
        if self._profile is None:
            return ""
        if self._active_zone and self._active_zone.override_directive:
            return self._active_zone.override_directive
        return self._profile.bot_directive

    def get_reaction_signature(self) -> str:
        """Get current reaction signature description."""
        if self._profile is None:
            return ""
        return self._profile.reaction.description

    def get_promise(self) -> str:
        """Get the thematic promise."""
        if self._profile is None:
            return ""
        return self._profile.thematic_promise

    # ── Knob Management ──────────────────────────────────────────────

    def set_knob(self, knob_id: str, value: object):
        """Set a custom knob value.

        Args:
            knob_id: The knob ID.
            value: The new value (type must match knob type).

        Raises:
            RuntimeError: If no profile is loaded.
            ValueError: If knob not found or value invalid.
        """
        if self._profile is None:
            raise RuntimeError("No profile loaded")

        knob = self._profile.get_knob(knob_id)
        if knob is None:
            raise ValueError(f"Knob '{knob_id}' not found")

        self._validate_knob_value(knob, value)
        knob.value = value

    def reset_knob(self, knob_id: Optional[str] = None):
        """Reset knob(s) to default values.

        Args:
            knob_id: Specific knob to reset, or None for all.
        """
        if self._profile is None:
            raise RuntimeError("No profile loaded")

        if knob_id:
            knob = self._profile.get_knob(knob_id)
            if knob is None:
                raise ValueError(f"Knob '{knob_id}' not found")
            knob.value = knob.default
        else:
            for knob in self._profile.knobs:
                knob.value = knob.default

    def get_knob_state(self) -> dict[str, object]:
        """Get current {knob_id: value} map."""
        if self._profile is None:
            return {}
        return {k.id: k.value for k in self._profile.knobs}

    # ── Behavioral Instructions ──────────────────────────────────────

    def get_behavioral_instructions(self) -> str:
        """Generate the full behavioral instruction block.

        This is the key output — the text block the AI reads on session
        entry or zone transition. Contains:
          1. Thematic promise
          2. Active axis values with descriptions
          3. Reaction signature
          4. Bot/behavior directive
          5. Custom knob states with behavioral descriptions
        """
        if self._profile is None:
            return ""

        p = self._profile
        axes = self.get_active_axes()
        lines = []

        # Header
        lines.append(f"=== THEMATIC CALIBRATION: {p.name} ===")
        if self._active_zone:
            lines.append(f"Zone: {self._active_zone.name}")
        lines.append("")

        # Promise
        lines.append(f"Thematic Promise: {p.thematic_promise}")
        if p.register:
            lines.append(f"Tonal Register: {p.register}")
        lines.append("")

        # Axes
        lines.append("--- Thematic Axes ---")
        for axis_name, axis_value in axes.items():
            axis_info = THEMATIC_AXES.get(axis_name, {})
            desc = axis_info.get("description", axis_name)
            lines.append(f"  {axis_name}: {axis_value}")
            lines.append(f"    ({desc})")
        lines.append("")

        # Reaction signature
        if p.reaction.description:
            lines.append("--- Reaction Signature ---")
            if p.reaction.template:
                lines.append(f"  Template: {p.reaction.template}")
            lines.append(p.reaction.description.strip())
            lines.append("")

        # Directive
        directive = self.get_directive()
        if directive:
            lines.append("--- Directive ---")
            lines.append(directive.strip())
            lines.append("")

        # Custom knobs
        if p.knobs:
            lines.append("--- Active Knobs ---")
            for domain in p.knob_domains():
                lines.append(f"  [{domain}]")
                for knob in p.knobs_by_domain(domain):
                    instruction = self._get_knob_instruction(knob)
                    lines.append(f"    {knob.label}: {knob.value}")
                    if instruction:
                        lines.append(f"      -> {instruction}")
            lines.append("")

        return "\n".join(lines)

    def get_knob_instruction(self, knob_id: str) -> str:
        """Get the behavioral instruction for a single knob at its current value."""
        if self._profile is None:
            return ""
        knob = self._profile.get_knob(knob_id)
        if knob is None:
            return ""
        return self._get_knob_instruction(knob)

    # ── State Export/Import ──────────────────────────────────────────

    def export_state(self) -> dict:
        """Export current engine state as a serializable dict."""
        if self._profile is None:
            return {}
        return {
            "profile": self._profile.name,
            "zone": self._active_zone.name if self._active_zone else None,
            "knobs": self.get_knob_state(),
        }

    def import_state(self, state: dict):
        """Import engine state from a dict.

        The profile must already be loaded. This restores zone and knob values.
        """
        if self._profile is None:
            raise RuntimeError("No profile loaded")

        zone_name = state.get("zone")
        if zone_name:
            self.enter_zone(zone_name)
        else:
            self.exit_zone()

        for knob_id, value in state.get("knobs", {}).items():
            try:
                self.set_knob(knob_id, value)
            except ValueError:
                pass  # skip unknown knobs (profile may have changed)

    # ── Internal ─────────────────────────────────────────────────────

    def _validate_knob_value(self, knob: Knob, value: object):
        """Validate a value against knob constraints."""
        if knob.knob_type == "slider":
            if not isinstance(value, (int, float)):
                raise ValueError(f"Knob '{knob.id}' requires numeric value")
            if knob.min_val is not None and value < knob.min_val:
                raise ValueError(f"Knob '{knob.id}' value {value} < min {knob.min_val}")
            if knob.max_val is not None and value > knob.max_val:
                raise ValueError(f"Knob '{knob.id}' value {value} > max {knob.max_val}")

        elif knob.knob_type == "toggle":
            if not isinstance(value, bool):
                raise ValueError(f"Knob '{knob.id}' requires bool value")

        elif knob.knob_type == "dropdown":
            if knob.options and value not in knob.options:
                raise ValueError(
                    f"Knob '{knob.id}' value '{value}' not in {knob.options}"
                )

        elif knob.knob_type == "curve":
            if not isinstance(value, list):
                raise ValueError(f"Knob '{knob.id}' requires list of [x, y] points")

        elif knob.knob_type == "text":
            if not isinstance(value, str):
                raise ValueError(f"Knob '{knob.id}' requires string value")
            if knob.max_length and len(value) > knob.max_length:
                raise ValueError(
                    f"Knob '{knob.id}' value length {len(value)} > "
                    f"max {knob.max_length}"
                )

    def _get_knob_instruction(self, knob: Knob) -> str:
        """Parse a knob's behavior string for its current value."""
        behavior = knob.behavior.strip()
        value = knob.value

        if knob.knob_type == "slider":
            return self._parse_slider_behavior(behavior, float(value))
        elif knob.knob_type == "toggle":
            return self._parse_toggle_behavior(behavior, bool(value))
        elif knob.knob_type == "dropdown":
            return self._parse_dropdown_behavior(behavior, str(value))
        else:
            # Curves and text return full behavior
            return behavior

    def _parse_slider_behavior(self, behavior: str, value: float) -> str:
        """Parse 'At X.X:' anchors and find the best match for value."""
        anchors = []
        pattern = re.compile(r"^At\s+([\d.]+)\s*:\s*(.+)", re.IGNORECASE)

        for line in behavior.split("\n"):
            line = line.strip()
            m = pattern.match(line)
            if m:
                anchors.append((float(m.group(1)), m.group(2).strip()))

        if not anchors:
            return behavior

        anchors.sort(key=lambda a: a[0])

        # Exact match
        for anchor_val, text in anchors:
            if abs(value - anchor_val) < 0.01:
                return text

        # Find surrounding anchors
        below = None
        above = None
        for anchor_val, text in anchors:
            if anchor_val <= value:
                below = (anchor_val, text)
            if anchor_val >= value and above is None:
                above = (anchor_val, text)

        if below and above and below != above:
            # Interpolate: describe position between two anchors
            t = (value - below[0]) / (above[0] - below[0])
            if t < 0.3:
                return f"{below[1]} (leaning toward: {above[1]})"
            elif t > 0.7:
                return f"{above[1]} (leaning from: {below[1]})"
            else:
                return f"Between: {below[1]} / {above[1]}"
        elif below:
            return below[1]
        elif above:
            return above[1]

        return behavior

    def _parse_toggle_behavior(self, behavior: str, value: bool) -> str:
        """Parse 'true:' / 'false:' lines."""
        target = "true" if value else "false"
        for line in behavior.split("\n"):
            line = line.strip()
            if line.lower().startswith(f"{target}:"):
                return line.split(":", 1)[1].strip()
        return behavior

    def _parse_dropdown_behavior(self, behavior: str, value: str) -> str:
        """Parse 'option_name:' lines."""
        for line in behavior.split("\n"):
            line = line.strip()
            if line.lower().startswith(f"{value.lower()}:"):
                return line.split(":", 1)[1].strip()
        return behavior
