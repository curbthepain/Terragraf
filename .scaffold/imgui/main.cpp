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

// #include <glad/glad.h>
// #include <GLFW/glfw3.h>
// #include "imgui.h"
// #include "imgui_impl_glfw.h"
// #include "imgui_impl_opengl3.h"
// #include "implot.h"
// #include "imnodes.h"

#include <cstdio>
#include <cstdlib>

// Forward declarations for panel render functions
void render_math_panel();
void render_spectrogram_panel();
void render_node_editor();
void render_volume_panel();
void render_tuning_panel();

/**
 * GLFW error callback.
 */
static void glfw_error_callback(int error, const char* description) {
    fprintf(stderr, "GLFW Error %d: %s\n", error, description);
}

int main(int argc, char** argv) {
    // ── Init GLFW ──────────────────────────────────────────────────
    // glfwSetErrorCallback(glfw_error_callback);
    // if (!glfwInit()) return 1;

    // OpenGL 4.5 core
    // glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    // glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 5);
    // glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    // GLFWwindow* window = glfwCreateWindow(1600, 900,
    //     "Terragraf — Math Modeling", nullptr, nullptr);
    // if (!window) {
    //     glfwTerminate();
    //     return 1;
    // }
    // glfwMakeContextCurrent(window);
    // glfwSwapInterval(1); // VSync

    // ── Init glad ──────────────────────────────────────────────────
    // if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
    //     fprintf(stderr, "Failed to initialize GLAD\n");
    //     return 1;
    // }

    // ── Init ImGui ─────────────────────────────────────────────────
    // IMGUI_CHECKVERSION();
    // ImGui::CreateContext();
    // ImPlot::CreateContext();
    // ImNodes::CreateContext();
    //
    // ImGuiIO& io = ImGui::GetIO();
    // io.ConfigFlags |= ImGuiConfigFlags_DockingEnable;
    //
    // // Dark theme
    // ImGui::StyleColorsDark();
    //
    // // Platform/renderer backends
    // ImGui_ImplGlfw_InitForOpenGL(window, true);
    // ImGui_ImplOpenGL3_Init("#version 450");

    // ── Main loop ──────────────────────────────────────────────────
    // while (!glfwWindowShouldClose(window)) {
    //     glfwPollEvents();
    //
    //     // Start ImGui frame
    //     ImGui_ImplOpenGL3_NewFrame();
    //     ImGui_ImplGlfw_NewFrame();
    //     ImGui::NewFrame();
    //
    //     // Dockspace
    //     ImGui::DockSpaceOverViewport(ImGui::GetMainViewport());
    //
    //     // ── Panels ─────────────────────────────────────────────
    //     render_math_panel();
    //     render_spectrogram_panel();
    //     render_node_editor();
    //     render_volume_panel();
    //     render_tuning_panel();
    //
    //     // Render
    //     ImGui::Render();
    //     int display_w, display_h;
    //     glfwGetFramebufferSize(window, &display_w, &display_h);
    //     glViewport(0, 0, display_w, display_h);
    //     glClearColor(0.1f, 0.1f, 0.1f, 1.0f);
    //     glClear(GL_COLOR_BUFFER_BIT);
    //     ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    //
    //     glfwSwapBuffers(window);
    // }

    // ── Cleanup ────────────────────────────────────────────────────
    // ImNodes::DestroyContext();
    // ImPlot::DestroyContext();
    // ImGui_ImplOpenGL3_Shutdown();
    // ImGui_ImplGlfw_Shutdown();
    // ImGui::DestroyContext();
    // glfwDestroyWindow(window);
    // glfwTerminate();

    printf("Terragraf ImGui scaffold ready.\n");
    printf("Uncomment code and link dependencies to build.\n");
    printf("See CMakeLists.txt for build instructions.\n");

    return 0;
}
