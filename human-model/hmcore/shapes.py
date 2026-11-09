"""The gluteus's and the breast's shapes, chosen by name: multipliers on the fat and muscle tables of the divided zones, from data/gluteus_shapes.json and data/breast_shapes.json. What is typed per region afterwards still wins (hmcore.character)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def _json(name, data):
    with open(os.path.join(data, name), encoding="utf-8") as fh:
        return json.load(fh)


def gluteus(fat_mm, shape, table):
    """A new fat table for this gluteus shape; a zone without a shape keeps its value. The shape's muscle factor goes to hmcore.muscle_bodies.solids, on the gluteus muscles."""
    s = table[shape]
    fat = dict(fat_mm)
    for zone, key in (("buttocks_upper_side", "width_above"), ("buttocks_lower_side", "width_base"), ("buttocks_upper_center", "projection"), ("buttocks_lower_center", "projection"), ("hips", "side_line")):
        fat[zone] *= s[key]
    return fat


def breast(fat_mm, breast_character, table, cup_ratio=1.0):
    """New fat table, and the skin-stiffness override in the two breast zones if pendentes is set, as (fat, regions, structure changes).
    cup_ratio is the bust minus underbust against the neutral body's, so the cup sets how much the breast holds."""
    s = table[breast_character["shape"]] if breast_character.get("shape") else {"fat": 1.0, "gland_skin_mm": None}
    fat = dict(fat_mm)
    a = breast_character.get("assimetricos", 1.0)
    side = {"L": a if not isinstance(a, dict) else a.get("L", 1.0), "R": a if not isinstance(a, dict) else a.get("R", 1.0)}
    for k in side:
        fat[f"breast_{k}"] *= s["fat"] * cup_ratio * side[k]
    fat["chest"] *= 1 - breast_character.get("espacados", 0.0) * table["adjustments"]["espacados_chest_fat_loss"]
    regions = {}
    if breast_character.get("pendentes"):
        softening = breast_character["pendentes"] * table["adjustments"]["pendentes_skin_softening"]
        regions["skin"] = {z: {"young_factor": 1 - softening} for z in ("breast_L", "breast_R")}
    structure = {} if s["gland_skin_mm"] is None else {"gland_skin_mm": s["gland_skin_mm"]}
    return fat, regions, structure
