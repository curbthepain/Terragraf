"""Tests for .scaffold/compute/math/algebra.py"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute.math.algebra import (
    poly_eval, poly_roots, interpolate, curve_fit_poly,
    lagrange_interpolate, newton_interpolate,
)


class TestPolyEval:
    def test_quadratic(self):
        # 2x^2 + 3x + 1
        coeffs = np.array([2, 3, 1])
        x = np.array([0, 1, 2])
        assert_allclose(poly_eval(coeffs, x), [1, 6, 15])

    def test_constant(self):
        assert_allclose(poly_eval(np.array([5]), np.array([0, 1, 100])), [5, 5, 5])


class TestPolyRoots:
    def test_quadratic_roots(self):
        # x^2 - 5x + 6 = (x-2)(x-3)
        coeffs = np.array([1, -5, 6])
        roots = poly_roots(coeffs)
        assert_allclose(sorted(np.real(roots)), [2.0, 3.0], atol=1e-10)

    def test_linear_root(self):
        # 2x - 4 = 0 => x = 2
        roots = poly_roots(np.array([2, -4]))
        assert_allclose(roots, [2.0], atol=1e-10)


class TestInterpolate:
    def test_exact_fit(self):
        x = np.array([0, 1, 2], dtype=float)
        y = np.array([1, 0, 1], dtype=float)
        # Just check that interpolation passes through points
        coeffs = interpolate(x, y)
        assert_allclose(poly_eval(coeffs, x), y, atol=1e-10)


class TestCurveFitPoly:
    def test_linear_fit(self):
        x = np.array([0, 1, 2, 3, 4], dtype=float)
        y = 2 * x + 1  # perfect linear
        coeffs = curve_fit_poly(x, y, degree=1)
        assert_allclose(coeffs, [2, 1], atol=1e-10)


class TestLagrangeInterpolate:
    def test_known_points(self):
        x_pts = np.array([0, 1, 2], dtype=float)
        y_pts = np.array([1, 3, 7], dtype=float)
        # Should pass through all given points
        for xi, yi in zip(x_pts, y_pts):
            assert_allclose(lagrange_interpolate(x_pts, y_pts, xi), yi, atol=1e-10)

    def test_interpolated_value(self):
        x_pts = np.array([0, 1, 2], dtype=float)
        y_pts = np.array([0, 1, 4], dtype=float)  # y = x^2
        assert_allclose(lagrange_interpolate(x_pts, y_pts, 1.5), 2.25, atol=1e-10)


class TestNewtonInterpolate:
    def test_known_points(self):
        x_pts = np.array([0, 1, 2], dtype=float)
        y_pts = np.array([1, 3, 7], dtype=float)
        for xi, yi in zip(x_pts, y_pts):
            assert_allclose(newton_interpolate(x_pts, y_pts, xi), yi, atol=1e-10)

    def test_matches_lagrange(self):
        x_pts = np.array([0, 1, 3], dtype=float)
        y_pts = np.array([2, 5, 11], dtype=float)
        x_eval = 2.0
        lag = lagrange_interpolate(x_pts, y_pts, x_eval)
        newt = newton_interpolate(x_pts, y_pts, x_eval)
        assert_allclose(lag, newt, atol=1e-10)
