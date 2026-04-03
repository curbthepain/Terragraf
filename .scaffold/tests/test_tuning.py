"""Tests for .scaffold/tuning/ — engine, loader, schema, state persistence."""

import json
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from tuning.schema import (
    UniverseProfile, Knob, Zone, ReactionSignature,
    THEMATIC_AXES, KNOB_TYPES,
    MORTALITY_WEIGHT_VALUES, POWER_FANTASY_VALUES, SHITPOST_TOLERANCE_VALUES,
)
from tuning.loader import load_profile, list_profiles, DEFAULT_PROFILES_DIR
from tuning.engine import ThematicEngine


# ── Schema ──────────────────────────────────────────────────────────


class TestSchema:
    def test_thematic_axes_have_required_keys(self):
        for axis in ("mortality_weight", "power_fantasy", "shitpost_tolerance"):
            assert axis in THEMATIC_AXES
            assert "values" in THEMATIC_AXES[axis]
            assert "description" in THEMATIC_AXES[axis]
            assert len(THEMATIC_AXES[axis]["values"]) >= 3

    def test_knob_types(self):
        assert KNOB_TYPES == {"slider", "toggle", "dropdown", "curve", "text"}

    def test_knob_default_sets_value(self):
        k = Knob(id="test", domain="d", label="Test", knob_type="slider",
                 default=0.5, behavior="test")
        assert k.value == 0.5

    def test_knob_value_override(self):
        k = Knob(id="test", domain="d", label="Test", knob_type="toggle",
                 default=True, behavior="test", value=False)
        assert k.value is False

    def test_universe_profile_defaults(self):
        p = UniverseProfile()
        assert p.mortality_weight == "medium-narrative"
        assert p.power_fantasy == "capable"
        assert p.shitpost_tolerance == "moderate"

    def test_get_knob(self):
        k1 = Knob(id="a", domain="d", label="A", knob_type="toggle",
                  default=True, behavior="b")
        k2 = Knob(id="b", domain="d", label="B", knob_type="toggle",
                  default=False, behavior="b")
        p = UniverseProfile(knobs=[k1, k2])
        assert p.get_knob("a") is k1
        assert p.get_knob("b") is k2
        assert p.get_knob("c") is None

    def test_knobs_by_domain(self):
        k1 = Knob(id="a", domain="combat", label="A", knob_type="toggle",
                  default=True, behavior="b")
        k2 = Knob(id="b", domain="ui", label="B", knob_type="toggle",
                  default=True, behavior="b")
        k3 = Knob(id="c", domain="combat", label="C", knob_type="toggle",
                  default=True, behavior="b")
        p = UniverseProfile(knobs=[k1, k2, k3])
        combat = p.knobs_by_domain("combat")
        assert len(combat) == 2
        assert combat[0].id == "a"
        assert combat[1].id == "c"

    def test_knob_domains_preserves_order(self):
        k1 = Knob(id="a", domain="combat", label="A", knob_type="toggle",
                  default=True, behavior="b")
        k2 = Knob(id="b", domain="ui", label="B", knob_type="toggle",
                  default=True, behavior="b")
        k3 = Knob(id="c", domain="combat", label="C", knob_type="toggle",
                  default=True, behavior="b")
        p = UniverseProfile(knobs=[k1, k2, k3])
        assert p.knob_domains() == ["combat", "ui"]

    def test_zone_names(self):
        z1 = Zone(name="arena")
        z2 = Zone(name="hub")
        p = UniverseProfile(zones=[z1, z2])
        assert p.zone_names() == ["arena", "hub"]

    def test_get_zone(self):
        z = Zone(name="arena", mortality_weight="high-personal")
        p = UniverseProfile(zones=[z])
        assert p.get_zone("arena") is z
        assert p.get_zone("nope") is None


# ── Loader ──────────────────────────────────────────────────────────


class TestLoader:
    def test_list_profiles_returns_names(self):
        profiles = list_profiles()
        assert len(profiles) >= 7
        assert "arena_slayer" in profiles
        assert "cartoon_platformer" in profiles
        assert "ai_assistant" in profiles

    def test_load_arena_slayer(self):
        p = load_profile(DEFAULT_PROFILES_DIR / "arena_slayer.toml")
        assert p.name == "arena_slayer"
        assert p.genre == "fps"
        assert p.mortality_weight == "high-personal"
        assert p.power_fantasy == "god-tier"
        assert p.shitpost_tolerance == "zero"
        assert p.register == "operatic metal"
        assert p.reaction.template == "visceral_operatic"
        assert len(p.zones) == 2
        assert len(p.knobs) >= 3

    def test_load_all_profiles(self):
        """Every shipped profile must load without validation errors."""
        for name in list_profiles():
            p = load_profile(DEFAULT_PROFILES_DIR / f"{name}.toml")
            assert p.name == name

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_profile("/nonexistent/profile.toml")

    def test_load_invalid_toml_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="wb",
                                         delete=False) as f:
            f.write(b'[meta]\nversion = "1.0"\n')
            path = f.name
        with pytest.raises(ValueError, match="name.*required"):
            load_profile(path)
        Path(path).unlink()


# ── Engine: Profile & Zone ──────────────────────────────────────────


class TestEngineProfileZone:
    def setup_method(self):
        self.engine = ThematicEngine()

    def test_no_profile_initially(self):
        assert self.engine.profile is None
        assert self.engine.active_zone is None

    def test_load_by_name(self):
        p = self.engine.load("arena_slayer")
        assert p.name == "arena_slayer"
        assert self.engine.profile is p

    def test_load_clears_zone(self):
        self.engine.load("arena_slayer")
        self.engine.enter_zone("combat_arena")
        assert self.engine.active_zone is not None
        self.engine.load("arena_slayer")
        assert self.engine.active_zone is None

    def test_list_profiles(self):
        profiles = self.engine.list_profiles()
        assert "arena_slayer" in profiles

    def test_enter_zone(self):
        self.engine.load("arena_slayer")
        zone = self.engine.enter_zone("combat_arena")
        assert zone.name == "combat_arena"
        assert self.engine.active_zone is zone

    def test_enter_invalid_zone_raises(self):
        self.engine.load("arena_slayer")
        with pytest.raises(ValueError, match="not found"):
            self.engine.enter_zone("nonexistent_zone")

    def test_enter_zone_no_profile_raises(self):
        with pytest.raises(RuntimeError, match="No profile"):
            self.engine.enter_zone("any")

    def test_exit_zone(self):
        self.engine.load("arena_slayer")
        self.engine.enter_zone("combat_arena")
        self.engine.exit_zone()
        assert self.engine.active_zone is None


# ── Engine: Axes ────────────────────────────────────────────────────


class TestEngineAxes:
    def setup_method(self):
        self.engine = ThematicEngine()
        self.engine.load("arena_slayer")

    def test_base_axes(self):
        axes = self.engine.get_active_axes()
        assert axes["mortality_weight"] == "high-personal"
        assert axes["power_fantasy"] == "god-tier"
        assert axes["shitpost_tolerance"] == "zero"

    def test_zone_overrides_axes(self):
        self.engine.enter_zone("hub_fortress")
        axes = self.engine.get_active_axes()
        assert axes["mortality_weight"] == "none"
        assert axes["shitpost_tolerance"] == "narrow"

    def test_exit_zone_restores_base_axes(self):
        self.engine.enter_zone("hub_fortress")
        self.engine.exit_zone()
        axes = self.engine.get_active_axes()
        assert axes["mortality_weight"] == "high-personal"

    def test_empty_axes_no_profile(self):
        engine = ThematicEngine()
        assert engine.get_active_axes() == {}


# ── Engine: Directive & Promise ─────────────────────────────────────


class TestEngineDirective:
    def setup_method(self):
        self.engine = ThematicEngine()
        self.engine.load("arena_slayer")

    def test_base_directive(self):
        d = self.engine.get_directive()
        assert "destroyed efficiently" in d

    def test_zone_directive_override(self):
        self.engine.enter_zone("combat_arena")
        d = self.engine.get_directive()
        assert "Maximum aggression" in d

    def test_promise(self):
        p = self.engine.get_promise()
        assert "threat" in p.lower()

    def test_reaction_signature(self):
        r = self.engine.get_reaction_signature()
        assert "operatic" in r.lower()

    def test_no_profile_returns_empty(self):
        engine = ThematicEngine()
        assert engine.get_directive() == ""
        assert engine.get_promise() == ""
        assert engine.get_reaction_signature() == ""


# ── Engine: Knobs ───────────────────────────────────────────────────


class TestEngineKnobs:
    def setup_method(self):
        self.engine = ThematicEngine()
        self.engine.load("arena_slayer")

    def test_set_slider_knob(self):
        self.engine.set_knob("execution_frequency", 0.3)
        assert self.engine.profile.get_knob("execution_frequency").value == 0.3

    def test_set_slider_out_of_range_raises(self):
        with pytest.raises(ValueError, match="min"):
            self.engine.set_knob("execution_frequency", -1.0)
        with pytest.raises(ValueError, match="max"):
            self.engine.set_knob("execution_frequency", 5.0)

    def test_set_nonexistent_knob_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.engine.set_knob("fake_knob", 1.0)

    def test_reset_single_knob(self):
        self.engine.set_knob("execution_frequency", 0.1)
        self.engine.reset_knob("execution_frequency")
        assert self.engine.profile.get_knob("execution_frequency").value == 0.7

    def test_reset_all_knobs(self):
        self.engine.set_knob("execution_frequency", 0.1)
        self.engine.set_knob("resource_from_kills", 0.1)
        self.engine.reset_knob()
        assert self.engine.profile.get_knob("execution_frequency").value == 0.7
        assert self.engine.profile.get_knob("resource_from_kills").value == 0.6

    def test_get_knob_state(self):
        state = self.engine.get_knob_state()
        assert "execution_frequency" in state
        assert "resource_from_kills" in state
        assert "aggression_scaling" in state

    def test_no_profile_knob_operations_raise(self):
        engine = ThematicEngine()
        with pytest.raises(RuntimeError):
            engine.set_knob("x", 1)
        with pytest.raises(RuntimeError):
            engine.reset_knob()
        assert engine.get_knob_state() == {}


# ── Engine: Behavioral Instructions ─────────────────────────────────


class TestEngineInstructions:
    def setup_method(self):
        self.engine = ThematicEngine()
        self.engine.load("arena_slayer")

    def test_instructions_contain_header(self):
        text = self.engine.get_behavioral_instructions()
        assert "THEMATIC CALIBRATION: arena_slayer" in text

    def test_instructions_contain_axes(self):
        text = self.engine.get_behavioral_instructions()
        assert "mortality_weight" in text
        assert "high-personal" in text
        assert "power_fantasy" in text
        assert "god-tier" in text

    def test_instructions_contain_promise(self):
        text = self.engine.get_behavioral_instructions()
        assert "Thematic Promise" in text

    def test_instructions_contain_knobs(self):
        text = self.engine.get_behavioral_instructions()
        assert "Active Knobs" in text
        assert "Execution Windows" in text

    def test_instructions_zone_indicator(self):
        self.engine.enter_zone("combat_arena")
        text = self.engine.get_behavioral_instructions()
        assert "Zone: combat_arena" in text

    def test_no_profile_returns_empty(self):
        engine = ThematicEngine()
        assert engine.get_behavioral_instructions() == ""

    def test_knob_instruction_slider(self):
        inst = self.engine.get_knob_instruction("execution_frequency")
        assert inst  # should return non-empty for default 0.7

    def test_knob_instruction_nonexistent(self):
        inst = self.engine.get_knob_instruction("fake")
        assert inst == ""


# ── Engine: Slider Behavior Parsing ─────────────────────────────────


class TestSliderBehaviorParsing:
    def setup_method(self):
        self.engine = ThematicEngine()
        self.engine.load("arena_slayer")

    def test_exact_anchor_match(self):
        self.engine.set_knob("execution_frequency", 0.0)
        inst = self.engine.get_knob_instruction("execution_frequency")
        assert "rare" in inst.lower() or "gunplay" in inst.lower()

    def test_exact_anchor_match_high(self):
        self.engine.set_knob("execution_frequency", 1.0)
        inst = self.engine.get_knob_instruction("execution_frequency")
        assert "aggressive" in inst.lower() or "constantly" in inst.lower()

    def test_interpolated_value(self):
        self.engine.set_knob("execution_frequency", 0.25)
        inst = self.engine.get_knob_instruction("execution_frequency")
        assert inst  # should return something between anchors


# ── Engine: State Export/Import ─────────────────────────────────────


class TestEngineState:
    def setup_method(self):
        self.engine = ThematicEngine()
        self.engine.load("arena_slayer")

    def test_export_state(self):
        self.engine.enter_zone("combat_arena")
        self.engine.set_knob("execution_frequency", 0.3)
        state = self.engine.export_state()
        assert state["profile"] == "arena_slayer"
        assert state["zone"] == "combat_arena"
        assert state["knobs"]["execution_frequency"] == 0.3

    def test_export_no_zone(self):
        state = self.engine.export_state()
        assert state["zone"] is None

    def test_export_no_profile(self):
        engine = ThematicEngine()
        assert engine.export_state() == {}

    def test_import_state_restores_zone(self):
        state = {"profile": "arena_slayer", "zone": "hub_fortress", "knobs": {}}
        self.engine.import_state(state)
        assert self.engine.active_zone.name == "hub_fortress"

    def test_import_state_restores_knobs(self):
        state = {
            "profile": "arena_slayer",
            "zone": None,
            "knobs": {"execution_frequency": 0.2},
        }
        self.engine.import_state(state)
        assert self.engine.profile.get_knob("execution_frequency").value == 0.2

    def test_import_state_skips_unknown_knobs(self):
        state = {
            "profile": "arena_slayer",
            "zone": None,
            "knobs": {"nonexistent_knob": 42},
        }
        self.engine.import_state(state)  # should not raise

    def test_roundtrip_export_import(self):
        self.engine.enter_zone("combat_arena")
        self.engine.set_knob("execution_frequency", 0.4)
        state = self.engine.export_state()

        # Load fresh and restore
        engine2 = ThematicEngine()
        engine2.load("arena_slayer")
        engine2.import_state(state)

        assert engine2.active_zone.name == "combat_arena"
        assert engine2.profile.get_knob("execution_frequency").value == 0.4


# ── State Persistence (JSON file) ──────────────────────────────────


class TestStatePersistence:
    def test_save_and_load_state_file(self):
        engine = ThematicEngine()
        engine.load("arena_slayer")
        engine.enter_zone("hub_fortress")
        engine.set_knob("execution_frequency", 0.15)
        state = engine.export_state()

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                         delete=False) as f:
            json.dump(state, f, indent=2)
            path = f.name

        with open(path) as f:
            loaded = json.load(f)

        engine2 = ThematicEngine()
        engine2.load(loaded["profile"])
        engine2.import_state(loaded)

        assert engine2.profile.name == "arena_slayer"
        assert engine2.active_zone.name == "hub_fortress"
        assert engine2.profile.get_knob("execution_frequency").value == 0.15

        axes = engine2.get_active_axes()
        assert axes["mortality_weight"] == "none"

        Path(path).unlink()

    def test_state_json_is_serializable(self):
        engine = ThematicEngine()
        engine.load("arena_slayer")
        engine.set_knob("execution_frequency", 0.5)
        state = engine.export_state()
        text = json.dumps(state)
        restored = json.loads(text)
        assert restored["profile"] == "arena_slayer"
        assert restored["knobs"]["execution_frequency"] == 0.5
