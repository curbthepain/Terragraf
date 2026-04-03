# Multi-Instancing

Terraformer's instance model replaces the traditional AI agent hierarchy
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

Instead of one AI spawning sub-agents, Terraformer runs **multiple AI
instances in parallel** that share the same scaffolding:

```
Instance 0 (coordinator)
    reads: .scaffold/instances/shared/queue.json
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

| | Traditional agents | Terraformer instances |
|---|---|---|
| **Topology** | Tree (parent → children) | Flat (coordinator + peers) |
| **Context** | Summarized at each level | Full scaffold per instance |
| **Parallelism** | Parent waits for child | All instances run concurrently |
| **Communication** | Return values up the tree | Shared filesystem (queue + results) |
| **Visibility** | Parent sees only output | All results visible to all instances |

## Instance lifecycle

1. **Spawn** — `manager.py` creates an instance with a task and working
   directory.
2. **Init** — the instance reads `ENTRY.md`, `MANIFEST.toml`, and the
   relevant headers for its task.
3. **Execute** — the instance follows routes and tables to do its work.
   It has its own full context window for its task.
4. **Report** — the instance writes its result to
   `shared/results.json`.
5. **Terminate** — the instance cleans up and releases any file locks.

## Coordination

- `shared/queue.json` — task queue. Instances pull tasks atomically
  using file locks.
- `shared/results.json` — completed results. The coordinator reads
  these.
- `shared/locks/` — file-based locks preventing two instances from
  editing the same file.

Current coordination is filesystem-based. The roadmap includes socket
and pipe IPC for sub-millisecond dispatch. See
[ROADMAP.md](ROADMAP.md#phase-7-socketpipe-ipc-for-multi-instancing).

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
├── manager.py          — spawns and coordinates instances
├── instance.py         — individual instance runtime
└── shared/
    ├── queue.json      — task queue
    └── results.json    — completed results
```
