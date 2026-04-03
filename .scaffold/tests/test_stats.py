"""Tests for .scaffold/compute/math/stats.py"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute.math.stats import (
    descriptive, correlation, covariance, linear_regression,
    normal_pdf, normal_cdf, t_test, chi_squared,
    percentile, zscore,
)


class TestDescriptive:
    def test_basic(self):
        data = np.array([1, 2, 3, 4, 5], dtype=float)
        d = descriptive(data)
        assert_allclose(d["mean"], 3.0)
        assert_allclose(d["median"], 3.0)
        assert_allclose(d["min"], 1.0)
        assert_allclose(d["max"], 5.0)
        assert d["n"] == 5

    def test_std_ddof1(self):
        data = np.array([2, 4, 4, 4, 5, 5, 7, 9], dtype=float)
        d = descriptive(data)
        assert_allclose(d["std"], np.std(data, ddof=1), atol=1e-10)

    def test_single_element(self):
        d = descriptive(np.array([42.0]))
        assert_allclose(d["mean"], 42.0)
        assert_allclose(d["std"], 0.0)


class TestCorrelation:
    def test_perfect_positive(self):
        x = np.array([1, 2, 3, 4, 5], dtype=float)
        assert_allclose(correlation(x, x), 1.0, atol=1e-10)

    def test_perfect_negative(self):
        x = np.array([1, 2, 3, 4, 5], dtype=float)
        assert_allclose(correlation(x, -x), -1.0, atol=1e-10)

    def test_uncorrelated(self):
        x = np.array([1, 0, -1, 0], dtype=float)
        y = np.array([0, 1, 0, -1], dtype=float)
        assert_allclose(correlation(x, y), 0.0, atol=1e-10)


class TestCovariance:
    def test_shape(self):
        data = np.array([[1, 2, 3], [4, 5, 6]], dtype=float)
        cov = covariance(data)
        assert cov.shape == (2, 2)

    def test_variance_on_diagonal(self):
        data = np.array([[1, 2, 3, 4], [5, 6, 7, 8]], dtype=float)
        cov = covariance(data)
        assert_allclose(cov[0, 0], np.var(data[0], ddof=1), atol=1e-10)
        assert_allclose(cov[1, 1], np.var(data[1], ddof=1), atol=1e-10)


class TestLinearRegression:
    def test_perfect_fit(self):
        x = np.array([0, 1, 2, 3, 4], dtype=float)
        y = 3 * x + 2
        slope, intercept, r2 = linear_regression(x, y)
        assert_allclose(slope, 3.0, atol=1e-10)
        assert_allclose(intercept, 2.0, atol=1e-10)
        assert_allclose(r2, 1.0, atol=1e-10)

    def test_noisy(self):
        rng = np.random.default_rng(42)
        x = np.linspace(0, 10, 100)
        y = 2 * x + 5 + rng.normal(0, 0.1, 100)
        slope, intercept, r2 = linear_regression(x, y)
        assert_allclose(slope, 2.0, atol=0.1)
        assert_allclose(intercept, 5.0, atol=0.2)
        assert r2 > 0.99


class TestNormalPDF:
    def test_peak_at_mean(self):
        x = np.array([0.0])
        pdf = normal_pdf(x, mu=0, sigma=1)
        assert_allclose(pdf, [1.0 / np.sqrt(2 * np.pi)], atol=1e-10)

    def test_symmetry(self):
        x_pos = normal_pdf(np.array([1.0]))
        x_neg = normal_pdf(np.array([-1.0]))
        assert_allclose(x_pos, x_neg, atol=1e-10)


class TestNormalCDF:
    def test_at_mean(self):
        cdf = normal_cdf(np.array([0.0]), mu=0, sigma=1)
        assert_allclose(cdf, [0.5], atol=1e-10)

    def test_monotonic(self):
        x = np.linspace(-3, 3, 100)
        cdf = normal_cdf(x)
        assert np.all(np.diff(cdf) >= 0)


class TestTTest:
    def test_same_distribution(self):
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 100)
        b = rng.normal(0, 1, 100)
        _, pval = t_test(a, b)
        assert pval > 0.05  # should not reject null

    def test_different_distributions(self):
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 100)
        b = rng.normal(5, 1, 100)
        _, pval = t_test(a, b)
        assert pval < 0.001  # should reject null


class TestChiSquared:
    def test_perfect_match(self):
        obs = np.array([25, 25, 25, 25], dtype=float)
        exp = np.array([25, 25, 25, 25], dtype=float)
        stat, pval = chi_squared(obs, exp)
        assert_allclose(stat, 0.0, atol=1e-10)
        assert_allclose(pval, 1.0, atol=1e-10)


class TestPercentile:
    def test_median(self):
        data = np.array([1, 2, 3, 4, 5], dtype=float)
        assert_allclose(percentile(data, 50), 3.0)

    def test_extremes(self):
        data = np.arange(101, dtype=float)
        assert_allclose(percentile(data, 0), 0.0)
        assert_allclose(percentile(data, 100), 100.0)


class TestZscore:
    def test_standardized(self):
        data = np.array([10, 20, 30, 40, 50], dtype=float)
        z = zscore(data)
        assert_allclose(np.mean(z), 0.0, atol=1e-10)
        assert_allclose(np.std(z, ddof=1), 1.0, atol=1e-10)

    def test_constant_data(self):
        data = np.array([5, 5, 5, 5], dtype=float)
        z = zscore(data)
        assert_allclose(z, [0, 0, 0, 0])
