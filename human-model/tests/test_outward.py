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
