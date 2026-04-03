# Terragraf

**This is not a code generator. This is the environment the AI operates inside of.**

[![CI](https://github.com/curbthepain/Terragraf/actions/workflows/ci.yml/badge.svg)](https://github.com/curbthepain/Terragraf/actions/workflows/ci.yml)

Terragraf is the working directory any AI reads on entry. It provides
structure, navigation, composition, and execution — everything an AI
needs to orient itself in a codebase and start producing immediately.

Tools like Claude Code, Cursor, and Aider burn context window on
rediscovering project structure every session. Terragraf eliminates
that tax — the AI reads headers, follows routes, and consults tables
instead of scanning every file or relying on summarization.

---

## Quickstart

```bash
# Clone and enter
git clone https://github.com/curbthepain/Terragraf.git
cd Terragraf

# Initialize in your project
./terra init

# See what's here
./terra status

# Route an intent
./terra route bug        # -> routes/bugs.route
./terra route feature    # -> headers/project.h
```

The `terra` CLI wires hooks, checks your environment, and gives the AI
a single entry point. See [COMMANDS.md](COMMANDS.md) for the full
command reference.

---

## What it does

Terragraf gives an AI session seven interlocking systems:

```
.scaffold/
├── headers/          .h    — what exists (modules, deps, platform targets)
├── includes/         .inc  — composable fragments (license, test skeletons)
├── routes/           .route — intent → location ("fix bug" → bugs.route)
├── tables/           .table — pre-made decisions (error fixes, dep graphs)
├── generators/             — scripts that read structure and produce output
├── instances/              — peer AI instances sharing one scaffold
├── git/                    — branch/commit/PR workflows baked in
│
├── compute/
│   ├── fft/                — FFT / spectral analysis (numpy + C++ FFTW)
│   ├── math/               — linalg, algebra, stats, transforms
│   ├── shaders/            — Vulkan/GLSL compute shaders
│   ├── vulkan/             — Vulkan instance, pipeline, memory
│   └── render/             — OpenGL mesh + volume renderers
├── viz/                    — spectrograms, heatmaps, 3D nodes, volumes
├── imgui/                  — real-time ImGui math modeling app
├── ml/                     — PyTorch models, datasets, training
├── hooks/                  — lifecycle hooks (enter, commit, generate)
└── tests/                  — pytest suite
```

### Headers

`.h` files declare what exists in a project — modules, conventions,
dependencies, platform targets. The AI reads these to understand the
shape of things without scanning every file.

### Includes

`.inc` fragments compose together like C includes. License blocks, file
headers, test skeletons, shader skeletons — small reusable pieces that
snap into generated output.

### Routes

`.route` tables map intent to location. "I need to fix a bug" routes to
one place. "I need to add a feature" routes to another. The AI stops
guessing and starts navigating.

### Tables

`.table` lookups for decisions already made. Known error patterns,
design patterns in use, internal dependency graphs. Compressed knowledge
the AI consults instead of re-deriving.

### Generators

JS, Python, and shell scripts that read the structure above and produce
output. Resolve includes, generate modules, scaffold models, emit
shaders.

### Instances

Multiple AI instances running as peers instead of a parent/child agent
hierarchy. They share the same scaffolding, pull tasks from a shared
queue, and write results back. No context window tax. No summarization
loss.

This is the architectural thesis of Terragraf — see
[INSTANCES.md](INSTANCES.md) for the full design.

### Git

Branching, commit, and PR workflows baked into the structure so the AI
follows project conventions without being told each time.

---

## What's next

- **Self-sharpening routes and tables** — the scaffolding updates itself
  from encountered errors and completed tasks instead of staying static.
  Routes that never fire get pruned. Error patterns that keep appearing
  get added to tables automatically. The scaffold becomes a learning
  surface, not a frozen config.

- **Instance coordination over sockets and pipes** — replacing
  filesystem IPC with real-time socket dispatch for sub-millisecond task
  handoff between instances.

- **Language-aware output** — generators adapt conventions and tooling
  per project language without separate configurations.

See [ROADMAP.md](ROADMAP.md) for the full phased plan.

---

## Platforms

Linux (Wayland) and Windows 10/11.

## Contributors

| Name | Role | Contact |
|------|------|---------|
| Austin Wisniewski | Creator, Lead | [@curbthepain](https://github.com/curbthepain) |
| Claude (Anthropic) | AI Contributor | [anthropic.com](https://anthropic.com) |

## License

Apache 2.0
