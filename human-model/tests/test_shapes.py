import json, os, sys
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


@pytest.mark.parametrize("shape", ["redondos", "gota", "conicos", "tuberosos"])
def test_every_breast_shape_is_in_the_file(shape):
    assert set(BREAST[shape]) == {"fat", "gland_skin_mm"}


def test_the_shape_sets_the_fat_and_the_gland():
    fat, regions, structure = shapes.breast(ZONES, {"shape": "conicos"}, BREAST)
    assert fat["breast_L"] == pytest.approx(10 * 0.95) and structure == {"gland_skin_mm": 10} and regions == {}


def test_the_cup_scales_the_breast():
    fat, _, _ = shapes.breast(ZONES, {"shape": "redondos"}, BREAST, cup_ratio=1.5)
    assert fat["breast_R"] == pytest.approx(10 * 1.05 * 1.5)


def test_asymmetry_is_per_side():
    fat, _, _ = shapes.breast(ZONES, {"shape": "gota", "assimetricos": {"L": 1.0, "R": 0.8}}, BREAST)
    assert fat["breast_L"] == pytest.approx(10.0) and fat["breast_R"] == pytest.approx(8.0)
    fat2, _, _ = shapes.breast(ZONES, {"shape": "gota", "assimetricos": 0.9}, BREAST)
    assert fat2["breast_L"] == pytest.approx(9.0) == fat2["breast_R"]


def test_spacing_thins_the_chest_between_the_breasts():
    fat, _, _ = shapes.breast(ZONES, {"shape": "gota", "espacados": 1.0}, BREAST)
    assert fat["chest"] == pytest.approx(5.0)


def test_pendentes_softens_the_skin():
    _, regions, _ = shapes.breast(ZONES, {"shape": "gota", "pendentes": 1.0}, BREAST)
    assert regions["skin"]["breast_L"]["young_factor"] == pytest.approx(0.5)


def test_no_shape_changes_nothing():
    fat, regions, structure = shapes.breast(ZONES, {}, BREAST)
    assert fat == ZONES and regions == {} and structure == {}
