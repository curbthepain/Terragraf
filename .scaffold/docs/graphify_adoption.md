# graphify Adoption — Investigation & Spec

**Status**: Investigation doc. No code written yet. This doc is the
spec the follow-up implementation session will execute against.

## TL;DR

[graphify](https://github.com/) is an MIT-licensed (Safi Shamsi, 2026)
AI coding-assistant skill that turns any folder of code, docs, papers,
or images into a queryable knowledge graph. It runs a two-pass
extractor (deterministic tree-sitter AST pass + parallel Claude
subagent pass), clusters the result with Leiden community detection,
and exports interactive HTML, JSON, and a plain-language audit report.

Terragraf can adopt it as a first-class skill at
`.scaffold/skills/graphify/` with a thin shim over the upstream
`graphifyy` PyPI package. `networkx` is already in Terragraf's pip dep
list (`terra.py:1212`, `terra.py:1223`) but is never imported — this
adoption activates the dep instead of carrying it as dead weight.

**Phase 1** ships graphify as a skill exposing `terra graphify` as a
CLI command, behaving exactly as upstream documents.
**Phase 2** (later session, after S29 Qt UX fixes land) promotes it to
a UX feature: embedded graph viewer panel, WelcomeTab health stats,
sidebar nav entry.

## License

Upstream repository ships plain **MIT**:

```
MIT License

Copyright (c) 2026 Safi Shamsi

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND [...]
```

Terragraf itself is not yet formally licensed; MIT is compatible with
whatever license Terragraf ultimately adopts (MIT, Apache-2.0, or
BSD). If we vendor the source rather than depending on the PyPI
package, the MIT notice must be preserved verbatim next to the
vendored code.

## What graphify does

Two-pass extraction:

1. **Deterministic AST pass** — tree-sitter parses 20 languages
   (Python, JS, TS, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala,
   PHP, Swift, Lua, Zig, PowerShell, Elixir, Objective-C, Julia) and
   extracts classes, functions, imports, call graphs, docstrings, and
   rationale comments. No LLM needed.
2. **Parallel Claude subagent pass** — Claude subagents run in
   parallel over docs, papers, and images to extract concepts,
   relationships, and design rationale.

The merged result goes into a **NetworkX graph**, is clustered with
**Leiden community detection** (graph-topology-based, no embeddings,
no vector database), and is exported as:

```
graphify-out/
├── graph.html       interactive graph (pyvis)
├── GRAPH_REPORT.md  god nodes, surprising connections, questions
├── graph.json       persistent graph
└── cache/           SHA256 cache — re-runs only process changed files
```

Every relationship is tagged **EXTRACTED** (found directly in
source), **INFERRED** (reasonable inference with a confidence score),
or **AMBIGUOUS** (flagged for review).

`.graphifyignore` (same syntax as `.gitignore`) excludes folders from
the graph.

**Honest-about-uncertainty claim**: graphify advertises "71.5× fewer
tokens per query vs reading the raw files", which is the value prop
for dropping it into an assistant-driven workflow like Terragraf's.

## Integration surface — Phase 1 (skill)

### Layout

Follow the existing `signal_analyze` skill pattern
(`.scaffold/skills/signal_analyze/SKILL.toml` + `run.py`):

```
.scaffold/skills/graphify/
├── SKILL.toml     — name=graphify, type=analyzer,
│                    triggers.commands=["terra graphify"],
│                    deps.modules=["graphifyy"]
└── run.py         — thin shim: parses terra args, shells to the
                     upstream `graphify` CLI with the right cwd,
                     forwards stdout/stderr, returns the exit code
```

### CLI

```
terra graphify .            # build graph of current dir
terra graphify query "..."  # forward to upstream query subcommand
terra graphify path A B     # forward to upstream path subcommand
terra graphify explain id   # forward to upstream explain subcommand
```

The shim does not reimplement graphify — it invokes the upstream CLI
via `subprocess.run([sys.executable, "-m", "graphify", ...])` (never
`shell=True`, to match the project's security posture). Output lands
in `graphify-out/` relative to the cwd.

### Subagent dispatch

graphify's Phase 2 extraction uses Claude subagents. The shim does
not need to replicate this — the upstream CLI handles it as long as
the user runs Terragraf from inside Claude Code (or another supported
platform). If the user invokes `terra graphify` outside an
AI-assistant session, upstream falls back to the behavior documented
in the graphify README.

### Install hook

`terra deps` currently lists `networkx` in the pip dep list at
`terra.py:1212` and again at `terra.py:1223`, but the dep is never
imported anywhere in the codebase. Replace both references with
`graphifyy` — the graphify package pulls `networkx` transitively, so
we stop listing the dead direct dep and get the real one in its
place.

### Skill reference pattern

The follow-up session should read
`.scaffold/skills/signal_analyze/SKILL.toml` and `run.py` as the
template for SKILL.toml section layout (`[skill]`, `[triggers]`,
`[deps]`) and for the `SCAFFOLD = Path(__file__).resolve().parent.parent.parent`
convention.

The delegation pattern — `terra <verb>` → skill runner → skill entry
point — is already proven by `terra analyze` at `terra.py:904`,
which forwards to `signal_analyze`.

## Integration surface — Phase 2 (UX feature, later session)

Deferred until after S29 Qt UX fixes (`Sidebar` animation,
`ImGuiPanel` → `QDockWidget`, footer truncation, version source).
S29 re-exposes the `ImGuiPanel` as a dockable widget — once that
dock pattern is in place, the graph viewer follows the same shape.

### Graph viewer panel

- New file: `.scaffold/app/widgets/graph_panel.py`
- Built on `QWebEngineView`, loading
  `graphify-out/graph.html` from the current workspace root
- Hosted in a `QDockWidget` alongside the re-exposed `ImGuiPanel`
- Toggled with **Ctrl+G** (matching Ctrl+I for ImGui)
- Empty state when `graphify-out/` is missing: a centered
  `QLabel[class="hint"]` reading *"No knowledge graph yet. Run `terra
  graphify .` to build one."* with a button that invokes the skill

### WelcomeTab health grid

`.scaffold/app/welcome_tab.py` currently has a 3×3 grid of
`stat_row()` entries (nine keys: `header_files`, `modules`,
`route_files`, `routes`, `table_files`, `queue_pending`,
`queue_running`, `hot_context_lines`, `recent_events`).

Extend to 3×4 (or append a fourth row) with:

| Key               | Source                                   |
|-------------------|------------------------------------------|
| `graph_nodes`     | `len(graph.json["nodes"])`               |
| `graph_communities` | `max(node["community"])` + 1           |
| `graph_god_nodes` | parsed from `GRAPH_REPORT.md` header     |

When `graphify-out/` doesn't exist, show `—` for all three (no error,
no log spam). Hook into the existing `self._state.state_changed`
signal so the stats refresh on the same cadence as the rest of the
grid.

### Sidebar nav entry

Add a new `IconButton[class="nav-item"]` in
`.scaffold/app/widgets/sidebar.py` with a graph icon (placeholder:
`"◈"` or a small SVG), routing to the graph panel dock-widget
toggle.

### Command palette

When the command palette lands (not yet planned), register:

- `terra graphify build`
- `terra graphify query`
- `terra graphify path`
- `terra graphify explain`

## Risks and open questions

- **PyPI name squatting**: the package is currently `graphifyy`
  (double `y`) per upstream README — the plain `graphify` name is
  being reclaimed. The skill must record this and add a TODO to
  re-check before each Terragraf release.
- **Subagent cost**: Phase 2 of graphify issues Claude API calls.
  Users running `terra graphify` without a configured LLM provider
  get partial results (AST pass only). The shim must print a clear
  warning when no provider is configured, not fail silently.
- **Cache collisions**: graphify writes `graphify-out/cache/` with
  SHA256 keys. Add `graphify-out/` to `.gitignore` in the
  implementation session.
- **Default `.graphifyignore`**: ship one at repo root excluding
  `.scaffold/vendor/`, `build/`, `Debug/`, `.venv/`, `src/vendor/`,
  `graphify-out/` itself, and the bundled fonts under
  `.scaffold/app/fonts/`.
- **Security review** per `SECURITY.md`: graphify's `ingest`
  subcommand fetches URLs. When Phase 1 lands, the Terragraf
  `SECURITY.md` threat table gets four new rows (SSRF via URL fetch,
  oversized downloads, XSS in graph HTML output, prompt injection
  via node labels) — all of which are already mitigated in upstream
  `graphify.security` and can be cited by reference.
- **Windows compatibility**: upstream README confirms Windows is
  supported via `graphify install --platform windows`. The shim
  should pass `--platform windows` through when running on `win32`.
- **Tree-sitter build**: tree-sitter grammars can require a C
  toolchain on first install. Phase 1 testing must verify cold
  install works on a clean Windows scaffold, not just a dev box
  that already has MSVC.

## Implementation checklist — follow-up session

- [ ] `pip install graphifyy` locally and verify the `graphify` CLI
      works on Windows
- [ ] Build `.scaffold/skills/graphify/` following the
      `signal_analyze` layout
- [ ] Wire `terra graphify` in `terra.py` (same pattern as
      `terra analyze` at line 904)
- [ ] Update the `terra deps` pip list — remove the dead `networkx`
      entries at `terra.py:1212` and `terra.py:1223`, add `graphifyy`
- [ ] Add `graphify-out/` to `.gitignore`
- [ ] Ship a default `.graphifyignore` at repo root
- [ ] Smoke test: `terra graphify .` on Terragraf itself — read
      `GRAPH_REPORT.md`, sanity-check that god nodes match our mental
      model (`terra.py`, `.scaffold/app/window.py`,
      `.scaffold/app/tab_widget.py` should be near the top)
- [ ] Confirm graphify appears in `terra skill list`
- [ ] Append four new rows to `SECURITY.md`'s threat table (SSRF,
      oversized downloads, XSS in graph HTML, prompt injection via
      node labels), citing upstream `graphify.security` mitigations
- [ ] **Phase 2 (deferred)**: `GraphPanel` Qt widget, WelcomeTab
      stats, sidebar nav entry, Ctrl+G toggle

## Files to reference during implementation

- `.scaffold/skills/signal_analyze/SKILL.toml` — skill metadata template
- `.scaffold/skills/signal_analyze/run.py` — skill entry-point template
- `terra.py:904` — `terra analyze` command delegation pattern
- `terra.py:1212`, `terra.py:1223` — pip/conda dep lists to update
- `.scaffold/app/welcome_tab.py` — Phase 2 health-grid extension point
- `.scaffold/app/widgets/sidebar.py` — Phase 2 nav-entry extension point
- `.scaffold/docs/qt/README.md` — Qt doc voice/tone reference for
  Phase 2's `GraphPanel` widget doc
- `SECURITY.md` — threat-table update target when Phase 1 lands
