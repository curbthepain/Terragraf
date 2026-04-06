# Hot Context — Terragraf

## Status: Session 16 Complete — Local Dependency Sourcing

Sessions 1-16 complete. All dependencies sourced locally into src/. Python via pip --target, C++ via git clone. CMake auto-detects local sources. 723 tests passing.

## Session Roadmap
| Session | Phase | Deliverable | Tests |
|---------|-------|-------------|-------|
| **9** | Tab Infrastructure | Session, Watcher, State, TabWidget | 479 |
| **10** | Native Tab | QueryEngine + IntentParser + chat panel | 514 |
| **11** | External Tab | ExternalDetector + activity feed + scaffold tree + diff viewer | 547 |
| **12** | ImGui Panel | Window reparenting + ImGuiDock + context switching | 579 |
| **14pw** | Pre-Work | hot_decompose skill + README update + route fixes | 609 |
| **13** | Integration | FeedbackLoop + CoherenceManager + welcome tab + end-to-end | 641 |
| **14** | LLM Provider | Anthropic + OpenAI streaming fallback from QueryEngine | 665 |
| **15** | MCP + Worktree | MCP resource server + git worktree isolation backend | 723 |
| **16** | Local Deps | `terra deps` — source all deps into src/ (Python + C++) | 723 |
| **16b** | ML Pipeline | Config, metrics, scheduling, transforms, export, loggers + 40 tests | 763 |

---

## Debug Notes
- `terra health` → Grade A (all checks pass)
- `pytest .scaffold/tests/` → 763 passed, 2 skipped
- `terra skill list` → 17 skills
- `terra workspace status` → prints health summary
- `terra mcp start` → launches MCP server on port 9878
- `terra worktree create` → creates isolated git worktree
- `terra deps` → local dependency status (27 Python + 22 C++)
- `terra deps sync` → source all deps into src/ (~2.9 GB)
- LLM fallback activates when best match score < 0.5

## What's Done (Session 23)

### TunePanel zone status indicator + Yibb→Debug worktree mirror

#### 1. TunePanel inline zone indicator (`app/widgets/panels/tune.py`)
- New `self.zone_label` QLabel placed directly under `active_label` in
  `_build_ui()`. Default text `"Zone: (none)"`, `objectName = "dim"`.
- New `_refresh_zone_indicator()` reads `self._engine.active_zone`
  (engine.py:38) and renders one of three states:
  - `"Zone: (no profile)"` when engine is None
  - `"Zone: (none)"` when engine present but no zone active
  - `"Zone: <name>"` when a zone is active
- New `_exit_zone_clicked()` method replaces the inline lambda on the
  Exit button. Runs `tune zone --exit` subprocess, then mirrors the
  mutation onto the in-memory engine via `engine.exit_zone()`, then
  refreshes the indicator. Same pattern as `_on_knob_changed`: subprocess
  is authoritative for disk state, in-memory engine kept in sync so the
  UI updates immediately without needing to reparse output.
- `_enter_zone_clicked()` extended with the same mirror-and-refresh tail.
- Indicator refresh wired into 4 call sites: `__init__` (after the
  conditional auto-load), `_load_profile_schema()` (after rebuild), and
  both zone click handlers.

#### 2. Tests (+1 in test_browsers_panels.py)
- `test_tune_panel_zone_indicator_reflects_engine` exercises
  `_refresh_zone_indicator` directly against the engine (rather than
  going through the click handlers, so it doesn't depend on the tuning
  subprocess succeeding inside the test environment). Asserts the label
  carries `"Zone:"` after profile load, contains the zone name after
  `engine.enter_zone()` + refresh, and reverts to `"(none)"` after
  `engine.exit_zone()` + refresh.

#### 3. Yibb → Yibb-debug worktree mirror (D:/Terragraf/Debug)
- Both worktrees were already on the same commit `032d519` but had
  divergent uncommitted state — Yibb had 93 changes (this session's work),
  Debug had 156 changes (extra files: `imgui/math_panel.cpp`,
  `node_editor.cpp`, `spectrogram_panel.cpp`, `volume_panel.cpp`,
  `includes/reactions/*`, `headers/tuning.h`, `sharpen/*`, ~20 skill
  edits, etc.). User confirmed Debug is a disposable local test sandbox
  with nothing pushed remote, so a destructive mirror was authorised.
- Used `robocopy D:\Terragraf D:\Terragraf\Debug /MIR /XD .git Debug
  /XF .git` (excludes the source `.git/` directory, the nested `Debug/`
  worktree, and the destination `.git` worktree-pointer file). 3.08 GB
  copied across ~93k files, 4 Debug-only extras purged.
- Robocopy only touches the working tree, NOT the per-worktree git
  index. After the mirror, Debug's stale index made `git status` show
  158 modified entries (65 phantoms vs Yibb's 92 real changes). Fixed by
  copying `D:/Terragraf/.git/index` → `D:/Terragraf/.git/worktrees/Debug/index`.
  Worktree indexes are interchangeable as long as both HEADs point at
  the same commit (they reference blob hashes, not branches).
- Final diff between `git status --short` outputs is exactly one line:
  Yibb sees `?? Debug/` as untracked (the nested worktree dir), Debug
  obviously doesn't list itself.

### Verification Results (Session 23)
- `pytest .scaffold/tests/test_browsers_panels.py -k tune` →
  **7 passed** (was 6, +1 zone indicator test)
- `pytest .scaffold/tests/` → **927 passed**, 0 skipped (was 926)
- Manual Qt smoke deferred (no display in this session); zone indicator
  call sites verified by reading the resulting tune.py end to end

### Key Files (Session 23)
```
.scaffold/app/widgets/panels/tune.py    — +zone_label widget,
                                          +_refresh_zone_indicator(),
                                          +_exit_zone_clicked(),
                                          _enter_zone_clicked() mirrors
                                          engine state, __init__ +
                                          _load_profile_schema() refresh
                                          the indicator (modified)
.scaffold/tests/test_browsers_panels.py — +test_tune_panel_zone_
                                          indicator_reflects_engine
                                          (modified)
```

### Decisions Made (Session 23)
- **Test exercises `_refresh_zone_indicator` directly, not via clicks**:
  click handlers shell out to `tune zone <name>` which fails inside the
  pytest sandbox (no working CWD-relative paths, no real state file).
  Driving the engine + refresh helper directly tests the contract that
  matters — the label tracks `engine.active_zone` — without coupling to
  subprocess invariants
- **Engine mirror happens AFTER the subprocess on zone changes, not
  before**: opposite of `_on_knob_changed` (which mirrors first so the
  instruction preview is responsive). Here the subprocess validates the
  zone name against the on-disk state file, so we let it run first and
  only echo into the engine if it didn't raise. Avoids leaving the
  in-memory engine in a state inconsistent with disk
- **Worktree index is interchangeable across branches at the same
  commit**: the index references blob hashes, not refs. Copying Yibb's
  index into the Yibb-debug worktree dir works because both HEADs are
  `032d519`. If they ever diverge, this trick stops working
- **Robocopy /MIR + index copy is the cleanest worktree mirror on
  Windows**: rsync isn't installed on this MSYS, and `git checkout` /
  `git stash` don't handle untracked files well. /MIR purges extras
  in one pass, /XD excludes the source `.git/` dir, /XF excludes the
  destination `.git` worktree pointer file from the purge. Index has
  to be copied separately because robocopy doesn't traverse into `.git/`

---

## Next Session (23 cont.): Remaining polish
- Real ML training dogfood (`terra train --dataset cifar10 --arch cnn`) on a
  GPU machine — wire up CIFAR-10, observe ImPlot training panel updating
  live via the bridge with the freshly-built `terragraf_imgui.exe`
- Manual Qt smoke of the new zone indicator on a display: open Tuning
  panel, verify `Zone: (none)` initial, Enter/Exit updates inline,
  reopen-after-Enter restores zone from `.tuning_state.json`

## What's Done (Session 24)

### Welcome polish + expanded sidebar default + responsive DPI + redundant tab `+` removal

Implemented the full Session 24 plan that was deferred from Session 23. Plus
one extra item the user spotted mid-session: the redundant top-right `+`
corner button on the tab bar.

#### 1. DPI policy: PassThrough (`app/main.py`, NEW `app/scaling.py`)
- `Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor` → `PassThrough`.
  Qt 6 + PySide6 handles fractional scales correctly; every `px` value in
  code and the stylesheet is now a logical pixel and Qt multiplies for
  device pixels at draw time. The old "prevents Windows artifacts" comment
  was Qt-5 lore — replaced with an accurate one
- NEW `app/scaling.py`: `_scale` module-global, `init(app)` reads
  `primaryScreen().logicalDotsPerInch() / 96.0` (clamped ≥ 1.0),
  `s(px: int) -> int`, `factor() -> float`. Called from `main.py`
  immediately after `QApplication(sys.argv)`. Used for the few cases
  that need explicit screen-relative clamps

#### 2. Adaptive window size (`app/window.py`)
- Added `QApplication` to the imports
- `resize(1440, 860)` → clamp against `primaryScreen().availableSize()`:
  `w = max(1024, min(1600, avail.width * 0.80))`,
  `h = max(640,  min(1000, avail.height * 0.85))`. Falls back to
  `resize(1440, 900)` if no primary screen. Logical px under PassThrough,
  so Qt scales for the user's DPI automatically

#### 3. Sidebar expanded by default
- `app/settings_page.py:38` `"sidebar_expanded": False` → `True`
- `app/window.py:106` fallback `settings.get("sidebar_expanded", False)`
  → `True`. Persisted user prefs unaffected

#### 4. Welcome tab cleanup (`app/welcome_tab.py`)
- Stripped the entire `actions_layout` block (4 broken buttons that were
  never wired: `New Native Tab`, `New External Tab`, `Toggle ImGui`,
  `Open Settings`)
- Replaced with a single dim, word-wrapped hint label: *"Use the sidebar
  on the left to create a new tab, browse routes, run a skill, or open
  settings."*
- Fixed two surviving Session 23 inline-style misses: the title
  `setStyleSheet(font-size:20px;...)` → `setObjectName("title")`, and the
  per-key cyan labels `setStyleSheet(color:CYAN)` → `setObjectName("status_cyan")`
- Cleaned up now-unused imports: `Qt`, `theme`, `QHBoxLayout`,
  `QPushButton`, `QScrollArea`

#### 5. Redundant tab `+` corner button removed (`app/tab_widget.py`)
- Deleted `_AddTabButton` class entirely
- Deleted the `setCornerWidget(add_btn, TopRightCorner)` block
- Deleted the now-unused `_on_add_clicked` handler (the `QInputDialog`
  type-picker popup)
- Removed unused `QInputDialog` import
- Reason: redundant — sidebar, Ctrl+T shortcut, tab-bar context menu, and
  the new welcome hint already cover "create a new tab". Verified by grep
  that no tests reference `_AddTabButton` / `_on_add_clicked` /
  `cornerWidget` / `TopRightCorner` across `.scaffold/`

#### 6. Theme + icon-button bumps
- `app/widgets/icon_button.py:27` `setFixedHeight(32)` → `36`
- `app/theme.py`: `QWidget` base `font-size: 13px` → `14px`,
  `SIDEBAR_WIDTH_COLLAPSED = 48` → `56`,
  `SIDEBAR_WIDTH_EXPANDED = 220` → `240`

#### 7. Tests
- `tests/test_integration.py`: replaced `test_welcome_tab_buttons_present`
  with `test_welcome_tab_has_hint_not_broken_buttons` — inverse assertion
  that none of the four button labels appear and that the word "sidebar"
  shows up in the QLabel text
- No other tests touch the DPI policy, sidebar default, or window sizing
  (verified via grep)

### Verification (Session 24)
- `pytest .scaffold/tests/test_integration.py -k welcome` → **5 passed**
- `pytest .scaffold/tests/test_app.py test_command_dialogs.py
  test_browsers_panels.py` → **80 passed** (focused Qt subset, run
  before the welcome cleanup as a smoke for the `+` removal)
- `pytest .scaffold/tests/` → **931 passed**, 0 skipped — held at the
  Session 23 baseline
- Manual visual smoke deferred — no display in this session

### Yibb → Yibb-debug worktree mirror refresh
After implementing all of the above on Yibb, mirrored Yibb to the Debug
worktree (D:/Terragraf/Debug) using the Session 23 procedure:
- `cmd /c "robocopy D:\Terragraf D:\Terragraf\Debug /MIR /XD .git Debug
  /XF .git"` — 92,350 files scanned, **1 file copied** (a freshly
  generated `__pycache__` artifact), 0 extras to purge. Disk state was
  effectively already aligned because the Debug worktree had been mirrored
  recently
- `cp D:/Terragraf/.git/index D:/Terragraf/.git/worktrees/Debug/index` —
  copied the Yibb worktree index into the Debug worktree's per-worktree
  index file. Required because robocopy doesn't traverse `.git/`
- Verification: `git status --short | wc -l` — Yibb 95, Debug 94. The
  one-line delta is the expected `?? Debug/` entry (Yibb sees the nested
  worktree dir; Debug obviously doesn't list itself). Both worktrees on
  commit `032d519`

### Key Files (Session 24)
```
.scaffold/app/main.py                    — PassThrough policy + scaling.init
.scaffold/app/scaling.py                 — NEW DPI helper module
.scaffold/app/window.py                  — adaptive resize + sidebar fallback flip
.scaffold/app/settings_page.py           — sidebar_expanded default → True
.scaffold/app/welcome_tab.py              — stripped actions, hint label,
                                            inline-style cleanup, import prune
.scaffold/app/tab_widget.py               — removed _AddTabButton +
                                            _on_add_clicked + corner widget
.scaffold/app/widgets/icon_button.py     — height 32 → 36
.scaffold/app/theme.py                    — base font 13 → 14, sidebar
                                            widths 48/220 → 56/240
.scaffold/tests/test_integration.py      — welcome buttons test inverted
```

### Decisions Made (Session 24)
- **PassThrough is the load-bearing change**: every other tweak in this
  session becomes correct once Qt is allowed to scale logical pixels
  properly. The bumps (font 14, sidebar widths 56/240, icon button 36)
  would have been wrong under the old `RoundPreferFloor` policy because
  they would have rendered at literal device pixels on a 1.0× floor
- **Adaptive window size lives in `window.py`, not `scaling.py`**: it's
  a one-shot at construction time, doesn't need to go through the helper.
  `scaling.s(px)` is reserved for the cases where a hardcoded `px`
  literal needs to scale at runtime (none yet — every path so far is
  either logical-px-correct or screen-relative)
- **Welcome hint replaces buttons rather than wiring them up**: the four
  buttons duplicated functionality already present in the sidebar, and
  the user explicitly asked to remove rather than fix them. One source
  of truth (sidebar) is better than two
- **Removing the tab `+` corner button is consistent with the welcome
  cleanup**: same principle — sidebar + Ctrl+T + context menu cover the
  "new tab" action, so the corner widget is duplication. User flagged
  this mid-session after seeing the welcome cleanup
- **Index copy across worktrees still works at the same commit**: same
  trick as Session 23. Both Yibb and Debug HEADs are `032d519`, so the
  index (which references blob hashes, not refs) is interchangeable

## What's Done (Session 25)

### First push of Sessions 9–24 to origin/Yibb + CI green

Local Yibb had been sitting at `032d519` (Session 6) for the entire run
of Sessions 7–24 — every later session's work lived only as untracked
files / unstaged modifications in the working tree. Local also turned
out to be 1 commit BEHIND `origin/Yibb` (`fb52316` — README quickstart
fix). Session 25 turned that whole pile into a clean linear history
on `origin/Yibb` with all 4 CI matrix jobs green.

#### 1. Worktree mirror at Debug/K
- New `Yibb-K` branch created via
  `git worktree add -b Yibb-K D:/Terragraf/Debug/K Yibb`. Pure local,
  no remote tracking. Lives alongside the existing Yibb-debug worktree
  at `D:/Terragraf/Debug`.
- User originally asked for "the contents of Yibb in K", which was
  initially misread as "copy the worktree". Reality: `git worktree add`
  checks out **committed** state, so Debug/K came up as a clean
  checkout of `032d519` with none of the in-progress Session 9–24 work.
  This was the trigger that surfaced just how much was uncommitted.

#### 2. 14-commit decomposition of Sessions 9–24
- 38 modified + 114 untracked files grouped by feature area (NOT
  strict session order — that gave better `git log` / `bisect`
  behaviour because files like `terra.py` (+556 lines), `theme.py`
  (+674), `window.py` (+740) accumulated changes across 10+ sessions
  and can't cleanly be split per session)
- Commits, oldest → newest after rebase:
  ```
  ea60b0d chore: test harness scaffolding and Debug/ ignore
  a22bcc3 feat(skills): hot_decompose pipeline + threshold hook
  0455538 feat(app): tab infrastructure (Session 9)
  646e599 feat(query): QueryEngine + IntentParser + native tab (S10)
  81c0072 feat(app): external tab (Session 11)
  507fa1c feat(imgui): panel + dock + window reparenting (S12)
  468d04b feat(app): integration - coherence, feedback, welcome (S13)
  4ce9326 feat(llm): provider abstraction + Anthropic/OpenAI (S14)
  12a9787 feat(mcp+worktree): MCP resource server + git worktree (S15)
  1a58faa feat(deps): local dependency manifest (Session 16)
  b5477b4 feat(ml): config, metrics, transforms, export, loggers (16b)
  cf165a3 feat(ui): theme/window/DPI/sidebar/widgets polish (S23/S24)
  459099d feat(terra): CLI expansion + docs + routes/instances updates
  b6a42a0 docs: HOT_CONTEXT through Session 24
  ```
- `Debug/` added to `.gitignore` so the new worktree dir doesn't show
  up as untracked in the parent

#### 3. Rebase + push
- 14 commits rebased cleanly onto `origin/Yibb` (`fb52316` README fix)
  with zero conflicts, despite commit 13 touching README.md heavily.
  The remote fix was a pure formatting tweak in a section local
  hadn't modified
- Fast-forward push: `fb52316..b6a42a0  Yibb -> Yibb`. No `--force`,
  no rewriting of public history

#### 4. CI rescue (round 1) — `576818f`
First push surfaced 4/4 test matrix jobs failing at collection time
(0 tests run, 7 collection errors per job). Two distinct root causes,
both hidden locally because local Python is 3.14:
- **`worktree/manager.py`**: `def list(self) -> list[WorktreeInfo]`
  on line 96 rebinds `list` in the class namespace. Line 145
  `def gc(self, ...) -> list[str]` then evaluates `list[str]` against
  the just-bound method object → `TypeError: 'function' object is not
  subscriptable`. Python 3.14 hides this via PEP 649 (lazy
  annotations); 3.11/3.12 still evaluate annotations eagerly.
  Fix: `from __future__ import annotations` at top of file
- **6 ml test files**: import torch (or `from ml.config import …`
  which cascades through `ml/__init__.py` re-exports). CI's
  `requirements-dev.txt` doesn't pin torch. Fix:
  `pytest.importorskip("torch")` at module top, before the `from ml…`
  imports that would otherwise trigger the cascade

#### 5. CI rescue (round 2) — `e3db11c`
Round 1 unblocked collection. New picture: **604 passed / 215 skipped
/ 15 failed / 27 errors**. Two new categories underneath:
- **PySide6 not installed in CI** (12 test files, 27 collection errors
  + 1 failure). Real prod dep — entire `app/` tree is built on it.
  Fixes:
  - `requirements-dev.txt` += `PySide6>=6.5`
  - `.github/workflows/ci.yml` split test step by OS:
    - Linux: `apt-get install xvfb libxkbcommon0 libxcb-cursor0
      libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0
      libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1
      libegl1 libgl1 libdbus-1-3 libfontconfig1 libxrender1`,
      then run pytest under `xvfb-run -a`. `QT_QPA_PLATFORM=offscreen`
      set as belt-and-suspenders fallback
    - Windows: just `QT_QPA_PLATFORM=offscreen`
- **`projects/knowledge_writer.py` and `knowledge_reader.py` were
  never tracked** — `projects/` was in `.gitignore` since the start,
  but `test_knowledge.py` (committed) shells out to those scripts.
  Always would have failed in CI; was masked locally because the
  files exist on disk, and masked in earlier CI runs because torch /
  list errors blocked collection entirely.
  Fix: changed `.gitignore` line `projects/` →
  ```
  projects/*
  !projects/knowledge_writer.py
  !projects/knowledge_reader.py
  !projects/KNOWLEDGE.toml
  ```
  then `git add` the three files. `projects/music-viz` and the
  `__pycache__` stay ignored

### Verification (Session 25)
- Local: `pytest .scaffold/tests/` → **931 passed**, 0 skipped,
  28 warnings (all upstream torch deprecations on 3.14), 24-25 s
- `terra health` → **Grade A**
- `hot_decompose --dry-run` and `terra sharpen run --dry-run` → both clean
- CI run `24035170839` on `e3db11c`:
  - test (ubuntu-latest, 3.11)  ✓
  - test (ubuntu-latest, 3.12)  ✓
  - test (windows-latest, 3.11) ✓
  - test (windows-latest, 3.12) ✓
  - lint                        ✓

### Key Files (Session 25)
```
.gitignore                              — +Debug/, projects/* exception
                                          pattern with 3 ! re-includes
.github/workflows/ci.yml                — split test step by OS, Linux
                                          installs xvfb + Qt deps and
                                          wraps pytest in xvfb-run,
                                          Windows sets offscreen
requirements-dev.txt                    — +PySide6>=6.5
projects/knowledge_writer.py            — NEW (was untracked, now in repo)
projects/knowledge_reader.py            — NEW (was untracked, now in repo)
projects/KNOWLEDGE.toml                  — NEW (registry seed)
.scaffold/worktree/manager.py           — +from __future__ import annotations
.scaffold/tests/test_ml_config.py       — pytest.importorskip("torch")
.scaffold/tests/test_ml_data.py         — pytest.importorskip("torch")
.scaffold/tests/test_ml_export.py       — pytest.importorskip("torch")
.scaffold/tests/test_ml_model_io.py     — pytest.importorskip("torch")
.scaffold/tests/test_ml_models.py       — pytest.importorskip("torch")
.scaffold/tests/test_ml_training.py     — pytest.importorskip("torch")
```

### Decisions Made (Session 25)
- **Group commits by feature area, not session number**: terra.py /
  theme.py / window.py grew across 10+ sessions each. Splitting them
  per session would require hand-rolled patches and the result still
  wouldn't bisect cleanly. Feature-area grouping gives 14 commits
  that each compile and have a coherent diff
- **Rebase before push, not merge**: local was 1 behind, 14 ahead.
  Rebase replays the 14 onto fb52316 → fast-forward push. Avoids a
  merge commit on a branch that nobody else writes to. The README
  conflict that was theoretically possible never materialised because
  fb52316's edit was in a section local hadn't touched
- **PySide6 + xvfb beats importorskip**: importorskip would have made
  CI green by skipping the entire UI layer (12 test files, hundreds
  of tests). The whole point of CI for this app is catching UI
  regressions, so installing the real Qt stack and running headless
  via xvfb is the only honest answer
- **knowledge_writer goes in `projects/` with gitignore exceptions,
  not refactored into `.scaffold/skills/`**: a refactor would touch
  every caller in terra.py and the writer/reader's CLI surface.
  Exception pattern is one .gitignore line and three `git add`s,
  zero behavioural risk
- **Skip torch in CI rather than install it**: torch is ~700MB on
  the install. PySide6 (~150MB) is borderline acceptable, torch is
  not. The 6 ml test files account for ~215 skipped tests in CI; ml
  tests still run locally where torch is installed. If ml regressions
  ever bite, that's the trigger to either install torch in CI or
  spin up a separate ml-only matrix job
- **Python 3.14's PEP 649 was the silent killer**: every CI failure
  in this session was something that local 3.14 hid via lazy
  annotations / different import semantics. Lesson: when CI is
  ahead-of-the-curve on Python versions and local is on the latest,
  prefer running pytest under at least one matching version locally
  before pushing — or trust CI as the only source of truth for the
  matrix

## Backlog
- End-to-end ImGui + bridge + Qt debug on a Vulkan machine (the build now
  works; live message-flow verification still requires display)
- Consider whether torch should land in a separate CI matrix job
  (would unskip ~215 ml tests in CI). Not urgent
