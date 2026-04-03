# .scaffold/headers/modes.h
# Operational mode contract — CI vs App
#
# Terragraf operates in two modes. The AI MUST respect these boundaries.
#
# ┌──────────────────────────────────────────────────────────────────┐
# │  MODE     │  CONTEXT          │  WHAT'S ALLOWED                 │
# ├──────────────────────────────────────────────────────────────────┤
# │  ci       │  GitHub Actions,  │  tests, lint, syntax checks,    │
# │           │  headless, no GPU │  generators, routes, tables,    │
# │           │  no display       │  math, queue, sharpen, hooks    │
# │           │                   │                                 │
# │  app      │  Interactive,     │  Everything in CI mode PLUS:    │
# │           │  display server,  │  gui, qt_app, imgui, bridge,    │
# │           │  GPU available    │  viz_interactive, vulkan,       │
# │           │                   │  tuning_ui, settings_ui,        │
# │           │                   │  instances_socket               │
# └──────────────────────────────────────────────────────────────────┘
#
# DETECTION PRIORITY:
#   1. TERRAGRAF_MODE env var ("ci" or "app") — explicit override
#   2. Standard CI env vars (CI, GITHUB_ACTIONS, GITLAB_CI, etc.)
#   3. Display server heuristics (DISPLAY, WAYLAND_DISPLAY)
#
# IN CI MODE, DO NOT:
#   - Build or modify Qt app code (app/*.py)
#   - Build or modify ImGui code (imgui/*.cpp)
#   - Build or modify bridge client/server
#   - Add Vulkan or GPU-dependent features
#   - Create interactive visualizations
#   - Modify settings/tuning UI components
#
# IN CI MODE, DO:
#   - Run and fix tests
#   - Fix lint errors
#   - Update routes, tables, headers
#   - Modify generators, math, sharpen logic
#   - Update CI workflows
#   - Fix Python module code (non-GUI)
#
# USAGE (Python):
#   from modes.detector import detect, require_app
#   info = detect()
#   if info.is_ci:
#       # skip GUI work
#   require_app("qt_app")  # raises RuntimeError in CI mode
#
# USAGE (Shell):
#   terra mode         # show current mode
#   terra mode check   # exit 0 if app, exit 1 if ci
#
# Module: modes/detector.py
# CLI:    terra mode
