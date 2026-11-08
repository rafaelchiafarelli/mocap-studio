import numpy as np
import pytest
from hmcore import fit


def test_rotation_between_is_a_rotation():
    R = fit.rotation_between([1, 0, 0], [0, 0, 1])
    assert R @ np.array([1, 0, 0]) == pytest.approx([0, 0, 1])
    assert np.linalg.det(R) == pytest.approx(1.0)
    R2 = fit.rotation_between([0, 0, 1], [0, 0, -1])
    assert R2 @ np.array([0, 0, 1]) == pytest.approx([0, 0, -1])


def test_segment_fit_lands_joints_on_targets():
    a, b = np.array([0, 0, 1.0]), np.array([0, 0, 0.0])
    v = np.array([a, b, [0.1, 0, 0.5]])
    out = fit.segment_fit(v, a, b, [1, 1, 1], [1, 1, 3])
    assert out[0] == pytest.approx([1, 1, 1]) and out[1] == pytest.approx([1, 1, 3])
    radial = np.linalg.norm(out[2] - np.array([1, 1, 2]))
    assert radial == pytest.approx(0.1 * 2 ** 0.7)


def test_frame_rotation_keeps_the_second_axis_near():
    R = fit.frame_rotation([1, 0, 0], [0, 1, 0], [0, 1, 0], [0, 0, 1])
    assert R @ np.array([1, 0, 0]) == pytest.approx([0, 1, 0])
    assert R @ np.array([0, 1, 0]) == pytest.approx([0, 0, 1])


def _cube():
    v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    starts = np.arange(0, 24, 4)
    return v, fit.triangles(starts, [4] * 6, np.array(q).ravel())


def test_winding_number_inside_and_outside():
    v, t = _cube()
    w = fit.winding_number([[0.5, 0.5, 0.5], [2, 2, 2]], v, t)
    assert w[0] == pytest.approx(1.0, abs=1e-6) and w[1] == pytest.approx(0.0, abs=1e-6)


def test_profiles_ignore_arms():
    skin = np.array([[0, -0.1, 1.0], [0, 0.1, 1.0], [0.01, 0, 1.0], [0.02, 0, 1.0], [0.5, 0, 1.0]])
    assert fit.body_profile(skin, 1.0) == (-0.1, 0.1)
    assert fit.body_half_width(skin, 1.0) == 0.02


def _sphere(r=1.0, n=24):
    th, ph = np.meshgrid(np.linspace(0, np.pi, n), np.linspace(0, 2 * np.pi, 2 * n, endpoint=False), indexing="ij")
    v = np.column_stack([r * np.sin(th).ravel() * np.cos(ph).ravel(), r * np.sin(th).ravel() * np.sin(ph).ravel(), r * np.cos(th).ravel()])
    idx = np.arange(n * 2 * n).reshape(n, 2 * n)
    t = []
    for i in range(n - 1):
        for j in range(2 * n):
            a, b, c, d = idx[i, j], idx[i, (j + 1) % (2 * n)], idx[i + 1, j], idx[i + 1, (j + 1) % (2 * n)]
            t += [(a, c, b), (b, c, d)]
    return v, np.array(t)


def test_skin_depth_is_signed():
    v, t = _sphere()
    depth = fit.SkinDepth(v, t, spacing=0.01)
    d = depth([[0, 0, 0.5], [0, 0, 1.2]])
    assert d[0] == pytest.approx(0.5, abs=0.02) and d[1] == pytest.approx(-0.2, abs=0.02)
    flipped = fit.SkinDepth(v, t[:, ::-1], spacing=0.01)  # the normals' direction doesn't matter
    assert flipped([[0, 0, 0.5]])[0] == pytest.approx(0.5, abs=0.02)


def test_settle_turns_a_poking_bar_back_inside():
    v, t = _sphere()
    depth = fit.SkinDepth(v, t, spacing=0.01)
    bar = np.column_stack([np.linspace(0.0, 1.05, 50), np.zeros(50), np.zeros(50)]) + [0, 0, 0.3]
    pivot = bar[0]
    move, before, after, amounts = fit.settle(bar, pivot, depth, 0.05, [("turn", [0, 1, 0], 40.0)])
    assert before > 0.05 and after == pytest.approx(0.0, abs=0.001)
    moved = move(bar)
    assert moved[0] == pytest.approx(pivot) and depth(moved).min() >= 0.05 - 0.01
    assert 0 < abs(amounts[0]) < 40


def test_settle_prefers_the_smallest_move():
    v, t = _sphere()
    depth = fit.SkinDepth(v, t, spacing=0.01)
    bar = np.column_stack([np.linspace(-0.2, 0.2, 20), np.zeros(20), np.zeros(20)])
    move, before, after, amounts = fit.settle(bar, bar[0], depth, 0.05, [("turn", [0, 0, 1], 30.0), ("shift", [1, 0, 0], 0.2)])
    assert before == 0.0 and np.all(amounts == 0)
