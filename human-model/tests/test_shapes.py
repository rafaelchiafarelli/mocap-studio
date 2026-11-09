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
    fat, _ = shapes.gluteus(ZONES, ZONES, "coracao", t)
    assert fat["buttocks_upper_side"] < 10 < fat["buttocks_lower_side"]


def test_em_v_is_the_opposite():
    fat, _ = shapes.gluteus(ZONES, ZONES, "em_v", table("gluteus_shapes.json"))
    assert fat["buttocks_upper_side"] > 10 > fat["buttocks_lower_side"]


def test_only_the_gluteus_zones_change():
    fat, muscle = shapes.gluteus(ZONES, ZONES, "redondo", table("gluteus_shapes.json"))
    assert fat["belly"] == 10.0 and muscle["belly"] == 10.0 and muscle["buttocks_upper_center"] > 10.0
