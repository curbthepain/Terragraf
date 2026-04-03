# .scaffold/ENTRY.md
# READ THIS FIRST. You are an AI. This is your src folder.

## What This Is

Kohala scaffolting. Not a project generator — this IS the project.
You work from inside this structure. Any AI can slot in.

Targets: **Linux (Wayland)** and **Windows 10/11** only.

## Core Concepts

1. **Scaffolting** — this structure. Your src folder. Where you live and work from.
2. **Headers (.h)** — declare what exists. Contracts. Like C headers.
3. **Includes (.inc)** — composable fragments. Snap together like C includes.
4. **Routes (.route)** — navigate from intent to files. "I want to X" → go here.
5. **Tables (.table)** — lookup decisions. Don't re-derive what's known.
6. **Generators (JS/PY)** — execute: read the structure, produce output.
7. **Instances** — multi-instancing replaces agents. Run parallel AI instances
   that share this scaffolting but work on separate tasks. Not sub-agents.
   Pseudo-agents. Structurally different.

## Structure

```
.scaffold/
├── ENTRY.md                ← You are here. Read first.
├── MANIFEST.toml           ← Config. Variables. Feature flags. Platform targets.
│
├── headers/                ← .h — DECLARE what exists (contracts)
│   ├── project.h           ← Modules, structure, boundaries
│   ├── conventions.h       ← Naming, patterns, hard rules
│   ├── deps.h              ← External dependencies
│   ├── platform.h          ← Platform contract (Win10/11, Linux/Wayland)
│   ├── git.h               ← Git/GitHub workflow contract
│   ├── ml.h                ← ML pipeline contract (PyTorch)
│   ├── compute.h           ← GPU/FFT/Vulkan compute contract
│   └── lang.h              ← Language-specific contracts
│
├── includes/               ← .inc — COMPOSE from reusable fragments
│   ├── license.inc         ← License block
│   ├── file_header.inc     ← Standard file header
│   ├── test_scaffold.inc   ← Test skeleton
│   ├── model_scaffold.inc  ← ML model skeleton
│   ├── shader_scaffold.inc ← GPU shader skeleton
│   └── cmake_scaffold.inc  ← CMake project skeleton
│
├── routes/                 ← .route — NAVIGATE from intent to files
│   ├── tasks.route         ← "I want to do X" → go here
│   ├── bugs.route          ← "symptom Y" → look here
│   └── structure.route     ← "concept Z" → this directory
│
├── tables/                 ← .table — LOOK UP known decisions
│   ├── errors.table        ← Error → cause → fix
│   ├── patterns.table      ← Pattern → where used → example
│   └── deps.table          ← Module → depends on → risk
│
├── instances/              ← Multi-instancing (replaces agents)
│   ├── manager.py          ← Spawn, track, and coordinate instances
│   ├── instance.py         ← Single instance lifecycle
│   ├── shared/             ← Shared state between instances
│   │   ├── queue.json      ← Task queue (instances pull from this)
│   │   ├── results.json    ← Completed results (instances push here)
│   │   └── locks/          ← File locks for coordination
│   └── README.md           ← How multi-instancing works
│
├── git/                    ← Git & GitHub workflow scaffolting
│   ├── branch.sh           ← Branch with conventions
│   ├── commit.sh           ← Structured commits
│   ├── pr.sh               ← PR with templates
│   ├── workflows/          ← CI/CD templates
│   └── templates/          ← PR/issue templates
│
├── ml/                     ← PyTorch ML scaffolting
│   ├── models/             ← Architecture templates (base, CNN, transformer)
│   ├── datasets/           ← Data pipeline templates
│   └── training/           ← Train/eval loops, config
│
├── compute/                ← GPU/Math scaffolting
│   ├── fft/                ← FFT utilities (Python, C++, spectral)
│   ├── vulkan/             ← Vulkan instance, pipeline, memory, layer
│   └── shaders/            ← GLSL compute shaders
│
├── generators/             ← JS/PY scripts that EXECUTE the scaffolting
│   ├── resolve.js          ← Resolves #include directives in .inc files
│   ├── gen_module.js       ← Generates a new module from headers
│   ├── gen_model.py        ← Generates ML model from config
│   ├── gen_shader.py       ← Generates compute shader from spec
│   └── scaffold.sh         ← Master orchestrator (shell baseline)
│
└── hooks/                  ← Lifecycle hooks
    ├── on_enter.sh         ← Run when AI enters the scaffolting
    ├── on_commit.sh        ← Run around commits
    ├── on_generate.sh      ← Run after file generation
    └── on_instance.sh      ← Run when an instance spawns/completes
```

## Flow

1. Read `ENTRY.md` → understand the system (you're doing this now)
2. Read `MANIFEST.toml` → get config, variables, what's enabled
3. Read relevant `.h` → understand what exists
4. Consult `.route` → find where to work
5. Check `.table` → look up known decisions
6. Use `.inc` → compose output from fragments
7. Use `instances/` → spin up parallel work instead of sub-agents
8. Use `git/` → manage version control
9. Use `ml/` → build and train models
10. Use `compute/` → FFT, Vulkan, GPU work
11. Run generators → automate repetitive scaffolting

**Headers declare. Includes compose. Routes navigate. Tables decide.
Generators execute. Instances parallelize.**
