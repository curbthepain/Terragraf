/**
 * .scaffold/imgui/main.cpp
 * Terragraf ImGui application entry point.
 *
 * GLFW + OpenGL 4.5 + Dear ImGui + ImPlot + ImNodes.
 * Platform: Linux (Wayland via GLFW 3.4+) and Windows (Win32).
 *
 * Build: see CMakeLists.txt
 * Run:   terra imgui run
 */

#include <glad/gl.h>
#include <GLFW/glfw3.h>
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include "implot.h"
#include "imnodes.h"

#include <cstdio>
#include <cstdlib>

#include "bridge_client.h"

// Global bridge client — panels use this to send/receive
BridgeClient* g_bridge = nullptr;
static BridgeClient g_bridge_instance;

// Forward declarations for panel render functions
void render_math_panel();
void render_spectrogram_panel();
void render_node_editor();
void render_volume_panel();
void render_tuning_panel();
void render_debug_panel();
void render_settings_panel();

// Bridge handler registration
void register_tuning_bridge_handlers(BridgeClient& bridge);
void register_debug_bridge_handlers();

// Settings accessors
bool settings_show_fps_overlay();
bool settings_show_debug_panel();
bool settings_show_math();
bool settings_show_spectrogram();
bool settings_show_node_editor();
bool settings_show_volume();
bool settings_show_tuning();
bool settings_vsync();
float settings_ui_scale();
bool settings_is_open();
void settings_set_open(bool open);


/**
 * GLFW error callback.
 */
static void glfw_error_callback(int error, const char* description) {
    fprintf(stderr, "GLFW Error %d: %s\n", error, description);
}

int main(int argc, char** argv) {
    // ── Init GLFW ──────────────────────────────────────────────────
    glfwSetErrorCallback(glfw_error_callback);
    if (!glfwInit()) return 1;

    // OpenGL 4.5 core
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 5);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow* window = glfwCreateWindow(1600, 900,
        "Terragraf", nullptr, nullptr);
    if (!window) {
        glfwTerminate();
        return 1;
    }
    glfwMakeContextCurrent(window);
    glfwSwapInterval(1); // VSync

    // ── Init glad ──────────────────────────────────────────────────
    if (!gladLoadGL(glfwGetProcAddress)) {
        fprintf(stderr, "Failed to initialize GLAD\n");
        return 1;
    }

    // ── Init ImGui ─────────────────────────────────────────────────
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImPlot::CreateContext();
    ImNodes::CreateContext();

    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_DockingEnable;

    // Dark theme
    ImGui::StyleColorsDark();

    // Platform/renderer backends
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 450");

    // ── Bridge connection ───────────────────────────────────────────
    g_bridge = &g_bridge_instance;
    register_tuning_bridge_handlers(g_bridge_instance);
    register_debug_bridge_handlers();
    if (!g_bridge_instance.connect()) {
        fprintf(stderr, "[main] bridge not available — running offline\n");
    }

    // ── Main loop ──────────────────────────────────────────────────
    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();

        // Start ImGui frame
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();

        // Dockspace
        ImGui::DockSpaceOverViewport();

        // Poll bridge messages (dispatches to handlers on main thread)
        g_bridge_instance.poll();

        // ── Panels (visibility controlled by settings) ─────────
        if (settings_show_math())         render_math_panel();
        if (settings_show_spectrogram())  render_spectrogram_panel();
        if (settings_show_node_editor())  render_node_editor();
        if (settings_show_volume())       render_volume_panel();
        if (settings_show_tuning())       render_tuning_panel();
        if (settings_show_debug_panel())  render_debug_panel();
        if (settings_is_open())           render_settings_panel();

        // FPS overlay
        if (settings_show_fps_overlay()) {
            ImGui::SetNextWindowPos(ImVec2(10, 10), ImGuiCond_Always);
            ImGui::SetNextWindowBgAlpha(0.4f);
            if (ImGui::Begin("##fps_overlay", nullptr,
                    ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_AlwaysAutoResize |
                    ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoFocusOnAppearing |
                    ImGuiWindowFlags_NoNav)) {
                ImGui::Text("%.1f FPS (%.2f ms)", io.Framerate, 1000.0f / io.Framerate);
            }
            ImGui::End();
        }

        // Render
        ImGui::Render();
        int display_w, display_h;
        glfwGetFramebufferSize(window, &display_w, &display_h);
        glViewport(0, 0, display_w, display_h);
        glClearColor(0.1f, 0.1f, 0.1f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());

        glfwSwapBuffers(window);
    }

    // ── Cleanup ────────────────────────────────────────────────────
    g_bridge_instance.disconnect();
    ImNodes::DestroyContext();
    ImPlot::DestroyContext();
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
    glfwDestroyWindow(window);
    glfwTerminate();

    return 0;
}
