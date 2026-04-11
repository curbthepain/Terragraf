/**
 * debug_panel.cpp — End-to-end debug overlay for Terragraf ImGui app.
 *
 * Shows bridge connection status, message log, latency, FPS,
 * and allows sending test messages.
 */

#include "imgui.h"
#include "implot.h"
#include "bridge_client.h"
#include <vector>
#include <string>
#include <chrono>
#include <deque>
#include <cstdio>
#include <cstring>
#include <mutex>

// ── Types ──────────────────────────────────────────────────────────

struct DebugLogEntry {
    double      timestamp;   // seconds since panel init
    std::string direction;   // "SEND" or "RECV"
    std::string msg_type;
    std::string payload;     // truncated raw json
};

struct DebugState {
    // Connection
    bool bridge_connected = false;
    int  reconnect_attempts = 0;

    // Message log
    std::deque<DebugLogEntry> log;
    static constexpr size_t MAX_LOG = 500;
    bool auto_scroll = true;
    bool show_payloads = false;

    // Stats
    uint64_t msgs_sent = 0;
    uint64_t msgs_recv = 0;
    uint64_t bytes_sent = 0;
    uint64_t bytes_recv = 0;

    // Latency tracking (ping-pong)
    double last_ping_time = 0.0;
    double last_rtt_ms = -1.0;
    std::deque<float> rtt_history;
    static constexpr size_t MAX_RTT_HISTORY = 120;

    // FPS history
    std::deque<float> fps_history;
    static constexpr size_t MAX_FPS_HISTORY = 120;

    // Test message
    char test_msg_type[64] = "ping";
    char test_msg_data[256] = "{}";

    // Filter
    char filter[128] = "";

    // Timing
    double init_time = 0.0;
    bool   initialized = false;
};

namespace {
    DebugState state;
    std::mutex log_mutex;
}

// ── Helpers ────────────────────────────────────────────────────────

static double now_seconds() {
    using namespace std::chrono;
    static auto start = steady_clock::now();
    return duration<double>(steady_clock::now() - start).count();
}

static std::string truncate(const std::string& s, size_t max_len = 120) {
    if (s.size() <= max_len) return s;
    return s.substr(0, max_len) + "...";
}

// ── Public API (called from bridge hooks) ──────────────────────────

void debug_log_send(const std::string& msg_type, const std::string& payload, size_t bytes) {
    std::lock_guard<std::mutex> lock(log_mutex);
    state.msgs_sent++;
    state.bytes_sent += bytes;
    state.log.push_back({now_seconds(), "SEND", msg_type, truncate(payload)});
    if (state.log.size() > DebugState::MAX_LOG) state.log.pop_front();
}

void debug_log_recv(const std::string& msg_type, const std::string& payload, size_t bytes) {
    std::lock_guard<std::mutex> lock(log_mutex);
    state.msgs_recv++;
    state.bytes_recv += bytes;
    state.log.push_back({now_seconds(), "RECV", msg_type, truncate(payload)});
    if (state.log.size() > DebugState::MAX_LOG) state.log.pop_front();

    // RTT calculation from pong
    if (msg_type == "pong" && state.last_ping_time > 0.0) {
        double rtt = (now_seconds() - state.last_ping_time) * 1000.0;
        state.last_rtt_ms = rtt;
        state.rtt_history.push_back(static_cast<float>(rtt));
        if (state.rtt_history.size() > DebugState::MAX_RTT_HISTORY)
            state.rtt_history.pop_front();
        state.last_ping_time = 0.0;
    }
}

void debug_set_connected(bool connected) {
    state.bridge_connected = connected;
    if (!connected) state.reconnect_attempts++;
}

// ── Bridge handler registration ────────────────────────────────────

extern BridgeClient* g_bridge;  // defined in main.cpp

void register_debug_bridge_handlers() {
    if (!g_bridge) return;
    g_bridge->on("pong", [](const BridgeMsg& msg) {
        debug_log_recv("pong", msg.raw_json, msg.raw_json.size());
    });
    g_bridge->on("debug_echo", [](const BridgeMsg& msg) {
        debug_log_recv("debug_echo", msg.raw_json, msg.raw_json.size());
    });
}

// ── Render ─────────────────────────────────────────────────────────

void render_debug_panel() {
    if (!state.initialized) {
        state.init_time = now_seconds();
        state.initialized = true;
    }

    ImGui::Begin("Debug — End to End");

    // ── Connection status ──
    if (ImGui::CollapsingHeader("Connection", ImGuiTreeNodeFlags_DefaultOpen)) {
        if (state.bridge_connected) {
            ImGui::TextColored(ImVec4(0.2f, 0.83f, 0.6f, 1.0f), "● CONNECTED");
        } else {
            ImGui::TextColored(ImVec4(0.97f, 0.44f, 0.44f, 1.0f), "● DISCONNECTED");
        }
        ImGui::SameLine();
        ImGui::TextDisabled("(reconnects: %d)", state.reconnect_attempts);

        if (g_bridge) {
            state.bridge_connected = g_bridge->is_connected();
            if (state.bridge_connected) {
                if (ImGui::Button("Send Ping")) {
                    state.last_ping_time = now_seconds();
                    g_bridge->send("ping", "{}");
                    debug_log_send("ping", "{}", 2);
                }
                ImGui::SameLine();
                if (state.last_rtt_ms >= 0.0) {
                    ImGui::Text("RTT: %.2f ms", state.last_rtt_ms);
                } else {
                    ImGui::TextDisabled("RTT: --");
                }
            } else {
                if (ImGui::Button("Reconnect")) {
                    g_bridge->connect();
                }
            }
        }
    }

    ImGui::Separator();

    // ── Stats ──
    if (ImGui::CollapsingHeader("Stats", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Columns(2, "stats_cols", false);
        ImGui::Text("Sent: %llu msgs", (unsigned long long)state.msgs_sent);
        ImGui::Text("Sent: %llu bytes", (unsigned long long)state.bytes_sent);
        ImGui::NextColumn();
        ImGui::Text("Recv: %llu msgs", (unsigned long long)state.msgs_recv);
        ImGui::Text("Recv: %llu bytes", (unsigned long long)state.bytes_recv);
        ImGui::Columns(1);

        // FPS
        float fps = ImGui::GetIO().Framerate;
        state.fps_history.push_back(fps);
        if (state.fps_history.size() > DebugState::MAX_FPS_HISTORY)
            state.fps_history.pop_front();

        ImGui::Text("FPS: %.1f", fps);
        ImGui::Text("Frame time: %.3f ms", 1000.0f / fps);
    }

    ImGui::Separator();

    // ── Graphs ──
    if (ImGui::CollapsingHeader("Graphs")) {
        if (!state.fps_history.empty() && ImPlot::BeginPlot("##fps", ImVec2(-1, 120))) {
            ImPlot::SetupAxes("", "FPS", ImPlotAxisFlags_NoLabel, ImPlotAxisFlags_AutoFit);
            ImPlot::SetupAxisLimits(ImAxis_X1, 0, (double)DebugState::MAX_FPS_HISTORY, ImPlotCond_Always);
            std::vector<float> fv(state.fps_history.begin(), state.fps_history.end());
            ImPlot::PlotLine("FPS", fv.data(), (int)fv.size());
            ImPlot::EndPlot();
        }
        if (!state.rtt_history.empty() && ImPlot::BeginPlot("##rtt", ImVec2(-1, 120))) {
            ImPlot::SetupAxes("", "ms", ImPlotAxisFlags_NoLabel, ImPlotAxisFlags_AutoFit);
            ImPlot::SetupAxisLimits(ImAxis_X1, 0, (double)DebugState::MAX_RTT_HISTORY, ImPlotCond_Always);
            std::vector<float> rv(state.rtt_history.begin(), state.rtt_history.end());
            ImPlot::PlotLine("RTT", rv.data(), (int)rv.size());
            ImPlot::EndPlot();
        }
    }

    ImGui::Separator();

    // ── Test message ──
    if (ImGui::CollapsingHeader("Send Test Message")) {
        ImGui::InputText("Type", state.test_msg_type, sizeof(state.test_msg_type));
        ImGui::InputText("Data", state.test_msg_data, sizeof(state.test_msg_data));
        if (ImGui::Button("Send") && g_bridge && g_bridge->is_connected()) {
            g_bridge->send(state.test_msg_type, state.test_msg_data);
            debug_log_send(state.test_msg_type, state.test_msg_data,
                           strlen(state.test_msg_data));
        }
    }

    ImGui::Separator();

    // ── Message log ──
    if (ImGui::CollapsingHeader("Message Log", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Checkbox("Auto-scroll", &state.auto_scroll);
        ImGui::SameLine();
        ImGui::Checkbox("Show payloads", &state.show_payloads);
        ImGui::SameLine();
        ImGui::InputTextWithHint("##filter", "filter...", state.filter, sizeof(state.filter));
        ImGui::SameLine();
        if (ImGui::Button("Clear")) {
            std::lock_guard<std::mutex> lock(log_mutex);
            state.log.clear();
        }

        ImGui::BeginChild("log_scroll", ImVec2(0, 300), true);
        {
            std::lock_guard<std::mutex> lock(log_mutex);
            for (auto& e : state.log) {
                // Filter
                if (state.filter[0] != '\0') {
                    if (e.msg_type.find(state.filter) == std::string::npos &&
                        e.direction.find(state.filter) == std::string::npos)
                        continue;
                }

                ImVec4 col = (e.direction == "SEND")
                    ? ImVec4(0.29f, 0.62f, 1.0f, 1.0f)   // blue
                    : ImVec4(0.2f, 0.83f, 0.6f, 1.0f);    // green

                ImGui::TextColored(ImVec4(0.45f, 0.45f, 0.5f, 1.0f),
                                   "[%7.2f]", e.timestamp);
                ImGui::SameLine();
                ImGui::TextColored(col, "%-4s", e.direction.c_str());
                ImGui::SameLine();
                ImGui::Text("%s", e.msg_type.c_str());

                if (state.show_payloads && !e.payload.empty()) {
                    ImGui::SameLine();
                    ImGui::TextDisabled("  %s", e.payload.c_str());
                }
            }
        }
        if (state.auto_scroll)
            ImGui::SetScrollHereY(1.0f);
        ImGui::EndChild();
    }

    ImGui::End();
}
