# Terraformer

A scaffolding system for AI.

Terraformer is the working directory any AI reads on entry. It provides
structure, navigation, composition, and execution everything an AI
needs to orient itself in a codebase and start producing immediately.

This is not a code generator. This is the environment the AI operates
inside of.

---

## What it does today

Terraformer gives an AI session seven interlocking systems:

- **Headers** `.h` files that declare what exists in a project, its
  modules, conventions, dependencies, and platform targets. The AI reads
  these to understand the shape of things without scanning every file.

- **Includes** `.inc` fragments that compose together like C includes.
  License blocks, file headers, test skeletons, shader skeletons, small
  reusable pieces that snap into generated output.

- **Routes** `.route` tables that map intent to location. "I need to
  fix a bug" routes to one place. "I need to add a feature" routes to
  another. The AI stops guessing and starts navigating.

- **Tables** `.table` lookups for decisions that have already been
  made. Known error patterns, design patterns in use, internal dependency
  graphs. Compressed knowledge the AI consults instead of re-deriving.

- **Generators** JS, Python, and shell scripts that read the structure
  above and produce output. Resolve includes, generate modules, scaffold
  models, emit shaders.

- **Instances** Multi-instancing that replaces the traditional agent
  model. Instead of one AI spawning sub-agents in a hierarchy, Terraformer
  runs multiple AI instances as peers. They share the same scaffolding,
  pull tasks from a shared queue, and write results back. No context
  window tax. No summarization loss.

- **Git** Branching, commit, and PR workflows baked into the structure
  so the AI follows project conventions without being told each time.

## What's next

- Instance coordination over sockets and pipes, not just filesystem IPC.

- Self-sharpening routes and tables — the scaffolding updates itself
  from encountered errors and completed tasks instead of staying static.

- Language-aware output that adapts conventions and tooling per project
  language without separate configurations.

## Platforms

Linux (Wayland) and Windows 10/11.

## Contributors

| Name | Role | Contact |
|------|------|---------|
| Austin Wisniewski | Creator, Lead | [@curbthepain](https://github.com/curbthepain) |
| Claude (Anthropic) | AI Contributor | [anthropic.com](https://anthropic.com) |

## License

Apache 2.0
