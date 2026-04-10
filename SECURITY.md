# Security Policy

## Supported Versions

Terragraf is pre-1.0 and ships from session-numbered development
branches. Only the following branches receive security fixes:

| Branch         | Role                       | Supported |
|----------------|----------------------------|-----------|
| `Yog-pls`      | Current development        | Yes       |
| `Yog`          | Main merge target          | Soon      |
| `main`         | Stable snapshot            | No        |
| legacy branches| Historical                 | No        |
|----------------|----------------------------|-----------|

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues via GitHub's private vulnerability reporting
feature on this repository, or email the maintainer directly. Please
include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to release a fix
within 7 days for critical issues.

## Security Model

Terragraf is a **local development scaffold and Qt workspace**. It
runs as:

- a Python CLI (`terra.py`)
- an optional local MCP stdio server (`.scaffold/mcp/server.py`)
- a PySide6 desktop app (`.scaffold/app/`)
- an optional native ImGui process (`terragraf_imgui.exe`) communicating
  over a local shared-memory bridge

Terragraf makes no network calls during normal operation. The only
outbound network activity is:

- `terra deps sync` — git clones from a hardcoded list of GitHub
  repositories defined in `terra.py`
- optional LLM provider calls — only when the user explicitly
  configures an API key and provider

### Threat Surface

| Vector | Mitigation |
|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Path traversal in skill runner           | Skills are discovered by directory enumeration under `.scaffold/skills/`, never by user-supplied names. All paths are resolved with `pathlib.Path.resolve()` before use.                                                                                       |
| Path traversal in MCP server             | `.scaffold/mcp/server.py` is stdio-only. Tool arguments that reference filesystem paths are resolved against `SCAFFOLD_ROOT` and rejected if they escape it.                                                                                                   |
| Shell injection via subprocess           | All `subprocess.run()` calls in `terra.py` and the skill runner use list-form `argv`. `shell=True` is not used anywhere in the codebase.                                                                                                                       |
| Malicious git clone targets              | `terra deps sync` clones only from the hardcoded GitHub URL list in `terra.py`. User input never reaches the clone URL.                                                                                                                                        |
| Untrusted QSS / theme loading            | The stylesheets under `.scaffold/app/themes/` are repo-shipped. Terragraf does not load QSS from user-supplied files. QSS itself does not execute code.                                                                                                        |
| LLM provider key exfiltration            | API keys are sourced from environment variables only and are never written to logs, hot-context files, or the knowledge table. LLM calls are opt-in via explicit user configuration.                                                                           |
| Hot-context / knowledge table corruption | `.scaffold/HOT_CONTEXT.md` and `projects/KNOWLEDGE.toml` are version-controlled. Corruption is recoverable via `git restore`.                                                                                                                                  |
| ImGui bridge (local IPC)                 | The Qt ↔ `terragraf_imgui.exe` bridge uses a local shared-memory segment. No network socket is opened.                                                                                                                                                         |
| Corrupted state files                    | The skill runner wraps `json.JSONDecodeError` and `toml` parse errors with clear recovery messages instead of crashing on malformed `.scaffold/state/*.json` or `projects/KNOWLEDGE.toml`.                                                                     |
| Symlink traversal during scans           | Scaffold health and consistency scans walk the tree without following symlinks.                                                                                                                                                                                |
| SSRF via `graphify ingest`               | `graphify ingest` only fetches URLs the user passes on the command line. No URLs are auto-discovered or fetched without explicit action. The upstream `graphify` package performs its own scheme and host validation.                                          |
| Oversized downloads during ingest        | Downloads initiated by `graphify ingest` are bounded by the upstream package's own size limits. Terragraf does not add a second size gate. The ingest command requires explicit user invocation.                                                               |
| XSS in graph HTML output                 | `GraphPanel` loads `graphify-out/graph.html` from the local filesystem into a `QWebEngineView`. The HTML is generated locally by `graphify` from the user's own codebase, not fetched from the network. Terragraf does not apply additional HTML sanitization. |
| Prompt injection via node labels         | Code comments and identifiers from the user's codebase become node labels in the knowledge graph. These labels may be included in LLM prompts when a provider is configured. LLM calls are opt-in and require explicit provider configuration.                 |
|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### What Terragraf does NOT do

- Does not run a network listener (MCP communicates over stdio only)
- Does not execute code from user source files
- Does not use `shell=True` in any subprocess call
- Does not store credentials or API keys on disk
- Does not phone home, submit telemetry, or publish usage metrics

### Optional network calls

- `terra deps sync` — hardcoded GitHub clones of dependency
  repositories
- LLM provider calls — opt-in, explicit user configuration, one
  provider per session
- `graphify ingest` — fetches URLs explicitly provided by the user
  on the command line. See the threat table above for details.
