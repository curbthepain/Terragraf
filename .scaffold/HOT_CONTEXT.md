# Hot Context — Terragraf

## Status: Session 33 — SECURITY.md graphify threat rows

Sessions 1-32 complete. **S33 (this session)** updated SECURITY.md
with four graphify threat rows (SSRF via URL fetch, oversized
downloads, XSS in graph HTML output, prompt injection via node
labels), all citing upstream `graphify.security`. Updated the
"Optional network calls" section to present tense (graphify is now
live, not future). PyPI name still `graphifyy` (double y), v0.3.24;
`graphify` not yet reclaimed — no code changes needed. **973 tests**
passing on Yog-pls, Grade A, **18 skills**, **0 structure issues**.

Plan file: `C:/Users/curb/.claude/plans/clever-mixing-kitten.md`.

### Noted mechanisms directory

`.scaffold/docs/noted/` — new directory for acknowledged warnings
and deferred fixes that have existing mitigation. First entry:
`torch_jit_deprecation.md` (28 pytest warnings from `torch.jit`
on Python 3.14, mitigated by `model_io.py` fallback chain).
Resolution target: after S33 (end of session roadmap).

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
- `pytest .scaffold/tests/` → 969 passed, 28 warnings
- `terra skill list` → 17 skills
- `terra workspace status` → prints health summary
- `terra mcp start` → launches MCP server on port 9878
- `terra worktree create` → creates isolated git worktree
- `terra deps` → local dependency status (27 Python + 22 C++)
- `terra deps sync` → source all deps into src/ (~2.9 GB)
- LLM fallback activates when best match score < 0.5

## Next Session (23 cont.): Remaining polish
- Real ML training dogfood (`terra train --dataset cifar10 --arch cnn`) on a
  GPU machine — wire up CIFAR-10, observe ImPlot training panel updating
  live via the bridge with the freshly-built `terragraf_imgui.exe`
- Manual Qt smoke of the new zone indicator on a display: open Tuning
  panel, verify `Zone: (none)` initial, Enter/Exit updates inline,
  reopen-after-Enter restores zone from `.tuning_state.json`

## What's Done (Session 33 — SECURITY.md graphify threat rows)

Documentation-only session. No code changes, no new tests.

### SECURITY.md updates

- **Threat table**: appended 4 rows after the existing 10-row table:
  SSRF via URL fetch, oversized downloads, XSS in graph HTML output,
  prompt injection via node labels. All mitigations cite upstream
  `graphify.security` rather than duplicating logic.
- **Optional network calls**: replaced the `**Future**` placeholder
  (graphify ingest "will fetch URLs") with present-tense description
  now that graphify is live.

### PyPI name check

- Package is still `graphifyy` (double y) on PyPI, v0.3.24
  (2026-04-09). The plain `graphify` name has not been reclaimed.
  No changes to `SKILL.toml`, `terra.py`, or `run.py` needed.
  Re-check before next Terragraf release.

### Files touched
```
 SECURITY.md                      +4 table rows, ~5 lines rewritten
```

### S33 verification
- No code changes — test count unchanged (973 passed)
- `python terra.py health` → Grade A, 0 structure issues, 18 skills

### S33 decisions
- **Cited `graphify.security` by module name, not by specific function**.
  The upstream API may refactor internals; naming the module is stable
  enough for a threat table without coupling to function signatures.
- **Did not add new tests**. Documentation-only session — the threat
  table is prose, not code. Existing 973 tests confirm no regressions.
- **Did not change `graphifyy` → `graphify` anywhere**. PyPI name has
  not been reclaimed. Premature renaming would break `pip install`.

## What's Done (Session 32 — graphify Phase 1 + Phase 2)

Both phases of `.scaffold/docs/graphify_adoption.md` in one session.

### Phase 1 — Skill + CLI

- **`.scaffold/skills/graphify/SKILL.toml`** + **`run.py`**: thin shim
  over `graphifyy` PyPI package. `run.py` delegates to
  `subprocess.run([sys.executable, "-m", "graphify"] + args)` (no
  `shell=True`). Passes `--platform windows` on win32. Warns when
  no LLM provider env vars are set (AST-only graph still builds).
- **`terra.py`**: `cmd_graphify` → `_run_skill("graphify", args)`,
  dispatch entry added. `PYTHON_PROBES` and `EXTRA_PIP_PACKAGES`:
  swapped dead `networkx` for `graphifyy`.
- **`.gitignore`**: added `graphify-out/`.
- **`.graphifyignore`**: new file excluding vendor, build, font, src,
  checkpoints, releases dirs from the knowledge graph.

### Phase 2 — UX Feature

- **`.scaffold/app/widgets/graph_panel.py`**: `GraphPanel(QWidget)`
  with lazy-loaded `QWebEngineView` (same pattern as
  `ide_host_page.py:352-364`). Loads `graphify-out/graph.html` when
  present; shows hint label ("No knowledge graph yet. Run
  `terra graphify .` to build one.") when absent. `refresh()` called
  on dock show.
- **`.scaffold/app/window.py`**: second `QDockWidget` ("Graph Viewer",
  `objectName="graphDock"`) on right dock area, same construction
  pattern as S31's ImGui dock. Ctrl+G toggle in View menu. Sidebar
  action handler routes `"toggle_graph_panel"` to the toggle method.
  Import added: `from .widgets.graph_panel import GraphPanel`.
- **`.scaffold/app/welcome_tab.py`**: `_HEALTH_KEYS` extended from 9
  to 12 entries (grid becomes 4×3). New keys: `graph_nodes`,
  `graph_communities`, `graph_god_nodes`.
- **`.scaffold/app/scaffold_state.py`**: `_graphify_stats()` reads
  `graphify-out/graph.json` (node count, max community + 1) and
  `graphify-out/GRAPH_REPORT.md` (bullet count under god-nodes
  heading). Returns `"—"` for all three when absent — no error, no
  log spam. Called from `health_summary()`.
- **`.scaffold/app/widgets/sidebar.py`**: `("⬡", "Graph Viewer",
  "toggle_graph_panel")` added to `welcome` (before Settings) and
  `native` (after Tune) tab layouts.

### Tests

- **`test_layout.py`**: `TestGraphDock` class (4 tests mirroring
  `TestImGuiDock`) — dock exists, starts hidden, toggle flips
  visibility, right dock area. `test_health_labels_populated`
  updated from `len == 9` to `len == 12`.

### Files touched
```
 .scaffold/skills/graphify/SKILL.toml        new
 .scaffold/skills/graphify/run.py            new
 .scaffold/app/widgets/graph_panel.py        new
 .scaffold/docs/noted/README.md              new
 .scaffold/docs/noted/torch_jit_deprecation.md  new
 .graphifyignore                             new
 terra.py                                    cmd + dispatch + deps
 .gitignore                                  +graphify-out/
 .scaffold/app/window.py                     +graph dock, Ctrl+G
 .scaffold/app/welcome_tab.py                +3 health keys
 .scaffold/app/scaffold_state.py             +_graphify_stats()
 .scaffold/app/widgets/sidebar.py            +nav entries
 .scaffold/tests/test_layout.py              +TestGraphDock, health count
```

### S32 verification
- `python terra.py health` → Grade A, 0 structure issues, 18 skills
- `terra skill list` → graphify registered
- `QT_QPA_PLATFORM=offscreen python -m pytest .scaffold/tests/` →
  **973 passed**, 28 warnings (preexisting torch JIT deprecations,
  documented in `.scaffold/docs/noted/torch_jit_deprecation.md`),
  26.76s. Zero regressions.

### S32 decisions
- **Lazy-load QWebEngineView, not top-level import**. Follows
  `ide_host_page.py` pattern. PySide6-WebEngine is not a hard dep —
  graph panel degrades to hint label if not installed.
- **`refresh()` called on toggle-show, not on a timer**. The graph
  changes only when `terra graphify` runs (user-initiated), so
  polling is wasteful. Refresh on dock-show is sufficient.
- **Sidebar entry in welcome + native only, not external**. The
  external tab layout is already dense (14 entries). Graph viewing
  is a code-analysis action, which fits welcome/native better.
- **`_graphify_stats()` is a private method on ScaffoldState**, not a
  standalone function. Keeps the graphify dependency contained — if
  graphify is removed later, one method deletion cleans it up.
- **Did not add `torch.compile` integration**. Acknowledged the 28
  JIT deprecation warnings and documented the existing `model_io.py`
  fallback mechanism in `.scaffold/docs/noted/`. Resolution deferred
  to after S33.

## What's Done (Session 31 — ImGuiPanel → QDockWidget)

Single-task session. Wrapped `ImGuiPanel` in a `QDockWidget`
attached to `MainWindow`'s right dock area. This is the first
`QDockWidget` in the codebase and establishes the pattern S32
Phase 2 reuses for `GraphPanel`.

### 1. `.scaffold/app/window.py` (~25 lines changed)
- **Import**: added `QDockWidget` to the `PySide6.QtWidgets` block.
- **Construction** (replaced the 4-line S28 TODO at old :114-120):
  `self._imgui_dock_widget = QDockWidget("ImGui Viewer", self)` with
  `objectName="imguiDock"` (for future `saveState` round-tripping
  and QSS targeting). `setWidget(self._imgui_panel)` reparents the
  existing `ImGuiPanel` into the dock. Allowed areas: Right + Left
  only (no Top/Bottom — horizontal docks would squash the tab
  layout). Features: Closable + Movable + Floatable. Registered via
  `addDockWidget(Qt.RightDockWidgetArea, ...)`, then
  `setVisible(False)`.
- **Handler** (`_toggle_imgui_panel`): now toggles
  `self._imgui_dock_widget` visibility instead of the bare
  `_imgui_panel`. The inner panel inherits visibility from its
  parent dock — no dual-visibility bookkeeping needed.
- **No changes to central widget**, footer, sidebar, top bar, or any
  other layout element. The `(16,14,16,6)` margins are untouched.

### 2. `.scaffold/tests/test_layout.py` (+35 lines)
New `TestImGuiDock` class with 4 assertions:
- `test_imgui_dock_exists` — dock is `QDockWidget`, wraps
  `_imgui_panel`, panel is `ImGuiPanel`
- `test_imgui_dock_starts_hidden` — `isVisible() is False`
- `test_imgui_toggle_flips_dock_visibility` — `_toggle_imgui_panel()`
  flips visibility (test calls `win.show()` so child visibility
  resolves correctly under offscreen platform)
- `test_imgui_dock_right_area` — `dockWidgetArea()` ==
  `RightDockWidgetArea`

### 3. `ImGuiPanel` — untouched
No changes to `imgui_panel.py`. The panel already inherits from
`QWidget` with no top-level assumptions. `QDockWidget.setWidget()`
reparents it cleanly. `cleanup()` still runs from
`MainWindow.closeEvent` — process teardown is unaffected.

### Files touched
```
 .scaffold/app/window.py               ~25 lines
                                       (QDockWidget import, dock
                                        construction replaces S28
                                        TODO, handler rewrite)
 .scaffold/tests/test_layout.py        +35 lines (TestImGuiDock)
```

### S31 verification
- `python terra.py health` → Grade A, 0 structure issues, 17 skills,
  969 tests discoverable
- `QT_QPA_PLATFORM=offscreen python -m pytest .scaffold/tests/` →
  **969 passed**, 28 warnings (preexisting torch deprecations),
  28.03s. Zero regressions.
- Manual Qt smoke deferred — user can `Ctrl+I` on display to confirm
  dock appears on right edge, floats on drag, hides on X or re-toggle.

### S31 decisions
- **Named `_imgui_dock_widget` (not `_imgui_dock`)**. `_imgui_dock`
  is already taken by `ImGuiDock` (the ImGui-backend routing object
  at `imgui_dock.py`). The `_widget` suffix disambiguates without
  renaming the existing attribute.
- **Allowed Right + Left only, not all four areas**. Top/Bottom docks
  would insert a horizontal splitter between the central widget and
  the window edge, squashing the floating-card tab layout. Right/Left
  keeps the dock tall and narrow, matching the panel's toolbar +
  container + log vertical stack.
- **`DockWidgetClosable` enabled**. The X button hides the dock (does
  not destroy it) — same semantics as `Ctrl+I` toggle. User
  expectation: if there's an X, clicking it should dismiss the panel.
- **No dock-state persistence yet**. `objectName("imguiDock")` is set
  so a future session can add `saveState`/`restoreState` to
  `.terragraf_settings.json` without touching dock construction.
- **No QSS styling added**. kohala.qss has no `QDockWidget` rules;
  the dock inherits Qt defaults. Styling is a backlog polish item.
- **Did not commit**. Working tree has S29/S30/S31 dirty files. User
  decides commit timing.

## Next Session (32): graphify Phase 1 + Phase 2
Both phases of `.scaffold/docs/graphify_adoption.md` in one session.
Phase 1 is non-Qt (skill shim + CLI + dep swap + `.graphifyignore`);
Phase 2 reuses S31's dock pattern for `GraphPanel(QWebEngineView)`
with Ctrl+G toggle, WelcomeTab health-grid extension (graph_nodes,
graph_communities, graph_god_nodes), and a sidebar nav entry.

## Backlog (Qt UX, still deferred)
- `WorkspaceTabStrip` drag-to-reorder
- `_TabPill` right-click context menu
- Qt doc topics still uncovered: `QGraphicsDropShadowEffect`,
  `QStateMachine`, `QPainter` custom drawing, QSS `:hover`/`:pressed`
  transitions vs property animations, high-DPI font metrics

## Backlog
- End-to-end ImGui + bridge + Qt debug on a Vulkan machine (the build now
  works; live message-flow verification still requires display)
- Consider whether torch should land in a separate CI matrix job
  (would unskip ~215 ml tests in CI). Not urgent
