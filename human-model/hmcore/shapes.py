"""The gluteus's and the breast's shapes, chosen by name: multipliers on the fat and muscle tables of the divided zones, from data/gluteus_shapes.json and data/breast_shapes.json. What is typed per region afterwards still wins (hmcore.character)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def _json(name, data):
    with open(os.path.join(data, name), encoding="utf-8") as fh:
        return json.load(fh)


def gluteus(fat_mm, muscle_mm, shape, table):
    """New fat and muscle tables for this gluteus shape; a zone without a shape keeps its value."""
    s = table[shape]
    fat, muscle = dict(fat_mm), dict(muscle_mm)
    for zone, key in (("buttocks_upper_side", "width_above"), ("buttocks_lower_side", "width_base"), ("buttocks_upper_center", "projection"), ("buttocks_lower_center", "projection"), ("hips", "side_line")):
        fat[zone] *= s[key]
    for zone in ("buttocks_upper_center", "buttocks_upper_side", "buttocks_lower_center", "buttocks_lower_side"):
        muscle[zone] *= s["muscle"]
    return fat, muscle
