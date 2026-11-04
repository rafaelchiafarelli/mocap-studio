import math
import numpy as np
import pytest
from hmcore import jaw, joints

CONDYLE = np.array([0.05, -0.02, 1.58])
INCISOR = np.array([0.0, -0.10, 1.52])


def test_reaches_the_published_opening_and_slide():
    t = jaw.table(CONDYLE, INCISOR)
    th, sl = jaw.pose(1.0, t)
    assert jaw.drop(th, sl, CONDYLE, INCISOR) == pytest.approx(jaw.MAX_INCISOR_M, abs=1e-4)
    assert sl == pytest.approx(jaw.MAX_CONDYLE_M)


def test_hinge_first_then_slide():
    t = jaw.table(CONDYLE, INCISOR)
    assert jaw.pose(t["break_o"] * 0.9, t)[1] == 0.0
    assert jaw.pose(t["break_o"] * 1.1, t)[1] > 0.0


def test_rotation_is_lower_than_the_proof_of_concept():
    t = jaw.table(CONDYLE, INCISOR)
    assert math.degrees(t["final_rad"]) < 30  # the rotation-only proof of concept needed 38


def test_incisor_goes_down_on_opening():
    t = jaw.table(CONDYLE, INCISOR)
    end = jaw.incisor_position(*jaw.pose(1.0, t), CONDYLE, INCISOR)
    assert end[2] < INCISOR[2] - 0.03


def test_limits_use_sex_values():
    assert joints.limits("female")["shin"][1] == 141.9
    assert joints.limits("male")["thigh"][0] == -130.4
    assert joints.elbow_limits("male") == (-0.8, 144.6)


def test_rib_rule_goes_from_pump_to_bucket():
    assert joints.rib_rule(1)[0] == 0.0 and joints.rib_rule(10)[0] == 1.0
