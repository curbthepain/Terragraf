"""
.scaffold/tuning/schema.py
Core data model for thematic tension calibration.

UniverseProfile — the full tonal contract for a universe.
Knob — a domain-specific dial beyond the core thematic axes.
Zone — a per-zone thematic override within a universe.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Thematic Axes ────────────────────────────────────────────────────

MORTALITY_WEIGHT_VALUES = [
    "none", "low", "medium-narrative", "high-personal", "high-surreal",
]

POWER_FANTASY_VALUES = [
    "outmatched", "capable", "chaotic-peer", "god-tier", "ceremonial",
]

SHITPOST_TOLERANCE_VALUES = [
    "zero", "narrow", "moderate", "high", "structural",
]

THEMATIC_AXES = {
    "mortality_weight": {
        "description": "How much death/failure costs emotionally",
        "values": MORTALITY_WEIGHT_VALUES,
    },
    "power_fantasy": {
        "description": "Where the user sits on the power curve",
        "values": POWER_FANTASY_VALUES,
    },
    "shitpost_tolerance": {
        "description": "How much canonical absurdity the universe allows",
        "values": SHITPOST_TOLERANCE_VALUES,
    },
}

KNOB_TYPES = {"slider", "toggle", "dropdown", "curve", "text"}


# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class Knob:
    """A domain-specific tuning dial beyond the core thematic axes."""

    id: str
    domain: str
    label: str
    knob_type: str                          # slider | toggle | dropdown | curve | text
    default: object                         # type depends on knob_type
    behavior: str
    description: str = ""

    # Slider fields
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    step: Optional[float] = None

    # Dropdown fields
    options: Optional[list[str]] = None

    # Curve fields
    x_label: str = ""
    y_label: str = ""

    # Text fields
    max_length: Optional[int] = None
    pattern: Optional[str] = None

    # Runtime state
    value: object = None

    def __post_init__(self):
        if self.value is None:
            self.value = self.default


@dataclass
class Zone:
    """A per-zone thematic override within a universe."""

    name: str
    mortality_weight: Optional[str] = None
    power_fantasy: Optional[str] = None
    shitpost_tolerance: Optional[str] = None
    override_directive: str = ""


@dataclass
class ReactionSignature:
    """What impact looks/sounds/feels like in this universe."""

    template: str = ""                      # maps to includes/reactions/<template>.inc
    description: str = ""


@dataclass
class UniverseProfile:
    """The full tonal contract for a universe."""

    # Meta
    name: str = ""
    version: str = "1.0"
    genre: str = ""
    description: str = ""

    # Thematic promise
    thematic_promise: str = ""
    register: str = ""                      # tonal register (e.g. "operatic metal")

    # Core axes
    mortality_weight: str = "medium-narrative"
    power_fantasy: str = "capable"
    shitpost_tolerance: str = "moderate"

    # Reaction signature
    reaction: ReactionSignature = field(default_factory=ReactionSignature)

    # Bot/behavior directive
    bot_directive: str = ""

    # Zones
    zones: list[Zone] = field(default_factory=list)

    # Custom knobs
    knobs: list[Knob] = field(default_factory=list)

    def get_knob(self, knob_id: str) -> Optional[Knob]:
        """Get a knob by ID."""
        for k in self.knobs:
            if k.id == knob_id:
                return k
        return None

    def knobs_by_domain(self, domain: str) -> list[Knob]:
        """Get all knobs in a domain."""
        return [k for k in self.knobs if k.domain == domain]

    def knob_domains(self) -> list[str]:
        """Get unique knob domain names, preserving order."""
        seen = set()
        domains = []
        for k in self.knobs:
            if k.domain not in seen:
                seen.add(k.domain)
                domains.append(k.domain)
        return domains

    def get_zone(self, zone_name: str) -> Optional[Zone]:
        """Get a zone by name."""
        for z in self.zones:
            if z.name == zone_name:
                return z
        return None

    def zone_names(self) -> list[str]:
        """Get all zone names."""
        return [z.name for z in self.zones]
