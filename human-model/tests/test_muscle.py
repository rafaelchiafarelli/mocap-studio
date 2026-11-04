import math
import numpy as np
import pytest
from hmcore import muscle


def test_stretch_keeps_volume():
    L, r = 0.1, 0.01
    v0 = muscle.spindle_volume(L, r)
    for s in (0.7, 1.0, 1.3):
        l2, r2 = muscle.stretched(L, r, s)
        assert muscle.spindle_volume(l2, r2) == pytest.approx(v0)


def test_radius_for_volume_inverts():
    r = muscle.radius_for_volume(0.2, 5e-5)
    assert muscle.spindle_volume(0.2, r) == pytest.approx(5e-5)


def test_profile_thin_at_tendons_thick_at_belly():
    assert muscle.spindle_profile(0.0) < 0.2 and muscle.spindle_profile(0.5) == pytest.approx(1.0)


def test_mesh_volume_of_a_spindle_is_close_to_the_integral():
    v, f = muscle.segment_mesh([0, 0, 0], [0, 0, 0.2], 0.02, 0.02, rings=24, sides=24)
    assert abs(muscle.mesh_volume(v, f)) == pytest.approx(muscle.spindle_volume(0.2, 0.02), rel=0.05)


def test_right_side_mirrors_offsets():
    ind = {"skin": np.array([[0.0, 0, 2.0], [0.08, 0, 2.0], [-0.08, 0, 2.0]]), "rig": {"spine.006": {"head": [0, 0, 1.0], "tail": [0, 0, 1.1]}, "x.L": {"head": [0.1, 0, 2], "tail": [0.1, 0, 2.1]}, "x.R": {"head": [-0.1, 0, 2], "tail": [-0.1, 0, 2.1]}}}
    res = muscle.Resolver(ind, {})
    lm = {"rig": "x.{s}", "t": 0.0, "off": [0.01, 0, 0]}
    assert res.point(lm, "L", False)[0] == pytest.approx(0.11)
    assert res.point(lm, "R", False)[0] == pytest.approx(-0.11)
