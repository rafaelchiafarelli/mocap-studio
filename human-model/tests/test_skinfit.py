import numpy as np
import pytest
from hmcore import skinfit


def _strip(n=20):
    """Two rows of n vertices joined by triangles: a strip one edge wide."""
    tris = np.array([[i, i + 1, i + n] for i in range(n - 1)] + [[i + 1, i + n + 1, i + n] for i in range(n - 1)])
    return tris, 2 * n


def test_least_depth_takes_the_longest_prefix():
    table = {"default": 2, "hip": 6, "vertebra": 4}
    assert skinfit.least_depth("hip_L", table) == pytest.approx(0.006)
    assert skinfit.least_depth("vertebra_T1", table) == pytest.approx(0.004)
    assert skinfit.least_depth("femur_L", table) == pytest.approx(0.002)


def test_spread_meets_the_need_and_falls_off():
    tris, n = _strip()
    need = np.zeros(n)
    need[[10, 30]] = 0.01
    d = skinfit.spread(need, tris, n, np.array([0, 19, 20, 39]), 40, 0.8)
    assert d[10] >= 0.01 and d[30] >= 0.01
    assert d[13] < d[11] < 0.01
    assert d[0] == 0 and d[19] == 0


def test_spread_without_falloff_reaches_far():
    tris, n = _strip()
    need = np.zeros(n)
    need[10] = 0.01
    far = skinfit.spread(need, tris, n, np.array([0]), 200, 1.0)[18]
    near = skinfit.spread(need, tris, n, np.array([0]), 200, 0.8)[18]
    assert far > 5 * near


def test_vertex_normals_point_out_of_a_tetrahedron():
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    f = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    n = skinfit.vertex_normals(v, f)
    assert (n[0] @ np.array([-1, -1, -1])) > 0 and (n[3] @ np.array([0, 0, 1])) > 0
