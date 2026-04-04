# Hot Context — Terragraf

## Status: Session 6 Complete — Skills Card, Commands Update, Windows Path Fix, Knowledge Registry Planned

Sessions 1-6 complete. Full skills infrastructure, docs overhaul, SVG cards for both commands and skills, Windows path bug fixed, knowledge registry designed and approved.

## What's Done (Session 6)

### 1. Fixed Windows Path Bug in signal_analyze
- **run.py:162**: Changed `":" in args.input` to `(":" in args.input and not Path(args.input).exists())`
- Windows absolute paths (C:\...) no longer misroute to synthetic spec generator
- Removed 2 `pytest.skip()` blocks from test_signal_analyze.py
- All 8 signal_analyze tests now pass on Windows (0 skipped)

### 2. Skills Card (gen_skills_card.py)
- New SVG card generator for all 15 skills, grouped into 8 categories
- Purple header color (#d2a8ff) to distinguish from commands card (blue)
- Categories: Generators, Analyzers, Validators, Workflows, Optimizers, Launchers, Pipelines, Utilities
- Fixed text overflow — shortened descriptions to fit columns

### 3. Commands Card Update (gen_commands_card.py)
- Added 14 missing commands across 5 new sections: ANALYZE, GIT, SKILLS, PROJECTS, ML
- Total: 18 sections, ~55 commands

### 4. COMMANDS.md Overhaul
- Full command reference with all CLI commands
- Added Skills table (15 skills with type, triggers, description)
- Added one-sentence descriptions for all new command groups

### 5. README.md Update
- Skills card embedded below commands card
- New Skills section in architecture overview
- Test counts updated: 424 passed, 11 skipped
- Architecture tree includes `skills/` directory

### Verification Results (Session 6)
- `pytest .scaffold/tests/test_signal_analyze.py` -> 8 passed, 0 skipped
- Both SVG cards generate cleanly
- Pushed to Yibb: f916e23

## What Was Done (Sessions 1-5)

### Session 5: Health Grade A, Music Viz Polish, Layout Persistence, Skill Tests
- Stale routes/tables cleanup (Grade D -> A)
- Music viz: MP3 support, spectrogram heatmap, toggle
- ImGui layout persistence (platform-specific config dirs)
- 29 new tests (test_skills, test_signal_analyze, test_math_solve)

### Session 4: Skills System (15 skills)
- SKILL.toml manifests, runner.py, registry, router, 12 CLI shortcuts

### Session 3: End-to-End Bridge Polish
### Session 2: Windows-Native Polish
### Session 1: Socket Transport + CLI

## Key Files

```
terra.py                                — Python CLI (~55 commands)
gen_commands_card.py                    — SVG commands card generator (18 sections)
gen_skills_card.py                      — SVG skills card generator (8 categories)
.scaffold/skills/runner.py              — Skill discovery + execution engine
.scaffold/skills/registry.table         — 15-skill registry
.scaffold/skills/router.route           — Intent -> skill routing (50+ mappings)
.scaffold/skills/signal_analyze/run.py  — FFT analysis (Windows path bug fixed)
.scaffold/headers/project.h             — Module declarations (16 modules)
.scaffold/routes/structure.route        — Concept -> directory mapping
.scaffold/tables/deps.table             — Module dependency matrix
.scaffold/tests/test_signal_analyze.py  — Signal analysis tests (8 pass, 0 skip)
.scaffold/tests/test_math_solve.py      — Math solver tests (12 tests)
.scaffold/tests/test_skills.py          — Skill runner tests (11 tests)
projects/music-viz/                     — Real-time music visualizer
```

## Debug Notes
- `terra health` -> Grade A (all checks pass)
- `pytest .scaffold/tests/` -> 424 passed, 11 skipped (PySide6 only)
- `terra skill list` -> 15 skills
- `terra analyze sine:440:44100:0.5 --no-render` -> FFT analysis
- `terra solve eigenvalues --matrix "[[1,2],[3,4]]"` -> [-0.372, 5.372]

---

## Plan: Session 7 — Knowledge Registry System

### Priority 1: Build the Knowledge Registry

A secondary registry (separate from skills registry) where the AI records reusable knowledge generated from project work. Lives in `projects/` because it's project-derived, not scaffolding infrastructure.

#### 1.1 Create `projects/KNOWLEDGE.toml`
- Format: `[[knowledge]]` blocks with id, source, category, summary, detail, tags, created
- Categories: pattern | decision | integration | domain | caveat
- Seed with 3 entries from music-viz (FFT import pattern, pydub fallback, OpenGL theme)

#### 1.2 Create `projects/knowledge_writer.py`
- CLI utility to append entries to KNOWLEDGE.toml
- Deduplicates by `id`
- Usage: `python knowledge_writer.py --id "slug" --source "project" --category pattern --summary "..." --detail "..." --tags "t1,t2"`

#### 1.3 Create `projects/knowledge_reader.py`
- Query utility: filter by tag, category, source, or free-text search
- Usage: `python knowledge_reader.py [--tag fft] [--category pattern] [--source music-viz] [--search "query"]`

#### 1.4 Wire into terra.py
- `terra knowledge` — list all entries (summaries)
- `terra knowledge search <query>` — search by keyword
- `terra knowledge add` — delegates to knowledge_writer.py

#### 1.5 Update scaffolding references
- `structure.route`: add knowledge + projects routes
- `deps.table`: add `projects | skills | uses | low`
- `scaffold_project/run.py`: print tip about `terra knowledge add` after creating project

#### 1.6 Tests
- `test_knowledge.py` — writer (add, deduplicate), reader (search, filter by tag/category/source)

#### 1.7 Update docs
- `gen_commands_card.py`: add KNOWLEDGE section
- `COMMANDS.md`: add knowledge commands
- Regenerate commands-card.svg

---

## ── SESSION BREAK ──────────────────────────────────────────────────────
## Everything above is Session 7. Everything below is Session 8+.
## Start a new session before continuing past this line.
## ────────────────────────────────────────────────────────────────────────

---

## Plan: Session 8+ — Polish & Enhancements

### Documentation & Visual Polish
- Verify README test counts against CI (run full suite, confirm 424/11)
- Visual check commands-card.svg for text overflow in new sections
- Update HOT_CONTEXT to Session 8

### Music Viz Enhancements
- Keyboard shortcuts: space=play/pause, left/right=seek 5s
- Mel-scale spectrogram heatmap option (mel filterbank already exists)

### ImGui & Qt Polish
- Ship default layout.ini with sensible panel arrangement
- First-run detection: copy default if no layout.ini exists
- Qt rendering artifacts on drag/resize (likely DPI-related)

### Dependency Sourcing (Large — Multi-Session)
- Source all dependencies locally into `src/` (~25-30GB)
- Requires git LFS or .gitignore planning
- This is its own multi-session effort

## Decisions Made (Session 6)
- Skills card uses purple headers to distinguish from blue commands card
- Shortened skill descriptions to prevent column overflow
- Windows path fix: check `Path.exists()` before treating colon as synthetic spec delimiter
- Knowledge registry lives in `projects/` not `.scaffold/` (project-derived, not scaffolding)
- KNOWLEDGE.toml uses `[[knowledge]]` array-of-tables format for easy append

## Backlog
- Source all dependencies locally into `src/` (~25-30GB)
- Qt app rendering artifacts on drag/resize
- Ship default ImGui layout.ini
- Mel-scale spectrogram heatmap in music viz
- Music viz keyboard shortcuts (space, left/right)
