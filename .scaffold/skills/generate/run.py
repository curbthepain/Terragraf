"""
generate — Unified code generation workflow.

Combines module, model, and shader generators with language detection
and post-generation consistency validation.

Usage:
    python run.py module <name> [--lang python|cpp|js]
    python run.py model <name> [--arch cnn|transformer|base]
    python run.py shader <name> [--type compute|volume|fft]
"""

import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
TERRA_ROOT = SCAFFOLD.parent

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def detect_lang():
    """Auto-detect project language."""
    try:
        sys.path.insert(0, str(SCAFFOLD))
        from generators.lang_detect import detect_language
        info = detect_language(TERRA_ROOT)
        return info.primary if info.primary != "unknown" else "python"
    except Exception:
        return "python"


def gen_module(args):
    import argparse
    parser = argparse.ArgumentParser(prog="terra generate module")
    parser.add_argument("name", help="Module name")
    parser.add_argument("--lang", help="Language (auto-detected if omitted)")
    parsed = parser.parse_args(args)

    lang = parsed.lang or detect_lang()
    print(f"  {CYAN}Generating module{RESET} {parsed.name} ({lang})")

    # Delegate to terra.py gen module
    cmd = [sys.executable, str(TERRA_ROOT / "terra.py"), "gen", "module", parsed.name, "--lang", lang]
    code = subprocess.run(cmd).returncode

    if code == 0:
        # Post-gen validation
        print()
        print(f"  {DIM}Running consistency check...{RESET}")
        scan = SCAFFOLD / "skills" / "consistency_scan" / "run.py"
        subprocess.run([sys.executable, str(scan)], capture_output=True)
        print(f"  {GREEN}Done{RESET}")
    return code


def gen_model(args):
    import argparse
    parser = argparse.ArgumentParser(prog="terra generate model")
    parser.add_argument("name", help="Model name")
    parser.add_argument("--arch", default="base",
                        choices=["base", "cnn", "transformer", "classifier"],
                        help="Model architecture")
    parser.add_argument("--num-classes", type=int, default=10)
    parser.add_argument("--output", "-o", help="Output path")
    parsed = parser.parse_args(args)

    print(f"  {CYAN}Generating model{RESET} {parsed.name} (arch: {parsed.arch})")

    cmd = [sys.executable, str(SCAFFOLD / "generators" / "gen_model.py"),
           "--name", parsed.name, "--base", parsed.arch,
           "--num-classes", str(parsed.num_classes)]
    if parsed.output:
        cmd.extend(["--output", parsed.output])
    return subprocess.run(cmd).returncode


def gen_shader(args):
    import argparse
    parser = argparse.ArgumentParser(prog="terra generate shader")
    parser.add_argument("name", help="Shader name")
    parser.add_argument("--type", default="compute",
                        choices=["compute", "volume", "fft"],
                        help="Shader type")
    parser.add_argument("--workgroup", type=int, default=256)
    parser.add_argument("--buffers", type=int, default=2)
    parsed = parser.parse_args(args)

    print(f"  {CYAN}Generating shader{RESET} {parsed.name} (type: {parsed.type})")

    cmd = [sys.executable, str(SCAFFOLD / "generators" / "gen_shader.py"),
           "--name", parsed.name, "--workgroup", str(parsed.workgroup),
           "--buffers", str(parsed.buffers)]
    return subprocess.run(cmd).returncode


def cli():
    if len(sys.argv) < 2:
        print(f"{BOLD}terra generate{RESET}")
        print(f"  {CYAN}module{RESET} <name> [--lang L]         generate code module")
        print(f"  {CYAN}model{RESET} <name> [--arch A]           generate ML model")
        print(f"  {CYAN}shader{RESET} <name> [--type T]          generate GLSL shader")
        return 0

    what = sys.argv[1]
    rest = sys.argv[2:]

    if what == "module":
        return gen_module(rest)
    elif what == "model":
        return gen_model(rest)
    elif what == "shader":
        return gen_shader(rest)
    else:
        print(f"  {RED}Unknown: {what}. Use: module, model, shader{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(cli())
