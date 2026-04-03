# terra commands

```
SETUP
  terra init                wire hooks, check env, first run

NAVIGATE
  terra status              what's here, what works
  terra route <intent>      where do I go for this?
  terra route feature       -> headers/project.h
  terra route bug           -> routes/bugs.route
  terra route model         -> ml/models/base_model.py

LOOK UP
  terra lookup <error>      known fix for this error?
  terra pattern [name]      what design pattern fits?
  terra dep [module]        what depends on what?

BUILD
  terra gen module <name>   generate a new module
  terra gen model <name>    generate a PyTorch model
  terra gen shader <name>   generate a compute shader

LIFECYCLE
  terra hook enter          run the entry hook
  terra hook commit         run the commit hook
  terra hook generate       run after file generation
  terra hook instance       run on instance spawn

IMGUI
  terra imgui build         build the ImGui app (cmake + make)
  terra imgui run           launch interactive viewer
  terra imgui bridge        start the Python bridge server

VISUALIZE
  terra viz spectrogram     render spectrogram from signal
  terra viz heatmap         render 2D heatmap
  terra viz stream          real-time data plotter
  terra viz 3d nodes        3D node graph
  terra viz 3d mesh         3D mesh/surface
  terra viz 3d volume       volumetric rendering

MATH
  terra math eval <expr>    evaluate a math expression
  terra math linalg <op>    linear algebra operation info
  terra math stats [op]     statistics operation info

INSTANCES
  terra queue               show the task queue
  terra queue add <task>    add a task to the queue

SHARPEN
  terra sharpen             run self-sharpening engine
  terra sharpen --dry-run   preview what would change
  terra sharpen status      show analytics summary

TUNING
  terra tune                show active profile + axes + knobs
  terra tune list           list available universe profiles
  terra tune load <name>    load a universe profile
  terra tune zone <name>    enter a thematic zone
  terra tune zone --exit    exit current zone
  terra tune set <id> <val> set a knob value
  terra tune axes           show current thematic axes
  terra tune directive      show current bot directive
  terra tune instructions   full behavioral instruction output
  terra tune promise        show thematic promise

APP
  terra app                 launch the Qt container app
  terra app --offscreen     launch headless (for testing)
```

## Qt container pages

The Qt app (`terra app`) includes five pages accessible via sidebar or Ctrl+1-5:

| Page | Key | What it does |
|------|-----|--------------|
| Home | Ctrl+1 | Landing page, test status, quick nav |
| Viewer | Ctrl+2 | Launch/stop bridge.py and ImGui processes |
| Tuning | Ctrl+3 | Profile selector, zone buttons, knob widgets, behavioral instructions |
| Debug | Ctrl+4 | Bridge connection, ping/RTT, message log, stats, test sender |
| Settings | Ctrl+5 | Bridge host/port, paths, panel visibility, persistent config |

## ImGui panels

The ImGui viewer (`terra imgui run`) includes seven dockable panels:

| Panel | What it does |
|-------|--------------|
| Math | Interactive function plotting with sliders |
| Spectrogram | Real-time FFT magnitude heatmap |
| Node Editor | Visual graph editor with ImNodes |
| Volume Slicer | Orthogonal slice viewer for volumetric data |
| Tuning | Thematic calibration (mirrors CLI via bridge) |
| Debug | Message log, FPS/RTT graphs, connection status |
| Settings | Panel visibility, theme, bridge config, render settings |

## One sentence each

- **route** finds where to work. You say what you want, it says where to go.
- **lookup** finds known fixes. You paste the error, it gives the answer.
- **pattern** shows how code is structured here. Match it, don't clash.
- **dep** shows what touches what. Check before you change.
- **gen** builds files from the scaffolding. Not from scratch.
- **queue** is for parallel work. Tasks go in, instances pull them out.
- **imgui** builds and runs the real-time ImGui math modeling app.
- **viz** renders spectrograms, heatmaps, streams, and 3D views.
- **math** evaluates expressions and navigates math primitives.
- **sharpen** prunes stale entries, promotes hot ones, learns from usage.
- **tune** loads universe profiles and generates behavioral instructions from thematic axes.
- **app** launches the Qt container — the graphical shell for Terragraf.
- **hook** runs at the right time. Enter, commit, generate, spawn.
