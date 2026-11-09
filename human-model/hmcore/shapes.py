"""The gluteus's and the breast's shapes, chosen by name: multipliers on the fat and muscle tables of the divided zones, from data/gluteus_shapes.json, and the breast as a volume over the chest, from data/breast_shapes.json. What is typed per region afterwards still wins (hmcore.character)."""
import json, os
import numpy as np

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


def breast_regions(breast_character, table):
    """The skin's stiffness over the breast, softened if pendentes is set, as hmcore.regions overrides."""
    if not breast_character.get("pendentes"):
        return {}
    softening = breast_character["pendentes"] * table["adjustments"]["pendentes_skin_softening"]
    return {"skin": {z: {"young_factor": 1 - softening} for z in ("breast_L", "breast_R")}}


def wall_y(inner, origin, h, x, z):
    """The chest's front at this x and z: the first cell of what's inside, coming from the front (the body faces -Y). None if the column is empty."""
    i, k = int((x - origin[0]) / h), int((z - origin[2]) / h)
    column = np.flatnonzero(inner[i, :, k])
    return float(origin[1] + column[0] * h) if len(column) else None


def breast_volume(apex, side, inner, origin, shape, h, difference_cm, neutral_difference_cm, breast_character, table):
    """One breast as a mask: a volume over the chest at this apex's height, its projection from bust minus underbust and its outline from the shape. side is +1 for the left (+X), -1 for the right."""
    s = table[breast_character.get("shape") or "redondos"]
    a = table["adjustments"]
    asym = breast_character.get("assimetricos", 1.0)
    factor = (asym if not isinstance(asym, dict) else asym.get("L" if side > 0 else "R", 1.0))
    cx = float(apex[0]) + side * breast_character.get("espacados", 0.0) * a["espacados_m"]
    cz = float(apex[2]) - breast_character.get("pendentes", 0.0) * a["pendentes_m"]
    wall = wall_y(inner, origin, h, cx, cz)
    mask = np.zeros(shape, bool)
    if wall is None or difference_cm <= 0:
        return mask
    project = difference_cm * a["projection_per_cm"] / 100 * factor
    radius = s["base_cm"] / 100 * (max(difference_cm, 1.0) / neutral_difference_cm) ** (1 / 3) * factor ** (1 / 3)
    reach = radius * max(s["upper"], s["lower"])
    lo = np.maximum(np.floor((np.array([cx - radius, wall - project, cz - reach]) - origin) / h).astype(int) - 1, 0)
    hi = np.minimum(np.ceil((np.array([cx + radius, wall, cz + reach]) - origin) / h).astype(int) + 2, shape)
    if (hi <= lo).any():
        return mask
    idx = np.indices(hi - lo).reshape(3, -1).T + lo
    c = origin + (idx + 0.5) * h
    front = wall - c[:, 1]
    ex = (c[:, 0] - cx) / radius
    dz = c[:, 2] - cz
    ez = dz / (radius * np.where(dz >= 0, s["upper"], s["lower"]))
    inside = (front >= 0) & (ex ** 2 + ez ** 2 + (np.maximum(front, 0.0) / project) ** s["power"] <= 1.0)
    mask[tuple(idx[inside].T)] = True
    return mask
