/**
 * .scaffold/imgui/spectrogram_panel.cpp
 * Real-time spectrogram display panel.
 *
 * Uses ImPlot heatmap for spectrogram visualization.
 * Receives FFT data from compute/fft/ via bridge.py.
 */

// #include "imgui.h"
// #include "implot.h"

#include <vector>
#include <cmath>
#include <algorithm>

namespace {

struct SpectrogramState {
    // Display
    int fft_size = 1024;
    int hop_size = 256;
    int history_frames = 200;       // how many time frames to show
    float min_db = -80.0f;
    float max_db = 0.0f;

    // Spectrogram buffer: (n_freqs, history_frames)
    std::vector<float> spec_buffer;
    int n_freqs = 0;
    int write_pos = 0;
    bool initialized = false;

    // Test signal params
    float test_freq1 = 440.0f;
    float test_freq2 = 880.0f;
    float sample_rate = 44100.0f;
    float test_time = 0.0f;
};

static SpectrogramState state;

void init_spectrogram() {
    state.n_freqs = state.fft_size / 2 + 1;
    state.spec_buffer.resize(state.n_freqs * state.history_frames, state.min_db);
    state.write_pos = 0;
    state.initialized = true;
}

/**
 * Push a new FFT frame into the spectrogram buffer.
 * spectrum: array of n_freqs magnitude values.
 */
void push_frame(const float* spectrum, int n_freqs) {
    if (!state.initialized) init_spectrogram();

    for (int i = 0; i < std::min(n_freqs, state.n_freqs); ++i) {
        // Convert to dB
        float mag = std::max(spectrum[i], 1e-10f);
        float db = 20.0f * std::log10(mag);
        db = std::clamp(db, state.min_db, state.max_db);

        // Write into circular buffer
        state.spec_buffer[i * state.history_frames + state.write_pos] = db;
    }

    state.write_pos = (state.write_pos + 1) % state.history_frames;
}

} // anonymous namespace

/**
 * Render the spectrogram panel.
 * Call this every frame from main loop.
 */
void render_spectrogram_panel() {
    // if (!state.initialized) init_spectrogram();
    //
    // ImGui::Begin("Spectrogram");
    //
    // // Controls
    // ImGui::SliderInt("FFT Size", &state.fft_size, 256, 4096);
    // ImGui::SliderFloat("Min dB", &state.min_db, -120.0f, -20.0f);
    // ImGui::SliderFloat("Max dB", &state.max_db, -20.0f, 20.0f);
    //
    // if (ImGui::Button("Reset")) {
    //     init_spectrogram();
    // }
    //
    // ImGui::Separator();
    //
    // // Test signal controls
    // ImGui::Text("Test Signal");
    // ImGui::SliderFloat("Freq 1 (Hz)", &state.test_freq1, 20.0f, 4000.0f);
    // ImGui::SliderFloat("Freq 2 (Hz)", &state.test_freq2, 20.0f, 4000.0f);
    //
    // // Generate test frame (sine wave mix)
    // std::vector<float> test_spectrum(state.n_freqs, 0.0f);
    // float freq_resolution = state.sample_rate / state.fft_size;
    // int bin1 = (int)(state.test_freq1 / freq_resolution);
    // int bin2 = (int)(state.test_freq2 / freq_resolution);
    // if (bin1 < state.n_freqs) test_spectrum[bin1] = 1.0f;
    // if (bin2 < state.n_freqs) test_spectrum[bin2] = 0.5f;
    // push_frame(test_spectrum.data(), state.n_freqs);
    //
    // // Render heatmap
    // if (ImPlot::BeginPlot("##Spectrogram", ImVec2(-1, 400))) {
    //     ImPlot::PlotHeatmap("dB",
    //         state.spec_buffer.data(),
    //         state.n_freqs, state.history_frames,
    //         state.min_db, state.max_db,
    //         nullptr,
    //         ImPlotPoint(0, 0),
    //         ImPlotPoint(state.history_frames, state.n_freqs));
    //     ImPlot::EndPlot();
    // }
    //
    // ImGui::End();
}
