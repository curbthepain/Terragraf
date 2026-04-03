cmake_minimum_required(VERSION 3.16)
project(TerragrafImGui LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

# ── Dependencies (FetchContent) ────────────────────────────────────

# GLFW 3.4+ (windowing — auto-detects Win32/Wayland)
FetchContent_Declare(glfw
    GIT_REPOSITORY https://github.com/glfw/glfw.git
    GIT_TAG        3.4
    GIT_SHALLOW    TRUE
)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_INSTALL OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(glfw)

# GLM (header-only math)
FetchContent_Declare(glm
    GIT_REPOSITORY https://github.com/g-truc/glm.git
    GIT_TAG        1.0.1
    GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(glm)

# glad2 (OpenGL 4.5 core loader)
FetchContent_Declare(glad
    GIT_REPOSITORY https://github.com/Dav1dde/glad.git
    GIT_TAG        v2.0.8
    GIT_SHALLOW    TRUE
    SOURCE_SUBDIR  cmake
)
FetchContent_MakeAvailable(glad)
glad_add_library(glad_gl STATIC REPRODUCIBLE API gl:core=4.5)

# Dear ImGui (docking branch — required for DockSpaceOverViewport)
FetchContent_Declare(imgui
    GIT_REPOSITORY https://github.com/ocornut/imgui.git
    GIT_TAG        v1.91.8-docking
)
FetchContent_MakeAvailable(imgui)

add_library(imgui_lib STATIC
    ${imgui_SOURCE_DIR}/imgui.cpp
    ${imgui_SOURCE_DIR}/imgui_draw.cpp
    ${imgui_SOURCE_DIR}/imgui_tables.cpp
    ${imgui_SOURCE_DIR}/imgui_widgets.cpp
    ${imgui_SOURCE_DIR}/imgui_demo.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_glfw.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_opengl3.cpp
)
target_include_directories(imgui_lib PUBLIC
    ${imgui_SOURCE_DIR}
    ${imgui_SOURCE_DIR}/backends
)
target_link_libraries(imgui_lib PUBLIC glfw glad_gl)

# ImPlot (real-time plotting)
FetchContent_Declare(implot
    GIT_REPOSITORY https://github.com/epezent/implot.git
    GIT_TAG        v0.16
    GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(implot)

add_library(implot_lib STATIC
    ${implot_SOURCE_DIR}/implot.cpp
    ${implot_SOURCE_DIR}/implot_items.cpp
)
target_include_directories(implot_lib PUBLIC ${implot_SOURCE_DIR})
target_link_libraries(implot_lib PUBLIC imgui_lib)

# ImNodes (node graph editor)
FetchContent_Declare(imnodes
    GIT_REPOSITORY https://github.com/Nelarius/imnodes.git
    GIT_TAG        v0.5
    GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(imnodes)

add_library(imnodes_lib STATIC
    ${imnodes_SOURCE_DIR}/imnodes.cpp
)
target_include_directories(imnodes_lib PUBLIC ${imnodes_SOURCE_DIR})
target_compile_definitions(imnodes_lib PRIVATE IMGUI_DEFINE_MATH_OPERATORS)
target_link_libraries(imnodes_lib PUBLIC imgui_lib)

# ── Application ────────────────────────────────────────────────────

find_package(OpenGL REQUIRED)

set(SOURCES
    main.cpp
    math_panel.cpp
    spectrogram_panel.cpp
    node_editor.cpp
    volume_panel.cpp
    tuning_panel.cpp
)

add_executable(terragraf_imgui ${SOURCES})

target_include_directories(terragraf_imgui PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(terragraf_imgui PRIVATE
    imgui_lib
    implot_lib
    imnodes_lib
    glfw
    glad_gl
    glm::glm
    OpenGL::GL
)

# ── Platform ───────────────────────────────────────────────────────

if(UNIX AND NOT APPLE)
    target_link_libraries(terragraf_imgui PRIVATE dl)
endif()

# ── Install ────────────────────────────────────────────────────────

install(TARGETS terragraf_imgui RUNTIME DESTINATION bin)
