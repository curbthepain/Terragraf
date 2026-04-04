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
  terra generate <t> <name> unified code generation (module/model/shader)

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

ANALYZE
  terra analyze <input>     signal/audio FFT analysis
  terra solve <op>          math computation router (linalg, stats, transforms)

MATH
  terra math eval <expr>    evaluate a math expression
  terra math linalg <op>    linear algebra operation info
  terra math stats [op]     statistics operation info

GIT
  terra branch <type> <n>   create conventional branch
  terra commit <msg>        structured commit with conventions
  terra pr --preview        PR template/preview

INSTANCES
  terra queue               show the task queue
  terra queue add <task>    add a task to the queue
  terra dispatch <task>     dispatch task to parallel instances

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

MODE
  terra mode                show current mode (CI or App) + capabilities
  terra mode check          exit 0 if app mode, exit 1 if CI
  terra mode can <cap>      check if a capability is available

SKILLS
  terra skill list          list all registered skills
  terra skill run <name>    execute a skill by name
  terra hot [action]        session hot context (show/update)
  terra health              full system diagnostic

PROJECTS
  terra project new <name>  scaffold a new project into projects/

ML
  terra train <dir>         ML training pipeline
  terra viewer              ImGui viewer lifecycle (build/bridge/launch)
  terra render <type> <in>  3D visualization (surfaces, volumes, meshes)
  terra test [module]       run test suite by subsystem

APP
  terra app                 launch the Qt container app
  terra app --offscreen     launch headless (for testing)
```

## Skills

Terragraf includes 15 registered skills — self-contained workflows the CLI
dispatches to. Run `terra skill list` to see them all.

| Skill | Type | Triggers | What it does |
|-------|------|----------|--------------|
| scaffold_project | generator | new project, create project | Scaffold a new project into projects/ |
| consistency_scan | validator | scan, check integrity | Verify headers, routes, tables, skills integrity |
| hot_context | utility | hot context, session status | Read, display, or update session hot context |
| signal_analyze | analyzer | analyze signal, run fft | FFT, spectral features, spectrogram export |
| math_solve | analyzer | solve math, eigenvalues | Linalg, algebra, stats, transforms |
| git_flow | workflow | branch, commit, pr | Git workflow: branch, commit, PR with conventions |
| generate | generator | generate module/model | Code generation with language detection |
| sharpen_run | optimizer | sharpen, analytics | Self-sharpening: analyze, preview, apply, validate |
| tune_session | calibrator | tune session, load universe | Thematic calibration: profiles, zones, knobs |
| train_model | pipeline | train model, ml pipeline | ML training: dataset, model, evaluation |
| viewer | launcher | launch viewer, imgui | ImGui viewer lifecycle: build, bridge, launch |
| render_3d | renderer | render 3d, volume, mesh | 3D visualization: surfaces, volumes, point clouds |
| test_suite | validator | run tests, validate | Test orchestration: discover, run, report |
| instance_dispatch | orchestrator | dispatch task | Parallel instance orchestration |
| health_check | diagnostic | health check | Full system diagnostic: structure, tests, env |

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
- **analyze** runs FFT and spectral analysis on signals and audio files.
- **solve** routes math problems to the right solver (linalg, stats, algebra).
- **queue** is for parallel work. Tasks go in, instances pull them out.
- **dispatch** sends tasks to parallel AI instances.
- **imgui** builds and runs the real-time ImGui math modeling app.
- **viz** renders spectrograms, heatmaps, streams, and 3D views.
- **math** evaluates expressions and navigates math primitives.
- **sharpen** prunes stale entries, promotes hot ones, learns from usage.
- **tune** loads universe profiles and generates behavioral instructions from thematic axes.
- **mode** detects CI vs App. Tells the AI what it can and can't build.
- **skill** lists and runs registered workflow skills.
- **hot** manages session hot context — the running log of what's happening now.
- **health** runs a full system diagnostic: structure, tests, analytics, environment.
- **project** scaffolds new projects into the projects/ directory.
- **train** runs the ML training pipeline end to end.
- **test** discovers and runs tests by subsystem with reporting.
- **app** launches the Qt container — the graphical shell for Terragraf.
- **hook** runs at the right time. Enter, commit, generate, spawn.
