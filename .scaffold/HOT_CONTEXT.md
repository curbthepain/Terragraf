# Hot Context — Terragraf

## Status: Session 35 — Kohala Tier 2 overrides (aniso + LOD bias)

Sessions 1-34 complete. **S35 (this session)** implemented Kohala Tier 2
Phase A: anisotropic filtering + LOD bias override-before-forward in
`kohala_CreateSampler`, with overlay UI controls. No Terragraf code
changes. **973 tests** passing on Yog-pls, Grade A, **18 skills**,
**0 structure issues**.

**Kohala hot context:** `projects/Kohala/.claude/kohala_overlay_hot_context.md`

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

## What's Done (Session 34 — Kohala session protocol integration)

Framework-only session. No code changes, no new tests, no skill changes.

### Session protocol (hub-and-spoke)

- **`PROTOCOL.md`** (repo root): the hub. 11 session commands adapted from
  Kohala v8 command interface. Each command has 3 trigger variants
  (formal/casual/short). 4 behavioral constraints always active. Layer
  stack adapted for Terragraf (L5 Runtime through L1 OS/Platform).
  Command combinations, evidence class reference table.
- **`CLAUDE.md`** (repo root): the spoke for Claude Code. Thin harness
  routing to PROTOCOL.md. Quick start, tools list, framework file index.
- **`improvements.md`** (repo root): empty template for the
  Consider/Graduate feedback loop.

### Commands integrated

Swap/Switch/ctx, Vertical/Debug/cat, Confidence/Blush/est,
Sweep/Crunch/brush, Phoenix/Rebirth/zero, Report/Condense/dumpsys,
Profile/Analyze/compute, Backup/RAID6/snapshot,
Consider/Failstate/wheresmycar, Graduate/Improve/uni, Test/Prove/bench.

### Commands NOT ported (Kohala-specific)

Boot/Route, Consume, Patch, Organize, Ship/Cache, Halt, Chain, Ad-hoc,
Decay (overlaps Confidence).

### Files touched
```
 PROTOCOL.md       new (~400 lines) — session command hub
 CLAUDE.md         new (~30 lines) — Claude Code spoke/harness
 improvements.md   new (~5 lines) — Consider/Graduate template
```

### S34 decisions
- **Hub-and-spoke, not CLAUDE.md monolith.** PROTOCOL.md is tool-agnostic;
  CLAUDE.md is the Claude Code-specific harness. Future .cursorrules or
  .windsurfrules spokes route to the same hub.
- **Kohala stays separate.** No files in projects/Kohala/ were modified.
  Kohala keeps its own v8 CLAUDE.md for when working in that directory.
- **Did not create a terra skill for Kohala.** Session commands are AI
  behavioral protocols, not CLI tools. Integrating them as a skill would
  have been the wrong abstraction.
- **Adapted layer stack for Terragraf.** Kohala's L1-L5 was Vulkan/C++;
  Terragraf's is Python/Qt/scaffold. Misdirection table rewritten.

---

## What's Done (Session 33 — SECURITY.md graphify threat rows)

Documentation-only session. No code changes, no new tests.

### SECURITY.md updates

- **Threat table**: appended 4 rows after the existing 10-row table:
  SSRF via URL fetch, oversized downloads, XSS in graph HTML output,
  prompt injection via node labels. Rows describe Terragraf's own
  posture (user-initiated commands, local filesystem, opt-in LLM)
  and credit upstream `graphify` without overclaiming unverified
  `graphify.security` mitigations.
- **Optional network calls**: replaced the `**Future**` placeholder
  (graphify ingest "will fetch URLs") with present-tense description
  now that graphify is live.

### PyPI name check

- Package is still `graphifyy` (double y) on PyPI, v0.3.24
  (2026-04-09). The plain `graphify` name has not been reclaimed.
  No changes to `SKILL.toml`, `terra.py`, or `run.py` needed.
  Re-check before next Terragraf release.

### Repo hygiene

- **Untracked runtime state files**: `queue.json`, `results.json`,
  `analytics.json` removed from git tracking (`git rm --cached`) and
  added to `.gitignore`. These change on every task run and created
  noisy diffs.

### Files touched
```
 SECURITY.md                      +4 table rows, ~5 lines rewritten
 .gitignore                       +3 runtime state exclusions
```

### S33 verification
- No code changes — test count unchanged (973 passed)
- `python terra.py health` → Grade A, 0 structure issues, 18 skills

### S33 decisions
- **Described Terragraf's posture, not upstream's**. Initial draft
  deferred all four mitigations to `graphify.security` — rewrote to
  lead with what Terragraf controls (user-initiated CLI, local
  filesystem, opt-in LLM) and credit upstream as a secondary layer.
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
