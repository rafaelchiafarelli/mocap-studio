import os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hmcore import bone_targets as bt, character as ch

BASE = ch.base_measures("female")


def sheet(**c):
    return ch.resolve({"sex": "female", **c})


def test_the_neutral_body_reproduces_its_own_proportions():
    t = bt.targets(sheet(), base_cm=BASE)
    p = bt.proportions("female")
    assert t["biacromial_m"] == pytest.approx(BASE["shoulder_width"] / 100 * p["biacromial_over_tape"], abs=1e-4)
    assert t["thigh_m"] / (t["thigh_m"] + t["shin_m"]) == pytest.approx(p["thigh_share_of_leg"], abs=1e-3)
    assert t["thickness"] == {r: 1.0 for r in bt.THICKNESS_REGIONS}


def test_a_blank_parameter_is_a_proportion_of_the_height_and_says_so():
    t = bt.targets(sheet(height_cm=176), base_cm=BASE)
    assert t["provenance"]["pelvis_width_m"] == "proportion" and t["pelvis_width_m"] == pytest.approx(1.76 * bt.proportions("female")["pelvis_share_of_height"])


def test_a_typed_parameter_wins_and_says_so():
    t = bt.targets(sheet(), {"pelvis_width_cm": 27, "thigh_share_of_leg": 0.55, "humerus_share_of_arm": 0.5}, base_cm=BASE)
    assert t["pelvis_width_m"] == 0.27 and t["provenance"]["pelvis_width_m"] == "parameter"
    assert t["thigh_m"] / (t["thigh_m"] + t["shin_m"]) == pytest.approx(0.55, abs=1e-3) and t["humerus_m"] == pytest.approx(t["forearm_m"], abs=1e-3)


def test_body_fat_alone_doesnt_change_any_bone():
    a, b = bt.targets(sheet(body_fat_percent=20), base_cm=BASE), bt.targets(sheet(body_fat_percent=40), base_cm=BASE)
    assert {k: v for k, v in a.items() if k != "provenance"} == {k: v for k, v in b.items() if k != "provenance"}


def test_waist_and_hip_dont_change_any_bone():
    a, b = bt.targets(sheet(distances={"cintura": 60, "quadril": 90}), base_cm=BASE), bt.targets(sheet(distances={"cintura": 90, "quadril": 120}), base_cm=BASE)
    assert {k: v for k, v in a.items() if k != "provenance"} == {k: v for k, v in b.items() if k != "provenance"}


def test_a_typed_wrist_thickens_the_forearm_only():
    t = bt.targets(sheet(distances={"punho": BASE["wrist"] * 1.2}), base_cm=BASE)
    assert t["thickness"]["forearm"] == pytest.approx(1.2) and t["thickness"]["humerus"] == 1.0


def test_the_biotype_scales_thickness():
    assert bt.targets(sheet(biotype={"type": "endomorph"}), base_cm=BASE)["thickness"]["femur"] == pytest.approx(1.1)


def test_the_spine_follows_the_rigs_line():
    import numpy as np
    from hmcore import skeleton
    rig = {"spine": {"head": [0, 0.02, 1.0], "tail": [0, 0.03, 1.1]}, "spine.001": {"head": [0, 0.04, 1.2], "tail": [0, 0.05, 1.3]}}
    ind = {"rig": rig}
    assert skeleton.spine_line_y(ind, 1.0) == pytest.approx(0.02) and skeleton.spine_line_y(ind, 1.1) == pytest.approx(0.03)


def test_the_trunks_scales_come_from_the_targets():
    import numpy as np
    from hmcore import skeleton
    ribs = np.array([[-0.1, 0.0, 0], [0.1, 0.1, 0]])
    pelvis = np.array([[-0.13, 0, 0], [0.13, 0, 0]])
    s = skeleton.trunk_scales(ribs, np.zeros((1, 3)), pelvis, {"ribcage_width_m": 0.3, "ribcage_depth_m": 0.15, "pelvis_width_m": 0.26})
    assert s == {"sx": pytest.approx(1.5), "sy": pytest.approx(1.5), "s_p": pytest.approx(1.0)}


def test_the_sacrum_meets_l5():
    import numpy as np
    from hmcore import skeleton
    sacrum = np.array([[0, 0.05, 1.0], [0, 0.02, 1.0], [0, 0.08, 1.2], [0, 0.07, 1.25]])
    assert skeleton.pelvis_forward(sacrum, 0.02, gap=0.003) == pytest.approx(0.08 - 0.02 - 0.003)
