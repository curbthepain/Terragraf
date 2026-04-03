/**
 * settings_panel.cpp — Basic settings window for Terragraf ImGui app.
 *
 * Bridge connection config, render settings, UI preferences.
 */

#include "imgui.h"
#include "bridge_client.h"
#include <cstring>
#include <cstdio>

// ── State ──────────────────────────────────────────────────────────

struct SettingsState {
    // Bridge
    char bridge_host[128] = "127.0.0.1";
    int  bridge_port = 9876;
    bool auto_reconnect = true;
    float reconnect_interval = 3.0f;

    // Render
    bool vsync = true;
    int  target_fps = 60;
    float ui_scale = 1.0f;

    // UI
    int  theme_idx = 0;  // 0=dark, 1=light, 2=classic
    bool show_fps_overlay = true;
    bool show_debug_panel = true;

    // Panels visibility
    bool show_math = true;
    bool show_spectrogram = true;
    bool show_node_editor = true;
    bool show_volume = true;
    bool show_tuning = true;

    // Dirty flag
    bool needs_apply = false;
};

namespace {
    SettingsState settings;
    bool settings_open = true;
}

// ── Accessors (used by main.cpp) ───────────────────────────────────

bool settings_show_fps_overlay()  { return settings.show_fps_overlay; }
bool settings_show_debug_panel()  { return settings.show_debug_panel; }
bool settings_show_math()         { return settings.show_math; }
bool settings_show_spectrogram()  { return settings.show_spectrogram; }
bool settings_show_node_editor()  { return settings.show_node_editor; }
bool settings_show_volume()       { return settings.show_volume; }
bool settings_show_tuning()       { return settings.show_tuning; }
bool settings_vsync()             { return settings.vsync; }
int  settings_target_fps()        { return settings.target_fps; }
float settings_ui_scale()         { return settings.ui_scale; }

const char* settings_bridge_host() { return settings.bridge_host; }
int  settings_bridge_port()        { return settings.bridge_port; }

void settings_set_open(bool open) { settings_open = open; }
bool settings_is_open()           { return settings_open; }

// ── Render ─────────────────────────────────────────────────────────

extern BridgeClient* g_bridge;

void render_settings_panel() {
    if (!settings_open) return;

    ImGui::Begin("Settings", &settings_open, ImGuiWindowFlags_AlwaysAutoResize);

    // ── Bridge ──
    if (ImGui::CollapsingHeader("Bridge Connection", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::InputText("Host", settings.bridge_host, sizeof(settings.bridge_host));
        ImGui::InputInt("Port", &settings.bridge_port);
        if (settings.bridge_port < 1) settings.bridge_port = 1;
        if (settings.bridge_port > 65535) settings.bridge_port = 65535;
        ImGui::Checkbox("Auto-reconnect", &settings.auto_reconnect);
        if (settings.auto_reconnect) {
            ImGui::SliderFloat("Interval (s)", &settings.reconnect_interval, 1.0f, 30.0f, "%.1f");
        }

        if (g_bridge) {
            if (g_bridge->is_connected()) {
                ImGui::TextColored(ImVec4(0.2f, 0.83f, 0.6f, 1.0f), "Connected");
                ImGui::SameLine();
                if (ImGui::Button("Disconnect")) {
                    g_bridge->disconnect();
                }
            } else {
                ImGui::TextColored(ImVec4(0.97f, 0.44f, 0.44f, 1.0f), "Disconnected");
                ImGui::SameLine();
                if (ImGui::Button("Connect")) {
                    g_bridge->connect();
                }
            }
        }
    }

    ImGui::Separator();

    // ── Render ──
    if (ImGui::CollapsingHeader("Render", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Checkbox("VSync", &settings.vsync);
        if (!settings.vsync) {
            ImGui::SliderInt("Target FPS", &settings.target_fps, 30, 240);
        }
        ImGui::SliderFloat("UI Scale", &settings.ui_scale, 0.75f, 2.0f, "%.2f");
        if (ImGui::IsItemDeactivatedAfterEdit()) {
            ImGui::GetIO().FontGlobalScale = settings.ui_scale;
        }
    }

    ImGui::Separator();

    // ── Theme ──
    if (ImGui::CollapsingHeader("Theme")) {
        const char* themes[] = { "Dark", "Light", "Classic" };
        if (ImGui::Combo("Style", &settings.theme_idx, themes, 3)) {
            switch (settings.theme_idx) {
                case 0: ImGui::StyleColorsDark(); break;
                case 1: ImGui::StyleColorsLight(); break;
                case 2: ImGui::StyleColorsClassic(); break;
            }
        }
    }

    ImGui::Separator();

    // ── Panel Visibility ──
    if (ImGui::CollapsingHeader("Panels", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Checkbox("Math Panel", &settings.show_math);
        ImGui::Checkbox("Spectrogram", &settings.show_spectrogram);
        ImGui::Checkbox("Node Editor", &settings.show_node_editor);
        ImGui::Checkbox("Volume Slicer", &settings.show_volume);
        ImGui::Checkbox("Tuning", &settings.show_tuning);
        ImGui::Separator();
        ImGui::Checkbox("Debug Panel", &settings.show_debug_panel);
        ImGui::Checkbox("FPS Overlay", &settings.show_fps_overlay);
    }

    ImGui::Separator();

    // ── Reset ──
    if (ImGui::Button("Reset to Defaults")) {
        settings = SettingsState{};
        ImGui::StyleColorsDark();
        ImGui::GetIO().FontGlobalScale = 1.0f;
    }

    ImGui::End();
}
