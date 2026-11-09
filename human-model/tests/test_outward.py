import numpy as np
import pytest
from hmcore import outward


def grid(n=60, h=0.01):
    a = (np.arange(n) + 0.5) * h - n * h / 2
    xyz = np.stack(np.meshgrid(a, a, a, indexing="ij"), axis=-1)
    return xyz, h


def _sphere(n=24, m=12, radius=1.0):
    th = np.linspace(0.2, np.pi - 0.2, m)
    ph = np.linspace(0, 2 * np.pi, n, endpoint=False)
    v = np.array([[radius * np.sin(t) * np.cos(p), radius * np.sin(t) * np.sin(p), radius * np.cos(t)] for t in th for p in ph])
    f = []
    for i in range(m - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            f += [(a, b + n, b), (a, a + n, b + n)]
    return v, np.array(f)


def test_the_skin_lands_on_the_layers_outer_surface():
    h = 0.01
    a = (np.arange(90) + 0.5) * h - 0.45
    xyz = np.stack(np.meshgrid(a, a, a, indexing="ij"), axis=-1)
    solid = np.linalg.norm(xyz, axis=-1) < 0.30
    origin = np.array([-0.45, -0.45, -0.45])
    sdf = outward.signed_distance(solid, h)
    skin, tris = _sphere(radius=0.36)
    n = outward.vertex_normals(skin, tris)
    moved = outward.project(skin, n, sdf, origin, h, most=0.1)
    assert np.linalg.norm(moved, axis=1) == pytest.approx(np.full(len(moved), 0.30), abs=1.2 * h)
    assert outward.folded(skin, moved, tris) == 0


def test_the_skin_grows_out_to_a_bigger_surface_too():
    h = 0.01
    a = (np.arange(90) + 0.5) * h - 0.45
    xyz = np.stack(np.meshgrid(a, a, a, indexing="ij"), axis=-1)
    solid = np.linalg.norm(xyz, axis=-1) < 0.38
    sdf = outward.signed_distance(solid, h)
    skin, tris = _sphere(radius=0.30)
    moved = outward.project(skin, outward.vertex_normals(skin, tris), sdf, np.array([-0.45, -0.45, -0.45]), h, most=0.1)
    assert np.linalg.norm(moved, axis=1) == pytest.approx(np.full(len(moved), 0.38), abs=1.2 * h)


def test_the_move_is_limited():
    h = 0.01
    a = (np.arange(90) + 0.5) * h - 0.45
    xyz = np.stack(np.meshgrid(a, a, a, indexing="ij"), axis=-1)
    solid = np.linalg.norm(xyz, axis=-1) < 0.15
    sdf = outward.signed_distance(solid, h)
    skin, tris = _sphere(radius=0.40)
    moved = outward.project(skin, outward.vertex_normals(skin, tris), sdf, np.array([-0.45, -0.45, -0.45]), h, most=0.05)
    n = outward.vertex_normals(skin, tris)
    assert np.einsum("ij,ij->i", moved - skin, n) == pytest.approx(np.full(len(moved), -0.05), abs=1e-6)


def test_a_turned_over_triangle_is_counted():
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], float)
    tris = np.array([[0, 1, 2]])
    assert outward.folded(v, v * np.array([1, 1, 1]), tris) == 0
    flipped = v * np.array([-1, 1, 1])
    assert outward.folded(v, flipped, tris) == 1


def test_the_skins_move_fades_out_at_the_rings():
    ring = np.array([[0.1, 0, 0.0], [-0.1, 0, 0.0], [0, 0.1, 0.0], [0, -0.1, 0.0]])
    points = np.array([[0.1, 0, 0.0], [0.1, 0, 0.025], [0.1, 0, 0.05], [0.1, 0, 0.2]])
    fade = outward.ring_fade(points, [ring], reach=0.05)
    assert fade[0] == 0 and 0 < fade[1] < 1 and fade[2] == 1 and fade[3] == 1


def test_a_step_at_the_rings_is_measured():
    before = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]], float)
    after = before + np.array([[0, 0, 0.002], [0, 0, 0.0], [0, 0, 0.5]])
    assert outward.ring_steps(before, after, [np.array([0, 1])]) == [2.0]


def test_the_core_keeps_the_lumbar_curve_out():
    chest = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (2, 3)], float)
    trunk = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (0, 3)], float)
    c = np.array([[0, 0, 1.0], [0, 0, 2.5], [0, 0, 9.0]])
    front = np.array([True, True, True])
    behind = np.array([False, True, True])
    assert outward.core_mask(c, chest, trunk, front, np.zeros(3, bool)).tolist() == [True, True, False]
    assert outward.core_mask(c, chest, trunk, behind, np.zeros(3, bool)).tolist() == [False, True, False]


def test_grow_keeps_to_keep():
    xyz, h = grid()
    core = np.linalg.norm(xyz, axis=-1) < 0.05
    keep = xyz[..., 2] < 0
    g = outward.grow(core, 0.02, keep, h)
    assert not g[~keep].any() and g[(np.linalg.norm(xyz, axis=-1) < 0.065) & keep].all()


def test_masses_count_the_real_skin():
    xyz, h = grid()
    in_bone = np.linalg.norm(xyz[..., :2], axis=-1) < 0.02
    keep = np.ones(in_bone.shape, bool)
    m = outward.masses_kg(in_bone, in_bone, np.zeros_like(in_bone), np.zeros_like(in_bone), keep, h, 1.0)
    assert m["skin"] == pytest.approx(1.0 * 0.0015 * 1100) and outward.fat_percent(m) == 0.0


def test_the_skin_goes_out_only_where_something_needs_it():
    h = 0.01
    a = (np.arange(60) + 0.5) * h - 0.3
    xyz = np.stack(np.meshgrid(a, a, a, indexing="ij"), axis=-1)
    inner = np.linalg.norm(xyz, axis=-1) < 0.12
    sdf = outward.signed_distance(inner, h)
    origin = np.full(3, -0.3)
    points = np.array([[0.08, 0, 0], [0.2, 0, 0]])
    need = outward.push_needed(points, sdf, origin, h)
    assert need[0] == pytest.approx(0.04, abs=1.5 * h) and need[1] == 0.0


def test_a_bone_between_the_vertices_is_seen():
    h = 0.005
    a = (np.arange(60) + 0.5) * h - 0.15
    xyz = np.stack(np.meshgrid(a, a, a, indexing="ij"), axis=-1)
    origin = np.full(3, -0.15)
    ridge = (np.abs(xyz[..., 0]) < 0.01) & (np.abs(xyz[..., 1]) < 0.1) & (xyz[..., 2] < 0.02) & (xyz[..., 2] > -0.05)  # under the plate's middle
    sdf = outward.signed_distance(ridge, h)
    points = np.array([[-0.05, -0.05, 0], [0.05, -0.05, 0], [0.05, 0.05, 0], [-0.05, 0.05, 0]], float)
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    assert (outward.push_needed(points, sdf, origin, h) == 0).all()
    assert outward.push_needed_on_surface(points, tris, sdf, origin, h).min() > 0.005
