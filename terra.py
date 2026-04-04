#!/usr/bin/env python3
"""
terra.py — single entry point for the Terragraf scaffolding system.
Platform-agnostic Python implementation (Linux + Windows native).

Human commands. Fits on one card.

  terra status          what's here, what works
  terra route <intent>  where do I go for this?
  terra lookup <error>  known fix for this error?
  terra pattern <name>  what pattern fits here?
  terra dep <module>    what depends on what?
  terra gen module <n>  generate a module
  terra gen model <n>   generate a model
  terra gen shader <n>  generate a shader
  terra hook enter      run the entry hook
  terra hook commit     run the commit hook
  terra queue           show the task queue
  terra queue add <t>   add a task to the queue
  terra analyze <input> signal/audio FFT analysis
  terra solve <op>      math computation router
  terra branch <t> <n>  create conventional branch
  terra commit <msg>    structured commit
  terra pr --preview    PR template/preview
  terra generate <t> <n> generate module/model/shader
  terra train <dir>     ML training pipeline
  terra viewer          ImGui viewer lifecycle
  terra render <t> <in> 3D visualization
  terra test [module]   run test suite
  terra dispatch <task> parallel instances
  terra health          system diagnostic
  terra hot [action]    session hot context
  terra skill list      list registered skills
  terra skill run <n>   execute a skill
  terra project new <n> scaffold a new project
  terra init            wire hooks into git, check env
  terra help            print this
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

TERRA_ROOT = Path(__file__).parent.resolve()
SCAFFOLD = TERRA_ROOT / ".scaffold"

# ── Colors ──────────────────────────────────────────────────────────

def _supports_color():
    """Check if the terminal supports ANSI colors."""
    if os.environ.get("NO_COLOR"):
        return False
    if sys.platform == "win32":
        # Windows 10+ supports ANSI via virtual terminal processing
        return os.environ.get("TERM") or os.environ.get("WT_SESSION") or True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

if _supports_color():
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RED = "\033[31m"
    RESET = "\033[0m"
else:
    BOLD = DIM = GREEN = YELLOW = CYAN = RED = RESET = ""

# Enable ANSI on Windows and fix encoding
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass
    # Ensure UTF-8 output on Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Helpers ─────────────────────────────────────────────────────────

def has_cmd(name):
    return shutil.which(name) is not None

def python_cmd():
    return sys.executable

def count_files(directory, ext):
    try:
        return len(list(Path(directory).glob(f"*.{ext}")))
    except OSError:
        return 0

def detect_platform():
    system = platform.system()
    if system == "Linux":
        if os.environ.get("WAYLAND_DISPLAY"):
            return "linux/wayland"
        return "linux"
    elif system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    return "unknown"

def record_hit(source, pattern, query):
    """Fire-and-forget analytics recording for self-sharpening."""
    try:
        sys.path.insert(0, str(SCAFFOLD))
        from sharpen.tracker import record_hit as _record
        _record(source, pattern, query)
    except Exception:
        pass

# ── status ──────────────────────────────────────────────────────────

def cmd_status():
    print(f"{BOLD}Terragraf{RESET}")
    print()

    # Platform
    plat = detect_platform()
    print(f"  platform   {GREEN}{plat}{RESET}")

    # Runtimes
    print(f"  bash       {GREEN}yes{RESET}" if has_cmd("bash") else f"  bash       {DIM}not found{RESET}")
    if has_cmd("node"):
        ver = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"  node       {GREEN}{ver}{RESET}")
    else:
        print(f"  node       {DIM}not found{RESET}")
    py_ver = platform.python_version()
    print(f"  python     {GREEN}{py_ver}{RESET}")
    print(f"  git        {GREEN}yes{RESET}" if has_cmd("git") else f"  git        {RED}no{RESET}")
    print()

    # Structure
    print(f"{BOLD}Structure{RESET}")
    print(f"  headers    {count_files(SCAFFOLD / 'headers', 'h')}")
    print(f"  includes   {count_files(SCAFFOLD / 'includes', 'inc')}")
    print(f"  routes     {count_files(SCAFFOLD / 'routes', 'route')}")
    print(f"  tables     {count_files(SCAFFOLD / 'tables', 'table')}")
    print()

    # Queue
    queue_file = SCAFFOLD / "instances" / "shared" / "queue.json"
    if queue_file.exists():
        try:
            data = json.loads(queue_file.read_text())
            tasks = data.get("tasks", data) if isinstance(data, dict) else data
            if isinstance(tasks, list):
                pending = sum(1 for t in tasks if t.get("status") == "pending")
                print(f"  queue      {pending} pending")
        except Exception:
            pass

    results_file = SCAFFOLD / "instances" / "shared" / "results.json"
    if results_file.exists():
        try:
            results = json.loads(results_file.read_text())
            if isinstance(results, list):
                print(f"  results    {len(results)} completed")
        except Exception:
            pass

# ── route ───────────────────────────────────────────────────────────

def cmd_route(args):
    if not args:
        print("Usage: terra route <intent>")
        return
    query = " ".join(args).lower()
    found = False

    for route_file in sorted((SCAFFOLD / "routes").glob("*.route")):
        for line in route_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "->" not in line:
                continue
            intent, _, target = line.partition("->")
            intent = intent.strip()
            target = target.split("#")[0].strip()
            if query in intent.lower():
                print(f"  {CYAN}{intent}{RESET} -> {BOLD}{target}{RESET}")
                record_hit(f"routes/{route_file.name}", intent, query)
                found = True

    if not found:
        print(f"  {DIM}no route matches '{query}'{RESET}")
        print(f"  {DIM}try: terra route feature, terra route bug, terra route model{RESET}")

# ── lookup ──────────────────────────────────────────────────────────

def cmd_lookup(args):
    if not args:
        print("Usage: terra lookup <error or keyword>")
        return
    query = " ".join(args).lower()
    found = False
    errors_table = SCAFFOLD / "tables" / "errors.table"
    if not errors_table.exists():
        print(f"  {DIM}no errors.table found{RESET}")
        return

    for line in errors_table.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        pattern, cause, fix = parts[0].strip(), parts[1].strip(), parts[2].strip()
        hint = parts[3].strip() if len(parts) > 3 else ""
        if query in pattern.lower():
            print(f"  {RED}error{RESET}  {pattern}")
            print(f"  {YELLOW}cause{RESET}  {cause}")
            print(f"  {GREEN}fix{RESET}    {fix}")
            if hint:
                print(f"  {DIM}where{RESET}  {hint}")
            print()
            record_hit("tables/errors.table", pattern, query)
            found = True

    if not found:
        print(f"  {DIM}no known error matches '{query}'{RESET}")

# ── pattern ──────────��─────────────────────────��────────────────────

def cmd_pattern(args):
    query = " ".join(args).lower() if args else ""
    found = False
    patterns_table = SCAFFOLD / "tables" / "patterns.table"
    if not patterns_table.exists():
        print(f"  {DIM}no patterns.table found{RESET}")
        return

    for line in patterns_table.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if not parts:
            continue
        name = parts[0].strip()
        where = parts[1].strip() if len(parts) > 1 else ""
        example = parts[2].strip() if len(parts) > 2 else ""
        notes = parts[3].strip() if len(parts) > 3 else ""
        if not query or query in name.lower():
            print(f"  {BOLD}{name}{RESET}")
            if where:
                print(f"    where   {where}")
            if example:
                print(f"    example {example}")
            if notes:
                print(f"    {DIM}{notes}{RESET}")
            print()
            if query:
                record_hit("tables/patterns.table", name, query)
            found = True

    if not found:
        print(f"  {DIM}no pattern matches '{query}'{RESET}")

# ── dep ─────────────────────────────────────────────��───────────────

def cmd_dep(args):
    query = " ".join(args).lower() if args else ""
    found = False
    deps_table = SCAFFOLD / "tables" / "deps.table"
    if not deps_table.exists():
        print(f"  {DIM}no deps.table found{RESET}")
        return

    for line in deps_table.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        module, depends, rel = parts[0].strip(), parts[1].strip(), parts[2].strip()
        risk = parts[3].strip() if len(parts) > 3 else ""
        if not query or query in module.lower():
            risk_color = {"high": RED, "medium": YELLOW, "low": GREEN}.get(risk, RESET)
            print(f"  {module} -> {depends}  {DIM}{rel}{RESET}  {risk_color}{risk}{RESET}")
            if query:
                record_hit("tables/deps.table", module, query)
            found = True

    if not found:
        print(f"  {DIM}no dependency matches '{query}'{RESET}")

# ── gen ─────────��──────────────────────────────���────────────────────

def cmd_gen(args):
    if not args:
        print("Usage: terra gen <module|model|shader> <name>")
        return
    what = args[0]
    rest = args[1:]

    if what == "module":
        if not rest:
            print("Usage: terra gen module <name> [--lang <lang>]")
            return
        # Use Python lang_detect for default language if --lang not specified
        if "--lang" not in rest:
            try:
                sys.path.insert(0, str(SCAFFOLD))
                from generators.lang_detect import detect_language
                info = detect_language(TERRA_ROOT)
                if info.primary != "unknown":
                    rest.extend(["--lang", info.primary])
            except Exception:
                pass
        if has_cmd("node"):
            subprocess.run(
                ["node", str(SCAFFOLD / "generators" / "gen_module.js")] + rest)
        else:
            # Python fallback: create basic structure
            name = rest[0]
            lang = "python"
            for i, a in enumerate(rest):
                if a == "--lang" and i + 1 < len(rest):
                    lang = rest[i + 1]
            _gen_module_fallback(name, lang)
    elif what == "model":
        subprocess.run(
            [sys.executable, str(SCAFFOLD / "generators" / "gen_model.py")] + rest)
    elif what == "shader":
        subprocess.run(
            [sys.executable, str(SCAFFOLD / "generators" / "gen_shader.py")] + rest)
    else:
        print(f"Unknown generator: {what}")
        print("Available: module, model, shader")

def _gen_module_fallback(name, lang):
    """Create basic module structure without Node.js."""
    target = Path("src") / name
    target.mkdir(parents=True, exist_ok=True)
    if lang == "python":
        (target / "__init__.py").write_text(f"# {name}\n")
        (target / f"{name}.py").write_text(f'"""\n{name} module\n"""\n')
        (target / f"test_{name}.py").write_text(
            f'import pytest\nfrom .{name} import *\n\n\nclass Test{name.capitalize()}:\n    pass\n')
    elif lang in ("javascript", "typescript"):
        (target / "index.js").write_text(f"// {name}\nmodule.exports = {{}};\n")
        (target / f"{name}.js").write_text(f"// {name}\n")
        (target / f"{name}.test.js").write_text(
            f"const {name} = require('./{name}');\n\ndescribe('{name}', () => {{}});\n")
    elif lang == "cpp":
        (target / f"{name}.h").write_text(
            f"#pragma once\n// {name}\n\nnamespace {name} {{\n\n}} // namespace {name}\n")
        (target / f"{name}.cpp").write_text(
            f'#include "{name}.h"\n\nnamespace {name} {{\n\n}} // namespace {name}\n')
    elif lang == "rust":
        (target / "mod.rs").write_text(f"// {name}\n")
    elif lang == "go":
        (target / f"{name}.go").write_text(f"package {name}\n")
        (target / f"{name}_test.go").write_text(
            f'package {name}\n\nimport "testing"\n\nfunc Test{name.capitalize()}(t *testing.T) {{}}\n')
    else:
        (target / f"{name}.txt").write_text(f"// {name} ({lang})\n")
    print(f"Module '{name}' created at {target} ({lang})")

# ── hook ────────────���───────────────────────────────────────────────

def cmd_hook(args):
    if not args:
        print("Usage: terra hook <enter|commit|generate|instance>")
        return
    name = args[0]
    rest = args[1:]

    # Try Python hook first, fall back to shell
    py_hook = SCAFFOLD / "hooks" / f"on_{name}.py"
    sh_hook = SCAFFOLD / "hooks" / f"on_{name}.sh"

    if py_hook.exists():
        subprocess.run([sys.executable, str(py_hook)] + rest)
    elif sh_hook.exists() and has_cmd("bash"):
        subprocess.run(["bash", str(sh_hook)] + rest)
    else:
        print(f"  {RED}no hook: on_{name}{RESET}")
        print(f"  {DIM}available: enter, commit, generate, instance{RESET}")

# ── queue ───��─────────────────────────────────────���─────────────────

def cmd_queue(args):
    action = args[0] if args else "show"
    queue_file = SCAFFOLD / "instances" / "shared" / "queue.json"

    if action == "show":
        if not queue_file.exists():
            print(f"  {DIM}queue is empty{RESET}")
            return
        print(f"{BOLD}Task Queue{RESET}")
        print()
        try:
            data = json.loads(queue_file.read_text())
            tasks = data.get("tasks", data) if isinstance(data, dict) else data
            if not tasks or not isinstance(tasks, list):
                print("  (empty)")
                return
            for t in tasks:
                sid = t.get("id", "?")[:8]
                status = t.get("status", "?")
                desc = t.get("description", t.get("task", "?"))
                color = {
                    "completed": GREEN, "pending": YELLOW, "running": CYAN
                }.get(status, RESET)
                print(f"  {color}{status:<10}{RESET} {sid}  {desc}")
        except Exception as e:
            print(f"  {RED}error reading queue: {e}{RESET}")

    elif action == "add":
        desc = " ".join(args[1:])
        if not desc:
            print("Usage: terra queue add <task description>")
            return
        import hashlib, time
        task_id = hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:12]
        try:
            if queue_file.exists():
                data = json.loads(queue_file.read_text())
            else:
                data = {"tasks": []}
            if isinstance(data, list):
                data = {"tasks": data}
            tasks = data.setdefault("tasks", [])
            tasks.append({"id": task_id, "status": "pending", "description": desc})
            queue_file.write_text(json.dumps(data, indent=2))
            print(f"  queued: {task_id}  {desc}")
        except Exception as e:
            print(f"  {RED}error: {e}{RESET}")
    else:
        print("Usage: terra queue [show|add <task>]")

# ── init ───────────��────────────────────────────────────────────────

def cmd_init():
    print(f"{BOLD}Terragraf init{RESET}")
    print()

    # Wire commit hooks into git
    git_dir = TERRA_ROOT / ".git"
    if git_dir.is_dir():
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # Generate Python-based git hooks (works on both platforms)
        hook_template = (
            '#!/usr/bin/env python3\n'
            'import subprocess, sys\n'
            'from pathlib import Path\n'
            'scaffold = Path(__file__).resolve().parent.parent.parent / ".scaffold"\n'
            'hook_py = scaffold / "hooks" / "on_commit.py"\n'
            'hook_sh = scaffold / "hooks" / "on_commit.sh"\n'
            'if hook_py.exists():\n'
            '    sys.exit(subprocess.run([sys.executable, str(hook_py), "{phase}"]).returncode)\n'
            'elif hook_sh.exists():\n'
            '    import shutil\n'
            '    if shutil.which("bash"):\n'
            '        sys.exit(subprocess.run(["bash", str(hook_sh), "{phase}"]).returncode)\n'
        )

        pre_commit = hooks_dir / "pre-commit"
        if not pre_commit.exists():
            pre_commit.write_text(hook_template.format(phase="pre"))
            if sys.platform != "win32":
                pre_commit.chmod(0o755)
            print(f"  {GREEN}wired{RESET}  pre-commit hook")
        else:
            print(f"  {DIM}exists{RESET} pre-commit hook")

        post_commit = hooks_dir / "post-commit"
        if not post_commit.exists():
            post_commit.write_text(hook_template.format(phase="post"))
            if sys.platform != "win32":
                post_commit.chmod(0o755)
            print(f"  {GREEN}wired{RESET}  post-commit hook")
        else:
            print(f"  {DIM}exists{RESET} post-commit hook")
    else:
        print(f"  {YELLOW}no .git directory{RESET}")

    # Ensure shared dirs exist
    shared = SCAFFOLD / "instances" / "shared"
    (shared / "locks").mkdir(parents=True, exist_ok=True)
    print(f"  {GREEN}ready{RESET}  shared instance dirs")

    # Initialize queue/results if empty
    queue_file = shared / "queue.json"
    results_file = shared / "results.json"
    if not queue_file.exists():
        queue_file.write_text('{"tasks":[]}')
    if not results_file.exists():
        results_file.write_text("[]")
    print(f"  {GREEN}ready{RESET}  queue and results")

    # Detect and display project language
    try:
        sys.path.insert(0, str(SCAFFOLD))
        from generators.lang_detect import detect_language
        info = detect_language(TERRA_ROOT)
        if info.primary != "unknown":
            print(f"  {GREEN}lang{RESET}   {info.primary} (confidence: {info.confidence})")
            if info.secondary:
                print(f"         also: {', '.join(info.secondary[:3])}")
    except Exception:
        pass

    print()

    # Run the entry hook
    py_hook = SCAFFOLD / "hooks" / "on_enter.py"
    sh_hook = SCAFFOLD / "hooks" / "on_enter.sh"
    if py_hook.exists():
        subprocess.run([sys.executable, str(py_hook)])
    elif sh_hook.exists() and has_cmd("bash"):
        subprocess.run(["bash", str(sh_hook)])

# ── imgui ───────────────────────────────────────────────────────────

def cmd_imgui(args):
    if not args:
        print("Usage: terra imgui <build|run|bridge|math|nodes>")
        return
    action = args[0]

    if action == "build":
        print(f"{BOLD}Building ImGui app...{RESET}")
        build_dir = SCAFFOLD / "imgui" / "build"
        build_dir.mkdir(parents=True, exist_ok=True)

        cmake = shutil.which("cmake")
        if not cmake:
            # Check VS2022 bundled cmake on Windows
            if sys.platform == "win32":
                for edition in ["Community", "Professional", "Enterprise"]:
                    vs_cmake = Path(f"C:/Program Files/Microsoft Visual Studio/2022/{edition}"
                                    "/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe")
                    if vs_cmake.exists():
                        cmake = str(vs_cmake)
                        break
        if not cmake:
            print(f"  {RED}cmake required to build ImGui app{RESET}")
            print(f"  {DIM}install: winget install cmake (Windows) or sudo apt install cmake (Linux){RESET}")
            return

        # Configure — use VS generator on Windows if MSVC, otherwise default
        configure_cmd = [cmake, "-B", str(build_dir), "-S", str(SCAFFOLD / "imgui")]
        if sys.platform == "win32" and not os.environ.get("CC"):
            configure_cmd[1:1] = ["-G", "Visual Studio 17 2022", "-A", "x64"]
        else:
            configure_cmd.extend(["-DCMAKE_BUILD_TYPE=Release"])

        result = subprocess.run(configure_cmd)
        if result.returncode != 0:
            return

        # Build — platform-agnostic
        build_cmd = [cmake, "--build", str(build_dir)]
        if sys.platform == "win32":
            build_cmd.extend(["--config", "Release"])
        subprocess.run(build_cmd)

    elif action == "run":
        binary = _find_imgui_binary()
        if binary:
            subprocess.run([str(binary)])
        else:
            print(f"  {YELLOW}not built yet{RESET}")
            print(f"  {DIM}run: terra imgui build{RESET}")

    elif action == "bridge":
        print(f"  {CYAN}Starting bridge server...{RESET}")
        subprocess.run([sys.executable, str(SCAFFOLD / "imgui" / "bridge.py")])

    elif action == "math":
        print(f"  {CYAN}imgui.math_panel{RESET} — interactive function plotter")
        print(f"  {DIM}see .scaffold/imgui/math_panel.cpp{RESET}")

    elif action == "nodes":
        print(f"  {CYAN}imgui.node_editor{RESET} — visual node graph editor")
        print(f"  {DIM}see .scaffold/imgui/node_editor.cpp{RESET}")

    else:
        print(f"  {BOLD}terra imgui{RESET}")
        print(f"    {CYAN}build{RESET}   build the ImGui app")
        print(f"    {CYAN}run{RESET}     launch interactive viewer")
        print(f"    {CYAN}bridge{RESET}  start Python bridge server")
        print(f"    {CYAN}math{RESET}    math modeling panel info")
        print(f"    {CYAN}nodes{RESET}   node graph editor info")

def _find_imgui_binary():
    """Find the ImGui binary, checking platform-specific locations."""
    candidates = [
        SCAFFOLD / "imgui" / "build" / "Release" / "terragraf_imgui.exe",
        SCAFFOLD / "imgui" / "build" / "terragraf_imgui.exe",
        SCAFFOLD / "imgui" / "build" / "terragraf_imgui",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

# ── viz ─────────────────────────────────────────────────────────────

def cmd_viz(args):
    if not args:
        _print_viz_help()
        return
    action = args[0]

    viz_info = {
        "spectrogram": ("viz.spectrogram", "render spectrogram from signal", ".scaffold/viz/spectrogram.py"),
        "heatmap": ("viz.heatmap", "render 2D data as heatmap", ".scaffold/viz/heatmap.py"),
        "stream": ("viz.stream", "real-time scrolling line chart", ".scaffold/viz/stream.py"),
    }

    if action in viz_info:
        name, desc, path = viz_info[action]
        print(f"  {CYAN}{name}{RESET} — {desc}")
        print(f"  {DIM}see {path}{RESET}")
    elif action == "3d":
        sub = args[1] if len(args) > 1 else "help"
        viz3d = {
            "nodes": ("viz.3d.nodes", "3D node graph", ".scaffold/viz/3d/nodes.py"),
            "mesh": ("viz.3d.mesh", "3D mesh/surface", ".scaffold/viz/3d/mesh.py"),
            "volume": ("viz.3d.volume", "volumetric rendering", ".scaffold/viz/3d/volume.py"),
        }
        if sub in viz3d:
            name, desc, path = viz3d[sub]
            print(f"  {CYAN}{name}{RESET} — {desc}")
            print(f"  {DIM}see {path}{RESET}")
        else:
            print(f"  {BOLD}terra viz 3d{RESET}")
            for k, (_, desc, _) in viz3d.items():
                print(f"    {CYAN}{k}{RESET}    {desc}")
    else:
        _print_viz_help()

def _print_viz_help():
    print(f"  {BOLD}terra viz{RESET}")
    print(f"    {CYAN}spectrogram{RESET}  render spectrogram")
    print(f"    {CYAN}heatmap{RESET}      render 2D heatmap")
    print(f"    {CYAN}stream{RESET}       real-time data plotter")
    print(f"    {CYAN}3d{RESET}           3D visualization")

# ── math ───────────���──────────────────────────��─────────────────────

def cmd_math(args):
    if not args:
        _print_math_help()
        return
    action = args[0]

    if action == "eval":
        expr = " ".join(args[1:])
        if not expr:
            print("Usage: terra math eval <expression>")
            return
        subprocess.run([sys.executable, "-c",
                        f"import numpy as np; print(eval({expr!r}))"])
    elif action == "linalg":
        op = args[1] if len(args) > 1 else "help"
        print(f"  {CYAN}linalg.{op}{RESET} — see .scaffold/compute/math/linalg.py")
        print(f"  {DIM}import: from scaffold.compute.math import linalg{RESET}")
    elif action == "stats":
        op = args[1] if len(args) > 1 else "describe"
        print(f"  {CYAN}stats.{op}{RESET} — see .scaffold/compute/math/stats.py")
        print(f"  {DIM}import: from scaffold.compute.math import stats{RESET}")
    else:
        _print_math_help()

def _print_math_help():
    print(f"  {BOLD}terra math{RESET}")
    print(f"    {CYAN}eval{RESET} <expr>     evaluate a math expression")
    print(f"    {CYAN}linalg{RESET} <op>     linear algebra operation info")
    print(f"    {CYAN}stats{RESET} [op]      statistics operation info")

# ── sharpen ──��────────────────────────��─────────────────────────────

def cmd_sharpen(args):
    action = args[0] if args else "status"
    subprocess.run([sys.executable, str(SCAFFOLD / "sharpen" / "cli.py"), action] + args[1:])

# ── tune ─────────���──────────────────────────────────────────────────

def cmd_tune(args):
    action = args[0] if args else "status"
    subprocess.run([sys.executable, str(SCAFFOLD / "tuning" / "cli.py"), action] + args[1:])

# ── mode ────────────────────────────────────────────────────────────

def cmd_mode(args):
    action = args[0] if args else "show"

    sys.path.insert(0, str(SCAFFOLD))
    from modes.detector import detect

    if action == "show":
        info = detect()
        print(f"  mode     {BOLD}{info.mode.value}{RESET}")
        print(f"  source   {info.source}")
        print()
        if info.is_ci:
            print(f"  {YELLOW}CI mode — headless, tests/lint only{RESET}")
            print("  Blocked systems:")
            for s in sorted(info.blocked):
                print(f"    {RED}✗{RESET} {s}")
        else:
            print(f"  {GREEN}App mode — full interactive access{RESET}")
        print()
        print("  Capabilities:")
        for c in sorted(info.capabilities):
            print(f"    {GREEN}✓{RESET} {c}")

    elif action == "check":
        info = detect()
        sys.exit(0 if info.is_app else 1)

    elif action == "can":
        if len(args) < 2:
            print("Usage: terra mode can <capability>")
            return
        cap = args[1]
        info = detect()
        if info.can(cap):
            print(f"  {GREEN}✓{RESET} {cap} is available in {info.mode.value} mode")
            sys.exit(0)
        else:
            print(f"  {RED}✗{RESET} {cap} is not available in {info.mode.value} mode")
            sys.exit(1)

    else:
        print(f"  {BOLD}terra mode{RESET}")
        print(f"    {CYAN}show{RESET}           display current mode and capabilities")
        print(f"    {CYAN}check{RESET}          exit 0 if app mode, exit 1 if CI")
        print(f"    {CYAN}can{RESET} <cap>      check if a capability is available")

# ── app ─���──────────────────────────���────────────────────────────────

def cmd_app(args):
    try:
        import PySide6
    except ImportError:
        print(f"{YELLOW}PySide6 not installed.{RESET}")
        print("  pip install -r requirements-app.txt")
        sys.exit(1)

    subprocess.run([sys.executable, "-m", "app.main"] + args, cwd=str(SCAFFOLD))

# ── skill shortcuts ──────────────────────────────────────────────

def _run_skill(name, args):
    """Helper: run a skill and exit with its return code."""
    sys.path.insert(0, str(SCAFFOLD))
    from skills.runner import run_skill
    sys.exit(run_skill(name, args))

def cmd_hot(args):
    _run_skill("hot_context", args)

def cmd_analyze(args):
    _run_skill("signal_analyze", args)

def cmd_solve(args):
    _run_skill("math_solve", args)

def cmd_branch(args):
    _run_skill("git_flow", ["branch"] + args)

def cmd_commit(args):
    _run_skill("git_flow", ["commit"] + args)

def cmd_pr(args):
    _run_skill("git_flow", ["pr"] + args)

def cmd_generate(args):
    _run_skill("generate", args)

def cmd_train(args):
    _run_skill("train_model", args)

def cmd_viewer(args):
    _run_skill("viewer", args)

def cmd_render(args):
    _run_skill("render_3d", args)

def cmd_test(args):
    _run_skill("test_suite", args)

def cmd_dispatch(args):
    _run_skill("instance_dispatch", args)

def cmd_health(args):
    _run_skill("health_check", args)

# ── skill ─────────────────────────────────────────────────────────

def cmd_skill(args):
    if not args:
        print("Usage: terra skill <list|run <name> [args...]>")
        return

    action = args[0]

    sys.path.insert(0, str(SCAFFOLD))
    from skills.runner import print_skills, run_skill, list_skills

    if action == "list":
        print(f"{BOLD}Skills{RESET}")
        print()
        print_skills()

    elif action == "run":
        if len(args) < 2:
            print("Usage: terra skill run <name> [args...]")
            return
        name = args[1]
        rest = args[2:]
        code = run_skill(name, rest)
        sys.exit(code)

    else:
        print(f"  {RED}unknown skill action: {action}{RESET}")
        print("Usage: terra skill <list|run <name>>")

# ── project ───────────────────────────────────────────────────────

def cmd_project(args):
    if not args:
        print("Usage: terra project new <name> [--type qt-app|cli|lib|test]")
        return

    action = args[0]

    if action == "new":
        # Delegate to scaffold_project skill
        rest = args[1:]
        sys.path.insert(0, str(SCAFFOLD))
        from skills.runner import run_skill
        code = run_skill("scaffold_project", rest)
        sys.exit(code)
    else:
        print(f"  {RED}unknown project action: {action}{RESET}")
        print("Usage: terra project new <name> [--type qt-app|cli|lib|test]")

# ── help ──────���─────────────────────────────────────────────────────

def cmd_help():
    print(f"{BOLD}terra{RESET} — Terragraf commands")
    print()
    print(f"  {CYAN}terra init{RESET}               wire hooks, check env")
    print(f"  {CYAN}terra status{RESET}             what's here, what works")
    print(f"  {CYAN}terra route{RESET} <intent>     where do I go for this?")
    print(f"  {CYAN}terra lookup{RESET} <error>     known fix for this error?")
    print(f"  {CYAN}terra pattern{RESET} [name]     what pattern fits here?")
    print(f"  {CYAN}terra dep{RESET} [module]       what depends on what?")
    print(f"  {CYAN}terra gen{RESET} <type> <name>  generate module/model/shader")
    print(f"  {CYAN}terra hook{RESET} <name>        run a lifecycle hook")
    print(f"  {CYAN}terra queue{RESET}              show task queue")
    print(f"  {CYAN}terra queue add{RESET} <task>   add task to queue")
    print(f"  {CYAN}terra imgui{RESET} <action>     ImGui real-time viewer")
    print(f"  {CYAN}terra viz{RESET} <action>       visualization")
    print(f"  {CYAN}terra math{RESET} <action>      math operations")
    print(f"  {CYAN}terra sharpen{RESET} [action]   self-sharpening analytics")
    print(f"  {CYAN}terra tune{RESET} [action]      thematic calibration")
    print(f"  {CYAN}terra mode{RESET} [action]      detect CI vs App mode")
    print(f"  {CYAN}terra analyze{RESET} <input>     signal/audio analysis (FFT, spectrogram)")
    print(f"  {CYAN}terra solve{RESET} <op> [opts]   math: eigenvalues, svd, fit, stats, dct")
    print(f"  {CYAN}terra branch{RESET} <type> <n>   create conventional branch")
    print(f"  {CYAN}terra commit{RESET} <msg>        structured commit (--auto for AI)")
    print(f"  {CYAN}terra pr{RESET} [--preview]      PR template/preview")
    print(f"  {CYAN}terra generate{RESET} <type> <n> generate module/model/shader")
    print(f"  {CYAN}terra train{RESET} <dir> [opts]  ML training pipeline")
    print(f"  {CYAN}terra viewer{RESET} [action]     ImGui viewer lifecycle")
    print(f"  {CYAN}terra render{RESET} <type> <in>  3D visualization (surface/volume/nodes)")
    print(f"  {CYAN}terra test{RESET} [module]       run test suite")
    print(f"  {CYAN}terra dispatch{RESET} <task>     parallel instance orchestration")
    print(f"  {CYAN}terra health{RESET} [--quick]    system diagnostic (grade A-F)")
    print(f"  {CYAN}terra hot{RESET} [action]        session hot context")
    print(f"  {CYAN}terra skill{RESET} <action>      skill system (list, run)")
    print(f"  {CYAN}terra project{RESET} new <n>     scaffold a new project")
    print(f"  {CYAN}terra app{RESET}                 Qt container app")
    print(f"  {CYAN}terra help{RESET}                this")
    print()
    print(f"  {DIM}Skills:  .scaffold/skills/ (15 registered){RESET}")
    print(f"  {DIM}Routes:  .scaffold/routes/*.route{RESET}")
    print(f"  {DIM}Tables:  .scaffold/tables/*.table{RESET}")
    print(f"  {DIM}Headers: .scaffold/headers/*.h{RESET}")

# ── Dispatch ───────────────��────────────────────────────────────────

COMMANDS = {
    "init": lambda args: cmd_init(),
    "status": lambda args: cmd_status(),
    "route": cmd_route,
    "lookup": cmd_lookup,
    "pattern": cmd_pattern,
    "dep": cmd_dep,
    "gen": cmd_gen,
    "hook": cmd_hook,
    "queue": cmd_queue,
    "imgui": cmd_imgui,
    "viz": cmd_viz,
    "math": cmd_math,
    "sharpen": cmd_sharpen,
    "tune": cmd_tune,
    "mode": cmd_mode,
    "hot": cmd_hot,
    "analyze": cmd_analyze,
    "solve": cmd_solve,
    "branch": cmd_branch,
    "commit": cmd_commit,
    "pr": cmd_pr,
    "generate": cmd_generate,
    "train": cmd_train,
    "viewer": cmd_viewer,
    "render": cmd_render,
    "test": cmd_test,
    "dispatch": cmd_dispatch,
    "health": cmd_health,
    "skill": cmd_skill,
    "project": cmd_project,
    "app": cmd_app,
    "help": lambda args: cmd_help(),
    "-h": lambda args: cmd_help(),
    "--help": lambda args: cmd_help(),
}

def main():
    args = sys.argv[1:]
    if not args:
        cmd_help()
        return

    cmd = args[0]
    rest = args[1:]

    handler = COMMANDS.get(cmd)
    if handler:
        handler(rest)
    else:
        print(f"  {RED}unknown command: {cmd}{RESET}")
        print()
        cmd_help()

if __name__ == "__main__":
    main()
