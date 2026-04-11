# Terragraf -- Session Protocol

#pragma once
#pragma priority 1

## Purpose

This file defines session commands and behavioral constraints for AI assistants
working on Terragraf. Commands are triggered by keyword -- any of three variants
(formal, casual, short) activates the same protocol.

This is the **hub**. Tool-specific files (CLAUDE.md, .cursorrules, etc.) are
**spokes** that route here. All protocol content lives in this file.

---

## Behavioral Constraints (Always Active)

These apply to every command, every turn, every session:

1. **Evidence Over Inference.** Do not generate hypotheses without gathering
   evidence. Run a command, read a file, check an output. After editing source,
   do not claim the change is effective until tests pass -- a source edit is not
   a deployed change.

2. **Vertical Movement.** When stuck, move up or down the layer stack. Do not
   iterate horizontally more than twice on the same file for the same issue.
   Announce layer transitions explicitly. (See Vertical command below.)

3. **Context Hold.** Re-read files before acting on them if 5+ turns have
   elapsed. Do not write code from memory when the actual content might have
   changed. Decay gracefully -- say "I need to re-read X" when uncertain.

4. **Hypothesis Decay.** Track confidence in active hypotheses. Direct
   observation decays slowly (lambda=0.05). Pure speculation decays fast
   (lambda=0.50). When confidence drops below 30%, the hypothesis is stale --
   abandon it, don't defend it. If the user directly contradicts a hypothesis
   with first-hand evidence, kill it immediately. The user's direct observation
   outranks any inference. Do not defend.

---

## Layer Stack (Terragraf-Adapted)

```
[L5] Runtime / CLI        -- terra.py, Qt app entry, pytest execution
[L4] Application Logic    -- skills, scaffold modules, ML pipeline, Qt widgets
[L3] Interface / Binding  -- imports, IPC bridge, MCP, LLM provider, subprocess
[L2] Build / Environment  -- pip, cmake (imgui), pytest config, MANIFEST.toml
[L1] OS / Platform        -- Windows paths, PySide6 platform plugins, GPU drivers
```

---

## Command Quick Reference

| # | Formal | Casual | Short | Purpose |
|---|--------|--------|-------|---------|
| 1 | Swap | Switch | ctx | Read/write HOT_CONTEXT |
| 2 | Vertical | Debug | cat | 5-layer debug protocol |
| 3 | Confidence | Blush | est | Context health self-assessment |
| 4 | Sweep | Crunch | brush | Re-read all relevant files |
| 5 | Phoenix | Rebirth | zero | Session refresh (don't restart) |
| 6 | Report | Condense | dumpsys | Structured findings by subsystem |
| 7 | Profile | Analyze | compute | Performance measurement + stats |
| 8 | Backup | RAID 6 | snapshot | Timestamped project snapshot |
| 9 | Consider | Failstate | wheresmycar | Session retrospective self-audit |
| 10 | Graduate | Improve | uni | Integrate improvements with approval |
| 11 | Test | Prove | bench | Cascade-aware test analysis |

---

## Commands

### "Swap" , "Switch" , "ctx"

Read or write session state via HOT_CONTEXT. Two modes:

**Swap-read** (default when no argument given):

1. Read `.scaffold/HOT_CONTEXT.md` from disk -- not from memory
2. Report: current session number, phase, test count, skill count, grade
3. List the backlog and next-session items
4. Note any staleness (file older than 48 hours)

**Swap-write** (when the user says "swap write", "ctx write", or session is ending):

1. Gather state -- re-read all files modified this session (mini-Sweep)
2. Update `.scaffold/HOT_CONTEXT.md` following the existing format:
   - Session number and status line
   - What's Done section (files touched, decisions, verification)
   - Backlog updates
3. Cross-reference against `projects/KNOWLEDGE.toml` for consistency
4. If HOT_CONTEXT exceeds `retain_sessions = 3` (MANIFEST.toml), note that
   `terra hot decompose` should run
5. Say **(swapped)** when done

---

### "Vertical" , "Debug" , "cat"

Invoke the Vertical Debug Framework on the current problem. Stop horizontal
iteration. Map the bug to a layer. Follow Three Strikes.

**Protocol:**
1. Stop. Do not attempt another fix on the current layer.
2. State the current symptom clearly
3. Map it to the 5-layer stack (L1-L5 above)
4. Check the misdirection table -- is this a common wrong-layer instinct?
5. Move in the biased direction (down for "should work" bugs, up for
   integration bugs)
6. Follow Three Strikes Protocol with new evidence at each strike
7. If exhausted, produce a structured debug report and halt

**Three Strikes:**
- Strike 1: one retry on the same layer. Gather new evidence first.
- Strike 2: move one layer down. Inspect the dependency. Read actual files.
- Strike 3: move one layer up. Inspect the caller or integration point.
- All three fail: stop and report.

**Misdirection Table:**

| Symptom | Wrong instinct (horizontal) | Right move (vertical) |
|---|---|---|
| ImportError | Rewrite the import | Go down: check if module installed, check sys.path |
| Qt widget not showing | Rewrite the widget | Go up: check if parent layout adds it, check show() |
| Test passes locally, fails CI | Fix the test | Go down: check CI env (offscreen, env vars, deps) |
| `terra` command fails | Fix terra.py dispatch | Go down: check if skill's run.py works standalone |
| Offscreen Qt crash | Fix widget code | Go down: check QT_QPA_PLATFORM, PySide6 version |
| Build succeeds but runtime fails | Tweak build flags | Go up: check what the caller actually passes |
| "Should work" but doesn't | Rewrite the function | Go down: verify environment, paths, versions |

**Loop Detection (any two = loop):**
- Edited the same file more than twice for the same issue
- Re-reading code already read this session without new information
- Proposed fix is a variation of something already tried
- Generating hypotheses without gathering new evidence

**Debug Report (when exhausted):**
```
## Debug Report
- Symptom: [what's failing]
- Layers inspected: [list]
- Evidence gathered: [what you actually read/ran]
- Hypotheses eliminated: [what you ruled out and why]
- Remaining unknowns: [what you haven't been able to verify]
- Suggested next step: [what a human should check]
```

---

### "Confidence" , "Blush" , "est"

Self-assess context health and report the confidence window.

**Protocol:**
1. Compute the confidence score:

```
C(t) = base(t) x framework_modifier x topic_load x recency_factor

base(t):
  With framework:     0.95 x e^(-0.012 x t)
  Without framework:  0.95 x e^(-0.04 x t)

framework_modifier:
  1.0   if PROTOCOL.md loaded AND referenced within last 5 turns
  0.85  if loaded but not referenced in 5-10 turns
  0.60  if loaded but not referenced in 10+ turns
  0.30  if not loaded

topic_load:
  1.0   1-3 active threads
  0.85  4-6 threads
  0.70  7-9 threads
  0.55  10+ threads

recency_factor:
  1.0   topic discussed < 3 turns ago
  0.85  3-7 turns ago
  0.70  8-12 turns ago
  0.55  13-15 turns ago
  0.40  15+ turns ago
```

2. Map to confidence band:
   - **FRESH**: 90%+ -- full precision
   - **HOLDING**: 70-89% -- reliable, minor drift possible
   - **DECAYING**: 50-69% -- hedging, qualifiers appearing
   - **STALE**: 30-49% -- repetition, vague references
   - **DECOHERENT**: <30% -- unreliable

3. Self-check: am I hedging, repeating, over-formatting, drifting?

4. Report:
```
## Confidence Window
- Session depth: [turns]
- Active threads: [count]
- Current topic recency: [turns since last active]
- Framework status: [loaded/referenced/stale]
- Confidence score: [percentage]
- Band: [FRESH / HOLDING / DECAYING / STALE / DECOHERENT]
- Symptoms detected: [any output/behavioral symptoms observed]
- Recommendation: [continue / sweep recommended / re-read required / halt]
```

5. If band is STALE or DECOHERENT, recommend a Sweep before continuing
6. **Phoenix gate:** If score <= 75%, automatically execute Phoenix after report

---

### "Sweep" , "Crunch" , "brush"

Re-observation pass. Re-read all files relevant to the current task and refresh
context. This is a manual standing-wave pulse -- force observation to prevent
decoherence.

**Protocol:**
1. List every file currently relevant to the active task
2. Read each one from disk (not memory)
3. After reading, state what changed or what you now notice that you missed
4. Check: does file inventory match what HOT_CONTEXT claims?
5. Resume work with refreshed context
6. Say **(swept)** when done

---

### "Phoenix" , "Rebirth" , "zero"

Execute the Session Refresh Protocol. Never surrender the session -- refresh
it instead.

**Automatic trigger:** Fires after any Confidence command that reports <= 75%.

**Manual trigger:** User says "phoenix", "rebirth", or "zero" at any time.

**Protocol:**
1. Write Phoenix Manifest to `.scaffold/.phoenix_manifest.md`:
   - Active task and current layer
   - Compressed thread list (what's alive, what's resolved)
   - Hot file inventory
   - Hypothesis table with confidence scores
   - Next steps
2. Re-read PROTOCOL.md from disk
3. Re-read HOT_CONTEXT from disk
4. Re-read all hot files listed in the manifest
5. Re-read the manifest itself
6. Run Confidence check -- expect 80-90% post-refresh
7. Resume work from manifest state. Do not ask "where were we?"
8. Say **(reborn)** when done

**Suppression:** No auto-Phoenix within 15 turns of the last one. Cap at 2
per 30 turns. If looping, report to user.

**Absolute rule:** Never tell the user to start a new session. Refresh
yourself and keep working.

---

### "Report" , "Condense" , "dumpsys"

Show what you know. Present findings structured by subsystem with evidence
classification.

**Protocol:**
1. Present findings structured by scaffold area:
   - Scaffold health (skills, routes, headers, tests)
   - Active project status (from HOT_CONTEXT)
   - Test results (count, grade, warnings)
   - Pending work (from backlog)
2. For each finding, state evidence class:
   - **Observed**: directly read from file or ran command this session
   - **Read**: read from file earlier in session (may be stale)
   - **Inferred**: derived from other evidence
   - **Speculated**: hypothesis without direct evidence
3. State confidence levels honestly -- what's solid, what's uncertain
4. Identify what needs re-observation before acting on it
5. Say **(reported)** when done

---

### "Profile" , "Analyze" , "compute"

Structured performance analysis. Measure, compute statistics, compare against
budgets. No hand-waving -- show the numbers.

**Protocol:**
1. Identify target: test suite duration, startup time, skill execution,
   Qt render time, specific function
2. Instrument: `time.perf_counter()`, `pytest --durations=N`, cProfile,
   or timing wrappers
3. Collect N samples (state N; minimum 10 for quick checks, 100 for stats)
4. Compute and report:
   - **Central tendency:** mean, median (P50)
   - **Tail latency:** P95, P99, max
   - **Spread:** stddev, coefficient of variation (CV = stddev/mean)
   - **Confidence:** 95% CI = mean +/- 1.96 x (stddev / sqrt(N))
5. If CV > 15% -- measurement is noisy, investigate variance source
6. Compare against budget (session targets, prior baselines, or user-specified)
7. If over budget, identify the bottleneck:
   - Serial vs parallel fraction
   - Amdahl's law: S(N) = 1 / ((1-P) + P/N)
8. Say **(benchmarked)** when done

---

### "Backup" , "RAID 6" , "snapshot"

Take a timestamped snapshot. Non-destructive, append-only.

**Protocol:**
1. Determine target folder (default: `.scaffold/`, or user-specified scope)
2. Generate snapshot path: `snapshots/dd-mm-yyyy-NNN/` where:
   - `dd-mm-yyyy` = current date
   - `NNN` = three-digit sequential number (scan existing, increment)
3. Create the snapshot directory
4. Copy target recursively, preserving structure
5. **Skip:** `.git/`, `__pycache__/`, `build/`, `src/` (2.9 GB local deps),
   `Debug/`, `Releases/`, `graphify-out/`, `snapshots/` (no recursion)
6. Report:
```
## Snapshot Receipt
- Path: snapshots/dd-mm-yyyy-NNN/
- Files: [count]
- Size: [human-readable]
- Cumulative: [total across all snapshots]
- License: [included if present]
```
7. Say **(snapshot)** when done

**Constraints:** Never delete or overwrite existing snapshots. Append-only.

---

### "Consider" , "Failstate" , "wheresmycar"

Retrospective self-audit. Review your own performance this session. Triage by
severity: failures first, then wins (for pattern extraction), then middling.

**Protocol:**
1. **Inventory actions this session.** List every significant action: files
   read, edits made, hypotheses formed, commands executed, bugs chased, fixes.
2. **Classify each action:**

```
## Session Retrospective

### FAILURES (priority 1 -- examine first)
- [action]: [what went wrong, root cause, which layer]

### WINS (priority 2 -- extract patterns)
- [action]: [what worked, why, is it repeatable?]

### MIDDLING (priority 3 -- note but don't dwell)
- [action]: [what was slow, inefficient, or required correction]
```

3. **Deprioritize middling.** Failures teach the most. Wins confirm what
   works. Middling is just friction.
4. **For each failure, trace the cause:**
   - Behavioral constraint violation? (Evidence, vertical movement, context hold)
   - Framework gap? (Missing command, missing protocol step)
   - Human-interaction failure? (Misread intent, over-committed before confirming)
   - Technical miss? (Wrong layer, wrong file, wrong hypothesis)
5. **For each win, extract the pattern:**
   - What made it work? Can it be generalized?
   - Does it suggest a new command or protocol step?
6. **Compare against PROTOCOL.md.** Re-read this file. Ask:
   - Did any failure happen BECAUSE a rule wasn't followed?
   - Did any failure happen DESPITE following the rules? (framework gap)
   - Would a new rule have prevented it?
7. **Write improvements to `improvements.md`** if any framework gaps found:

```
## Improvement: [short name]
- Source: [which session failure or pattern]
- Target: [which file or command]
- Proposal: [specific change]
- Evidence class: [observed / inferred]
- Priority: [high / medium / low]
```

8. Say **(considered)** when done.

**Math anchor:** If a session has N actions and F failures: F/N > 20% = systemic
issues, look for common root cause. F/N < 5% = extract wins aggressively.

---

### "Graduate" , "Improve" , "uni"

Read `improvements.md` and integrate approved improvements into framework files.
This is the feedback loop -- Consider identifies gaps, Graduate closes them.

**Protocol:**
1. Read `improvements.md` from disk. If empty, say so and stop.
2. For each improvement entry:
   a. **Validate** -- observed improvements apply directly. Inferred need
      user confirmation.
   b. **Locate target** -- which file does this change?
   c. **Draft the change** -- specific edit, new rule, or new protocol step
   d. **Present to user** -- show proposed change in context. Do NOT apply
      without approval.
3. On user approval: apply change, mark INTEGRATED with date in improvements.md
4. On user denial: mark REJECTED with reason
5. On user deferral: leave as pending
6. Say **(graduated)** when done.

**Lifecycle:**
```
Consider (retrospective)
    |
    v
improvements.md (proposals)
    |
    v
Graduate (review + apply)
    |
    +--> Approved  --> Apply, mark INTEGRATED
    +--> Denied    --> Mark REJECTED with reason
    +--> Deferred  --> Leave pending
```

**Constraints:** Graduate NEVER applies changes without user approval.

---

### "Test" , "Prove" , "bench"

Run the test suite with cascade detection. Do not treat cascade victims as
independent failures.

**Protocol:**
1. Identify test scope: all (`pytest .scaffold/tests/`), specific subsystem
   (`pytest .scaffold/tests/test_X.py`), or specific test
2. Run the suite. Capture stdout + stderr.
3. Categorize every result: PASS / FAIL / SKIP
4. **Cascade detection:** If a fixture or import fails, count all downstream
   failures as ONE root cause:
   - `apparent_failures` = raw FAIL count
   - `unique_root_causes` = distinct independent failures
   - `cascade_ratio` = apparent / unique (>3 means cascade dominates)
5. For each unique root cause: map to the L1-L5 stack, state evidence class
6. Produce structured report:

```
## Test Report
- Scope: [what was tested]
- Pass rate: X/Y (Z%) -- apparent
- Effective failure rate: U unique root causes / Y total (W%)
- Cascade ratio: apparent_failures / unique_root_causes
- Root causes: [list with layer mapping]
- Recommended action: [per root cause]
```

7. If pass rate < 100%, invoke Vertical Debug on the highest-priority unique
   failure

---

## Command Combinations

Commands can be chained. Say both names:

- **"Swap-read, Sweep"** -- load session state then refresh all relevant files
- **"Confidence, Sweep"** -- check health then re-observe if decaying
- **"Confidence -> Phoenix"** -- automatic: if <= 75%, Phoenix fires after report
- **"Test, Vertical"** -- run tests then debug failures vertically
- **"Consider, Graduate"** -- retrospective then integrate improvements
- **"Consider, Swap-write"** -- retrospective then handoff (best end-of-session)
- **"Sweep, Vertical"** -- refresh context then debug vertically
- **"Profile, Report"** -- benchmark then present findings with numbers

If no command is given, default behavior is: follow all behavioral constraints,
use Vertical on errors, maintain Context Hold, and work toward the current task.

---

## Evidence Class Reference

| Class | Lambda | Half-life | Stale at step |
|---|---|---|---|
| Direct observation (ran command, read output) | 0.05 | ~14 steps | ~24 steps |
| Code reading (read file this session) | 0.10 | ~7 steps | ~12 steps |
| Structural inference (derived from evidence) | 0.20 | ~3.5 steps | ~6 steps |
| Pure speculation (hypothesis without evidence) | 0.50 | ~1.4 steps | ~2.4 steps |

---

*Protocol version: v1*
*Project: Terragraf*
*Adapted from: Kohala Session Command Interface v8 (Sigand, Inc.)*
