import numpy as np
import pytest
from hmcore import layers


def _tube(radius, z0, z1, n=48, rings=21, closed=False):
    """A cylinder around the Z axis, outward, open at both ends unless closed."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    z = np.linspace(z0, z1, rings)
    v = np.array([[radius * np.cos(t), radius * np.sin(t), h] for h in z for t in a])
    f = []
    for r in range(rings - 1):
        for i in range(n):
            p, q = r * n + i, r * n + (i + 1) % n
            f += [(p, q, q + n), (p, q + n, p + n)]
    f = np.array(f)
    if closed:
        v = np.vstack([v, [0, 0, z0], [0, 0, z1]])
        bottom, top = len(v) - 2, len(v) - 1
        f = np.vstack([f, [(bottom, (i + 1) % n, i) for i in range(n)], [(top, (rings - 1) * n + i, (rings - 1) * n + (i + 1) % n) for i in range(n)]])
    return v, f


@pytest.fixture(scope="module")
def limb():
    # A tube of skin 6 cm in radius at x = 0.2, so it's on the +X side, around a closed bone 1.2 cm in radius
    skin, tris = _tube(0.06, 0.0, 0.2)
    bone, bone_tris = _tube(0.012, -0.05, 0.25, closed=True)
    skin[:, 0] += 0.2
    bone[:, 0] += 0.2
    fat = dict(front=15.0, back=15.0, inner=15.0, outer=15.0)
    r = layers.build(skin, tris, bone, bone_tris, 1, -0.01, 0.21, 0.005, fat)
    return skin, bone, fat, r


def test_capped_patch_is_closed(limb):
    skin, _, _, r = limb
    assert len(layers.boundary_loops(r["patch"])) == 2
    assert layers.boundary_loops(r["capped_tris"]) == []


def test_tetrahedra_have_positive_volume_and_fill_the_tube(limb):
    _, _, _, r = limb
    v = r["nodes"][r["tets"]]
    vol = np.einsum("ij,ij->i", np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), v[:, 3] - v[:, 0]) / 6
    assert (vol > 0).all()
    # The skin band adds up to one voxel outside, so the total is a little more than the tube's
    assert np.pi * 0.06 ** 2 * 0.2 < vol.sum() < np.pi * 0.07 ** 2 * 0.2


def test_layers_go_bone_muscle_fat_outward(limb):
    _, _, _, r = limb
    c = r["nodes"][r["tets"]].mean(axis=1)
    radius = np.hypot(c[:, 0] - 0.2, c[:, 1])
    mid = (c[:, 2] > 0.05) & (c[:, 2] < 0.15)
    lab = r["tet_label"]
    assert radius[mid & (lab == layers.BONE)].max() < 0.015
    assert radius[mid & (lab == layers.MUSCLE)].min() > 0.008
    assert radius[mid & (lab == layers.MUSCLE)].max() < 0.06 - 0.010
    assert radius[mid & (lab == layers.FAT)].min() > 0.06 - 0.020


def test_skin_is_tied_exactly(limb):
    skin, _, _, r = limb
    w = r["skin_bary"]
    assert w.min() > -1e-9
    assert w.sum(axis=1) == pytest.approx(np.ones(len(w)))
    back = np.einsum("ik,ikd->id", w, r["nodes"][r["tets"][r["skin_tet"]]])
    assert back == pytest.approx(skin[r["skin_ids"]], abs=1e-9)


def test_measure_reports_the_declared_fat(limb):
    skin, bone, fat, r = limb
    m = layers.measure(r, skin, bone, 1, fat)
    assert m["bone_points_outside_skin"] == 0
    assert m["bone_min_distance_to_skin_mm"] == pytest.approx(48, abs=1)
    for zone in layers.ZONES:
        assert m["fat"][zone]["median_mm"] == pytest.approx(15, abs=3)


def test_zone_weights_add_to_one_and_face_minus_y():
    p = np.array([[0, -1, 0], [0, 1, 0], [-1, 0, 0], [1, 0, 0], [0.6, -0.8, 0]], float)
    w = layers.zone_weights(p, np.zeros(3), np.array([0, 0, 1.0]), 1)
    assert w.sum(axis=1) == pytest.approx(np.ones(5))
    assert w[:4].argmax(axis=1).tolist() == [0, 1, 2, 3]
    assert layers.zone_weights(p[2:3], np.zeros(3), np.array([0, 0, 1.0]), -1).argmax() == 3


def test_ply_header(tmp_path):
    layers.write_ply(tmp_path / "a.ply", np.zeros((3, 3)), np.array([[0, 1, 2]]))
    data = (tmp_path / "a.ply").read_bytes()
    assert data.startswith(b"ply\n") and b"element face 1" in data
    assert len(data.split(b"end_header\n")[1]) == 3 * 12 + 13
