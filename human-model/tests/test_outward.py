import numpy as np
import pytest
from hmcore import outward


def grid(n=60, h=0.01):
    a = (np.arange(n) + 0.5) * h - n * h / 2
    xyz = np.stack(np.meshgrid(a, a, a, indexing="ij"), axis=-1)
    return xyz, h


def test_the_core_is_the_bones_and_the_trunks_hull():
    centres = np.array([[0, 0, 0.5], [0.9, 0.9, 0.9], [0, 0, 5.0]], float)
    pts = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
    in_bone = np.array([False, False, True])
    assert outward.core_mask(centres, pts, in_bone).tolist() == [True, True, True]
    assert outward.core_mask(centres * 2, pts, np.zeros(3, bool)).tolist() == [True, False, False]


def test_muscle_grows_from_the_bone_by_its_thickness():
    xyz, h = grid()
    core = np.linalg.norm(xyz[..., :2], axis=-1) < 0.02  # a rod
    keep = np.ones(core.shape, bool)
    m = outward.muscle_layer(core, np.full(core.shape, 0.05), 1.0, keep, h)
    r = np.linalg.norm(xyz[..., :2], axis=-1)
    assert m[(r > 0.03) & (r < 0.06)].all() and not m[r > 0.09].any() and not m[core].any()


def test_the_biotype_scales_the_muscle():
    xyz, h = grid()
    core = np.linalg.norm(xyz[..., :2], axis=-1) < 0.02
    keep = np.ones(core.shape, bool)
    a = outward.muscle_layer(core, np.full(core.shape, 0.05), 1.0, keep, h)
    b = outward.muscle_layer(core, np.full(core.shape, 0.05), 0.5, keep, h)
    assert b.sum() < 0.6 * a.sum()


def test_muscle_stays_in_keep():
    xyz, h = grid()
    core = np.linalg.norm(xyz[..., :2], axis=-1) < 0.02
    keep = xyz[..., 2] < 0
    assert not outward.muscle_layer(core, np.full(core.shape, 0.05), 1.0, keep, h)[~keep].any()


def test_the_muscle_table_writes_old_zones_as_their_new_parts():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import muscle_table
    from hmcore import body
    t = muscle_table.per_zone(np.array([0.05, 0.06, 0.02, 0.02]), np.array(["buttocks", "buttocks", "breast", "neck"]))
    assert {t[z] for z in body.GLUTEUS_ZONES} == {55.0} and {t[z] for z in body.BREAST_ZONES} == {20.0} and t["neck"] == 20.0


def _rod_body():
    xyz, h = grid(100, 0.003)
    r = np.linalg.norm(xyz[..., :2], axis=-1)
    in_bone = r < 0.02
    core = in_bone
    keep = np.ones(in_bone.shape, bool)
    muscle = (r >= 0.02) & (r < 0.06)
    return xyz, h, r, in_bone, core, muscle, keep


@pytest.mark.parametrize("target", [10.0, 25.0, 40.0])
def test_the_fat_reaches_the_percentage_within_tolerance(target):
    xyz, h, r, in_bone, core, muscle, keep = _rod_body()
    z = xyz[..., 2]
    thickness = 0.015 + 0.02 * (z - z.min()) / (z.max() - z.min())  # a thickness that varies, as a body's does, so the percentage isn't stuck on whole rings of cells
    out = outward.fat_to_percent(in_bone, core, muscle, keep, thickness, target, h, 0.0)
    assert out["reached"] and abs(out["percent"] - target) <= 0.5
    assert not (out["fat"] & (core | muscle)).any()


def test_the_fat_is_outside_the_muscle():
    xyz, h, r, in_bone, core, muscle, keep = _rod_body()
    out = outward.fat_to_percent(in_bone, core, muscle, keep, np.full(in_bone.shape, 0.02), 25.0, h, 0.0)
    assert r[out["fat"]].min() >= 0.059


def test_a_percentage_out_of_reach_says_so():
    xyz, h, r, in_bone, core, muscle, keep = _rod_body()
    out = outward.fat_to_percent(in_bone, core, muscle, keep, np.full(in_bone.shape, 0.02), 99.0, h, 0.0, hi=1.0)
    assert not out["reached"]


def test_masses_count_the_real_skin():
    xyz, h, r, in_bone, core, muscle, keep = _rod_body()
    m = outward.masses_kg(in_bone, core, muscle, np.zeros_like(in_bone), keep, h, 1.0)
    assert m["skin"] == pytest.approx(1.0 * 0.0015 * 1100)
    assert outward.fat_percent(m) == 0.0


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
