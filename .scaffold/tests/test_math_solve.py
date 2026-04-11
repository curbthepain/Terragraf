"""Integration tests for .scaffold/skills/math_solve — math computation router."""

import subprocess
import sys
from pathlib import Path

import pytest

SCAFFOLD = Path(__file__).parent.parent
SKILL_DIR = SCAFFOLD / "skills" / "math_solve"
RUN_PY = SKILL_DIR / "run.py"


def run_solve(*args):
    """Run math_solve skill as subprocess, return CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(RUN_PY)] + list(args),
        capture_output=True, text=True, cwd=str(SCAFFOLD.parent),
    )


class TestEigenvalues:
    def test_2x2_matrix(self):
        result = run_solve("eigenvalues", "--matrix", "[[1,2],[3,4]]")
        assert result.returncode == 0
        assert "Eigenvalues" in result.stdout
        # Known eigenvalues: ~-0.372 and ~5.372
        assert "-0.37" in result.stdout or "-0.372" in result.stdout
        assert "5.37" in result.stdout or "5.372" in result.stdout

    def test_identity_matrix(self):
        result = run_solve("eigenvalues", "--matrix", "[[1,0],[0,1]]")
        assert result.returncode == 0
        assert "1" in result.stdout


class TestSVD:
    def test_basic(self):
        result = run_solve("svd", "--matrix", "[[1,2],[3,4]]")
        assert result.returncode == 0
        assert "SVD" in result.stdout
        assert "singular" in result.stdout.lower()


class TestSolve:
    def test_2x2_system(self):
        result = run_solve("solve", "--A", "[[1,0],[0,1]]", "--b", "[3,4]")
        assert result.returncode == 0
        assert "3" in result.stdout
        assert "4" in result.stdout


class TestPolynomialRoots:
    def test_quadratic(self):
        # x^2 - 4 = 0 → roots at -2, 2
        result = run_solve("roots", "--coeffs", "[1,0,-4]")
        assert result.returncode == 0
        assert "2" in result.stdout


class TestDescriptiveStats:
    def test_basic(self):
        result = run_solve("describe", "--data", "[1,2,3,4,5,6,7,8,9,10]")
        assert result.returncode == 0
        assert "mean" in result.stdout.lower() or "5.5" in result.stdout


class TestRegression:
    def test_linear(self):
        result = run_solve("regression", "--x", "[1,2,3,4,5]", "--y", "[2,4,6,8,10]")
        assert result.returncode == 0
        assert "R" in result.stdout  # R^2


class TestTTest:
    def test_two_samples(self):
        result = run_solve("ttest", "--a", "[1,2,3,4,5]", "--b", "[2,3,4,5,6]")
        assert result.returncode == 0
        assert "t-statistic" in result.stdout.lower() or "t-Test" in result.stdout


class TestTransforms:
    def test_dct(self):
        result = run_solve("dct", "--signal", "[1,2,3,4]")
        assert result.returncode == 0
        assert "DCT" in result.stdout

    def test_hilbert(self):
        result = run_solve("hilbert", "--signal", "[1,0,-1,0,1,0,-1,0]")
        assert result.returncode == 0
        assert "Hilbert" in result.stdout


class TestErrorHandling:
    def test_invalid_operation(self):
        result = run_solve("nonexistent_op")
        assert result.returncode != 0

    def test_missing_matrix(self):
        result = run_solve("eigenvalues")
        assert result.returncode != 0
