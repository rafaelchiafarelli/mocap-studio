import numpy as np
import pytest
from hmcore import softtissue


def _sheet(n=25):
    xs, zs = np.meshgrid(np.linspace(-0.05, 0.05, n), np.linspace(1.6, 1.7, n))
    v = np.column_stack([xs.ravel(), np.full(xs.size, -0.1), zs.ravel()])
    t = []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            t += [(a, a + 1, a + n), (a + 1, a + n + 1, a + n)]
    return v, np.array(t)


def test_areas_sum_to_the_sheet():
    v, t = _sheet()
    assert softtissue.vertex_areas(v, t).sum() == pytest.approx(0.01, rel=1e-6)


def test_uniform_operator_solves_a_pull_with_a_fixed_edge():
    v, t = _sheet()
    g = softtissue.edge_graph(v, t)
    adj = (g > 0).astype(float)
    assert g.nnz > 0 and np.allclose(np.asarray((g - g.T).todense()), 0)
    assert adj.sum() == g.nnz


def test_smoothing_keeps_a_constant():
    v, t = _sheet()
    g = softtissue.edge_graph(v, t)
    assert softtissue.smooth(g, np.ones(len(v))) == pytest.approx(np.ones(len(v)))


def test_normals_are_unit():
    v, t = _sheet()
    n = softtissue.vertex_normals(v, t)
    assert np.linalg.norm(n, axis=1) == pytest.approx(np.ones(len(v)))
