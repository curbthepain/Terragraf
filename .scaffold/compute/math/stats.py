"""
.scaffold/compute/math/stats.py
Statistics primitives — distributions, hypothesis tests, correlation, regression.

Provides:
  - descriptive         — mean, median, std, var, min, max, skew, kurtosis
  - correlation         — Pearson correlation coefficient
  - covariance          — covariance matrix
  - linear_regression   — simple linear regression (y = mx + b)
  - normal_pdf, normal_cdf — Gaussian distribution functions
  - t_test              — two-sample t-test
  - chi_squared         — chi-squared goodness-of-fit test
  - percentile          — compute percentile(s)
  - zscore              — standardize data
"""

import numpy as np
from typing import Dict, Tuple


def descriptive(data: np.ndarray) -> Dict[str, float]:
    """
    Descriptive statistics for a 1D dataset.
    Returns dict with mean, median, std, var, min, max, skew, kurtosis.
    """
    n = len(data)
    mean = np.mean(data)
    std = np.std(data, ddof=1) if n > 1 else 0.0
    centered = data - mean
    skew = float(np.mean(centered ** 3) / (std ** 3)) if std > 0 else 0.0
    kurtosis = float(np.mean(centered ** 4) / (std ** 4) - 3.0) if std > 0 else 0.0
    return {
        "mean": float(mean),
        "median": float(np.median(data)),
        "std": float(std),
        "var": float(std ** 2),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "skew": skew,
        "kurtosis": kurtosis,
        "n": n,
    }


def correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation coefficient between x and y."""
    return float(np.corrcoef(x, y)[0, 1])


def covariance(data: np.ndarray) -> np.ndarray:
    """
    Covariance matrix.
    data: 2D array where each row is a variable and each column is an observation.
    """
    return np.cov(data)


def linear_regression(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """
    Simple linear regression: y = slope * x + intercept.
    Returns (slope, intercept, r_squared).
    """
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs[0], coeffs[1]
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return float(slope), float(intercept), float(r_squared)


def normal_pdf(x: np.ndarray, mu: float = 0.0, sigma: float = 1.0) -> np.ndarray:
    """Gaussian probability density function."""
    coeff = 1.0 / (sigma * np.sqrt(2 * np.pi))
    exponent = -0.5 * ((x - mu) / sigma) ** 2
    return coeff * np.exp(exponent)


def normal_cdf(x: np.ndarray, mu: float = 0.0, sigma: float = 1.0) -> np.ndarray:
    """Gaussian cumulative distribution function (via erf)."""
    from scipy.special import erf
    return 0.5 * (1 + erf((x - mu) / (sigma * np.sqrt(2))))


def t_test(sample1: np.ndarray, sample2: np.ndarray) -> Tuple[float, float]:
    """
    Two-sample Welch's t-test (unequal variance).
    Returns (t_statistic, p_value).
    """
    from scipy.stats import ttest_ind
    stat, pval = ttest_ind(sample1, sample2, equal_var=False)
    return float(stat), float(pval)


def chi_squared(observed: np.ndarray, expected: np.ndarray) -> Tuple[float, float]:
    """
    Chi-squared goodness-of-fit test.
    Returns (chi2_statistic, p_value).
    """
    from scipy.stats import chisquare
    stat, pval = chisquare(observed, f_exp=expected)
    return float(stat), float(pval)


def percentile(data: np.ndarray, q) -> np.ndarray:
    """Compute percentile(s). q can be scalar or array (0-100 scale)."""
    return np.percentile(data, q)


def zscore(data: np.ndarray) -> np.ndarray:
    """Standardize data to zero mean and unit variance."""
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    if std == 0:
        return np.zeros_like(data)
    return (data - mean) / std
