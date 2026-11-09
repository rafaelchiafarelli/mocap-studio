import json, os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hmcore import body, shapes

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
ZONES = {z: 10.0 for z in body.ZONES}


def table(name):
    return json.load(open(os.path.join(DATA, name)))


@pytest.mark.parametrize("shape", ["quadrado", "redondo", "coracao", "em_v"])
def test_every_gluteus_shape_is_in_the_file(shape):
    assert set(table("gluteus_shapes.json")[shape]) == {"width_above", "width_base", "projection", "side_line", "muscle"}


def test_coracao_is_narrow_above_and_full_at_the_base():
    t = table("gluteus_shapes.json")
    fat = shapes.gluteus(ZONES, "coracao", t)
    assert fat["buttocks_upper_side"] < 10 < fat["buttocks_lower_side"]


def test_em_v_is_the_opposite():
    fat = shapes.gluteus(ZONES, "em_v", table("gluteus_shapes.json"))
    assert fat["buttocks_upper_side"] > 10 > fat["buttocks_lower_side"]


def test_only_the_gluteus_zones_change():
    fat = shapes.gluteus(ZONES, "redondo", table("gluteus_shapes.json"))
    assert fat["belly"] == 10.0 and fat["buttocks_lower_center"] > 10.0


BREAST = table("breast_shapes.json")
H, SHAPE = 0.004, (80, 80, 80)
ORIGIN = np.array([-0.16, -0.16, -0.16])


def wall():
    idx = np.indices(SHAPE).reshape(3, -1).T
    y = ORIGIN[1] + (idx[:, 1] + 0.5) * H
    return (y >= 0).reshape(SHAPE)


def volume(difference=16.0, character=None, side=1, apex=(0.0, 0.0, 0.0)):
    return shapes.breast_volume(np.array(apex), side, wall(), ORIGIN, SHAPE, H, difference, 16.0, character or {}, BREAST)


def extent(mask, axis):
    idx = np.argwhere(mask)
    return (idx[:, axis].max() - idx[:, axis].min() + 1) * H


def centre(mask, axis):
    return float(ORIGIN[axis] + (np.argwhere(mask)[:, axis].mean() + 0.5) * H)


@pytest.mark.parametrize("name", ["redondos", "gota", "conicos", "tuberosos"])
def test_every_breast_shape_is_in_the_file(name):
    assert set(BREAST[name]) == {"base_cm", "upper", "lower", "power"}


def test_the_breast_stands_out_from_the_chest_by_the_cup():
    m = volume(16.0)
    assert extent(m, 1) == pytest.approx(0.056, abs=2 * H) and not m[:, 40:, :].any()  # in front of the wall only
    assert extent(volume(24.0), 1) > extent(m, 1) and volume(24.0).sum() > m.sum()


def test_gota_reaches_higher_than_it_hangs():
    m = volume(character={"shape": "gota"})
    idx = np.argwhere(m)
    z = ORIGIN[2] + (idx[:, 2] + 0.5) * H
    assert z.max() > -z.min()


def test_espacados_moves_it_outward_on_each_side():
    assert centre(volume(character={"espacados": 1.0}), 0) == pytest.approx(BREAST["adjustments"]["espacados_m"], abs=2 * H)
    assert centre(volume(character={"espacados": 1.0}, side=-1), 0) == pytest.approx(-BREAST["adjustments"]["espacados_m"], abs=2 * H)


def test_pendentes_lowers_it():
    assert centre(volume(character={"pendentes": 1.0}), 2) < centre(volume(), 2) - 0.02


def test_asymmetry_is_per_side():
    wish = {"assimetricos": {"L": 1.0, "R": 0.7}}
    assert volume(character=wish, side=-1).sum() < volume(character=wish, side=1).sum()


def test_pendentes_softens_the_skin():
    assert shapes.breast_regions({"pendentes": 1.0}, BREAST)["skin"]["breast_L"]["young_factor"] == pytest.approx(0.5)
    assert shapes.breast_regions({}, BREAST) == {}
