/**
 * .scaffold/compute/render/gl_context.cpp
 * OpenGL context creation scaffold — Wayland (Linux) and Win32 (Windows).
 *
 * Creates a GLFW window with an OpenGL 4.5 core profile context.
 * Platform-specific backends are handled by GLFW 3.4+.
 *
 * Dependencies:
 *   - GLFW 3.4+ (zlib license)
 *   - glad (MIT/PD) for OpenGL function loading
 *
 * Build:
 *   g++ -std=c++17 gl_context.cpp -lglfw -lGL -ldl -o gl_context
 *   (Windows: link glfw3.lib opengl32.lib)
 */

#pragma once

#include <stdexcept>
#include <string>
#include <functional>

// Forward declarations — include glad/glfw in your build
// #include <glad/glad.h>
// #include <GLFW/glfw3.h>

namespace scaffold::render {

struct ContextConfig {
    int width = 1280;
    int height = 720;
    std::string title = "Terragraf";
    int gl_major = 4;
    int gl_minor = 5;
    bool vsync = true;
    bool resizable = true;
    bool fullscreen = false;
};

/**
 * Create and manage an OpenGL context via GLFW.
 *
 * Usage:
 *   GLContext ctx({.width = 1920, .height = 1080, .title = "My App"});
 *   ctx.init();
 *   while (!ctx.should_close()) {
 *       // render...
 *       ctx.swap();
 *       ctx.poll();
 *   }
 *   ctx.destroy();
 */
class GLContext {
public:
    explicit GLContext(const ContextConfig& config = {})
        : config_(config), window_(nullptr) {}

    ~GLContext() { destroy(); }

    /**
     * Initialize GLFW, create window, load OpenGL functions.
     * Throws on failure.
     */
    void init() {
        // GLFW init
        // if (!glfwInit())
        //     throw std::runtime_error("Failed to initialize GLFW");

        // Window hints
        // glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, config_.gl_major);
        // glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, config_.gl_minor);
        // glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
        // glfwWindowHint(GLFW_RESIZABLE, config_.resizable ? GLFW_TRUE : GLFW_FALSE);

        // Platform: GLFW 3.4+ auto-detects Wayland vs X11 on Linux
        // No platform-specific code needed here

        // Create window
        // GLFWmonitor* monitor = config_.fullscreen ? glfwGetPrimaryMonitor() : nullptr;
        // window_ = glfwCreateWindow(config_.width, config_.height,
        //                            config_.title.c_str(), monitor, nullptr);
        // if (!window_) {
        //     glfwTerminate();
        //     throw std::runtime_error("Failed to create GLFW window");
        // }

        // glfwMakeContextCurrent(window_);

        // Load OpenGL via glad
        // if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
        //     throw std::runtime_error("Failed to initialize GLAD");

        // VSync
        // glfwSwapInterval(config_.vsync ? 1 : 0);

        // Viewport
        // glViewport(0, 0, config_.width, config_.height);
    }

    bool should_close() const {
        // return glfwWindowShouldClose(window_);
        return false;
    }

    void swap() {
        // glfwSwapBuffers(window_);
    }

    void poll() {
        // glfwPollEvents();
    }

    void destroy() {
        // if (window_) {
        //     glfwDestroyWindow(window_);
        //     window_ = nullptr;
        // }
        // glfwTerminate();
    }

    void set_resize_callback(std::function<void(int, int)> callback) {
        resize_callback_ = callback;
        // glfwSetFramebufferSizeCallback(window_, [](GLFWwindow*, int w, int h) {
        //     glViewport(0, 0, w, h);
        // });
    }

    // void* native_window() const { return window_; }
    const ContextConfig& config() const { return config_; }

private:
    ContextConfig config_;
    void* window_;  // GLFWwindow*
    std::function<void(int, int)> resize_callback_;
};

} // namespace scaffold::render
