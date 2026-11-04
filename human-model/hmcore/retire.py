"""Stored data standing in for a layer: a compact linear basis of the muscle fields."""
import numpy as np


def compress(fields, keep_energy=None, k=None):
    """PCA of fields (n_muscles, n_points, 3), without centring so zero activation stays zero. Returns basis (k, n_points, 3) and coefficients (n_muscles, k)."""
    n = fields.shape[0]
    A = fields.reshape(n, -1)
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    if k is None:
        energy = np.cumsum(S ** 2) / (S ** 2).sum()
        k = int(np.searchsorted(energy, keep_energy) + 1)
    return Vt[:k].reshape(k, fields.shape[1], 3), U[:, :k] * S[:k]


def reconstruct(basis, coeff, activation):
    return np.tensordot(coeff.T @ activation, basis, axes=1)


def error_mm(fields, basis, coeff):
    """Per-muscle (rms, max) of the reconstruction at full activation, mm."""
    rec = np.tensordot(coeff, basis, axes=1)
    d = np.linalg.norm(rec - fields, axis=2)
    return float(np.sqrt((d ** 2).mean()) * 1000), float(d.max() * 1000)
