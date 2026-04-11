"""
graphify — Build and query a knowledge graph of the codebase.

Thin shim over the upstream ``graphifyy`` PyPI package. Delegates to
``python -m graphify`` with the correct cwd, forwarding stdout/stderr
and returning the upstream exit code.

Usage:
    terra graphify .                  # build graph of current dir
    terra graphify query "..."        # query the knowledge graph
    terra graphify path A B           # find path between nodes
    terra graphify explain <id>       # explain a node or edge
"""

import os
import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCAFFOLD))

# ANSI
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

# graphify-out/ lands relative to cwd (the repo root).
TERRA_ROOT = SCAFFOLD.parent


def _check_llm_provider():
    """Warn if no LLM provider env vars are configured."""
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    if not has_anthropic and not has_openai:
        print(
            f"{YELLOW}[graphify]{RESET} No LLM provider configured "
            f"(ANTHROPIC_API_KEY / OPENAI_API_KEY).\n"
            f"  Phase 2 extraction (docs, images) will be skipped.\n"
            f"  AST-only graph will still be built.",
            file=sys.stderr,
        )


def cli():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(f"""{BOLD}terra graphify{RESET} — knowledge graph builder

{CYAN}Usage:{RESET}
  terra graphify .                  Build graph of current directory
  terra graphify query "..."        Query the knowledge graph
  terra graphify path A B           Find path between two nodes
  terra graphify explain <id>       Explain a node or edge

{DIM}Powered by graphifyy (MIT, Safi Shamsi 2026).
Output lands in graphify-out/ relative to the working directory.{RESET}""")
        return 0

    _check_llm_provider()

    cmd = [sys.executable, "-m", "graphify"] + args

    # Pass --platform windows on win32 per upstream docs.
    if sys.platform == "win32" and "--platform" not in args:
        cmd.append("--platform")
        cmd.append("windows")

    result = subprocess.run(cmd, cwd=str(TERRA_ROOT))
    return result.returncode


if __name__ == "__main__":
    sys.exit(cli())
