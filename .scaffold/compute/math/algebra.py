"""
.scaffold/compute/math/algebra.py
Algebraic operations — polynomial evaluation, roots, interpolation, curve fitting.

Provides:
  - poly_eval              — evaluate polynomial at points
  - poly_roots             — find roots of polynomial
  - interpolate            — polynomial interpolation from data points
  - curve_fit_poly         — least-squares polynomial fit
  - lagrange_interpolate   — Lagrange interpolation
  - newton_interpolate     — Newton divided difference interpolation
"""

import numpy as np
from typing import Optional


def poly_eval(coeffs: np.ndarray, x: np.ndarray) -> np.ndarray:
    """
    Evaluate polynomial at x.
    coeffs: highest degree first [a_n, a_{n-1}, ..., a_1, a_0].
    """
    return np.polyval(coeffs, x)


def poly_roots(coeffs: np.ndarray) -> np.ndarray:
    """
    Find roots of polynomial.
    coeffs: highest degree first [a_n, a_{n-1}, ..., a_1, a_0].
    Returns complex array of roots.
    """
    return np.roots(coeffs)


def interpolate(x: np.ndarray, y: np.ndarray, degree: Optional[int] = None) -> np.ndarray:
    """
    Polynomial interpolation through data points.
    Returns polynomial coefficients (highest degree first).
    degree defaults to len(x) - 1 (exact interpolation).
    """
    if degree is None:
        degree = len(x) - 1
    return np.polyfit(x, y, degree)


def curve_fit_poly(x: np.ndarray, y: np.ndarray, degree: int) -> np.ndarray:
    """
    Least-squares polynomial fit of given degree.
    Returns coefficients (highest degree first).
    """
    return np.polyfit(x, y, degree)


def lagrange_interpolate(x_points: np.ndarray, y_points: np.ndarray,
                          x: float) -> float:
    """
    Lagrange interpolation at a single point x.
    Exact interpolation through all given (x, y) pairs.
    """
    n = len(x_points)
    result = 0.0
    for i in range(n):
        basis = y_points[i]
        for j in range(n):
            if i != j:
                basis *= (x - x_points[j]) / (x_points[i] - x_points[j])
        result += basis
    return result


def newton_interpolate(x_points: np.ndarray, y_points: np.ndarray,
                        x: float) -> float:
    """
    Newton divided difference interpolation at a single point x.
    """
    n = len(x_points)
    # Build divided difference table
    dd = np.copy(y_points).astype(float)
    for j in range(1, n):
        for i in range(n - 1, j - 1, -1):
            dd[i] = (dd[i] - dd[i - 1]) / (x_points[i] - x_points[i - j])

    # Evaluate using Horner's method
    result = dd[n - 1]
    for i in range(n - 2, -1, -1):
        result = result * (x - x_points[i]) + dd[i]
    return result
