# Multi-Instancing

Terragraf's instance model replaces the traditional AI agent hierarchy
with peer instances sharing one scaffold.

## The problem with agents

Traditional AI agent systems (sub-agents, tool-calling chains) are:

- **Hierarchical** — a parent spawns children and waits for them.
  Bottleneck is always the parent.
- **Context-lossy** — each child starts fresh or gets a summary of the
  parent's context. Information degrades at every level.
- **Serially bottlenecked** — parent dispatches, waits, reads result,
  dispatches again. Parallelism is an afterthought.
- **Opaque** — the parent never sees the child's full reasoning, only
  its final output.

This is the model Claude Code, Cursor, and most agentic frameworks use
today. It works for simple delegation but breaks down when tasks are
complex, interdependent, or need shared context.

## How multi-instancing works

Instead of one AI spawning sub-agents, Terragraf runs **multiple AI
instances in parallel** that share the same scaffolding:

```
Instance 0 (coordinator)
    reads: task queue (socket or filesystem)
    writes: tasks to queue
    reads: results from completed instances

Instance 1                Instance 2                Instance 3
    pulls task                pulls task                pulls task
    reads scaffolding         reads scaffolding         reads scaffolding
    does work                 does work                 does work
    writes result             writes result             writes result
```

Every instance reads the same headers, routes, and tables. No instance
is subordinate to another. Instance 0 coordinates (decides what tasks
exist and reads results) but does not own or control the others.

## Key differences from agents

| | Traditional agents | Terragraf instances |
|---|---|---|
| **Topology** | Tree (parent -> children) | Flat (coordinator + peers) |
| **Context** | Summarized at each level | Full scaffold per instance |
| **Parallelism** | Parent waits for child | All instances run concurrently |
| **Communication** | Return values up the tree | Socket IPC + filesystem fallback |
| **Visibility** | Parent sees only output | All results visible to all instances |

## IPC transport

Instances communicate via **TCP socket IPC** (default) with automatic
fallback to filesystem polling.

### Socket mode (default)

- `TransportServer` listens on `127.0.0.1:9877`, accepts peer connections
- `TransportClient` connects, auto-registers with instance ID
- Length-prefixed JSON protocol (4-byte big-endian header + payload)
- Message types: `task_assign`, `task_result`, `register`, `heartbeat`
- Thread-safe inbox with mutex, heartbeats filtered at receive time
- Sub-millisecond dispatch, supports 10+ concurrent instances

### Filesystem mode (fallback)

- `shared/queue.json` — task queue, atomic via file locks
- `shared/results.json` — completed results
- `shared/locks/` — file-based locks preventing concurrent edits
- Used when socket port is unavailable or explicitly configured

### Mode selection

Set in `MANIFEST.toml`:

```toml
[features]
ipc = "auto"      # try socket, fall back to filesystem
# ipc = "socket"  # socket only (fail if unavailable)
# ipc = "filesystem"  # filesystem only
```

## Instance lifecycle

1. **Spawn** — `manager.py` creates an instance with a task and working
   directory.
2. **Init** — the instance reads `ENTRY.md`, `MANIFEST.toml`, and the
   relevant headers. If socket mode, connects to TransportServer and
   registers.
3. **Wait** — `wait_for_task()` blocks until a task is assigned via
   socket or polls the filesystem queue.
4. **Execute** — the instance follows routes and tables to do its work.
   It has its own full context window for its task.
5. **Report** — the instance sends its result via socket (`task_result`
   message) or writes to `shared/results.json`.
6. **Cleanup** — the instance disconnects transport and releases
   resources.

## When to multi-instance

**Use multiple instances when:**
- Tasks are independent (fix bug A while building feature B)
- Research and implementation can happen in parallel
- Multiple files need generation that don't depend on each other

**Use a single instance when:**
- Tasks are sequential (B depends on A's output)
- Shared state is complex enough that one context is simpler
- The task is small enough that parallelism adds overhead

## Files

```
.scaffold/instances/
├── manager.py          — spawns and coordinates instances (socket + filesystem)
├── instance.py         — individual instance runtime (socket + filesystem)
├── transport.py        — TCP socket transport layer (server + client)
└── shared/
    ├── queue.json      — task queue (filesystem mode)
    ├── results.json    — completed results
    └── locks/          — file-based locks
```

## Tests

16 transport tests covering:
- Wire protocol roundtrips (single, multiple, large messages)
- Server/client connection and registration
- Broadcast and unicast message delivery
- Multiple concurrent clients
- Heartbeat filtering
- Disconnect detection and reconnection
- Manager socket integration (startup, fallback, dispatch, result reporting)
