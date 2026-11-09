import numpy as np
import pytest
from hmcore import body, regions


CFG = {"MUSCLE_YOUNG": 15000.0, "FAT_YOUNG": 4000.0, "SKIN_YOUNG": 100000.0, "CAVITY_YOUNG": 3000.0, "MUSCLE_DENSITY": 900.0, "FAT_DENSITY": 750.0, "SKIN_DENSITY": 1100.0, "CAVITY_DENSITY": 1000.0, "POISSON": 0.45, "DAMPING": 20.0}
LABELS = ("bone", "muscle", "fat", "skin", "cavity")
ZONES = ("a", "b")


def table():
    return regions.defaults(CFG, LABELS)


def line():
    # a row of 10 voxels, six tetrahedra each, fat throughout; zone a in the first five, b in the rest
    n = 10
    vox = np.column_stack([np.arange(n), np.zeros(n, int), np.zeros(n, int)])
    voxel_of_tet = np.repeat(np.arange(n), 6)
    label = np.full(n * 6, 2)
    zone = np.repeat(np.r_[np.zeros(5, int), np.ones(5, int)], 6)
    return label, zone, voxel_of_tet, vox


def test_no_overrides_gives_todays_values():
    label = np.array([0, 1, 2, 3, 4])
    v = regions.per_tet(label, np.zeros(5, int), np.arange(5), np.column_stack([np.arange(5), np.zeros((5, 2), int)]), table(), {}, LABELS, ZONES)
    assert v["young"].tolist() == [15000, 15000, 4000, 100000, 3000] and v["density"].tolist() == [900, 900, 750, 1100, 1000]
    assert (v["poisson"] == 0.45).all() and (v["damping"] == 20.0).all()


def test_an_override_applies_to_one_tissue_and_zone():
    label, zone, voxel, vox = line()
    v = regions.per_tet(label, zone, voxel, vox, table(), {"fat": {"b": {"damping": 40.0}}}, LABELS, ZONES)
    assert v["damping"][voxel == 9] == pytest.approx(40.0) and v["damping"][voxel == 0] == pytest.approx(20.0)
    assert (v["young"] == 4000).all()


def test_an_override_fades_in_at_the_zones_border():
    label, zone, voxel, vox = line()
    v = regions.per_tet(label, zone, voxel, vox, table(), {"fat": {"b": {"damping": 40.0}}}, LABELS, ZONES)["damping"]
    per_voxel = v[::6]
    assert per_voxel[3] == pytest.approx(20.0)
    assert 20.0 < per_voxel[4] < per_voxel[5] < 40.0 and per_voxel[6] == pytest.approx(40.0)


def test_node_values_average_their_tetrahedra():
    tets = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    assert regions.node_values(tets, np.array([10.0, 20.0]), 5).tolist() == [10.0, 15.0, 15.0, 15.0, 20.0]


def test_an_override_reaches_its_full_value_in_a_thin_layer():
    # a slab one voxel thick, 8 x 8: the box average would leave a third of the override without the tissue's own weight
    ij = np.array([[i, j, 3] for i in range(8) for j in range(8)])
    voxel = np.repeat(np.arange(len(ij)), 6)
    label = np.full(len(voxel), 2)
    zone = np.zeros(len(voxel), int)
    v = regions.per_tet(label, zone, voxel, ij, table(), {"fat": {"a": {"damping": 40.0}}}, LABELS, ZONES)["damping"]
    assert v == pytest.approx(40.0)
