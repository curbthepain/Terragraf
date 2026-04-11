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
#include <cstring>
#include <string>
#include <sys/stat.h>

#ifdef _WIN32
#include <shlobj.h>
#pragma comment(lib, "shell32.lib")
#define GLFW_EXPOSE_NATIVE_WIN32
#else
#include <pwd.h>
#include <unistd.h>
#ifdef __linux__
  // X11 native handle (Wayland has no reparentable handle)
  #if defined(GLFW_EXPOSE_NATIVE_X11) || !defined(GLFW_EXPOSE_NATIVE_WAYLAND)
    #define GLFW_EXPOSE_NATIVE_X11
  #endif
#endif
#endif

#include <GLFW/glfw3native.h>

#include "bridge_client.h"

// Layout ini path — persists docking state across sessions
static std::string g_ini_path;

static std::string get_layout_path() {
    std::string base;
#ifdef _WIN32
    char path[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathA(nullptr, CSIDL_LOCAL_APPDATA, nullptr, 0, path))) {
        base = std::string(path) + "\\Terragraf";
    } else {
        base = ".";
    }
#else
    const char* home = getenv("HOME");
    if (!home) home = getpwuid(getuid())->pw_dir;
    base = std::string(home) + "/.config/terragraf";
#endif
    return base + "/layout.ini";
}

// Global bridge client — panels use this to send/receive
BridgeClient* g_bridge = nullptr;
static BridgeClient g_bridge_instance;

// Embedded mode — set via --embedded CLI flag
static bool g_embedded = false;

// Store GLFW window globally so bridge handlers can access it
static GLFWwindow* g_window = nullptr;

// Current context from Qt (set by context_switch message)
static std::string g_active_tab_type;   // "native" or "external"
static std::string g_active_session_id;
static std::string g_active_label;

// Forward declarations for panel render functions
void render_math_panel();
void render_spectrogram_panel();
void render_node_editor();
void render_volume_panel();
void render_tuning_panel();
void render_debug_panel();
void render_settings_panel();
void render_training_panel();

// Bridge handler registration
void register_tuning_bridge_handlers(BridgeClient& bridge);
void register_debug_bridge_handlers();
void register_training_bridge_handlers(BridgeClient& bridge);

// Settings accessors
bool settings_show_fps_overlay();
bool settings_show_debug_panel();
bool settings_show_math();
bool settings_show_spectrogram();
bool settings_show_node_editor();
bool settings_show_volume();
bool settings_show_tuning();
bool settings_show_training();
bool settings_vsync();
float settings_ui_scale();
bool settings_is_open();
void settings_set_open(bool open);

// Layout persistence — exposed for settings panel
const char* layout_ini_path() { return g_ini_path.c_str(); }

/**
 * Get the path to default_layout.ini shipped alongside the executable.
 */
static std::string get_default_layout_path() {
#ifdef _WIN32
    char exe_path[MAX_PATH];
    GetModuleFileNameA(nullptr, exe_path, MAX_PATH);
    std::string dir(exe_path);
    dir = dir.substr(0, dir.find_last_of("\\/"));
    return dir + "\\default_layout.ini";
#else
    // Resolve via /proc/self/exe on Linux
    char exe_path[4096];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len > 0) {
        exe_path[len] = '\0';
        std::string dir(exe_path);
        dir = dir.substr(0, dir.rfind('/'));
        return dir + "/default_layout.ini";
    }
    return "default_layout.ini";
#endif
}

/**
 * Ensure parent directory of a path exists.
 */
static void ensure_parent_dir(const std::string& path) {
    std::string dir = path;
#ifdef _WIN32
    auto sep = dir.find_last_of("\\/");
#else
    auto sep = dir.rfind('/');
#endif
    if (sep == std::string::npos) return;
    dir = dir.substr(0, sep);

#ifdef _WIN32
    CreateDirectoryA(dir.c_str(), nullptr);
#else
    mkdir(dir.c_str(), 0755);
#endif
}

/**
 * Copy a file from src to dst using simple fread/fwrite.
 * Returns true on success.
 */
static bool copy_file(const std::string& src, const std::string& dst) {
    FILE* in = fopen(src.c_str(), "rb");
    if (!in) return false;
    FILE* out = fopen(dst.c_str(), "wb");
    if (!out) { fclose(in); return false; }
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), in)) > 0) {
        fwrite(buf, 1, n, out);
    }
    fclose(in);
    fclose(out);
    return true;
}

/**
 * Copy default_layout.ini to the user's config path.
 */
static void install_default_layout() {
    ensure_parent_dir(g_ini_path);
    std::string src = get_default_layout_path();
    if (!copy_file(src, g_ini_path)) {
        fprintf(stderr, "[layout] could not copy default from %s\n", src.c_str());
    }
}

void reset_layout() {
    // Wipe in-memory parsed settings (no ClearIniSettings in this ImGui version)
    ImGui::LoadIniSettingsFromMemory("", 0);
    std::remove(g_ini_path.c_str());
    // Restore the curated default rather than leaving no file
    install_default_layout();
    // Re-parse the freshly-installed file so the new layout takes effect
    ImGui::LoadIniSettingsFromDisk(g_ini_path.c_str());
}


/**
 * GLFW error callback.
 */
static void glfw_error_callback(int error, const char* description) {
    fprintf(stderr, "GLFW Error %d: %s\n", error, description);
}

/**
 * Register bridge handlers for Qt embedding protocol.
 * Must be called after g_window is set.
 */
static void register_embedding_bridge_handlers(BridgeClient& bridge) {
    // get_window_handle — Qt requests the native window handle for reparenting
    bridge.on("get_window_handle", [](const BridgeMsg& msg) {
        if (!g_window) return;
        std::string platform;
        uint64_t handle = 0;

#ifdef _WIN32
        handle = reinterpret_cast<uint64_t>(glfwGetWin32Window(g_window));
        platform = "win32";
#elif defined(GLFW_EXPOSE_NATIVE_X11)
        handle = static_cast<uint64_t>(glfwGetX11Window(g_window));
        platform = "x11";
#else
        platform = "wayland";
#endif

        char buf[256];
        snprintf(buf, sizeof(buf),
            "\"handle\": %llu, \"platform\": \"%s\"",
            (unsigned long long)handle, platform.c_str());
        g_bridge->send("window_handle_response", std::string(buf));
    });

    // context_switch — Qt tells us which tab is active
    bridge.on("context_switch", [](const BridgeMsg& msg) {
        g_active_tab_type = msg.data_string("tab_type");
        g_active_session_id = msg.data_string("session_id");
        g_active_label = msg.data_string("label");
        fprintf(stderr, "[embed] context_switch: %s / %s\n",
            g_active_tab_type.c_str(), g_active_label.c_str());
    });

    // resize — Qt forwards its container size
    bridge.on("resize", [](const BridgeMsg& msg) {
        if (!g_window) return;
        int w = static_cast<int>(msg.data_number("width"));
        int h = static_cast<int>(msg.data_number("height"));
        if (w > 0 && h > 0) {
            glfwSetWindowSize(g_window, w, h);
        }
    });

    // route_tree, scaffold_snapshot, activity_feed — store for panel rendering
    // (panels read from g_bridge message queue via existing poll mechanism)
    bridge.on("route_tree", [](const BridgeMsg& msg) {
        // Panels will read this data via their own bridge handlers
        fprintf(stderr, "[embed] route_tree received\n");
    });
    bridge.on("scaffold_snapshot", [](const BridgeMsg& msg) {
        fprintf(stderr, "[embed] scaffold_snapshot received\n");
    });
    bridge.on("activity_feed", [](const BridgeMsg& msg) {
        fprintf(stderr, "[embed] activity_feed received\n");
    });
}

int main(int argc, char** argv) {
    // ── Parse CLI flags ────────────────────────────────────────────
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--embedded") == 0) {
            g_embedded = true;
        }
    }

    // ── Init GLFW ──────────────────────────────────────────────────
    glfwSetErrorCallback(glfw_error_callback);
    if (!glfwInit()) return 1;

    // OpenGL 4.5 core
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 5);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    // Embedded mode: no decorations, floating (for reparenting into Qt)
    if (g_embedded) {
        glfwWindowHint(GLFW_DECORATED, GLFW_FALSE);
        glfwWindowHint(GLFW_FLOATING, GLFW_TRUE);
    }

    GLFWwindow* window = glfwCreateWindow(1600, 900,
        "Terragraf", nullptr, nullptr);
    if (!window) {
        glfwTerminate();
        return 1;
    }
    g_window = window;  // Store globally for bridge handlers
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

    // Persistent layout — save/restore docking state
    g_ini_path = get_layout_path();

    // First-run detection — copy default layout if none exists
    if (FILE* f = fopen(g_ini_path.c_str(), "r")) {
        fclose(f);
    } else {
        install_default_layout();
    }

    io.IniFilename = g_ini_path.c_str();

    // Dark theme
    ImGui::StyleColorsDark();

    // Platform/renderer backends
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 450");

    // ── Bridge connection ───────────────────────────────────────────
    g_bridge = &g_bridge_instance;
    register_tuning_bridge_handlers(g_bridge_instance);
    register_debug_bridge_handlers();
    register_training_bridge_handlers(g_bridge_instance);
    register_embedding_bridge_handlers(g_bridge_instance);
    if (!g_bridge_instance.connect()) {
        fprintf(stderr, "[main] bridge not available — running offline\n");
    }

    // ── Main loop ──────────────────────────────────────────────────
    int reconnect_counter = 0;
    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();

        // Start ImGui frame
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();

        // Dockspace
        ImGui::DockSpaceOverViewport();

        // Auto-reconnect to bridge every ~3 seconds if disconnected
        if (!g_bridge_instance.is_connected()) {
            if (++reconnect_counter >= 180) {
                reconnect_counter = 0;
                g_bridge_instance.connect();
            }
        } else {
            reconnect_counter = 0;
        }

        // Poll bridge messages (dispatches to handlers on main thread)
        g_bridge_instance.poll();

        // ── Panels (visibility controlled by settings) ─────────
        if (settings_show_math())         render_math_panel();
        if (settings_show_spectrogram())  render_spectrogram_panel();
        if (settings_show_node_editor())  render_node_editor();
        if (settings_show_volume())       render_volume_panel();
        if (settings_show_tuning())       render_tuning_panel();
        if (settings_show_debug_panel())  render_debug_panel();
        if (settings_show_training())     render_training_panel();
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
