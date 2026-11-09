import numpy as np
import pytest
from hmcore import body, muscle_bodies as mb


def grid(n=80, h=0.005):
    return np.full(3, -n * h / 2), (n, n, n), h


def cell_centres(origin, shape, h):
    idx = np.indices(shape).reshape(3, -1).T
    return origin + (idx + 0.5) * h


def test_a_muscle_is_thin_at_its_tendons_and_thick_at_its_belly():
    origin, shape, h = grid()
    m = mb.rasterize([[0, 0, -0.15], [0, 0, 0.15]], 0.04, origin, shape, h, np.zeros(shape, bool))
    c = cell_centres(origin, shape, h)[m.ravel()]
    r = lambda z: np.linalg.norm(c[np.abs(c[:, 2] - z) < h, :2], axis=1).max() if (np.abs(c[:, 2] - z) < h).any() else 0.0
    assert r(0.0) == pytest.approx(0.04, abs=h) and r(0.14) < 0.012


def test_a_chain_follows_its_points():
    origin, shape, h = grid()
    m = mb.rasterize([[0, 0, -0.1], [0.05, 0, 0.0], [0, 0, 0.1]], 0.02, origin, shape, h, np.zeros(shape, bool))
    c = cell_centres(origin, shape, h)[m.ravel()]
    assert c[np.abs(c[:, 2]) < h, 0].mean() == pytest.approx(0.05, abs=2 * h)


def test_a_longer_bone_moves_the_muscles_ends_with_it():
    origin, shape, h = grid()
    short = mb.rasterize([[0, 0, -0.08], [0, 0, 0.08]], 0.02, origin, shape, h, np.zeros(shape, bool))
    long = mb.rasterize([[0, 0, -0.15], [0, 0, 0.15]], 0.02, origin, shape, h, np.zeros(shape, bool))
    assert np.ptp(cell_centres(origin, shape, h)[long.ravel(), 2]) > np.ptp(cell_centres(origin, shape, h)[short.ravel(), 2])


def test_the_biotype_scales_the_volume():
    origin, shape, h = grid()
    muscles = [{"name": "a_l", "group": "leg", "points": [[0, 0, -0.1], [0, 0, 0.1]], "radius": 0.03}]
    a, b = mb.solids(muscles, origin, shape, h, 1.0).sum(), mb.solids(muscles, origin, shape, h, 2.0).sum()
    assert b / a == pytest.approx(2.0, rel=0.12)


def test_a_shape_scales_its_own_muscles():
    origin, shape, h = grid()
    muscles = [{"name": "glmax1_l", "group": "leg", "points": [[0.05, 0, -0.1], [0.05, 0, 0.1]], "radius": 0.02}, {"name": "vaslat_l", "group": "leg", "points": [[-0.05, 0, -0.1], [-0.05, 0, 0.1]], "radius": 0.02}]
    base = mb.solids(muscles, origin, shape, h, 1.0)
    grown = mb.solids(muscles, origin, shape, h, 1.0, {"gl": 2.0})
    c = cell_centres(origin, shape, h)
    assert grown.ravel()[c[:, 0] > 0].sum() > base.ravel()[c[:, 0] > 0].sum() and grown.ravel()[c[:, 0] < 0].sum() == base.ravel()[c[:, 0] < 0].sum()


def test_the_faces_muscles_arent_body_volume():
    muscles = [{"name": "zygomaticus_major_L", "group": "face"}, {"name": "vaslat_l", "group": "leg"}, {"name": "pectoralis_major_sternal_L", "group": "trunk"}]
    assert [m["name"] for m in mb.select(muscles)] == ["vaslat_l", "pectoralis_major_sternal_L"]
    assert [m["name"] for m in mb.select(muscles, replaced=("pectoralis_major_sternal",))] == ["vaslat_l"]


def test_what_isnt_muscle_is_fat():
    n = 3
    args = dict(d_bone=np.full(n, 0.05), inside=np.ones(n, bool), in_bone=np.zeros(n, bool), in_chest=np.zeros(n, bool), in_trunk=np.zeros(n, bool), front_of_spine=np.ones(n, bool), chest_bone=np.zeros(n, bool),
                breast=np.zeros(n, bool), h=0.005, s={"abdominal_wall_mm": 0.015, "cavity_bone_gap_mm": 0.005, "pectoral_mm": 0.015}, skin_band_voxels=1)
    d_skin = np.full(n, 0.03)
    t_fat = np.full(n, 0.01)
    lab = body.label_voxels(d_skin, t_fat, np.full(n, 1.0), muscle_mask=np.array([True, False, True]), **args)
    assert lab.tolist() == [body.MUSCLE, body.FAT, body.MUSCLE]
