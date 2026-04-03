cmake_minimum_required(VERSION 3.16)
project(TerraformerImGui LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Dependencies ────────────────────────────────────────────────────
# These should be installed or available as submodules.
# See THIRD_PARTY_LICENSES.md for license info.

# GLFW 3.4+ (auto-detects Wayland on Linux, Win32 on Windows)
find_package(glfw3 3.4 REQUIRED)

# OpenGL
find_package(OpenGL REQUIRED)

# Dear ImGui — add as subdirectory or fetch
# set(IMGUI_DIR "${CMAKE_CURRENT_SOURCE_DIR}/vendor/imgui")
# set(IMPLOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/vendor/implot")
# set(IMNODES_DIR "${CMAKE_CURRENT_SOURCE_DIR}/vendor/imnodes")

# glad — OpenGL loader
# add_subdirectory(vendor/glad)

# glm — math library
find_package(glm REQUIRED)

# ── Source files ────────────────────────────────────────────────────

set(SOURCES
    main.cpp
    math_panel.cpp
    spectrogram_panel.cpp
    node_editor.cpp
    volume_panel.cpp
)

# ImGui sources (when using as source, not as library)
# list(APPEND SOURCES
#     ${IMGUI_DIR}/imgui.cpp
#     ${IMGUI_DIR}/imgui_draw.cpp
#     ${IMGUI_DIR}/imgui_tables.cpp
#     ${IMGUI_DIR}/imgui_widgets.cpp
#     ${IMGUI_DIR}/imgui_demo.cpp
#     ${IMGUI_DIR}/backends/imgui_impl_glfw.cpp
#     ${IMGUI_DIR}/backends/imgui_impl_opengl3.cpp
#     ${IMPLOT_DIR}/implot.cpp
#     ${IMPLOT_DIR}/implot_items.cpp
#     ${IMNODES_DIR}/imnodes.cpp
# )

# ── Build ───────────────────────────────────────────────────────────

add_executable(terraformer_imgui ${SOURCES})

target_include_directories(terraformer_imgui PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    # ${IMGUI_DIR}
    # ${IMGUI_DIR}/backends
    # ${IMPLOT_DIR}
    # ${IMNODES_DIR}
)

target_link_libraries(terraformer_imgui PRIVATE
    glfw
    OpenGL::GL
    glm::glm
    # glad
)

# ── Platform ────────────────────────────────────────────────────────
# GLFW 3.4+ handles Wayland vs X11 automatically on Linux.
# No platform-specific flags needed.

if(UNIX AND NOT APPLE)
    target_link_libraries(terraformer_imgui PRIVATE dl)
endif()

# ── Install ─────────────────────────────────────────────────────────

install(TARGETS terraformer_imgui RUNTIME DESTINATION bin)
