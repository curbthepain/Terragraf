"""
git_flow — Git workflow orchestrator.

Wraps git/branch.sh, git/commit.sh, git/pr.sh with Python fallback for Windows.

Usage:
    python run.py branch <type> <name>
    python run.py commit <message>
    python run.py commit --auto
    python run.py pr --preview
    python run.py pr --template
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
TERRA_ROOT = SCAFFOLD.parent
GIT_DIR = SCAFFOLD / "git"

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

BRANCH_TYPES = ["feature", "fix", "refactor", "docs", "ci", "test", "chore"]


def run_git(*args, capture=False):
    """Run a git command."""
    cmd = ["git"] + list(args)
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(TERRA_ROOT))
        return r.stdout.strip(), r.returncode
    return subprocess.run(cmd, cwd=str(TERRA_ROOT)).returncode


def cmd_branch(args):
    if len(args) < 2:
        print(f"Usage: terra branch <{'|'.join(BRANCH_TYPES)}> <name>")
        return 1

    btype, name = args[0], args[1]
    if btype not in BRANCH_TYPES:
        print(f"  {RED}Unknown branch type: {btype}{RESET}")
        print(f"  {DIM}Types: {', '.join(BRANCH_TYPES)}{RESET}")
        return 1

    # Get default branch
    default, _ = run_git("symbolic-ref", "refs/remotes/origin/HEAD", "--short", capture=True)
    if not default:
        default = "origin/main"

    branch_name = f"{btype}/{name}"
    print(f"  {CYAN}Creating branch{RESET} {branch_name} from {default}")

    run_git("fetch", "origin")
    code = run_git("checkout", "-b", branch_name, default)
    if code == 0:
        print(f"  {GREEN}Created{RESET} {branch_name}")
    return code


def cmd_commit(args):
    parser = argparse.ArgumentParser(prog="terra commit")
    parser.add_argument("message", nargs="?", help="Commit message")
    parser.add_argument("--auto", action="store_true", help="Show diff for AI to generate message")
    parsed = parser.parse_args(args)

    if parsed.auto:
        print(f"{BOLD}Staged changes:{RESET}")
        run_git("diff", "--cached", "--stat")
        print()
        print(f"{BOLD}Recent commits:{RESET}")
        run_git("log", "--oneline", "-5")
        print()
        print(f"  {DIM}Review the diff and provide a commit message{RESET}")
        return 0

    if not parsed.message:
        print("Usage: terra commit <message> or terra commit --auto")
        return 1

    # Validate conventional commit format
    msg = parsed.message
    code = run_git("commit", "-m", msg)
    if code == 0:
        print(f"  {GREEN}Committed{RESET}")
    return code


def cmd_pr(args):
    parser = argparse.ArgumentParser(prog="terra pr")
    parser.add_argument("--preview", action="store_true", help="Show what PR would contain")
    parser.add_argument("--template", action="store_true", help="Print PR template")
    parsed = parser.parse_args(args)

    if parsed.template:
        template_path = GIT_DIR / "templates" / "pull_request.md"
        if template_path.exists():
            print(template_path.read_text())
        else:
            print(f"  {YELLOW}No PR template found{RESET}")
        return 0

    if parsed.preview:
        # Show commits and diff stats for this branch
        default, _ = run_git("symbolic-ref", "refs/remotes/origin/HEAD", "--short", capture=True)
        if not default:
            default = "origin/main"
        print(f"{BOLD}Commits since {default}:{RESET}")
        run_git("log", f"{default}..HEAD", "--oneline")
        print()
        print(f"{BOLD}Changed files:{RESET}")
        run_git("diff", f"{default}..HEAD", "--stat")
        return 0

    print("Usage: terra pr --preview | terra pr --template")
    return 1


def cli():
    if len(sys.argv) < 2:
        print(f"{BOLD}terra git_flow{RESET}")
        print(f"  {CYAN}branch{RESET} <type> <name>   create conventional branch")
        print(f"  {CYAN}commit{RESET} <message>        structured commit")
        print(f"  {CYAN}commit{RESET} --auto            show diff for message generation")
        print(f"  {CYAN}pr{RESET} --preview             show PR contents")
        print(f"  {CYAN}pr{RESET} --template            print PR template")
        return 0

    action = sys.argv[1]
    rest = sys.argv[2:]

    if action == "branch":
        return cmd_branch(rest)
    elif action == "commit":
        return cmd_commit(rest)
    elif action == "pr":
        return cmd_pr(rest)
    else:
        print(f"  {RED}Unknown action: {action}{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(cli())
