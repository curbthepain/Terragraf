"""
.scaffold/compute/math/linalg.py
Linear algebra primitives — NumPy/SciPy backend.

Provides:
  - mat_mul, mat_inv, determinant  — basic matrix operations
  - eigenvalues, eigenvectors      — eigendecomposition
  - svd                            — singular value decomposition
  - lu_decompose                   — LU factorization
  - solve                          — linear system solver (Ax = b)
  - norm, rank                     — matrix properties
"""

import numpy as np
from typing import Tuple


def mat_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Matrix multiplication. Works with 1D vectors too."""
    return np.matmul(a, b)


def mat_inv(matrix: np.ndarray) -> np.ndarray:
    """Matrix inverse. Raises LinAlgError if singular."""
    return np.linalg.inv(matrix)


def determinant(matrix: np.ndarray) -> float:
    """Matrix determinant."""
    return float(np.linalg.det(matrix))


def eigenvalues(matrix: np.ndarray) -> np.ndarray:
    """Eigenvalues of a square matrix."""
    return np.linalg.eigvals(matrix)


def eigenvectors(matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Eigenvalues and eigenvectors. Returns (values, vectors)."""
    return np.linalg.eig(matrix)


def svd(matrix: np.ndarray, full: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Singular Value Decomposition.
    Returns (U, S, Vt) where matrix = U @ diag(S) @ Vt.
    """
    return np.linalg.svd(matrix, full_matrices=full)


def lu_decompose(matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    LU decomposition with partial pivoting.
    Returns (P, L, U) where P @ matrix = L @ U.
    Requires scipy.
    """
    from scipy.linalg import lu
    return lu(matrix)


def solve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Solve linear system Ax = b. Returns x."""
    return np.linalg.solve(a, b)


def norm(x: np.ndarray, ord=None) -> float:
    """
    Vector or matrix norm.
    ord=None: Frobenius for matrices, L2 for vectors.
    ord=1, 2, np.inf also supported.
    """
    return float(np.linalg.norm(x, ord=ord))


def rank(matrix: np.ndarray) -> int:
    """Matrix rank (number of linearly independent rows/columns)."""
    return int(np.linalg.matrix_rank(matrix))
