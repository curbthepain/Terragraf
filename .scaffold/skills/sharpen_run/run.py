"""
sharpen_run — Self-sharpening with validation feedback loop.

Delegates to the existing sharpen CLI and adds post-sharpen consistency
validation via consistency_scan.

Usage:
    python run.py [status|run|reset|report] [--dry-run]
"""

import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
TERRA_ROOT = SCAFFOLD.parent

BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


def cli():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    rest = sys.argv[2:]

    if action == "report":
        # Full report: sharpen status + consistency scan
        print(f"{BOLD}Sharpen Report{RESET}")
        print()
        subprocess.run([sys.executable, str(SCAFFOLD / "sharpen" / "cli.py"), "status"])
        print()
        print(f"{BOLD}Consistency Validation{RESET}")
        print()
        subprocess.run([sys.executable, str(SCAFFOLD / "skills" / "consistency_scan" / "run.py")])
        return 0

    # Delegate to sharpen CLI
    code = subprocess.run(
        [sys.executable, str(SCAFFOLD / "sharpen" / "cli.py"), action] + rest
    ).returncode

    # Post-sharpen validation if we actually applied changes
    if action == "run" and "--dry-run" not in rest and code == 0:
        print()
        print(f"  {DIM}Post-sharpen validation...{RESET}")
        subprocess.run(
            [sys.executable, str(SCAFFOLD / "skills" / "consistency_scan" / "run.py")],
            capture_output=True,
        )
        print(f"  {GREEN}Validation complete{RESET}")

    return code


if __name__ == "__main__":
    sys.exit(cli())
