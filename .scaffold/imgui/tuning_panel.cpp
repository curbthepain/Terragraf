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

#include <cmath>
#include <vector>
#include <array>
#include <string>
#include <algorithm>

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

} // anonymous namespace

/**
 * Render the thematic tension calibration panel.
 * Call this every frame from main loop.
 *
 * All data comes from bridge.py via tune_* messages.
 * The panel sends tune_load, tune_zone, tune_set_knob, etc.
 */
void render_tuning_panel() {
    ImGui::Begin("Thematic Calibration");

    // ── Profile Selector ──────────────────────────────────────────

    if (!state.profiles_loaded) {
        ImGui::TextColored(ImVec4(0.5f, 0.5f, 0.5f, 1.0f),
            "Waiting for profile list from bridge...");
        // On first frame, send tune_list request via bridge
        // bridge_send("tune_list", {});
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
            // bridge_send("tune_load",
            //     {{"name", state.profile_names[state.selected_profile]}});
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
                    // bridge_send("tune_zone_exit", {});
                } else {
                    // bridge_send("tune_zone",
                    //     {{"zone", state.zones[i].name}});
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
                // bridge_send("tune_zone_exit", {});
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
                            // bridge_send("tune_set_knob",
                            //     {{"id", knob.id},
                            //      {"value", knob.slider_value}});
                        }
                    }
                    else if (knob.knob_type == "toggle") {
                        if (ImGui::Checkbox(knob.label.c_str(),
                                &knob.toggle_value)) {
                            // bridge_send("tune_set_knob",
                            //     {{"id", knob.id},
                            //      {"value", knob.toggle_value}});
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
                            // bridge_send("tune_set_knob",
                            //     {{"id", knob.id},
                            //      {"value",
                            //       knob.options[knob.dropdown_index]}});
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
                            // bridge_send("tune_set_knob",
                            //     {{"id", knob.id},
                            //      {"value", knob.text_value}});
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
            // bridge_send("tune_reset_knobs", {});
        }

        ImGui::Separator();
    }

    // ── Behavioral Instructions Output ─────────────────────────────

    if (ImGui::CollapsingHeader("Behavioral Instructions",
            ImGuiTreeNodeFlags_DefaultOpen)) {
        if (ImGui::Button("Refresh")) {
            // bridge_send("tune_get_instructions", {});
        }
        ImGui::BeginChild("InstructionsScroll", ImVec2(0, 300),
            ImGuiChildFlags_Borders, ImGuiWindowFlags_HorizontalScrollbar);
        ImGui::TextUnformatted(
            state.behavioral_instructions.c_str());
        ImGui::EndChild();
    }

    ImGui::End();
}
