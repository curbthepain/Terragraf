# Hot Context — Terragraf

## Status: Session 5 Complete — Health Grade A, Music Viz Polish, Layout Persistence, Skill Tests

Sessions 1-5 complete. Full skills infrastructure, clean scaffold integrity, polished music visualizer, ImGui layout persistence, and comprehensive skill tests.

## What's Done (Session 5)

### 1. Stale Routes/Tables Cleanup (Grade D -> A)
- **bugs.route**: Removed 8 phantom `src/` references (models, main, config, native, services)
- **structure.route**: Removed 14 stale entries (src/, build.gradle.kts, .github/workflows/, checkpoints/, runs/, tests/fixtures/, tests/conftest.*)
- **deps.table**: Replaced undeclared modules (ui, core, models, services, config, compute) with correct declared module dependencies
- **project.h**: Added `#module imgui` and `#module sharpen` declarations (both dirs existed but were undeclared)
- **Result**: `terra health` -> Grade A, 0 structure issues

### 2. Music Viz Polish
- **MP3 support** (player.py): pydub fallback when soundfile can't read a format; AudioSegment -> numpy float32 mono conversion
- **Spectrogram heatmap** (visualizer.py): New `SpectrogramHeatmapWidget` — OpenGL 2D time-frequency heatmap with theme-aware color ramp (BG -> CYAN -> ACCENT -> YELLOW -> RED)
- **Toggle** (main.py): Spectrogram button swaps between spectrum bars and heatmap view
- **requirements.txt**: Added pydub>=0.25

### 3. ImGui Panel Layout Persistence
- **main.cpp**: `io.IniFilename` set to platform-specific config path (`%LOCALAPPDATA%/Terragraf/layout.ini` on Windows, `~/.config/terragraf/layout.ini` on Linux)
- **settings_panel.cpp**: New "Layout" section with Reset Layout button (clears ini + deletes file)
- ImGui auto-saves/restores docking layout, panel positions, sizes, collapsed state

### 4. Skill Tests (29 new tests)
- **test_skills.py** (11 tests): list_skills, match_skill, _load_manifest, run_skill — discovery, matching, entry point validation, error handling
- **test_signal_analyze.py** (8 tests): synthetic sine/chirp/noise/square, bandpass, CSV/NPY input (Windows-skipped), PNG export
- **test_math_solve.py** (12 tests): eigenvalues, SVD, solve, roots, describe, regression, ttest, DCT, hilbert, error handling

### Verification Results (Session 5)
- `terra health` -> Grade A (0 structure issues, 424 tests discoverable)
- `pytest .scaffold/tests/` -> 424 passed, 2 skipped
- Consistency scan -> all checks passed

## What Was Done (Sessions 1-4)

### Session 4: Skills System (15 skills)
- `.scaffold/skills/` — SKILL.toml manifests, runner.py, registry, router
- 15 workflow skills, 12 CLI shortcuts, projects directory

### Session 3: End-to-End Bridge Polish
- bridge.py auto-reconnect, signal handling, viewer auto-launch

### Session 2: Windows-Native Polish
- All hooks/generators converted to Python, CI matrix

### Session 1: Socket Transport + CLI
- transport.py, terra.py CLI, 382+ tests passing

## Key Files

```
terra.py                                — Python CLI (30+ commands)
.scaffold/skills/runner.py              — Skill discovery + execution engine
.scaffold/skills/registry.table         — 15-skill registry
.scaffold/skills/router.route           — Intent -> skill routing (50+ mappings)
.scaffold/headers/project.h             — Module declarations (16 modules incl. imgui, sharpen)
.scaffold/routes/bugs.route             — Bug symptom routing (cleaned)
.scaffold/routes/structure.route        — Concept -> directory mapping (cleaned)
.scaffold/tables/deps.table             — Module dependency matrix (cleaned)
.scaffold/imgui/main.cpp                — ImGui app with layout persistence
.scaffold/imgui/settings_panel.cpp      — Settings with Reset Layout button
projects/music-viz/player.py            — Audio player with MP3 support (pydub)
projects/music-viz/visualizer.py        — Spectrum bars + spectrogram heatmap
projects/music-viz/main.py              — Qt app with spectrogram toggle
.scaffold/tests/test_skills.py          — Skill runner unit tests
.scaffold/tests/test_signal_analyze.py  — Signal analysis integration tests
.scaffold/tests/test_math_solve.py      — Math solver integration tests
```

## Debug Notes
- `terra health` -> Grade A (all checks pass)
- `pytest .scaffold/tests/` -> 424 passed
- `terra skill list` -> 15 skills
- `terra analyze sine:440:44100:0.5 --no-render` -> FFT analysis
- `terra solve eigenvalues --matrix "[[1,2],[3,4]]"` -> [-0.372, 5.372]

---

## Plan: Next Session Ideas

### Music Viz Enhancements
- Mel-scale spectrogram heatmap option (mel filterbank already exists)
- Peak frequency annotation on spectrum bars
- Keyboard shortcuts (space=play/pause, left/right=seek)

### Panel Layout Defaults
- Ship a default `layout.ini` with sensible panel arrangement
- First-run detection to set initial docking layout programmatically

### Expand Skill Tests
- Test `run_skill()` with real skills (health_check, consistency_scan)
- Test skill routing via router.route
- Add benchmark tests for FFT performance

## Decisions Made (Session 5)
- Declared imgui and sharpen as modules in project.h (both had existing dirs)
- deps.table now only references declared modules (removed phantom ui/core/models/services/config/compute)
- structure.route stripped of all non-existent template paths
- Spectrogram heatmap uses theme color ramp (dark->cyan->blue->yellow->red)
- Layout persistence uses platform-specific config dirs (not project-local)
- File input tests now pass on Windows (fixed path-colon detection in cli())

## Backlog
- Source all dependencies locally into `src/` (~25-30GB)
- Qt app rendering artifacts on drag/resize
- Ship default ImGui layout.ini
- Mel-scale spectrogram heatmap in music viz
