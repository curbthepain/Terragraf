/**
 * .scaffold/imgui/volume_panel.cpp
 * Interactive 3D volume slicer — explore volumetric data via orthogonal slices.
 *
 * Uses ImGui sliders to control slice position and ImPlot for rendering.
 * Pairs with viz/3d/volume.py and compute/shaders/volume.comp.
 */

// #include "imgui.h"
// #include "implot.h"

#include <vector>
#include <cmath>
#include <algorithm>

namespace {

struct VolumeState {
    // Volume dimensions
    int size_x = 64;
    int size_y = 64;
    int size_z = 64;

    // Slice positions (0 to size-1)
    int slice_x = 32;   // sagittal
    int slice_y = 32;   // coronal
    int slice_z = 32;   // axial

    // Display
    float window_center = 0.5f;   // density windowing
    float window_width = 1.0f;
    float opacity = 0.8f;

    // Volume data (flat array)
    std::vector<float> volume;
    bool has_data = false;

    // Slice buffers for display
    std::vector<float> slice_xy;  // axial (Z slice)
    std::vector<float> slice_xz;  // coronal (Y slice)
    std::vector<float> slice_yz;  // sagittal (X slice)
};

static VolumeState state;

/**
 * Generate a test volume (3D Gaussian blobs).
 */
void generate_test_volume() {
    state.volume.resize(state.size_x * state.size_y * state.size_z);

    auto idx = [&](int x, int y, int z) -> size_t {
        return z * state.size_x * state.size_y + y * state.size_x + x;
    };

    // Place a few Gaussian blobs
    struct Blob { float cx, cy, cz, sigma, intensity; };
    Blob blobs[] = {
        {0.3f, 0.5f, 0.5f, 0.1f, 1.0f},
        {0.7f, 0.4f, 0.6f, 0.15f, 0.8f},
        {0.5f, 0.7f, 0.3f, 0.12f, 0.9f},
    };

    for (int z = 0; z < state.size_z; ++z) {
        for (int y = 0; y < state.size_y; ++y) {
            for (int x = 0; x < state.size_x; ++x) {
                float fx = (float)x / state.size_x;
                float fy = (float)y / state.size_y;
                float fz = (float)z / state.size_z;

                float val = 0;
                for (auto& b : blobs) {
                    float dx = fx - b.cx, dy = fy - b.cy, dz = fz - b.cz;
                    float d2 = dx*dx + dy*dy + dz*dz;
                    val += b.intensity * std::exp(-d2 / (2 * b.sigma * b.sigma));
                }
                state.volume[idx(x, y, z)] = std::clamp(val, 0.0f, 1.0f);
            }
        }
    }
    state.has_data = true;
}

/**
 * Extract a 2D slice from the volume.
 */
void extract_slices() {
    if (!state.has_data) return;

    auto idx = [&](int x, int y, int z) -> size_t {
        return z * state.size_x * state.size_y + y * state.size_x + x;
    };

    // Axial (XY plane at Z = slice_z)
    state.slice_xy.resize(state.size_x * state.size_y);
    for (int y = 0; y < state.size_y; ++y)
        for (int x = 0; x < state.size_x; ++x)
            state.slice_xy[y * state.size_x + x] = state.volume[idx(x, y, state.slice_z)];

    // Coronal (XZ plane at Y = slice_y)
    state.slice_xz.resize(state.size_x * state.size_z);
    for (int z = 0; z < state.size_z; ++z)
        for (int x = 0; x < state.size_x; ++x)
            state.slice_xz[z * state.size_x + x] = state.volume[idx(x, state.slice_y, z)];

    // Sagittal (YZ plane at X = slice_x)
    state.slice_yz.resize(state.size_y * state.size_z);
    for (int z = 0; z < state.size_z; ++z)
        for (int y = 0; y < state.size_y; ++y)
            state.slice_yz[z * state.size_y + y] = state.volume[idx(state.slice_x, y, z)];
}

} // anonymous namespace

/**
 * Render the volume slicer panel.
 * Call this every frame from main loop.
 */
void render_volume_panel() {
    // if (!state.has_data) generate_test_volume();
    //
    // ImGui::Begin("Volume Slicer");
    //
    // // Slice controls
    // bool changed = false;
    // changed |= ImGui::SliderInt("X (Sagittal)", &state.slice_x, 0, state.size_x - 1);
    // changed |= ImGui::SliderInt("Y (Coronal)", &state.slice_y, 0, state.size_y - 1);
    // changed |= ImGui::SliderInt("Z (Axial)", &state.slice_z, 0, state.size_z - 1);
    //
    // ImGui::Separator();
    //
    // // Window/Level controls
    // ImGui::SliderFloat("Window Center", &state.window_center, 0.0f, 1.0f);
    // ImGui::SliderFloat("Window Width", &state.window_width, 0.01f, 2.0f);
    //
    // if (ImGui::Button("Reset View")) {
    //     state.slice_x = state.size_x / 2;
    //     state.slice_y = state.size_y / 2;
    //     state.slice_z = state.size_z / 2;
    //     state.window_center = 0.5f;
    //     state.window_width = 1.0f;
    //     changed = true;
    // }
    //
    // if (changed) extract_slices();
    //
    // ImGui::Separator();
    //
    // // Render three slice views side by side
    // float wl_min = state.window_center - state.window_width / 2;
    // float wl_max = state.window_center + state.window_width / 2;
    //
    // ImGui::Text("Axial (Z=%d)", state.slice_z);
    // if (ImPlot::BeginPlot("##axial", ImVec2(250, 250))) {
    //     ImPlot::PlotHeatmap("##ax", state.slice_xy.data(),
    //         state.size_y, state.size_x, wl_min, wl_max);
    //     ImPlot::EndPlot();
    // }
    // ImGui::SameLine();
    //
    // ImGui::BeginGroup();
    // ImGui::Text("Coronal (Y=%d)", state.slice_y);
    // if (ImPlot::BeginPlot("##coronal", ImVec2(250, 250))) {
    //     ImPlot::PlotHeatmap("##cor", state.slice_xz.data(),
    //         state.size_z, state.size_x, wl_min, wl_max);
    //     ImPlot::EndPlot();
    // }
    // ImGui::EndGroup();
    // ImGui::SameLine();
    //
    // ImGui::BeginGroup();
    // ImGui::Text("Sagittal (X=%d)", state.slice_x);
    // if (ImPlot::BeginPlot("##sagittal", ImVec2(250, 250))) {
    //     ImPlot::PlotHeatmap("##sag", state.slice_yz.data(),
    //         state.size_z, state.size_y, wl_min, wl_max);
    //     ImPlot::EndPlot();
    // }
    // ImGui::EndGroup();
    //
    // ImGui::End();
}
