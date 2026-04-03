"""
.scaffold/tuning/loader.py
Load and validate universe TOML profiles.
"""

import sys
from pathlib import Path
from typing import Optional

# tomllib is stdlib in 3.11+, tomli is the backport
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore

from .schema import (
    UniverseProfile,
    Knob,
    Zone,
    ReactionSignature,
    THEMATIC_AXES,
    KNOB_TYPES,
    MORTALITY_WEIGHT_VALUES,
    POWER_FANTASY_VALUES,
    SHITPOST_TOLERANCE_VALUES,
)


SCAFFOLD_DIR = Path(__file__).parent.parent
DEFAULT_PROFILES_DIR = SCAFFOLD_DIR / "tuning" / "profiles"


def list_profiles(profiles_dir: Optional[Path] = None) -> list[str]:
    """List available universe profile names (without .toml extension)."""
    d = profiles_dir or DEFAULT_PROFILES_DIR
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.toml"))


def load_profile(path: "str | Path") -> UniverseProfile:
    """Load and validate a universe profile from a TOML file.

    Args:
        path: Path to the .toml profile file.

    Returns:
        A validated UniverseProfile.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If validation fails.
        RuntimeError: If tomllib is not available.
    """
    if tomllib is None:
        raise RuntimeError(
            "TOML parsing requires Python 3.11+ or the 'tomli' package. "
            "Install with: pip install tomli"
        )

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    errors = _validate_profile_data(data)
    if errors:
        raise ValueError(
            f"Profile validation failed for {path.name}:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return _build_profile(data)


# ── Validation ───────────────────────────────────────────────────────

def _validate_profile_data(data: dict) -> list[str]:
    """Validate raw TOML data, return list of error strings."""
    errors = []

    # Meta
    meta = data.get("meta", {})
    if not meta.get("name"):
        errors.append("[meta] 'name' is required")

    # Thematic promise
    promise = data.get("thematic_promise", {})
    if not promise.get("text"):
        errors.append("[thematic_promise] 'text' is required")

    # Axes
    axes = data.get("axes", {})
    if "mortality_weight" in axes:
        if axes["mortality_weight"] not in MORTALITY_WEIGHT_VALUES:
            errors.append(
                f"[axes] mortality_weight '{axes['mortality_weight']}' "
                f"not in {MORTALITY_WEIGHT_VALUES}"
            )
    if "power_fantasy" in axes:
        if axes["power_fantasy"] not in POWER_FANTASY_VALUES:
            errors.append(
                f"[axes] power_fantasy '{axes['power_fantasy']}' "
                f"not in {POWER_FANTASY_VALUES}"
            )
    if "shitpost_tolerance" in axes:
        if axes["shitpost_tolerance"] not in SHITPOST_TOLERANCE_VALUES:
            errors.append(
                f"[axes] shitpost_tolerance '{axes['shitpost_tolerance']}' "
                f"not in {SHITPOST_TOLERANCE_VALUES}"
            )

    # Zones
    zone_names = set()
    for i, zone in enumerate(data.get("zone", [])):
        name = zone.get("name")
        if not name:
            errors.append(f"[[zone]][{i}] 'name' is required")
        elif name in zone_names:
            errors.append(f"[[zone]][{i}] duplicate zone name '{name}'")
        else:
            zone_names.add(name)

        if "mortality_weight" in zone:
            if zone["mortality_weight"] not in MORTALITY_WEIGHT_VALUES:
                errors.append(
                    f"[[zone]] '{name}' mortality_weight "
                    f"'{zone['mortality_weight']}' invalid"
                )
        if "power_fantasy" in zone:
            if zone["power_fantasy"] not in POWER_FANTASY_VALUES:
                errors.append(
                    f"[[zone]] '{name}' power_fantasy "
                    f"'{zone['power_fantasy']}' invalid"
                )
        if "shitpost_tolerance" in zone:
            if zone["shitpost_tolerance"] not in SHITPOST_TOLERANCE_VALUES:
                errors.append(
                    f"[[zone]] '{name}' shitpost_tolerance "
                    f"'{zone['shitpost_tolerance']}' invalid"
                )

    # Knobs
    knob_ids = set()
    for i, knob in enumerate(data.get("knob", [])):
        kid = knob.get("id")
        if not kid:
            errors.append(f"[[knob]][{i}] 'id' is required")
            continue

        if kid in knob_ids:
            errors.append(f"[[knob]] duplicate id '{kid}'")
        knob_ids.add(kid)

        ktype = knob.get("type")
        if ktype not in KNOB_TYPES:
            errors.append(f"[[knob]] '{kid}' type '{ktype}' not in {KNOB_TYPES}")
            continue

        if not knob.get("behavior"):
            errors.append(f"[[knob]] '{kid}' 'behavior' is required")

        errors.extend(_validate_knob_type(kid, ktype, knob))

    return errors


def _validate_knob_type(kid: str, ktype: str, knob: dict) -> list[str]:
    """Validate type-specific knob fields."""
    errors = []

    if ktype == "slider":
        for field in ("min", "max", "step", "default"):
            if field not in knob:
                errors.append(f"[[knob]] '{kid}' slider requires '{field}'")
        if "min" in knob and "max" in knob:
            if knob["min"] >= knob["max"]:
                errors.append(f"[[knob]] '{kid}' min must be < max")
            if "default" in knob:
                if not (knob["min"] <= knob["default"] <= knob["max"]):
                    errors.append(
                        f"[[knob]] '{kid}' default {knob['default']} "
                        f"outside [{knob['min']}, {knob['max']}]"
                    )
        if "step" in knob and knob["step"] <= 0:
            errors.append(f"[[knob]] '{kid}' step must be > 0")

    elif ktype == "toggle":
        if "default" not in knob:
            errors.append(f"[[knob]] '{kid}' toggle requires 'default'")
        elif not isinstance(knob["default"], bool):
            errors.append(f"[[knob]] '{kid}' toggle default must be bool")

    elif ktype == "dropdown":
        if "options" not in knob or not knob["options"]:
            errors.append(f"[[knob]] '{kid}' dropdown requires non-empty 'options'")
        elif "default" in knob and knob["default"] not in knob["options"]:
            errors.append(
                f"[[knob]] '{kid}' default '{knob['default']}' "
                f"not in options"
            )

    elif ktype == "curve":
        default = knob.get("default")
        if not isinstance(default, list) or len(default) < 2:
            errors.append(f"[[knob]] '{kid}' curve requires default with >= 2 points")
        elif default:
            for j, pt in enumerate(default):
                if not isinstance(pt, list) or len(pt) != 2:
                    errors.append(
                        f"[[knob]] '{kid}' curve point [{j}] must be [x, y]"
                    )

    elif ktype == "text":
        if "default" not in knob:
            errors.append(f"[[knob]] '{kid}' text requires 'default'")

    return errors


# ── Builder ──────────────────────────────────────────────────────────

def _build_profile(data: dict) -> UniverseProfile:
    """Build a UniverseProfile from validated TOML data."""
    meta = data.get("meta", {})
    promise = data.get("thematic_promise", {})
    axes = data.get("axes", {})
    reaction_data = data.get("reaction_signature", {})
    bot = data.get("bot_directive", {})

    reaction = ReactionSignature(
        template=reaction_data.get("template", ""),
        description=reaction_data.get("description", ""),
    )

    zones = []
    for z in data.get("zone", []):
        zones.append(Zone(
            name=z["name"],
            mortality_weight=z.get("mortality_weight"),
            power_fantasy=z.get("power_fantasy"),
            shitpost_tolerance=z.get("shitpost_tolerance"),
            override_directive=z.get("override_directive", ""),
        ))

    knobs = []
    for k in data.get("knob", []):
        knobs.append(Knob(
            id=k["id"],
            domain=k.get("domain", "general"),
            label=k.get("label", k["id"]),
            knob_type=k["type"],
            default=k["default"],
            behavior=k["behavior"],
            description=k.get("description", ""),
            min_val=k.get("min"),
            max_val=k.get("max"),
            step=k.get("step"),
            options=k.get("options"),
            x_label=k.get("x_label", ""),
            y_label=k.get("y_label", ""),
            max_length=k.get("max_length"),
            pattern=k.get("pattern"),
        ))

    return UniverseProfile(
        name=meta.get("name", ""),
        version=meta.get("version", "1.0"),
        genre=meta.get("genre", ""),
        description=meta.get("description", ""),
        thematic_promise=promise.get("text", ""),
        register=promise.get("register", ""),
        mortality_weight=axes.get("mortality_weight", "medium-narrative"),
        power_fantasy=axes.get("power_fantasy", "capable"),
        shitpost_tolerance=axes.get("shitpost_tolerance", "moderate"),
        reaction=reaction,
        bot_directive=bot.get("text", ""),
        zones=zones,
        knobs=knobs,
    )
