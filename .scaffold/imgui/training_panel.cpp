/**
 * .scaffold/imgui/training_panel.cpp
 * Live ML training monitor — loss curves, LR schedule, metrics, status.
 *
 * Receives `training_started`, `training_update`, `training_finished`
 * bridge messages from the train_model skill and renders via ImPlot.
 */

#include "imgui.h"
#include "implot.h"
#include "bridge_client.h"

#include <string>
#include <vector>

extern BridgeClient* g_bridge;

namespace {

struct TrainingState {
    // Model info
    std::string arch;
    std::string device;
    int total_params = 0;
    int total_epochs = 0;

    // Status: "idle" | "training" | "done" | "error"
    std::string status = "idle";
    int current_epoch = 0;
    float elapsed = 0.0f;

    // History (parallel vectors for ImPlot)
    std::vector<float> epoch_idx;
    std::vector<float> train_loss;
    std::vector<float> val_loss;
    std::vector<float> lr_history;

    // Final metrics
    bool has_final = false;
    float final_accuracy = 0.0f;
    float final_f1 = 0.0f;

    void reset() {
        arch.clear();
        device.clear();
        total_params = 0;
        total_epochs = 0;
        status = "training";
        current_epoch = 0;
        elapsed = 0.0f;
        epoch_idx.clear();
        train_loss.clear();
        val_loss.clear();
        lr_history.clear();
        has_final = false;
        final_accuracy = 0.0f;
        final_f1 = 0.0f;
    }
};

TrainingState state;

}  // namespace

// ── Bridge handler registration ────────────────────────────────────

void register_training_bridge_handlers(BridgeClient& bridge) {
    bridge.on("training_started", [](const BridgeMsg& msg) {
        state.reset();
        state.arch = msg.data_string("arch");
        state.device = msg.data_string("device");
        state.total_params = (int)msg.data_number("params");
        state.total_epochs = (int)msg.data_number("epochs");
        state.status = "training";
    });

    bridge.on("training_update", [](const BridgeMsg& msg) {
        int epoch = (int)msg.data_number("epoch");
        float tl = (float)msg.data_number("train_loss");
        float vl = (float)msg.data_number("val_loss");
        float lr = (float)msg.data_number("lr");

        state.current_epoch = epoch;
        state.elapsed = (float)msg.data_number("elapsed");
        state.epoch_idx.push_back((float)epoch);
        state.train_loss.push_back(tl);
        state.val_loss.push_back(vl);
        state.lr_history.push_back(lr);

        if (state.total_epochs == 0) {
            state.total_epochs = (int)msg.data_number("total_epochs");
        }
    });

    bridge.on("training_finished", [](const BridgeMsg& msg) {
        state.status = "done";
        state.has_final = true;
        state.final_accuracy = (float)msg.data_number("accuracy");
        state.final_f1 = (float)msg.data_number("f1");
    });
}

// ── Render ─────────────────────────────────────────────────────────

void render_training_panel() {
    ImGui::Begin("Training Monitor");

    // ── Model info header ────────────────────────────────────────
    if (state.arch.empty()) {
        ImGui::TextDisabled("No training session active.");
        ImGui::TextDisabled("Run: terra train <data_dir> --arch cnn");
        ImGui::End();
        return;
    }

    ImGui::Text("Arch: %s   Device: %s   Params: %d",
                state.arch.c_str(), state.device.c_str(), state.total_params);

    // Status indicator
    if (state.status == "training") {
        ImGui::TextColored(ImVec4(0.2f, 0.83f, 0.6f, 1.0f), "● TRAINING");
    } else if (state.status == "done") {
        ImGui::TextColored(ImVec4(0.3f, 0.6f, 1.0f, 1.0f), "● DONE");
    } else {
        ImGui::TextColored(ImVec4(0.97f, 0.44f, 0.44f, 1.0f), "● %s", state.status.c_str());
    }

    ImGui::SameLine();
    ImGui::Text("   Epoch %d / %d   (%.1fs)",
                state.current_epoch, state.total_epochs, state.elapsed);

    // ── Progress bar ─────────────────────────────────────────────
    float progress = (state.total_epochs > 0)
        ? (float)state.current_epoch / (float)state.total_epochs
        : 0.0f;
    ImGui::ProgressBar(progress, ImVec2(-1, 0));

    ImGui::Separator();

    // ── Loss curves ──────────────────────────────────────────────
    if (ImGui::CollapsingHeader("Loss", ImGuiTreeNodeFlags_DefaultOpen)) {
        if (!state.epoch_idx.empty()) {
            if (ImPlot::BeginPlot("##loss", ImVec2(-1, 180))) {
                ImPlot::SetupAxes("epoch", "loss");
                ImPlot::PlotLine("train",
                    state.epoch_idx.data(),
                    state.train_loss.data(),
                    (int)state.epoch_idx.size());
                ImPlot::PlotLine("val",
                    state.epoch_idx.data(),
                    state.val_loss.data(),
                    (int)state.epoch_idx.size());
                ImPlot::EndPlot();
            }
        } else {
            ImGui::TextDisabled("Waiting for first epoch...");
        }
    }

    // ── LR schedule ──────────────────────────────────────────────
    if (ImGui::CollapsingHeader("Learning Rate")) {
        if (!state.lr_history.empty()) {
            if (ImPlot::BeginPlot("##lr", ImVec2(-1, 150))) {
                ImPlot::SetupAxes("epoch", "lr");
                ImPlot::PlotLine("lr",
                    state.epoch_idx.data(),
                    state.lr_history.data(),
                    (int)state.epoch_idx.size());
                ImPlot::EndPlot();
            }
        }
    }

    // ── Final metrics ────────────────────────────────────────────
    if (state.has_final) {
        ImGui::Separator();
        ImGui::Text("Final Metrics");
        ImGui::Text("  accuracy: %.4f", state.final_accuracy);
        ImGui::Text("  f1:       %.4f", state.final_f1);
    }

    // ── Epoch table (last 10) ────────────────────────────────────
    if (ImGui::CollapsingHeader("Epoch History")) {
        if (ImGui::BeginTable("##epochs", 4,
                ImGuiTableFlags_Borders | ImGuiTableFlags_RowBg |
                ImGuiTableFlags_ScrollY, ImVec2(-1, 150))) {
            ImGui::TableSetupColumn("epoch");
            ImGui::TableSetupColumn("train");
            ImGui::TableSetupColumn("val");
            ImGui::TableSetupColumn("lr");
            ImGui::TableHeadersRow();

            int n = (int)state.epoch_idx.size();
            int start = n > 10 ? n - 10 : 0;
            for (int i = start; i < n; ++i) {
                ImGui::TableNextRow();
                ImGui::TableSetColumnIndex(0);
                ImGui::Text("%d", (int)state.epoch_idx[i]);
                ImGui::TableSetColumnIndex(1);
                ImGui::Text("%.4f", state.train_loss[i]);
                ImGui::TableSetColumnIndex(2);
                ImGui::Text("%.4f", state.val_loss[i]);
                ImGui::TableSetColumnIndex(3);
                ImGui::Text("%.2e", state.lr_history[i]);
            }
            ImGui::EndTable();
        }
    }

    ImGui::End();
}
