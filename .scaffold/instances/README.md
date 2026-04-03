# instances/

Multi-instancing system. Replaces traditional AI agents/sub-agents.

## The Problem With Agents

Traditional AI agents (like Claude's sub-agents) are:
- Spawned by a parent — hierarchical, not parallel
- Context-limited — each agent starts fresh or gets a summary
- Serial bottlenecked — parent waits for child, then acts
- Opaque — parent doesn't see child's full reasoning

## How Multi-Instancing Works

Instead of one AI spawning sub-agents, Terraformer runs **multiple AI instances
in parallel** that share the same scaffolding:

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

### Key Differences From Agents

1. **Shared structure** — all instances read the same headers, routes,
   tables. No context loss.
2. **Peer-to-peer** — no parent/child hierarchy. Instance 0 coordinates
   but doesn't own the others.
3. **Filesystem IPC** — instances communicate via shared JSON files and
   file locks. Simple, debuggable, platform-agnostic.
4. **No context window tax** — each instance has its own full context
   for its task. No summarization loss.
5. **Concurrent by default** — instances run simultaneously, not
   sequentially.

### Instance Lifecycle

1. **Spawn** — `manager.py` creates instance with a task and working dir
2. **Init** — instance reads ENTRY.md, MANIFEST.toml, relevant headers
3. **Execute** — instance follows routes/tables to do its work
4. **Report** — instance writes result to shared/results.json
5. **Terminate** — instance cleans up, releases locks

### Coordination

- `shared/queue.json` — task queue. Instances pull tasks atomically.
- `shared/results.json` — completed results. Coordinator reads these.
- `shared/locks/` — file-based locks preventing two instances from
  editing the same file simultaneously.

### When to Multi-Instance vs Single

**Multi-instance when:**
- Tasks are independent (fix bug A while building feature B)
- Research + implementation can happen in parallel
- Multiple files need generation that don't depend on each other

**Single instance when:**
- Tasks are sequential (B depends on A's output)
- Shared state is complex (easier for one brain to manage)
- Task is small enough that parallelism adds overhead
