"""Tests for .scaffold/compute/math/linalg.py"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compute.math.linalg import (
    mat_mul, mat_inv, determinant, eigenvalues, eigenvectors,
    svd, lu_decompose, solve, norm, rank,
)


class TestMatMul:
    def test_square_matrices(self):
        a = np.array([[1, 2], [3, 4]])
        b = np.array([[5, 6], [7, 8]])
        result = mat_mul(a, b)
        assert_allclose(result, [[19, 22], [43, 50]])

    def test_identity(self):
        a = np.array([[1, 2], [3, 4]])
        i = np.eye(2)
        assert_allclose(mat_mul(a, i), a)

    def test_vector(self):
        a = np.array([[1, 2], [3, 4]])
        v = np.array([1, 0])
        assert_allclose(mat_mul(a, v), [1, 3])

    def test_non_square(self):
        a = np.array([[1, 2, 3], [4, 5, 6]])  # 2x3
        b = np.array([[1], [2], [3]])           # 3x1
        assert_allclose(mat_mul(a, b), [[14], [32]])


class TestMatInv:
    def test_invertible(self):
        a = np.array([[1, 2], [3, 4]], dtype=float)
        inv = mat_inv(a)
        assert_allclose(mat_mul(a, inv), np.eye(2), atol=1e-10)

    def test_singular_raises(self):
        singular = np.array([[1, 2], [2, 4]], dtype=float)
        with pytest.raises(np.linalg.LinAlgError):
            mat_inv(singular)


class TestDeterminant:
    def test_2x2(self):
        a = np.array([[1, 2], [3, 4]])
        assert_allclose(determinant(a), -2.0, atol=1e-10)

    def test_identity(self):
        assert_allclose(determinant(np.eye(3)), 1.0, atol=1e-10)

    def test_singular(self):
        a = np.array([[1, 2], [2, 4]])
        assert_allclose(determinant(a), 0.0, atol=1e-10)


class TestEigen:
    def test_eigenvalues_symmetric(self):
        a = np.array([[2, 1], [1, 2]], dtype=float)
        vals = eigenvalues(a)
        assert_allclose(sorted(np.real(vals)), [1.0, 3.0], atol=1e-10)

    def test_eigenvectors_reconstruction(self):
        a = np.array([[2, 1], [1, 2]], dtype=float)
        vals, vecs = eigenvectors(a)
        for i in range(len(vals)):
            lhs = mat_mul(a, vecs[:, i])
            rhs = vals[i] * vecs[:, i]
            assert_allclose(lhs, rhs, atol=1e-10)


class TestSVD:
    def test_reconstruction(self):
        a = np.array([[1, 2], [3, 4], [5, 6]], dtype=float)
        u, s, vt = svd(a)
        reconstructed = u[:, :2] @ np.diag(s) @ vt
        assert_allclose(reconstructed, a, atol=1e-10)


class TestLU:
    def test_reconstruction(self):
        a = np.array([[2, 1, 1], [4, 3, 3], [8, 7, 9]], dtype=float)
        p, l, u = lu_decompose(a)
        assert_allclose(p @ l @ u, a, atol=1e-10)


class TestSolve:
    def test_simple_system(self):
        a = np.array([[1, 2], [3, 4]], dtype=float)
        b = np.array([5, 6], dtype=float)
        x = solve(a, b)
        assert_allclose(mat_mul(a, x), b, atol=1e-10)


class TestNorm:
    def test_vector_l2(self):
        v = np.array([3, 4], dtype=float)
        assert_allclose(norm(v), 5.0)

    def test_vector_l1(self):
        v = np.array([3, -4], dtype=float)
        assert_allclose(norm(v, ord=1), 7.0)


class TestRank:
    def test_full_rank(self):
        a = np.array([[1, 0], [0, 1]])
        assert rank(a) == 2

    def test_rank_deficient(self):
        a = np.array([[1, 2], [2, 4]])
        assert rank(a) == 1
