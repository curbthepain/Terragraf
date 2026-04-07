"""
math_solve — Math computation router.

Routes problems to the correct compute module: linalg, algebra, stats, transforms.

Usage:
    python run.py <operation> [options]

Operations:
    eigenvalues --matrix "[[1,2],[3,4]]"
    svd --matrix "[[1,2],[3,4]]"
    solve --A "[[1,2],[3,4]]" --b "[5,6]"
    fit --x "[1,2,3,4]" --y "[2,5,10,17]" --degree 2
    roots --coeffs "[1,0,-4]"
    describe --data "[1,2,3,4,5,6,7,8,9,10]"
    regression --x "[1,2,3,4,5]" --y "[2.1,4.0,5.9,8.1,10.0]"
    ttest --a "[1,2,3,4,5]" --b "[2,3,4,5,6]"
    dct --signal "[1,2,3,4]"
    hilbert --signal "[1,0,-1,0,1,0,-1,0]"
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCAFFOLD))

from compute.math.linalg import (
    mat_mul, mat_inv, determinant, eigenvalues, eigenvectors,
    svd, lu_decompose, solve, norm, rank,
)
from compute.math.algebra import poly_eval, poly_roots, curve_fit_poly, interpolate
from compute.math.stats import (
    descriptive, correlation, linear_regression, t_test, chi_squared,
    percentile, zscore,
)
from compute.math.transforms import dct, idct, hilbert, wavelet_transform

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def parse_array(s):
    """Parse a JSON array string into numpy array."""
    return np.array(json.loads(s), dtype=float)


def fmt_array(a, precision=6):
    """Format array for display."""
    if a.ndim == 1:
        return "[" + ", ".join(f"{x:.{precision}g}" for x in a) + "]"
    return "\n".join("  " + fmt_array(row, precision) for row in a)


def op_eigenvalues(args):
    m = parse_array(args.matrix)
    vals = eigenvalues(m)
    print(f"{BOLD}Eigenvalues{RESET}")
    print(f"  {fmt_array(vals)}")


def op_eigenvectors(args):
    m = parse_array(args.matrix)
    vals, vecs = eigenvectors(m)
    print(f"{BOLD}Eigendecomposition{RESET}")
    print(f"  values:  {fmt_array(vals)}")
    print(f"  vectors:")
    print(f"{fmt_array(vecs)}")


def op_svd(args):
    m = parse_array(args.matrix)
    U, S, Vt = svd(m)
    print(f"{BOLD}SVD{RESET}")
    print(f"  S (singular values): {fmt_array(S)}")
    print(f"  rank: {np.sum(S > 1e-10)}")


def op_solve(args):
    A = parse_array(args.A)
    b = parse_array(args.b)
    x = solve(A, b)
    print(f"{BOLD}Solve Ax = b{RESET}")
    print(f"  x = {fmt_array(x)}")
    residual = np.linalg.norm(A @ x - b)
    print(f"  residual: {residual:.2e}")


def op_inverse(args):
    m = parse_array(args.matrix)
    inv = mat_inv(m)
    print(f"{BOLD}Matrix Inverse{RESET}")
    print(fmt_array(inv))
    print(f"  det: {determinant(m):.6g}")


def op_fit(args):
    x = parse_array(args.x)
    y = parse_array(args.y)
    degree = args.degree or 2
    coeffs = curve_fit_poly(x, y, degree)
    print(f"{BOLD}Polynomial Fit (degree {degree}){RESET}")
    terms = []
    for i, c in enumerate(coeffs):
        if i == 0:
            terms.append(f"{c:.6g}")
        elif i == 1:
            terms.append(f"{c:.6g}x")
        else:
            terms.append(f"{c:.6g}x^{i}")
    print(f"  p(x) = {' + '.join(terms)}")
    y_pred = poly_eval(coeffs, x)
    r2 = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - np.mean(y)) ** 2)
    print(f"  R^2 = {r2:.6f}")


def op_roots(args):
    coeffs = parse_array(args.coeffs)
    r = poly_roots(coeffs)
    print(f"{BOLD}Polynomial Roots{RESET}")
    for i, root in enumerate(r):
        if np.isreal(root):
            print(f"  r{i+1} = {root.real:.6g}")
        else:
            print(f"  r{i+1} = {root:.6g}")


def op_describe(args):
    data = parse_array(args.data)
    stats = descriptive(data)
    print(f"{BOLD}Descriptive Statistics{RESET}")
    for k, v in stats.items():
        print(f"  {k:<12} {v:.6g}")


def op_regression(args):
    x = parse_array(args.x)
    y = parse_array(args.y)
    slope, intercept, r2 = linear_regression(x, y)
    print(f"{BOLD}Linear Regression{RESET}")
    print(f"  y = {slope:.6g}x + {intercept:.6g}")
    print(f"  R^2 = {r2:.6f}")


def op_ttest(args):
    a = parse_array(args.a)
    b = parse_array(args.b)
    t_stat, p_val = t_test(a, b)
    print(f"{BOLD}Two-Sample t-Test{RESET}")
    print(f"  t-statistic: {t_stat:.6f}")
    print(f"  p-value:     {p_val:.6f}")
    sig = "significant" if p_val < 0.05 else "not significant"
    color = GREEN if p_val < 0.05 else YELLOW
    print(f"  {color}{sig}{RESET} at alpha=0.05")


def op_dct(args):
    signal = parse_array(args.signal)
    result = dct(signal)
    print(f"{BOLD}DCT{RESET}")
    print(f"  {fmt_array(result)}")


def op_hilbert(args):
    signal = parse_array(args.signal)
    result = hilbert(signal)
    envelope = np.abs(result)
    print(f"{BOLD}Hilbert Transform{RESET}")
    print(f"  envelope max: {np.max(envelope):.6g}")
    print(f"  envelope min: {np.min(envelope):.6g}")


OPERATIONS = {
    "eigenvalues": op_eigenvalues,
    "eigenvectors": op_eigenvectors,
    "svd": op_svd,
    "solve": op_solve,
    "inverse": op_inverse,
    "fit": op_fit,
    "roots": op_roots,
    "describe": op_describe,
    "regression": op_regression,
    "ttest": op_ttest,
    "dct": op_dct,
    "hilbert": op_hilbert,
}


def cli():
    parser = argparse.ArgumentParser(description="Math computation router")
    parser.add_argument("operation", choices=list(OPERATIONS.keys()),
                        help="Math operation to perform")
    parser.add_argument("--matrix", help="Matrix as JSON array")
    parser.add_argument("--A", help="Matrix A for solve")
    parser.add_argument("--b", help="Vector b for solve")
    parser.add_argument("--x", help="X data as JSON array")
    parser.add_argument("--y", help="Y data as JSON array")
    parser.add_argument("--data", help="Data as JSON array")
    parser.add_argument("--a", help="Sample A for t-test")
    parser.add_argument("--coeffs", help="Polynomial coefficients as JSON array")
    parser.add_argument("--signal", help="Signal as JSON array")
    parser.add_argument("--degree", type=int, help="Polynomial degree")
    args = parser.parse_args()

    OPERATIONS[args.operation](args)
    return 0


if __name__ == "__main__":
    sys.exit(cli())
