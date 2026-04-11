/**
 * .scaffold/imgui/math_panel.cpp
 * Interactive math modeling panel — sliders, live function plotting.
 *
 * Uses ImGui for controls and ImPlot for real-time graphs.
 * Connects to compute/math/ via bridge.py for heavy computation.
 */

#include "imgui.h"
#include "implot.h"

#include <cmath>
#include <vector>
#include <array>
#include <string>

namespace {

// ── State ──────────────────────────────────────────────────────────

struct MathState {
    // Function parameters (adjustable via sliders)
    float amplitude = 1.0f;
    float frequency = 1.0f;
    float phase = 0.0f;
    float damping = 0.0f;

    // Polynomial coefficients
    float poly_coeffs[5] = {0, 0, 0, 1, 0};  // a4*x^4 + ... + a0
    int poly_degree = 3;

    // Plot data
    std::vector<float> x_data;
    std::vector<float> y_data;
    int n_points = 500;
    float x_min = -5.0f;
    float x_max = 5.0f;

    // Function selector
    int selected_func = 0;
    const char* func_names[6] = {
        "sin(x)", "cos(x)", "exp(x)", "damped sine",
        "polynomial", "gaussian"
    };
};

static MathState state;

// ── Function evaluation ────────────────────────────────────────────

float evaluate(float x) {
    switch (state.selected_func) {
        case 0: // sin
            return state.amplitude * std::sin(state.frequency * x + state.phase);
        case 1: // cos
            return state.amplitude * std::cos(state.frequency * x + state.phase);
        case 2: // exp
            return state.amplitude * std::exp(state.frequency * x);
        case 3: // damped sine
            return state.amplitude * std::exp(-state.damping * std::abs(x))
                   * std::sin(state.frequency * x + state.phase);
        case 4: { // polynomial
            float result = 0;
            float xn = 1;
            for (int i = state.poly_degree; i >= 0; --i) {
                result += state.poly_coeffs[i] * xn;
                xn *= x;
            }
            return result;
        }
        case 5: // gaussian
            return state.amplitude * std::exp(
                -(x - state.phase) * (x - state.phase)
                / (2 * state.frequency * state.frequency)
            );
        default:
            return 0;
    }
}

void update_plot_data() {
    state.x_data.resize(state.n_points);
    state.y_data.resize(state.n_points);
    for (int i = 0; i < state.n_points; ++i) {
        float t = (float)i / (state.n_points - 1);
        state.x_data[i] = state.x_min + t * (state.x_max - state.x_min);
        state.y_data[i] = evaluate(state.x_data[i]);
    }
}

} // anonymous namespace

/**
 * Render the math modeling panel.
 * Call this every frame from main loop.
 */
void render_math_panel() {
    ImGui::Begin("Math Modeling");

    // Function selector
    ImGui::Combo("Function", &state.selected_func,
                 state.func_names, 6);

    ImGui::Separator();

    // Common parameters
    ImGui::SliderFloat("Amplitude", &state.amplitude, 0.01f, 10.0f);
    ImGui::SliderFloat("Frequency", &state.frequency, 0.1f, 20.0f);
    ImGui::SliderFloat("Phase", &state.phase, -3.14159f, 3.14159f);

    if (state.selected_func == 3) {
        ImGui::SliderFloat("Damping", &state.damping, 0.0f, 2.0f);
    }

    if (state.selected_func == 4) {
        ImGui::SliderInt("Degree", &state.poly_degree, 0, 4);
        for (int i = 0; i <= state.poly_degree; ++i) {
            char label[16];
            snprintf(label, sizeof(label), "a%d", i);
            ImGui::SliderFloat(label, &state.poly_coeffs[i], -5.0f, 5.0f);
        }
    }

    ImGui::Separator();

    // Range
    ImGui::SliderFloat("X min", &state.x_min, -100.0f, 0.0f);
    ImGui::SliderFloat("X max", &state.x_max, 0.0f, 100.0f);
    ImGui::SliderInt("Points", &state.n_points, 50, 2000);

    // Update data
    update_plot_data();

    // Plot
    if (ImPlot::BeginPlot("Function Plot", ImVec2(-1, 300))) {
        ImPlot::PlotLine("f(x)",
            state.x_data.data(), state.y_data.data(), state.n_points);
        ImPlot::EndPlot();
    }

    ImGui::End();
}
