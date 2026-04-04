# Hot Context — Terragraf

## Status: Skills System Complete — 15 Workflow Skills, Projects Infra, Music Viz

Sessions 1-4 complete. Full skills infrastructure with 15 registered workflow skills, projects directory, music visualizer, and CLI shortcuts for everything.

## What's Done (Session 4)

### Skills Infrastructure (15 skills)
- `.scaffold/skills/` — SKILL.toml manifests, runner.py discovery/execution, registry.table, router.route
- Each skill is a **workflow** composing multiple modules, not a function wrapper

| # | Skill | Type | CLI | What it does |
|---|-------|------|-----|-------------|
| 1 | scaffold_project | generator | `terra project new` | Scaffold projects (cli/qt-app/lib/test) |
| 2 | consistency_scan | validator | `terra skill run consistency_scan` | Validate headers/routes/tables/skills integrity |
| 3 | hot_context | utility | `terra hot` | Read/update/reset session hot context |
| 4 | signal_analyze | analyzer | `terra analyze` | FFT → spectral features → spectrogram → export |
| 5 | math_solve | analyzer | `terra solve` | Eigenvalues, SVD, fit, regression, t-test, DCT |
| 6 | git_flow | workflow | `terra branch/commit/pr` | Conventional branches, structured commits, PR preview |
| 7 | generate | generator | `terra generate` | Module/model/shader gen with lang detection + validation |
| 8 | sharpen_run | optimizer | `terra sharpen` | Self-sharpening with post-validation feedback loop |
| 9 | tune_session | calibrator | `terra tune` | Guided thematic calibration: profiles, zones, knobs |
| 10 | train_model | pipeline | `terra train` | ML pipeline: dataset → model → training → eval |
| 11 | viewer | launcher | `terra viewer` | ImGui lifecycle: build → bridge → launch → cleanup |
| 12 | render_3d | renderer | `terra render` | Surfaces, volumes, node graphs, point clouds |
| 13 | test_suite | validator | `terra test` | Discover/run/categorize tests by subsystem |
| 14 | instance_dispatch | orchestrator | `terra dispatch` | Enqueue tasks, monitor instances, collect results |
| 15 | health_check | diagnostic | `terra health` | System grade A-F: structure + tests + env + queue |

### Projects Directory
- `projects/` at repo root (gitignored)
- `projects/music-viz/` — first test project: Qt + sounddevice + Terragraf FFT + OpenGL spectrum bars

### CLI Expansion (terra.py)
- 12 new shortcut commands: analyze, solve, branch, commit, pr, generate, train, viewer, render, test, dispatch, health
- All delegate to skills via runner.py

## What Was Done (Sessions 1-3)

### Session 3: End-to-End Bridge Polish
- bridge.py: `__main__` entrypoint, signal handling, auto-reconnect
- main.cpp: reconnect timer every ~3s
- tuning_panel.cpp: reconnect button resets state
- viewer_page.py: auto-start bridge, binary path search

### Session 2: Windows-Native Polish
- All hooks/generators converted to Python
- App code fixed for Windows, CI matrix: Ubuntu + Windows

### Session 1: Socket Transport + CLI
- transport.py: SO_EXCLUSIVEADDRUSE on Windows
- terra.py: full Python CLI, 382+ tests passing

## Key Files

```
terra.py                                — Python CLI (30+ commands)
.scaffold/skills/runner.py              — Skill discovery + execution engine
.scaffold/skills/registry.table         — 15-skill registry
.scaffold/skills/router.route           — Intent → skill routing (50+ mappings)
.scaffold/skills/signal_analyze/run.py  — FFT + spectral + spectrogram workflow
.scaffold/skills/math_solve/run.py      — Math computation router (12 operations)
.scaffold/skills/health_check/run.py    — System diagnostic with grading
.scaffold/skills/test_suite/run.py      — Test orchestration by subsystem
.scaffold/headers/project.h             — Module declarations (now incl. skills, projects)
.scaffold/routes/tasks.route            — Intent routing (now incl. all skill routes)
projects/music-viz/                     — Real-time music visualizer
```

## Verification Results (Session 4)
- `terra skill list` — all 15 skills displayed
- `terra analyze sine:440:44100:0.5 --no-render` — FFT analysis works
- `terra solve eigenvalues --matrix "[[1,2],[3,4]]"` — returns [-0.372, 5.372]
- `terra test fft` — 27 passed, 0 failed
- `terra health` — Grade D (39 pre-existing structure issues from stale src/ routes)
- `pytest .scaffold/tests/` — 395 passed

## Debug Notes
- `terra skill list` → shows all 15 registered skills
- `terra analyze <input>` → signal analysis (WAV/CSV/NPY or synthetic)
- `terra solve <op> --data/--matrix` → math computation
- `terra test [module]` → run tests (fft, math, tuning, viz, etc.)
- `terra health [--quick]` → system diagnostic grade
- `terra hot` → this file, formatted
- `terra viewer` → build + bridge + launch ImGui
- `terra dispatch enqueue <desc>` → add task to parallel queue

---

## Plan: Next Session Ideas

### Clean Up Stale Routes/Tables (Priority)
- health_check reports Grade D due to 39 pre-existing issues
- Mostly stale `src/` references in bugs.route and structure.route
- Also undeclared modules in deps.table (ui, core, services, config, compute, imgui, sharpen)
- Fix would raise grade to A/B

### Music Viz Polish
- Add MP3 support (pydub fallback for soundfile)
- Spectrogram heatmap view
- Theme-aware color palette from tuning profiles

### Panel Layout Persistence
- ImGui docking state save/restore
- Remember which panels are open/closed

### Skill Tests
- Add pytest tests for skills/runner.py (discovery, matching, execution)
- Add integration tests for signal_analyze, math_solve

## Decisions Made (Session 4)
- Skills are workflows, not wrappers — each composes multiple modules
- SKILL.toml uses [skill], [triggers], [deps] sections
- Skills discovered by scanning subdirs of .scaffold/skills/ for SKILL.toml
- terra.py shortcuts delegate to skills via _run_skill() helper
- Projects in projects/ are gitignored (user output, not scaffold code)
- health_check grades A-F based on structure issues, test collectability, env
- Signal analysis uses --synthetic for test signals (sine:freq:sr:duration)

## Backlog
- Source all dependencies locally into `src/` (~25-30GB)
- Qt app rendering artifacts on drag/resize
- Panel layout persistence in ImGui
- Clean up stale route/table entries
- Add skill tests to test suite
