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
  terra imgui build         build the ImGui app
  terra imgui run           launch interactive viewer
  terra imgui math          math modeling panel info
  terra imgui nodes         node graph editor info

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
```

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
- **hook** runs at the right time. Enter, commit, generate, spawn.
