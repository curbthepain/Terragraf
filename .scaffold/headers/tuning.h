// .scaffold/headers/tuning.h
// Declares the thematic tension calibration subsystem.
// AI reads this to understand WHAT the tuning system provides.

#ifndef TUNING_H
#define TUNING_H

#include "project.h"

// ─── Thematic Axes ──────────────────────────────────────────────────
// Core model. Every universe profile declares values for each axis.
// These are categorical with narrative weight, not numeric sliders.

#thematic_axes {
    mortality_weight: "none | low | medium-narrative | high-personal | high-surreal",
    power_fantasy: "outmatched | capable | chaotic-peer | god-tier | ceremonial",
    shitpost_tolerance: "zero | narrow | moderate | high | structural",
    // Plus: thematic_promise (freeform text), reaction_signature (.inc fragment)
}

// ─── Profile System ─────────────────────────────────────────────────

#profiles {
    dir: "tuning/profiles",
    format: "toml",
    builtin: [
        "cartoon_platformer",   // bright, fair, forgiving
        "arena_slayer",         // power fantasy FPS
        "mythic_roguelike",     // death is story
        "looter_chaos",         // everything is loot and comedy
        "milsim_surreal",       // war is real and also somehow this
        "punishing_action",     // every encounter is a test
        "ai_assistant",         // helpful, clear, never harmful
        "realtime_engine",      // fast and correct
    ]
}

// ─── Knob Types ─────────────────────────────────────────────────────
// Custom dials beyond core axes. Domain-specific per profile.

#knob_types {
    slider: "numeric range with step — ImGui SliderFloat/Int",
    toggle: "boolean — ImGui Checkbox",
    dropdown: "string enum — ImGui Combo",
    curve: "list of [x,y] control points — ImPlot interactive spline",
    text: "freeform string — ImGui InputText",
}

// ─── Engine ─────────────────────────────────────────────────────────

#tuning_engine {
    template: "tuning/engine.py",
    operations: [
        load,                   // load a universe profile
        enter_zone,             // shift axes for a zone
        exit_zone,              // return to base profile
        get_active_axes,        // current axis values (zone-aware)
        get_directive,          // current bot/behavior directive
        get_behavioral_instructions,  // FULL instruction block
        set_knob,               // adjust a custom knob
        get_reaction_signature, // current reaction template
        export_state,           // serialize current state
        import_state,           // restore from serialized state
    ]
}

// ─── Reaction Signatures ────────────────────────────────────────────
// Composable .inc fragments for different tonal registers.

#reaction_signatures {
    dir: "includes/reactions",
    templates: [
        "cartoon_comedy",       // bright, bouncy, safe
        "visceral_operatic",    // metal, decisive, aesthetic gore
        "mythic_wounded",       // wounded but not broken
        "chaos_maximum",        // everything is a bit
        "surreal_horror",       // half meme half disturbing
        "neutral_professional", // AI/engine/software
    ]
}

// ─── Bridge Protocol (Phase 2) ──────────────────────────────────────

#tuning_bridge {
    messages: [
        "tune_load_profile",    // C++ -> Python: load a profile
        "tune_profile_data",    // Python -> C++: full profile JSON
        "tune_zone_enter",      // C++ -> Python: enter a zone
        "tune_zone_data",       // Python -> C++: zone-shifted axes
        "tune_knob_update",     // C++ -> Python: knob value change
        "tune_instructions",    // Python -> C++: behavioral block
    ]
}

#endif // TUNING_H
