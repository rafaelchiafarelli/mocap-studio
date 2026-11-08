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


def test_solids_are_positive_inside_any_mesh_whichever_way_it_is_wound():
    v, t = _sphere()
    far = v + [5, 0, 0]
    both = fit.solids([(v, t), (far, t[:, ::-1])], spacing=0.01)
    d = both([[0, 0, 0.5], [5, 0, 0.5], [2.5, 0, 0]])
    assert d[0] == pytest.approx(0.5, abs=0.02) and d[1] == pytest.approx(0.5, abs=0.02) and d[2] < -1


def test_settle_does_not_move_a_bone_into_its_neighbour():
    v, t = _sphere()
    depth = fit.SkinDepth(v, t, spacing=0.01)
    bar = np.column_stack([np.linspace(0.0, 0.9, 50), np.zeros(50), np.zeros(50)]) + [0, 0, 0.6]
    wall = (np.array([[-0.6, -0.6, 0.1], [0.6, -0.6, 0.1], [-0.6, 0.6, 0.1], [0.6, 0.6, 0.1],
                      [-0.6, -0.6, 0.45], [0.6, -0.6, 0.45], [-0.6, 0.6, 0.45], [0.6, 0.6, 0.45]]) + [0.45, 0, 0],
            np.array([[0, 2, 1], [1, 2, 3], [4, 5, 6], [5, 7, 6], [0, 1, 4], [1, 5, 4], [2, 6, 3], [3, 6, 7], [0, 4, 2], [2, 4, 6], [1, 3, 5], [3, 7, 5]]))
    inside_wall = fit.solids([wall], spacing=0.01)
    free = fit.settle(bar, bar[0], depth, 0.05, [("shift", [0, 0, -1], 0.35)])[0](bar)  # free, it comes to rest inside the wall
    blocked = fit.settle(bar, bar[0], depth, 0.05, [("shift", [0, 0, -1], 0.35)], avoid=inside_wall)[0](bar)
    assert inside_wall(free).max() > 0
    assert inside_wall(blocked).max() <= -0.003 + 0.01


def test_outward_turns_an_inside_out_mesh():
    v, t = _cube()
    good = fit.outward(v, t)
    vol = lambda tri: np.einsum("ij,ij->i", v[tri][:, 0], np.cross(v[tri][:, 1], v[tri][:, 2])).sum()
    assert vol(good) > 0
    assert (fit.outward(v, good[:, [0, 2, 1]]) == good).all()


def test_largest_scale_finds_the_limit_and_keeps_what_fits():
    assert fit.largest_scale(lambda s: s - 0.7) == pytest.approx(0.7, abs=0.001)
    assert fit.largest_scale(lambda s: -1.0) == 1.0
    assert fit.largest_scale(lambda s: 1.0, least=0.4) == 0.4


def test_slim_to_skin_narrows_only_where_it_pokes():
    v, t = _sphere()
    depth = fit.SkinDepth(v, t, spacing=0.01)
    z = np.linspace(-0.8, 0.8, 161)
    bone = np.column_stack([np.full(161, 0.7), np.zeros(161), z])  # a line 0.7 off-centre: near the top and bottom it leaves the sphere
    (placed,), least = fit.slim_to_skin([bone], [0, 0, -1.0], [0, 0, 1.0], v, depth, 0.05, start=0.0, bin_size=0.05, reach=2.0, least=0.1)
    assert least < 1 and depth(placed).min() >= 0.05 - 0.015
    assert placed[80] == pytest.approx(bone[80], abs=1e-6)  # the middle fits, so it stays


def test_slim_to_skin_along_one_direction_leaves_the_others():
    v, t = _sphere()
    depth = fit.SkinDepth(v, t, spacing=0.01)
    z = np.linspace(-0.1, 0.1, 21)
    side = np.column_stack([np.full(21, 1.02), np.zeros(21), z])
    front = np.column_stack([np.zeros(21), np.full(21, 0.97), z])  # too close to the skin, but a sideways move can't help it
    (a, b), least = fit.slim_to_skin([side, front], [0, 0, -1.0], [0, 0, 1.0], v, depth, 0.05, start=0.0, bin_size=0.05, reach=2.0, only=np.array([1.0, 0, 0]))
    assert 0.8 < least < 1 and a[:, 0].max() < 0.96
    assert b == pytest.approx(front, abs=1e-9)
