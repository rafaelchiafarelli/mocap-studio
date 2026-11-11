import numpy as np

from hmcore import folds


def grid(n=11, spacing=0.01):
    verts = np.array([[i * spacing, j * spacing, 0.0] for i in range(n) for j in range(n)])
    tris = []
    for i in range(n - 1):
        for j in range(n - 1):
            p, q, r, s = i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1
            tris += [[p, q, r], [p, r, s]]
    return verts, np.array(tris)


def test_surface_distance_grows_from_the_line_and_stops_at_the_limit():
    v, t = grid()
    d = folds.surface_distance(v, folds.edges_of(t), [5 * 11 + 5], 0.03)
    assert d[5 * 11 + 5] == 0.0
    assert abs(d[6 * 11 + 5] - 0.01) < 1e-9
    assert np.isinf(d[0])


def test_profile_is_a_dent_with_a_small_bulge_beside_it():
    p = folds.profile(np.array([0.0, 0.015, np.inf]), 0.02)
    assert p[0] > 0.7
    assert p[1] < p[0]
    assert abs(p[2]) < 1e-6
    side = folds.profile(np.array([0.018]), 0.02, bulge=0.35)
    assert side[0] < 0.2
