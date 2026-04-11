# Terragraf -- Claude Code Harness

Read and follow `PROTOCOL.md` in this directory. It contains all session
commands and behavioral constraints. This file is the Claude Code spoke;
PROTOCOL.md is the hub.

## Quick Start

1. On session start: execute **Swap-read** (read HOT_CONTEXT from disk)
2. During work: follow behavioral constraints (Evidence Over Inference,
   Vertical Movement, Context Hold, Hypothesis Decay)
3. On errors: invoke **Vertical** debug protocol before iterating
4. On session end: execute **Swap-write** (update HOT_CONTEXT)

## Tools Available

- `terra.py` CLI: `terra health`, `terra test`, `terra skill list`,
  `terra hot`, `terra hot decompose`, etc.
- pytest: `python -m pytest .scaffold/tests/`
- All scaffold skills via `terra <skill>`

## Project Structure

`terra.py` is the CLI entry point (repo root). Run `python terra.py help`
for all commands.

`.scaffold/` is the project itself — not a tool that generates projects.
Read `.scaffold/ENTRY.md` first for the full architecture: headers,
includes, routes, tables, generators, instances, ML, compute, and the
Qt app.

## Framework Files

| File | Purpose |
|------|---------|
| `PROTOCOL.md` | Session commands and behavioral constraints (the hub) |
| `.scaffold/HOT_CONTEXT.md` | Session state persistence |
| `.scaffold/MANIFEST.toml` | Project configuration |
| `.scaffold/ENTRY.md` | Scaffold architecture guide |
| `improvements.md` | Consider/Graduate feedback loop |
