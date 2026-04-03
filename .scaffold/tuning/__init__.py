"""
.scaffold/tuning/ — Thematic Tension Calibration Framework.

Domain-agnostic behavioral tuning. Universe profiles declare the tonal
contract. The engine evaluates output against that contract. ImGui gives
real-time visibility. Self-sharpening learns from session outcomes.

Modules:
    config   — TuningConfig dataclass
    schema   — ThematicAxis, Knob, Zone, UniverseProfile
    loader   — Load/validate universe TOML profiles
    engine   — ThematicEngine: evaluate, instruct, zone-shift
    tracker  — Record session outcomes for self-sharpening
    cli      — CLI entry point for `terra tune`
"""

from .schema import UniverseProfile, Knob, Zone, THEMATIC_AXES
from .loader import load_profile, list_profiles
from .engine import ThematicEngine
from .config import TuningConfig

__all__ = [
    "UniverseProfile",
    "Knob",
    "Zone",
    "THEMATIC_AXES",
    "load_profile",
    "list_profiles",
    "ThematicEngine",
    "TuningConfig",
]
