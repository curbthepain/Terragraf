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

## What's Done (Session 22)

### hot_decompose age-out + hard-cap forcer + re-entry guard

Closed the Session 20b follow-up AND fixed the re-entry bug surfaced by
dogfooding. HOT_CONTEXT.md now has both a session age-out policy AND a
hard 1000-line ceiling enforced by a forcer pass that keeps extracting h3
sub-sections into KNOWLEDGE.toml until the file is under cap. A lockfile
guard prevents the threshold hook from re-firing decompose mid-edit.

#### 1. Session age-out (`skills/hot_decompose/run.py`)
- New `extract_session_number(heading)` regex parses `(Session N)`,
  `(Sessions M-N)` (uses upper bound), `(Session 19b)`, `(Session 21 — in
  progress)`, and "Everything above is Session N" separator lines
- New `Block.session_number: int | None` field, populated immediately
  after `parse_blocks()`
- New `apply_age_out(blocks, retain_count)` partitions blocks into keep /
  archive sets. Blocks with `session_number is None` always kept
  (architectural notes, status, backlog). Retained-session blocks forced
  to `block_type = "session"` so the existing classifier doesn't extract
  their sub-sections. Separator + pure-decorative `## ────` blocks dropped
- New `_archive_category(heading)` maps aged-out headings to KNOWLEDGE
  categories: decision / pattern / caveat / domain
- New `get_retain_sessions()` reads `[hot_context] retain_sessions` from
  MANIFEST.toml, default 3

#### 2. Hard cap forcer (same file)
- New `DEFAULT_HARD_MAX_LINES = 1000` and `EXTRACTABLE_H3_KEYWORDS`
  (key files / verification / tests / decisions made / decisions)
- New `apply_hard_cap(keep_blocks, hard_max, dry_run)` runs AFTER the
  age-out + standard dispatch loop. Walks retained sessions oldest-first,
  finds the first matching h3, builds a synthetic Block, routes it to
  KNOWLEDGE.toml tagged `["hot-context", "session-N", "archived",
  "hard-cap"]`, and removes the section from the parent block's body
- Loop terminates when line count ≤ hard_max OR no extractable h3
  remains. Defensive bailout if a removal fails to shrink the count
- New `_find_extractable_h3(block)` and `_count_total_lines(blocks)`
  helpers (the latter reuses `rewrite_hot_context(dry_run=True)`)

#### 3. Re-entry guard (lockfile)
- New `LOCKFILE = .scaffold/.hot_decompose.lock` + `LOCK_STALE_SECONDS = 60`
- New `is_locked()`, `_acquire_lock()`, `_release_lock()` helpers
- `cmd_decompose` now wraps its body in `_acquire_lock()` /
  `_release_lock()` (try/finally). If the lock is already held it prints
  `"hot_decompose already in progress (lockfile present) — skipping"`
  and returns 0 without touching HOT_CONTEXT
- Stale locks (mtime > 60s) are treated as absent — protects against
  crashed runs leaving the lock behind
- Hook (`hooks/on_hot_threshold.py`) gained a parallel `_decompose_in_progress()`
  helper and short-circuits inside `check_threshold()` when locked, surfacing
  `locked: True` in its result dict and printing
  `[hot_context] N/M over → skipped (decompose already in progress)`
- Hook envelope filter ALSO dropped `Read` from the trigger tool list —
  reading HOT_CONTEXT should never trigger a decompose, and the read-then-
  edit cycle that Claude Code uses to modify files would otherwise be
  broken by the hook firing on the Read step and mutating the file before
  the Edit even started. This was the actual root cause of the bug

#### 4. cmd_decompose flow
- Acquire lockfile (skip + return 0 if held)
- Pre-classification: `extract_session_number()` populates each Block
- Age-out runs first → archive aged-out sessions to KNOWLEDGE.toml
- Standard classifier dispatch on kept blocks
- Forcer runs last → extracts h3 sub-sections until under hard cap
- Final summary line is now 3-state: `(under threshold)` /
  `(over soft, under hard cap)` / `(STILL over hard cap — nothing
  extractable left)`
- Release lockfile in `finally`

#### 5. MANIFEST.toml
- `[hot_context] retain_sessions = 3`
- `[hot_context] hard_max_lines = 1000`

#### 6. Tests (+14 across test_hot_decompose.py and test_hot_threshold.py)
- `TestAgeOut` (5): keeps_latest_3, preserves_non_session_content,
  archives_to_knowledge, configurable_retention,
  decisions_route_to_correct_table
- `TestHardCap` (6): get_hard_max_lines_default + _from_manifest,
  noop_when_under_limit, extracts_h3_subsections, stops_when_no_extractable,
  extracts_oldest_session_first
- `TestLockfile` (3): acquire_release_roundtrip, stale_lock_is_ignored,
  cmd_decompose_skips_when_locked
- `TestEnvelopeFiltering` updated: `Read` trigger now returns False;
  added `test_envelope_write_on_hot_context_triggers`
- New helpers: `_build_sessions()`, `_build_session_with_h3s()`,
  `_patch_hot_decompose()` (redirects HOT_CONTEXT/MANIFEST/KNOWLEDGE_WRITER
  to tmp_path, captures `subprocess.run` calls to knowledge_writer.py)

### Verification Results (Session 22)
- `pytest .scaffold/tests/test_hot_decompose.py` → **44 passed** (was 30,
  +14 across TestAgeOut + TestHardCap + TestLockfile)
- `pytest .scaffold/tests/test_hot_threshold.py` → **13 passed**
- `pytest .scaffold/tests/` → **926 passed**, 0 skipped
- Live age-out on real HOT_CONTEXT: 1152 → 447 lines, archived
  Sessions 8–18 to KNOWLEDGE.toml with `archived` + `session-N` tags
- Live forcer stress test (`hard_max_lines = 250` temporarily):
  447 → 255 lines, extracted 12 h3 sub-sections (Key Files /
  Verification Results / Decisions Made × Sessions 19/19b/20/21) tagged
  `hard-cap`. Stopped because the remaining 4 h3s are session intro
  prose, not extractable
- Steady state at `hard_max_lines = 1000`: HOT_CONTEXT.md = 255 lines,
  `(over 80 soft threshold, under 1000 hard cap)`
- `terra health` → **Grade A** maintained

### Key Files (Session 22)
```
.scaffold/skills/hot_decompose/run.py   — +session_number field, +regexes,
                                          +extract_session_number,
                                          +_archive_category, +apply_age_out,
                                          +get_retain_sessions,
                                          +get_hard_max_lines,
                                          +_find_extractable_h3,
                                          +_count_total_lines,
                                          +apply_hard_cap forcer loop,
                                          +LOCKFILE constants,
                                          +is_locked / _acquire_lock /
                                          _release_lock,
                                          cmd_decompose wrapped in
                                          try/finally lock guard (modified)
.scaffold/hooks/on_hot_threshold.py     — +LOCKFILE constants,
                                          +_decompose_in_progress(),
                                          check_threshold() short-circuits
                                          when locked, +locked field in
                                          result dict, _envelope_targets_
                                          hot_context() drops Read from
                                          trigger list (modified)
.scaffold/MANIFEST.toml                 — +retain_sessions = 3,
                                          +hard_max_lines = 1000 (modified)
.scaffold/tests/test_hot_decompose.py   — +TestAgeOut (5), +TestHardCap (6),
                                          +TestLockfile (3),
                                          +_patch_hot_decompose helper
                                          (modified)
.scaffold/tests/test_hot_threshold.py   — Read trigger test inverted,
                                          +Write trigger test (modified)
```

### Decisions Made (Session 22)
- **Read tool removed from PostToolUse trigger list**: this was the
  ROOT CAUSE of the re-entry bug. Claude Code's read-then-edit cycle calls
  Read first, then Edit. With Read in the trigger list, the hook fired
  decompose on the Read, mutating HOT_CONTEXT before the Edit could
  apply. Reads are non-mutating and should never trigger decompose
- **Lockfile guard is defense in depth**: even with Read removed, the hook
  can still fire on Edit/Write. If a write to HOT_CONTEXT comes from
  inside a decompose run, the lockfile prevents the hook from spawning
  a recursive decompose. Both fixes work together
- **60-second stale-lock TTL**: long enough for any reasonable decompose
  run, short enough that a crashed process doesn't permanently jam the
  pipeline. Tested by `test_stale_lock_is_ignored`
- **Lock file path under `.scaffold/`**: alongside HOT_CONTEXT.md so
  it's discoverable. Could be moved to `instances/shared/locks/` later
  if multi-instance coordination is needed
- **Age-out is a SECOND pass before classifier dispatch**: retained-
  session blocks are force-set to `block_type = "session"` to short-
  circuit the existing classifier so their sub-sections (Decisions Made,
  Verification Results) stay verbatim instead of being extracted by the
  Session 20b classifier
- **19b extracts as session number 19**: regex captures the digit and
  ignores the trailing `b`, so `Session 19` and `Session 19b` both pass
  the `in retained` check together. They're sub-versions of the same
  logical session
- **Forcer walks oldest-first**: newer sessions are more valuable to keep
  verbatim, so heaviest extraction targets the oldest retained session
- **Synthetic h3-extraction block heading appends `(Session N)`**: makes
  slugs unique per (session, h3) pair (e.g. `key-files-session-19`).
  Collisions handled silently by knowledge_writer's existing `already
  exists` dedup
- **`hard-cap` tag distinguishes forcer extractions from age-out**:
  age-out entries are tagged `["hot-context", "session-N", "archived"]`;
  forcer entries get `"hard-cap"` appended
- **Hard cap is on HOT_CONTEXT only, not KNOWLEDGE.toml**: explicitly
  scoped per user. KNOWLEDGE.toml is allowed to grow unbounded; if
  rotation is needed later it would touch the writer + reader, not
  hot_decompose

---

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

## Backlog
- End-to-end ImGui + bridge + Qt debug on a Vulkan machine (the build now
  works; live message-flow verification still requires display)
