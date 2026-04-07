"""
test_suite — Test orchestration workflow.

Discovers and runs all .scaffold/tests/, categorizes by subsystem,
respects CI mode, produces summary report.

Usage:
    python run.py [module] [--ci] [--report] [--verbose]
"""

import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
TERRA_ROOT = SCAFFOLD.parent
TESTS_DIR = SCAFFOLD / "tests"

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

# Test file → subsystem mapping
SUBSYSTEMS = {
    "test_algebra": "math",
    "test_linalg": "math",
    "test_stats": "math",
    "test_transforms": "math",
    "test_fft": "fft",
    "test_spectral": "fft",
    "test_tuning": "tuning",
    "test_transport": "instances",
    "test_app": "app",
    "test_app_host": "app",
    "test_modes": "modes",
    "test_generators": "generators",
    "test_lang_detect": "generators",
    "test_sharpen": "sharpen",
    "test_viz": "viz",
    "test_viz3d": "viz",
}

# GUI tests to skip in CI
CI_SKIP = {"test_app"}


def discover_tests():
    """Find all test files, grouped by subsystem."""
    tests = {}
    for f in sorted(TESTS_DIR.glob("test_*.py")):
        name = f.stem
        subsystem = SUBSYSTEMS.get(name, "other")
        tests.setdefault(subsystem, []).append(f)
    return tests


def run_tests(files, verbose=False):
    """Run pytest on given files, return (passed, failed, total)."""
    cmd = [sys.executable, "-m", "pytest"] + [str(f) for f in files]
    cmd += ["-q", "--tb=short"]
    if verbose:
        cmd.append("-v")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(TERRA_ROOT))
    output = result.stdout + result.stderr

    # Parse results from pytest output
    passed = failed = 0
    for line in output.splitlines():
        if "passed" in line:
            import re
            m = re.search(r"(\d+) passed", line)
            if m:
                passed = int(m.group(1))
            m = re.search(r"(\d+) failed", line)
            if m:
                failed = int(m.group(1))

    return passed, failed, passed + failed, result.returncode, output


def cli():
    module = None
    ci_mode = "--ci" in sys.argv
    report = "--report" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    # Find module arg (first arg that isn't a flag)
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            module = arg
            break

    tests = discover_tests()

    if module:
        # Run specific subsystem
        if module not in tests:
            available = ", ".join(sorted(tests.keys()))
            print(f"  {RED}Unknown module: {module}{RESET}")
            print(f"  {DIM}Available: {available}{RESET}")
            return 1
        files = tests[module]
        print(f"{BOLD}Running {module} tests{RESET} ({len(files)} file(s))")
        passed, failed, total, code, output = run_tests(files, verbose)
        color = GREEN if failed == 0 else RED
        print(f"  {color}{passed} passed, {failed} failed{RESET} ({total} total)")
        if verbose or failed > 0:
            print(output)
        return code

    # Run all
    print(f"{BOLD}Test Suite{RESET}")
    print()

    total_passed = total_failed = 0
    results = {}

    for subsystem in sorted(tests.keys()):
        files = tests[subsystem]
        if ci_mode and any(f.stem in CI_SKIP for f in files):
            files = [f for f in files if f.stem not in CI_SKIP]
            if not files:
                print(f"  {DIM}{subsystem:<14} skipped (CI){RESET}")
                continue

        passed, failed, total, code, output = run_tests(files)
        total_passed += passed
        total_failed += failed
        results[subsystem] = (passed, failed, total)

        color = GREEN if failed == 0 else RED
        print(f"  {color}{subsystem:<14}{RESET} {passed:>3} passed  {failed:>3} failed")

    print()
    total = total_passed + total_failed
    color = GREEN if total_failed == 0 else RED
    print(f"  {color}{BOLD}{total_passed} passed, {total_failed} failed{RESET} ({total} total)")

    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(cli())
