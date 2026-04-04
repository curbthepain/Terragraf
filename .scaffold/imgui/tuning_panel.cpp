/**
 * .scaffold/imgui/tuning_panel.cpp
 * Thematic Tension Calibration panel — profile loading, axis display,
 * zone switching, knob editing, behavioral instruction output.
 *
 * Data-driven from bridge JSON: renders any universe profile without
 * hardcoding domain knowledge. Follows math_panel.cpp pattern.
 */

#include "imgui.h"
#include "implot.h"
#include "bridge_client.h"

#include <cmath>
#include <vector>
#include <array>
#include <string>
#include <algorithm>
#include <cstring>

extern BridgeClient* g_bridge;

namespace {

// ── Knob state (mirrors schema.py Knob) ───────────────────────────

struct KnobState {
    std::string id;
    std::string domain;
    std::string label;
    std::string knob_type;      // slider | toggle | dropdown | curve | text
    std::string description;

    // Current value (union by type)
    float slider_value = 0.0f;
    bool toggle_value = false;
    int dropdown_index = 0;
    std::string text_value;
    std::vector<std::array<float, 2>> curve_points;

    // Slider constraints
    float min_val = 0.0f;
    float max_val = 1.0f;
    float step = 0.05f;

    // Dropdown options
    std::vector<std::string> options;

    // Text constraints
    int max_length = 256;

    // Curve labels
    std::string x_label;
    std::string y_label;
};

// ── Zone state ────────────────────────────────────────────────────

struct ZoneInfo {
    std::string name;
};

// ── Panel state ───────────────────────────────────────────────────

struct TuningPanelState {
    // Profile list
    std::vector<std::string> profile_names;
    int selected_profile = 0;
    bool profiles_loaded = false;
    bool list_requested = false;

    // Active profile
    bool profile_active = false;
    std::string name;
    std::string genre;
    std::string description;
    std::string thematic_promise;
    std::string register_text;

    // Axes (zone-aware)
    std::string mortality_weight;
    std::string power_fantasy;
    std::string shitpost_tolerance;

    // Reaction signature
    std::string reaction_template;
    std::string reaction_description;

    // Directive
    std::string directive;

    // Zones
    std::vector<ZoneInfo> zones;
    int active_zone = -1;       // -1 = base profile (no zone)

    // Knobs grouped by domain
    std::vector<std::string> knob_domains;
    std::vector<KnobState> knobs;

    // Behavioral instructions output
    std::string behavioral_instructions;
};

static TuningPanelState state;

// ── Helpers ───────────────────────────────────────────────────────

std::vector<KnobState> knobs_for_domain(const std::string& domain) {
    std::vector<KnobState> result;
    for (auto& k : state.knobs) {
        if (k.domain == domain) {
            result.push_back(k);
        }
    }
    return result;
}

// Format a JSON object string from key-value pairs
std::string json_obj(std::initializer_list<std::pair<std::string, std::string>> pairs) {
    std::string out = "{";
    bool first = true;
    for (auto& [k, v] : pairs) {
        if (!first) out += ", ";
        out += "\"" + k + "\": " + v;
        first = false;
    }
    out += "}";
    return out;
}

std::string json_str(const std::string& s) {
    return "\"" + s + "\"";
}

} // anonymous namespace

// ── Bridge handler registration ───────────────────────────────────

void register_tuning_bridge_handlers(BridgeClient& bridge) {
    // tune_profiles — list of profile names
    bridge.on("tune_profiles", [](const BridgeMsg& msg) {
        // Parse profile names from JSON array in data.profiles
        // Raw JSON: {"type":"tune_profiles","data":{"profiles":["name1","name2",...]}}
        std::string profiles_str = msg.data_string("profiles");
        // profiles_str is a JSON array like ["a","b","c"]
        state.profile_names.clear();
        size_t pos = 0;
        while ((pos = profiles_str.find('"', pos)) != std::string::npos) {
            pos++; // skip opening quote
            auto end = profiles_str.find('"', pos);
            if (end == std::string::npos) break;
            state.profile_names.push_back(profiles_str.substr(pos, end - pos));
            pos = end + 1;
        }
        state.profiles_loaded = true;
    });

    // tune_profile_data — full profile loaded
    bridge.on("tune_profile_data", [](const BridgeMsg& msg) {
        state.profile_active = true;
        state.name = msg.get_string("name");
        state.genre = msg.get_string("genre");
        state.description = msg.get_string("description");
        state.thematic_promise = msg.get_string("thematic_promise");
        state.register_text = msg.get_string("register");
        state.mortality_weight = msg.get_string("mortality_weight");
        state.power_fantasy = msg.get_string("power_fantasy");
        state.shitpost_tolerance = msg.get_string("shitpost_tolerance");
        state.reaction_template = msg.get_string("reaction_template");
        state.reaction_description = msg.get_string("reaction_description");
        state.directive = msg.get_string("bot_directive");
        state.behavioral_instructions = msg.get_string("instructions");
    });

    // tune_state_update — axes/zone/knobs changed
    bridge.on("tune_state_update", [](const BridgeMsg& msg) {
        std::string zone = msg.get_string("zone");
        if (zone.empty() || zone == "null") {
            state.active_zone = -1;
        } else {
            for (int i = 0; i < (int)state.zones.size(); ++i) {
                if (state.zones[i].name == zone) {
                    state.active_zone = i;
                    break;
                }
            }
        }
        state.behavioral_instructions = msg.get_string("instructions");
    });

    // tune_instructions — behavioral text update
    bridge.on("tune_instructions", [](const BridgeMsg& msg) {
        state.behavioral_instructions = msg.data_string("text");
    });
}

/**
 * Render the thematic tension calibration panel.
 * Call this every frame from main loop.
 *
 * All data comes from bridge.py via tune_* messages.
 * The panel sends tune_load, tune_zone, tune_set_knob, etc.
 */
void render_tuning_panel() {
    ImGui::Begin("Thematic Calibration");

    // Connection status
    if (!g_bridge->is_connected()) {
        ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.4f, 1.0f),
            "Bridge disconnected");
        if (ImGui::Button("Reconnect")) {
            g_bridge->connect();
        }
        ImGui::End();
        return;
    }

    // ── Profile Selector ──────────────────────────────────────────

    if (!state.profiles_loaded) {
        ImGui::TextColored(ImVec4(0.5f, 0.5f, 0.5f, 1.0f),
            "Waiting for profile list from bridge...");
        if (!state.list_requested) {
            g_bridge->send("tune_list");
            state.list_requested = true;
        }
        ImGui::End();
        return;
    }

    if (!state.profile_names.empty()) {
        // Build combo items string
        std::string combo_items;
        for (auto& n : state.profile_names) {
            combo_items += n;
            combo_items += '\0';
        }
        combo_items += '\0';

        ImGui::Combo("Profile", &state.selected_profile,
                     combo_items.c_str());
        ImGui::SameLine();
        if (ImGui::Button("Load")) {
            g_bridge->send("tune_load",
                json_obj({{"name", json_str(state.profile_names[state.selected_profile])}}));
        }
    }

    if (!state.profile_active) {
        ImGui::End();
        return;
    }

    ImGui::Separator();

    // ── Profile Header ────────────────────────────────────────────

    ImGui::TextColored(ImVec4(0.345f, 0.651f, 1.0f, 1.0f),
        "%s", state.name.c_str());
    if (!state.genre.empty()) {
        ImGui::SameLine();
        ImGui::TextColored(ImVec4(0.49f, 0.522f, 0.565f, 1.0f),
            "(%s)", state.genre.c_str());
    }
    if (!state.description.empty()) {
        ImGui::TextWrapped("%s", state.description.c_str());
    }

    ImGui::Separator();

    // ── Thematic Promise ──────────────────────────────────────────

    if (!state.thematic_promise.empty()) {
        ImGui::TextColored(ImVec4(0.345f, 0.651f, 1.0f, 1.0f),
            "Thematic Promise");
        ImGui::TextWrapped("%s", state.thematic_promise.c_str());
        if (!state.register_text.empty()) {
            ImGui::TextColored(ImVec4(0.49f, 0.522f, 0.565f, 1.0f),
                "Register: %s", state.register_text.c_str());
        }
        ImGui::Separator();
    }

    // ── Thematic Axes ─────────────────────────────────────────────

    ImGui::TextColored(ImVec4(0.345f, 0.651f, 1.0f, 1.0f),
        "Thematic Axes");
    if (state.active_zone >= 0) {
        ImGui::SameLine();
        ImGui::TextColored(ImVec4(1.0f, 0.85f, 0.3f, 1.0f),
            "[zone: %s]", state.zones[state.active_zone].name.c_str());
    }

    ImGui::BulletText("Mortality Weight: %s",
        state.mortality_weight.c_str());
    ImGui::BulletText("Power Fantasy: %s",
        state.power_fantasy.c_str());
    ImGui::BulletText("Shitpost Tolerance: %s",
        state.shitpost_tolerance.c_str());

    ImGui::Separator();

    // ── Zone Selector ─────────────────────────────────────────────

    if (!state.zones.empty()) {
        ImGui::TextColored(ImVec4(0.345f, 0.651f, 1.0f, 1.0f),
            "Zones");

        for (int i = 0; i < (int)state.zones.size(); ++i) {
            bool is_active = (i == state.active_zone);
            if (is_active) {
                ImGui::PushStyleColor(ImGuiCol_Button,
                    ImVec4(0.2f, 0.4f, 0.8f, 1.0f));
            }
            if (ImGui::Button(state.zones[i].name.c_str())) {
                if (is_active) {
                    g_bridge->send("tune_zone_exit");
                } else {
                    g_bridge->send("tune_zone",
                        json_obj({{"zone", json_str(state.zones[i].name)}}));
                }
            }
            if (is_active) {
                ImGui::PopStyleColor();
            }
            if (i < (int)state.zones.size() - 1) {
                ImGui::SameLine();
            }
        }

        if (state.active_zone >= 0) {
            ImGui::SameLine();
            if (ImGui::SmallButton("Exit Zone")) {
                g_bridge->send("tune_zone_exit");
            }
        }

        ImGui::Separator();
    }

    // ── Knobs by Domain ───────────────────────────────────────────

    if (!state.knobs.empty()) {
        ImGui::TextColored(ImVec4(0.345f, 0.651f, 1.0f, 1.0f),
            "Knobs");

        for (auto& domain : state.knob_domains) {
            if (ImGui::CollapsingHeader(domain.c_str(),
                    ImGuiTreeNodeFlags_DefaultOpen)) {

                for (auto& knob : state.knobs) {
                    if (knob.domain != domain) continue;

                    ImGui::PushID(knob.id.c_str());

                    if (knob.knob_type == "slider") {
                        if (ImGui::SliderFloat(knob.label.c_str(),
                                &knob.slider_value,
                                knob.min_val, knob.max_val)) {
                            g_bridge->send("tune_set_knob",
                                json_obj({{"id", json_str(knob.id)},
                                          {"value", std::to_string(knob.slider_value)}}));
                        }
                    }
                    else if (knob.knob_type == "toggle") {
                        if (ImGui::Checkbox(knob.label.c_str(),
                                &knob.toggle_value)) {
                            g_bridge->send("tune_set_knob",
                                json_obj({{"id", json_str(knob.id)},
                                          {"value", knob.toggle_value ? "true" : "false"}}));
                        }
                    }
                    else if (knob.knob_type == "dropdown") {
                        std::string opts;
                        for (auto& o : knob.options) {
                            opts += o;
                            opts += '\0';
                        }
                        opts += '\0';
                        if (ImGui::Combo(knob.label.c_str(),
                                &knob.dropdown_index,
                                opts.c_str())) {
                            g_bridge->send("tune_set_knob",
                                json_obj({{"id", json_str(knob.id)},
                                          {"value", json_str(knob.options[knob.dropdown_index])}}));
                        }
                    }
                    else if (knob.knob_type == "curve") {
                        ImGui::Text("%s", knob.label.c_str());
                        if (!knob.curve_points.empty() &&
                            ImPlot::BeginPlot(knob.label.c_str(),
                                ImVec2(-1, 150))) {
                            std::vector<float> xs, ys;
                            for (auto& pt : knob.curve_points) {
                                xs.push_back(pt[0]);
                                ys.push_back(pt[1]);
                            }
                            ImPlot::PlotLine("##curve",
                                xs.data(), ys.data(),
                                (int)xs.size());
                            ImPlot::EndPlot();
                        }
                    }
                    else if (knob.knob_type == "text") {
                        char buf[512];
                        strncpy(buf, knob.text_value.c_str(),
                                sizeof(buf) - 1);
                        buf[sizeof(buf) - 1] = '\0';
                        if (ImGui::InputText(knob.label.c_str(),
                                buf, sizeof(buf))) {
                            knob.text_value = buf;
                            g_bridge->send("tune_set_knob",
                                json_obj({{"id", json_str(knob.id)},
                                          {"value", json_str(knob.text_value)}}));
                        }
                    }

                    if (!knob.description.empty()) {
                        ImGui::SameLine();
                        ImGui::TextColored(
                            ImVec4(0.49f, 0.522f, 0.565f, 1.0f),
                            "(?)");
                        if (ImGui::IsItemHovered()) {
                            ImGui::SetTooltip("%s",
                                knob.description.c_str());
                        }
                    }

                    ImGui::PopID();
                }
            }
        }

        if (ImGui::Button("Reset All Knobs")) {
            g_bridge->send("tune_reset_knobs");
        }

        ImGui::Separator();
    }

    // ── Behavioral Instructions Output ─────────────────────────────

    if (ImGui::CollapsingHeader("Behavioral Instructions",
            ImGuiTreeNodeFlags_DefaultOpen)) {
        if (ImGui::Button("Refresh")) {
            g_bridge->send("tune_get_instructions");
        }
        ImGui::BeginChild("InstructionsScroll", ImVec2(0, 300),
            ImGuiChildFlags_Borders, ImGuiWindowFlags_HorizontalScrollbar);
        ImGui::TextUnformatted(
            state.behavioral_instructions.c_str());
        ImGui::EndChild();
    }

    ImGui::End();
}
