"""
health_check — Full system diagnostic.

Composes consistency_scan, test results, sharpen analytics, mode detection,
and queue status into a graded health report.

Usage:
    python run.py [--quick] [--json]
"""

import json
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


def check_structure():
    """Run consistency_scan and count issues."""
    result = subprocess.run(
        [sys.executable, str(SCAFFOLD / "skills" / "consistency_scan" / "run.py")],
        capture_output=True, text=True,
    )
    # Count "!" lines as issues
    issues = sum(1 for line in result.stdout.splitlines() if "!" in line)
    return issues


def check_tests_quick():
    """Quick test check — just verify pytest can collect without errors."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(SCAFFOLD / "tests"), "--collect-only", "-q"],
        capture_output=True, text=True, cwd=str(TERRA_ROOT),
    )
    # Parse "N tests collected"
    import re
    m = re.search(r"(\d+) test", result.stdout)
    count = int(m.group(1)) if m else 0
    return count, result.returncode == 0


def check_environment():
    """Check runtimes and tools."""
    import shutil
    import platform
    checks = {
        "python": platform.python_version(),
        "git": "yes" if shutil.which("git") else "no",
        "cmake": "yes" if shutil.which("cmake") else "no",
        "node": "yes" if shutil.which("node") else "no",
    }
    return checks


def check_mode():
    """Detect current mode."""
    try:
        sys.path.insert(0, str(SCAFFOLD))
        from modes.detector import detect
        info = detect()
        return info.mode.value, len(info.capabilities)
    except Exception:
        return "unknown", 0


def check_skills():
    """Count registered skills."""
    sys.path.insert(0, str(SCAFFOLD))
    from skills.runner import list_skills
    return len(list_skills())


def check_queue():
    """Check queue status."""
    queue_file = SCAFFOLD / "instances" / "shared" / "queue.json"
    results_file = SCAFFOLD / "instances" / "shared" / "results.json"
    pending = 0
    completed = 0
    if queue_file.exists():
        data = json.loads(queue_file.read_text())
        if isinstance(data, list):
            pending = sum(1 for t in data if t.get("status") == "pending")
    if results_file.exists():
        results = json.loads(results_file.read_text())
        completed = len(results)
    return pending, completed


def grade(structure_issues, tests_ok, env):
    """Compute health grade A-F."""
    score = 100
    score -= min(structure_issues * 2, 30)  # Max -30 for structure issues
    if not tests_ok:
        score -= 30
    if env.get("git") == "no":
        score -= 10
    if env.get("cmake") == "no":
        score -= 5

    if score >= 90:
        return "A", GREEN
    elif score >= 80:
        return "B", GREEN
    elif score >= 70:
        return "C", YELLOW
    elif score >= 60:
        return "D", YELLOW
    else:
        return "F", RED


def cli():
    quick = "--quick" in sys.argv
    as_json = "--json" in sys.argv

    report = {}

    # Environment
    env = check_environment()
    report["environment"] = env

    # Mode
    mode, capabilities = check_mode()
    report["mode"] = mode
    report["capabilities"] = capabilities

    # Skills
    n_skills = check_skills()
    report["skills"] = n_skills

    # Structure
    structure_issues = check_structure()
    report["structure_issues"] = structure_issues

    # Tests (quick = collection only)
    test_count, tests_ok = check_tests_quick()
    report["test_count"] = test_count
    report["tests_collectable"] = tests_ok

    # Queue
    pending, completed = check_queue()
    report["queue_pending"] = pending
    report["queue_completed"] = completed

    # Grade
    g, color = grade(structure_issues, tests_ok, env)
    report["grade"] = g

    if as_json:
        print(json.dumps(report, indent=2))
        return 0

    # Pretty print
    print(f"{BOLD}System Health{RESET}")
    print()

    print(f"  {BOLD}Grade:  {color}{g}{RESET}")
    print()

    print(f"  {BOLD}Environment{RESET}")
    for k, v in env.items():
        c = GREEN if v not in ("no", "unknown") else YELLOW
        print(f"    {k:<10} {c}{v}{RESET}")
    print(f"    mode       {mode} ({capabilities} capabilities)")
    print()

    print(f"  {BOLD}Scaffold{RESET}")
    print(f"    skills     {GREEN}{n_skills}{RESET} registered")
    sc = GREEN if structure_issues == 0 else YELLOW
    print(f"    structure  {sc}{structure_issues}{RESET} issues")
    tc = GREEN if tests_ok else RED
    print(f"    tests      {tc}{test_count}{RESET} discoverable")
    print()

    print(f"  {BOLD}Queue{RESET}")
    print(f"    pending    {pending}")
    print(f"    completed  {completed}")

    return 0


if __name__ == "__main__":
    sys.exit(cli())
